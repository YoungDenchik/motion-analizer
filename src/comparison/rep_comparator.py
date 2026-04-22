"""
Repetition-aware comparison: rep-count-independent technique scoring.

The problem with full-sequence DTW
───────────────────────────────────
If the reference is 1 squat (60 frames) and the user performs 3 squats
(180 frames), DTW warps the sequences to find the cheapest alignment.
That alignment is pathological — it maps the entire 3-rep user sequence
against a single reference rep, producing meaningless per-frame deviations
and a score that reflects "how many reps" rather than "how good the form is".

Solution
────────
1. Segment both sequences into individual reps (RepSegmenter).
2. Derive a single canonical reference rep:
   • If the reference has 1 rep  → use it directly.
   • If the reference has N reps → average them (smoother template).
3. For each user rep:
   a. Resample it to the same length as the canonical reference rep.
      (DTW still handles minor length differences, but resampling first
       prevents extreme warping paths that skip whole movement phases.)
   b. Run DTW against the canonical reference.
   c. Produce a per-rep DTWResult + ScoreReport.
4. Aggregate scores across all user reps (mean ± std).
5. Concatenate per-frame deviations in temporal order so the video
   renderer gets a frame-accurate deviation array.

Why resample before DTW?
  DTW's Sakoe-Chiba band (radius parameter) assumes the two sequences
  are roughly the same length. If a user rep is 40 frames but the
  reference is 80, only diagonal paths within ±radius are allowed,
  forcing every user frame to match a reference frame ≥2 frames away.
  Resampling to the reference length first centers the band correctly.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

from ..timeseries.builder import TimeSeries
from ..timeseries.segmentation import RepSegmenter, SegmentationResult
from .dtw import DTWComparator, DTWResult


@dataclass
class RepResult:
    """DTW comparison result for a single repetition."""
    rep_index: int                  # 0-based
    dtw_result: DTWResult
    score: float                    # 0-100 for this rep
    rep_frames: int                 # length of this user rep (after resampling)


@dataclass
class RepComparisonResult:
    """
    Aggregated comparison of all user reps against the reference.

    Exposes the same interface expected by ScoringEngine and ErrorClassifier
    (via the `combined_dtw` property) while also providing per-rep detail.
    """
    rep_results: List[RepResult]
    reference_rep: TimeSeries           # canonical reference (1 rep)
    user_segmentation: SegmentationResult
    reference_segmentation: SegmentationResult

    # Concatenated across reps in temporal order — used by the renderer
    # Shape: (total_user_frames, F)
    per_frame_deviations: np.ndarray
    per_frame_scores: np.ndarray        # (total_user_frames,)

    @property
    def num_user_reps(self) -> int:
        return len(self.rep_results)

    @property
    def num_reference_reps(self) -> int:
        return len(self.reference_segmentation.reps)

    @property
    def overall_score(self) -> float:
        if not self.rep_results:
            return 0.0
        return float(np.mean([r.score for r in self.rep_results]))

    @property
    def per_rep_scores(self) -> List[float]:
        return [r.score for r in self.rep_results]

    @property
    def score_std(self) -> float:
        """Consistency score: std dev of per-rep scores. Lower = more consistent."""
        if len(self.rep_results) < 2:
            return 0.0
        return float(np.std([r.score for r in self.rep_results]))

    @property
    def worst_rep_index(self) -> int:
        return int(np.argmin([r.score for r in self.rep_results]))

    @property
    def best_rep_index(self) -> int:
        return int(np.argmax([r.score for r in self.rep_results]))

    @property
    def combined_dtw(self) -> DTWResult:
        """
        Synthesize a single DTWResult by concatenating all per-rep results.

        This allows the existing ScoringEngine and ErrorClassifier to operate
        on the aggregated data without changes.
        """
        if not self.rep_results:
            raise ValueError("No rep results to combine.")

        # Merge per-frame deviations and distances
        all_devs = self.per_frame_deviations
        all_dists = np.mean(np.abs(all_devs), axis=1)

        total_distance = float(np.mean([r.dtw_result.distance for r in self.rep_results]))
        total_path_len = sum(len(r.dtw_result.path) for r in self.rep_results)

        # Build a synthetic path: identity mapping (each frame maps to itself)
        T = all_devs.shape[0]
        synthetic_path = [(i, i) for i in range(T)]

        return DTWResult(
            distance=total_distance,
            path=synthetic_path,
            per_frame_deviations=all_devs,
            per_frame_distances=all_dists,
            query_length=T,
            reference_length=self.reference_rep.num_frames,
            feature_names=self.reference_rep.feature_names,
        )


class RepComparator:
    """
    Rep-count-independent technique comparator.

    Segments both sequences, builds a canonical reference rep, then runs
    DTW on each user rep individually. Works correctly when the user
    performs any number of reps (1, 2, 10, …) regardless of how many
    reps the reference contains.
    """

    def __init__(
        self,
        segmenter: Optional[RepSegmenter] = None,
        dtw_comparator: Optional[DTWComparator] = None,
        scoring_sensitivity: float = 0.05,
    ):
        self.segmenter = segmenter or RepSegmenter()
        self.dtw = dtw_comparator or DTWComparator()
        self.sensitivity = scoring_sensitivity

    def compare(
        self,
        user_ts: TimeSeries,
        reference_ts: TimeSeries,
    ) -> RepComparisonResult:
        """
        Compare user sequence against reference, agnostic to rep count.

        Args:
            user_ts: Full user session time series (any number of reps).
            reference_ts: Full reference time series (usually 1 rep, may be more).

        Returns:
            RepComparisonResult with per-rep breakdown and aggregate metrics.
        """
        # ── Step 1: Segment both sequences ───────────────────────────────────
        user_seg = self.segmenter.segment(user_ts)
        ref_seg = self.segmenter.segment(reference_ts)

        print(f"[RepComparator] User reps detected:      {len(user_seg.reps)} "
              f"(indicator: {user_seg.indicator_feature})")
        print(f"[RepComparator] Reference reps detected: {len(ref_seg.reps)} "
              f"(indicator: {ref_seg.indicator_feature})")

        # ── Step 2: Build canonical reference rep ─────────────────────────────
        ref_rep = self._build_canonical_rep(ref_seg.reps)
        print(f"[RepComparator] Canonical reference rep: {ref_rep.num_frames} frames")

        # ── Step 3: Compare each user rep against the reference rep ──────────
        rep_results: List[RepResult] = []
        all_deviations: List[np.ndarray] = []
        all_scores: List[np.ndarray] = []

        for i, user_rep in enumerate(user_seg.reps):
            # Resample user rep to reference rep length before DTW
            resampled = user_rep.resample(ref_rep.num_frames)
            dtw_result = self.dtw.compare(resampled, ref_rep)
            rep_score = self._dtw_to_score(dtw_result)

            rep_results.append(RepResult(
                rep_index=i,
                dtw_result=dtw_result,
                score=rep_score,
                rep_frames=user_rep.num_frames,
            ))

            # Map DTW deviations back to original (un-resampled) user rep length
            # by resampling the deviation array itself
            devs_resampled = dtw_result.per_frame_deviations  # (ref_len, F)
            devs_original = self._resample_deviations(devs_resampled, user_rep.num_frames)
            all_deviations.append(devs_original)

            # Per-frame scores for this rep
            abs_devs = np.abs(devs_original).mean(axis=1)
            frame_scores = 100.0 * np.exp(-self.sensitivity * abs_devs)
            all_scores.append(frame_scores)

            print(f"[RepComparator] Rep {i + 1}: score={rep_score:.1f}, "
                  f"frames={user_rep.num_frames}, DTW={dtw_result.distance:.1f}")

        # ── Step 4: Concatenate across reps ──────────────────────────────────
        if all_deviations:
            concat_devs = np.concatenate(all_deviations, axis=0).astype(np.float32)
            concat_scores = np.concatenate(all_scores, axis=0).astype(np.float32)
        else:
            F = reference_ts.num_features
            concat_devs = np.zeros((user_ts.num_frames, F), dtype=np.float32)
            concat_scores = np.full(user_ts.num_frames, 50.0, dtype=np.float32)

        return RepComparisonResult(
            rep_results=rep_results,
            reference_rep=ref_rep,
            user_segmentation=user_seg,
            reference_segmentation=ref_seg,
            per_frame_deviations=concat_devs,
            per_frame_scores=concat_scores,
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _build_canonical_rep(reps: List[TimeSeries]) -> TimeSeries:
        """
        Build a single canonical reference rep from one or more ref reps.

        • 1 rep  → use directly (no change).
        • N reps → resample all to median length, then average frame-by-frame.
                   Averaging smooths out any idiosyncrasies in individual reps
                   and produces a more robust template.
        """
        if len(reps) == 1:
            return reps[0]

        lengths = [r.num_frames for r in reps]
        target_len = int(np.median(lengths))

        resampled = [r.resample(target_len) for r in reps]
        averaged_data = np.mean(
            np.stack([r.data for r in resampled], axis=0),
            axis=0,
        ).astype(np.float32)

        return TimeSeries(
            data=averaged_data,
            feature_names=reps[0].feature_names,
            fps=reps[0].fps,
        )

    def _dtw_to_score(self, dtw_result: DTWResult) -> float:
        """Convert a DTWResult's normalized distance to a 0–100 score."""
        abs_devs = np.abs(dtw_result.per_frame_deviations).mean(axis=1)
        frame_scores = 100.0 * np.exp(-self.sensitivity * abs_devs)
        return float(np.mean(frame_scores))

    @staticmethod
    def _resample_deviations(devs: np.ndarray, target_len: int) -> np.ndarray:
        """
        Resample a (T, F) deviation array to (target_len, F) using linear
        interpolation. Used to map DTW deviations back to the original
        (un-resampled) frame count for correct video overlay alignment.
        """
        if devs.shape[0] == target_len:
            return devs
        from scipy.interpolate import interp1d
        T = devs.shape[0]
        t_orig = np.linspace(0, 1, T)
        t_new = np.linspace(0, 1, target_len)
        interpolator = interp1d(t_orig, devs, axis=0, kind="linear",
                                fill_value="extrapolate")
        return interpolator(t_new).astype(np.float32)
