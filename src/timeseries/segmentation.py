"""
Exercise repetition segmentation.

Goal: split a multi-rep session time series into individual reps so that
each can be compared one-to-one against a reference rep.

    knee_angle
    180 |  *         *         *
        | * *       * *       * *
     90 |     * * *     * * *     * * *
         ─────┬─────────┬─────────┬────
             rep1       rep2      rep3

Algorithm
─────────
1. Build a 1D indicator signal via PCA (first principal component across all
   features). PCA is used instead of a single feature because:
   - It combines correlated joint movements, not just the noisiest one.
   - Intra-rep wobbles in individual features average out across joints.
   - The dominant oscillation (the rep itself) shows up in the first PC
     regardless of which joint has the highest raw amplitude.

2. Detect peaks across multiple smoothing scales (fine → coarse).
   For each scale, sweep amplitude-proportional prominence thresholds and
   score each candidate peak set by:
       score = CV(inter-peak intervals) + 0.002 × num_peaks
   - CV penalises inconsistent rep durations (spurious peaks cause uneven
     intervals and raise the CV).
   - The per-peak penalty breaks exact CV ties toward fewer peaks (Occam's
     Razor: prefer the simpler explanation when evidence is equal).
   The best-scoring candidate across ALL scales is returned.

3. Build rep boundaries peak-to-peak. The head segment [0 → first_peak]
   and tail segment [last_peak → end] are included ONLY if they are at
   least min_frames long — otherwise they are just approach / cooldown.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np
from scipy.signal import find_peaks, savgol_filter

from .builder import TimeSeries


@dataclass
class SegmentationResult:
    reps: List[TimeSeries]
    boundaries: List[Tuple[int, int]]   # (start, end) inclusive per rep
    indicator_feature: str
    peak_frames: List[int]


class RepSegmenter:
    """
    Splits a multivariate exercise time series into individual repetitions.

    Parameters are time-based (seconds) so they work across any frame rate.
    """

    def __init__(
        self,
        min_rep_seconds: float = 1.0,
        peak_prominence: float = 15.0,
        smoothing_window: int = 11,
    ):
        """
        Args:
            min_rep_seconds: Minimum duration of one rep in seconds. Sets the
                minimum distance between detected peaks so intra-rep wobbles
                cannot be mistaken for rep boundaries. 1.0s suits most gym
                exercises; go lower only for fast, small-ROM movements.
            peak_prominence: Minimum absolute prominence (in the same units
                as the PCA signal) a peak must have. Acts as a floor — the
                adaptive amplitude-proportional threshold is used instead
                whenever it is higher.
            smoothing_window: Base Savitzky-Golay window (frames, odd, ≥5).
                Multi-scale detection also tries 2× and 4× this window.
        """
        self.min_rep_seconds = min_rep_seconds
        self.peak_prominence = peak_prominence
        self.smoothing_window = smoothing_window

    def segment(
        self,
        ts: TimeSeries,
        indicator_feature: Optional[str] = None,
    ) -> SegmentationResult:
        """
        Detect individual repetitions in a time series.

        Falls back to the whole sequence as a single rep if no clear
        periodicity is found.
        """
        min_rep_frames = max(5, int(self.min_rep_seconds * ts.fps))

        if ts.num_frames < min_rep_frames * 2:
            return self._single_rep(ts, indicator_feature)

        # Build 1D indicator signal
        if indicator_feature:
            feat_idx = ts.feature_names.index(indicator_feature)
            raw_signal = ts.data[:, feat_idx].astype(float)
            indicator_name = indicator_feature
        else:
            raw_signal, indicator_name = self._pca_signal(ts)

        peaks = self._detect_peaks(raw_signal, min_rep_frames)
        boundaries = self._peaks_to_boundaries(peaks, ts.num_frames, min_rep_frames)
        reps = self._slice_reps(ts, boundaries)

        return SegmentationResult(
            reps=reps,
            boundaries=boundaries,
            indicator_feature=indicator_name,
            peak_frames=peaks,
        )

    # ── Signal building ───────────────────────────────────────────────────────

    def _pca_signal(self, ts: TimeSeries) -> Tuple[np.ndarray, str]:
        """
        Build the 1D indicator signal as the first principal component.

        PCA is run on the zero-meaned (but not scaled) feature matrix so
        that high-oscillation joints naturally dominate. The PC is oriented
        to be positively correlated with the highest-amplitude single feature
        so that peaks in the PC correspond to peaks in that feature.

        Falls back to the highest-amplitude single feature if SVD fails.
        """
        data = ts.data.astype(float)              # (T, F)
        centered = data - data.mean(axis=0)

        try:
            _, _, Vt = np.linalg.svd(centered, full_matrices=False)
            pc1 = centered @ Vt[0]                # (T,)

            # Orient: positive correlation with highest-amplitude feature
            amps = data.max(axis=0) - data.min(axis=0)
            ref_col = data[:, int(np.argmax(amps))]
            if float(np.corrcoef(pc1, ref_col)[0, 1]) < 0:
                pc1 = -pc1

            return pc1, "pca_1"

        except np.linalg.LinAlgError:
            amps = data.max(axis=0) - data.min(axis=0)
            idx = int(np.argmax(amps))
            return data[:, idx].copy(), ts.feature_names[idx]

    # ── Multi-scale peak detection ────────────────────────────────────────────

    def _detect_peaks(self, signal: np.ndarray, min_distance: int) -> List[int]:
        """
        Find rep-boundary peaks by running the prominence sweep at three
        smoothing scales and returning the globally best candidate.

        Coarser smoothing suppresses intra-rep local maxima that survive fine
        smoothing. Running all three scales and taking the best ensures that
        neither under- nor over-smoothing dominates.
        """
        T = len(signal)
        amplitude = float(signal.max() - signal.min())

        if amplitude < 1.0:
            return []  # flat signal — no detectable movement

        # Build distinct window sizes: base, 2×, 4× (bounded to T//4)
        seen: set[int] = set()
        windows: List[int] = []
        for mult in (1, 2, 4):
            w = self.smoothing_window * mult
            w = min(w, (T // 4) * 2 + 1)
            w = max(w, 5)
            if w % 2 == 0:
                w += 1
            if w not in seen:
                seen.add(w)
                windows.append(w)

        best_peaks: List[int] = []
        best_score = float("inf")

        for win in windows:
            poly = min(3, win - 2)
            smoothed = savgol_filter(signal, window_length=win, polyorder=poly)
            amp_s = float(smoothed.max() - smoothed.min())

            peaks, score = self._best_peaks_on_signal(smoothed, min_distance, amp_s)

            if score < best_score:
                best_score = score
                best_peaks = peaks

        return best_peaks

    def _best_peaks_on_signal(
        self,
        signal: np.ndarray,
        min_distance: int,
        amplitude: float,
    ) -> Tuple[List[int], float]:
        """
        Sweep amplitude-proportional prominence thresholds on a smoothed signal.

        Direction policy — positive peaks only (primary), inverted as fallback:
          The PCA signal is oriented so that its maxima (positive peaks) fall at
          the "natural high" of the exercise: standing for squats, arms extended
          for rows, etc. These are the true rep boundaries. Positive-peak
          boundaries produce clean interior segments (one full rep each) and
          tiny head/tail that gets dropped.

          If we allowed the inverted signal to win by prominence sum, peaks would
          land at the BOTTOM of each rep. Interior segments then straddle two
          half-reps, and BOTH head and tail are half-rep-length — long enough to
          pass the min_frames gate — so they get counted as extra reps, producing
          a systematic +1 over-count.

          Fallback: if no 2-peak solution is found in the positive direction at
          any threshold, the inverted direction is tried. This handles exercises
          where the "natural high" is genuinely less prominent (e.g., partial-ROM
          movements where the person never fully extends between reps).

        Scoring: CV(inter-peak intervals) + 0.002 × n_peaks.
          * CV rewards temporal consistency (real reps take similar time).
          * Per-peak penalty breaks exact CV ties toward fewer peaks.

        Returns (best_peaks, best_score). Score=inf if no 2-peak solution found.
        """
        best_peaks: List[int] = []
        best_score = float("inf")

        # ── Pass 1: positive peaks (preferred) ───────────────────────────────
        for ratio in (0.20, 0.25, 0.30, 0.35, 0.40, 0.45):
            prominence = max(self.peak_prominence, ratio * amplitude)

            peaks_arr, _ = find_peaks(signal, distance=min_distance, prominence=prominence)
            peaks = peaks_arr.tolist()

            if len(peaks) < 2:
                if not best_peaks:
                    best_peaks = peaks
                break

            intervals = np.diff(peaks).astype(float)
            cv = float(intervals.std() / intervals.mean())
            score = cv + 0.002 * len(peaks)

            if score < best_score:
                best_score = score
                best_peaks = peaks

        # ── Pass 2: inverted peaks (fallback only if no positive solution) ───
        if len(best_peaks) < 2:
            for ratio in (0.20, 0.25, 0.30, 0.35, 0.40, 0.45):
                prominence = max(self.peak_prominence, ratio * amplitude)

                peaks_arr, _ = find_peaks(-signal, distance=min_distance, prominence=prominence)
                peaks = peaks_arr.tolist()

                if len(peaks) < 2:
                    if not best_peaks:
                        best_peaks = peaks
                    break

                intervals = np.diff(peaks).astype(float)
                cv = float(intervals.std() / intervals.mean())
                score = cv + 0.002 * len(peaks)

                if score < best_score:
                    best_score = score
                    best_peaks = peaks

        if not best_peaks:
            # Absolute last resort: fixed prominence, positive direction first
            peaks_pos, _ = find_peaks(signal, distance=min_distance, prominence=self.peak_prominence)
            peaks_neg, _ = find_peaks(-signal, distance=min_distance, prominence=self.peak_prominence)
            best_peaks = peaks_pos.tolist() if len(peaks_pos) >= len(peaks_neg) else peaks_neg.tolist()
            best_score = float("inf")

        return best_peaks, best_score

    # ── Boundary building ─────────────────────────────────────────────────────

    def _peaks_to_boundaries(
        self,
        peaks: List[int],
        total_frames: int,
        min_frames: int,
    ) -> List[Tuple[int, int]]:
        """
        Convert peak positions to (start, end) rep boundaries.

        Interior segments (peak[i] → peak[i+1]) are always kept — they are
        full rep cycles between two boundaries of the same type.

        Head [0 → first_peak] and tail [last_peak → end] represent partial
        cycles at the recording edges. They are kept only when long enough to
        plausibly contain a full rep, measured against the median interior
        segment length:

            threshold = max(min_frames, 0.6 × median_interior_length)

        Why 0.6 × median?
          When peaks fall at the "natural high" (standing position), a true
          partial rep at the edge is ~50–100 % of interior length. An approach
          or cooldown (person walking in, standing, walking out) is typically
          much shorter. 0.6 keeps genuine edge reps and drops short warmups.

          Crucially, if peaks land at the movement BOTTOM (inverted fallback),
          both head and tail are each exactly ~50 % of interior length. The 0.6
          threshold drops them both, preventing the systematic +1 over-count
          that occurred when min_frames alone passed them.
        """
        if len(peaks) < 2:
            return [(0, total_frames - 1)]

        interior = [(peaks[i], peaks[i + 1]) for i in range(len(peaks) - 1)]

        median_interior = float(np.median([e - s for s, e in interior]))
        threshold = max(min_frames, int(0.6 * median_interior))

        head = (0, peaks[0])
        tail = (peaks[-1], total_frames - 1)

        boundaries: List[Tuple[int, int]] = []
        if (head[1] - head[0]) >= threshold:
            boundaries.append(head)
        boundaries.extend(interior)
        if (tail[1] - tail[0]) >= threshold:
            boundaries.append(tail)

        return boundaries if boundaries else [(0, total_frames - 1)]

    def _slice_reps(
        self,
        ts: TimeSeries,
        boundaries: List[Tuple[int, int]],
    ) -> List[TimeSeries]:
        reps = []
        for start, end in boundaries:
            end_excl = min(end + 1, ts.num_frames)
            reps.append(TimeSeries(
                data=ts.data[start:end_excl].copy(),
                feature_names=ts.feature_names,
                fps=ts.fps,
            ))
        return reps

    def _single_rep(
        self, ts: TimeSeries, indicator_feature: Optional[str]
    ) -> SegmentationResult:
        return SegmentationResult(
            reps=[ts],
            boundaries=[(0, ts.num_frames - 1)],
            indicator_feature=indicator_feature or ts.feature_names[0],
            peak_frames=[],
        )
