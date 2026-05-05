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
   • If the reference has N reps → average them (smoother template) and
     compute per-frame std deviation across those reps as a tolerance band.
3. For each user rep:
   a. Run DTW against the canonical reference.
   b. Map the reference tolerance onto user frames via the DTW path.
   c. Apply the tolerance: effective_dev = max(0, |raw_dev| − tolerance).
      Deviations that fall within the natural reference variation are
      treated as zero — the user is moving within the acceptable range.
   d. Score using the tolerance-adjusted deviations.
4. Aggregate scores across all user reps (mean ± std).
5. Concatenate per-frame (tolerance-adjusted) deviations in temporal order
   so the video renderer gets a frame-accurate deviation array.

Reference tolerance
───────────────────
When the reference contains N > 1 reps they are resampled to the same
length and stacked. The std deviation across reps gives a per-frame,
per-feature tolerance — the natural spread of the reference motion itself.
A user deviation within that spread is considered correct form.

With a single reference rep the tolerance is zero everywhere (no spread
information available), so every deviation is counted in full.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np

from ..timeseries.builder import TimeSeries
from ..timeseries.segmentation import RepSegmenter, SegmentationResult
from .dtw import DTWComparator, DTWResult


@dataclass
class RepResult:
    """DTW comparison result for a single repetition."""
    rep_index: int                  # 0-based
    dtw_result: DTWResult           # raw DTW (unclipped deviations, for diagnostics)
    score: float                    # 0-100 for this rep (tolerance-adjusted)
    rep_frames: int                 # length of this user rep


@dataclass
class RepComparisonResult:
    """
    Aggregated comparison of all user reps against the reference.

    Exposes the same interface expected by ScoringEngine and ErrorClassifier
    (via the `combined_dtw` property) while also providing per-rep detail.
    """
    rep_results: List[RepResult]
    reference_rep: TimeSeries            # canonical reference (averaged, 1 rep)
    reference_tolerance: np.ndarray      # (T_ref, F) — per-frame std across ref reps
    user_segmentation: SegmentationResult
    reference_segmentation: SegmentationResult

    # Tolerance-adjusted, concatenated across reps in temporal order
    # Shape: (total_user_frames, F)
    per_frame_deviations: np.ndarray
    per_frame_scores: np.ndarray         # (total_user_frames,)

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

        Uses the already tolerance-adjusted `per_frame_deviations`, so
        ScoringEngine and ErrorClassifier operate on the same values as the
        per-rep scores without any changes.
        """
        if not self.rep_results:
            raise ValueError("No rep results to combine.")

        all_devs = self.per_frame_deviations
        all_dists = np.mean(np.abs(all_devs), axis=1)

        total_distance = float(np.mean([r.dtw_result.distance for r in self.rep_results]))

        # Synthetic path: identity mapping so downstream consumers can iterate it
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

    Segments both sequences, builds a canonical reference rep (with a
    per-frame tolerance derived from inter-rep variation), then runs DTW
    on each user rep individually. Deviations within the reference tolerance
    are not penalised.
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

        # ── Step 2: Build canonical reference rep + tolerance band ────────────
        ref_rep, ref_tolerance = self._build_canonical_rep(ref_seg.reps)
        mean_tol = float(ref_tolerance.mean())
        print(f"[RepComparator] Canonical reference rep: {ref_rep.num_frames} frames  "
              f"| tolerance mean={mean_tol:.1f} deg "
              f"(from {len(ref_seg.reps)} ref rep(s))")

        # ── Step 3: Compare each user rep against the reference rep ──────────
        rep_results: List[RepResult] = []
        all_deviations: List[np.ndarray] = []
        all_scores: List[np.ndarray] = []

        for i, user_rep in enumerate(user_seg.reps):
            dtw_result = self.dtw.compare(user_rep, ref_rep)

            # Apply reference tolerance: clip deviations that fall within the
            # natural spread of the reference reps — these are "correct" form.
            effective_devs = self._apply_tolerance(
                dtw_result.per_frame_deviations,
                dtw_result.path,
                ref_tolerance,
            )

            rep_score = self._devs_to_score(effective_devs)

            rep_results.append(RepResult(
                rep_index=i,
                dtw_result=dtw_result,   # raw result preserved for diagnostics
                score=rep_score,
                rep_frames=user_rep.num_frames,
            ))

            all_deviations.append(effective_devs)

            abs_devs = np.abs(effective_devs).mean(axis=1)
            frame_scores = 100.0 * np.exp(-self.sensitivity * abs_devs)
            all_scores.append(frame_scores)

            length_ratio = user_rep.num_frames / max(ref_rep.num_frames, 1)
            print(f"[RepComparator] Rep {i + 1}: score={rep_score:.1f}, "
                  f"frames={user_rep.num_frames} (ratio {length_ratio:.2f}x ref), "
                  f"DTW={dtw_result.distance:.1f}")

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
            reference_tolerance=ref_tolerance,
            user_segmentation=user_seg,
            reference_segmentation=ref_seg,
            per_frame_deviations=concat_devs,
            per_frame_scores=concat_scores,
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _build_canonical_rep(
        reps: List[TimeSeries],
    ) -> Tuple[TimeSeries, np.ndarray]:
        """
        Build a single canonical reference rep and its per-frame tolerance.

        Returns:
            (canonical_rep, tolerance)
            tolerance shape: (T_ref, F) — per-frame, per-feature std deviation
            across all reference reps. Zero everywhere when only 1 rep exists.
        """
        T, F = reps[0].num_frames, reps[0].num_features

        if len(reps) == 1:
            tolerance = np.zeros((T, F), dtype=np.float32)
            return reps[0], tolerance

        lengths = [r.num_frames for r in reps]
        target_len = int(np.median(lengths))

        resampled = [r.resample(target_len) for r in reps]
        stacked = np.stack([r.data for r in resampled], axis=0)  # (N, T, F)

        averaged_data = stacked.mean(axis=0).astype(np.float32)
        tolerance = stacked.std(axis=0).astype(np.float32)        # (T, F)

        canonical = TimeSeries(
            data=averaged_data,
            feature_names=reps[0].feature_names,
            fps=reps[0].fps,
        )
        return canonical, tolerance

    @staticmethod
    def _apply_tolerance(
        raw_devs: np.ndarray,
        path: List[Tuple[int, int]],
        tolerance: np.ndarray,
    ) -> np.ndarray:
        """
        Subtract the reference tolerance from raw per-frame deviations.

        The DTW path maps each query frame to a reference frame. We look up
        the tolerance at that reference frame and clip the deviation:
            effective = sign(raw) * max(0, |raw| - tolerance)

        Deviations within the reference's own natural spread are zeroed out
        (the user is moving within the acceptable range).
        """
        T_ref = len(tolerance)

        # Build query→ref mapping (first ref frame per query frame)
        query_to_ref: dict[int, int] = {}
        for q_idx, r_idx in path:
            if q_idx not in query_to_ref:
                query_to_ref[q_idx] = r_idx

        T_q = len(raw_devs)
        effective = np.empty_like(raw_devs)
        for q_idx in range(T_q):
            r_idx = min(query_to_ref.get(q_idx, 0), T_ref - 1)
            tol = tolerance[r_idx]                          # (F,)
            abs_dev = np.abs(raw_devs[q_idx])
            effective[q_idx] = np.sign(raw_devs[q_idx]) * np.maximum(0.0, abs_dev - tol)

        return effective

    def _devs_to_score(self, devs: np.ndarray) -> float:
        """Convert tolerance-adjusted per-frame deviations to a 0–100 score."""
        abs_devs = np.abs(devs).mean(axis=1)
        frame_scores = 100.0 * np.exp(-self.sensitivity * abs_devs)
        return float(np.mean(frame_scores))
