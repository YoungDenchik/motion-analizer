"""
Exercise repetition segmentation.

Problem: a raw time series from a 3-rep squat session looks like:

    knee_angle
    180 |  *         *         *
        | * *       * *       * *
        |*   *     *   *     *   *
     90 |     *   *     *   *     *
        |      * *       * *
         0-----------------------------> frame

We need to split this into three separate reps so each can be compared
independently against a single reference rep.

Algorithm
─────────
1. Select an "indicator" feature — the one that oscillates most clearly
   (highest amplitude across the sequence).
2. Smooth it with a Savitzky-Golay filter to remove per-frame jitter.
3. Call scipy.find_peaks on the smoothed signal.
   • First try raw signal peaks (exercises that start/end standing: squats,
     deadlifts, push-ups — "high" angle at rest).
   • If fewer than 2 peaks found, try inverted signal (exercises that end
     at low angle: bicep curls, pull-ups — "low" angle at rest).
4. Each consecutive (peak[i], peak[i+1]) interval = one rep.
5. Edge cases:
   • 0 or 1 peaks found → whole sequence = single rep (no segmentation).
   • Segment shorter than min_rep_frames → dropped (noise / incomplete rep).

Why peak-to-peak and not valley-to-valley?
  Both work. Peaks are preferable because the "standing/starting position"
  is the natural rest point between reps — it's where movement velocity is
  lowest, making boundary detection more stable.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np
from scipy.signal import find_peaks, savgol_filter

from .builder import TimeSeries


@dataclass
class SegmentationResult:
    """Output of repetition detection on a single time series."""
    reps: List[TimeSeries]          # One TimeSeries per detected rep
    boundaries: List[Tuple[int, int]]  # (start_frame, end_frame) inclusive, per rep
    indicator_feature: str          # Which feature was used for peak detection
    peak_frames: List[int]          # Frame indices of detected peaks


class RepSegmenter:
    """
    Splits a multivariate exercise time series into individual repetitions.

    Designed to be exercise-agnostic: it auto-selects the most periodic
    feature and handles both "peaks at top" and "peaks at bottom" exercises.
    """

    def __init__(
        self,
        min_rep_frames: int = 15,
        smoothing_window: int = 9,
        peak_prominence: float = 8.0,
    ):
        """
        Args:
            min_rep_frames: Discard detected reps shorter than this.
                            At 30fps, 15 frames = 0.5s minimum rep duration.
            smoothing_window: Savitzky-Golay window for peak detection signal.
                              Must be odd and > polyorder (3).
            peak_prominence: Minimum prominence (degrees) for a valid peak.
                             Prevents noise spikes from being counted as reps.
        """
        self.min_rep_frames = min_rep_frames
        self.smoothing_window = smoothing_window
        self.peak_prominence = peak_prominence

    def segment(
        self,
        ts: TimeSeries,
        indicator_feature: Optional[str] = None,
    ) -> SegmentationResult:
        """
        Detect and return individual repetitions from a time series.

        Args:
            ts: The full session time series (may contain 1 to N reps).
            indicator_feature: Feature name to drive peak detection.
                               None = auto-select (highest amplitude feature).

        Returns:
            SegmentationResult. If no repetitions detected, reps contains
            the full sequence as a single element.
        """
        if ts.num_frames < self.min_rep_frames * 2:
            # Too short to contain multiple reps — return whole sequence
            return SegmentationResult(
                reps=[ts],
                boundaries=[(0, ts.num_frames - 1)],
                indicator_feature=indicator_feature or ts.feature_names[0],
                peak_frames=[],
            )

        feat = indicator_feature or self._auto_select_feature(ts)
        feat_idx = ts.feature_names.index(feat)
        signal = ts.data[:, feat_idx].astype(float)

        # Smooth to suppress jitter before peak detection
        win = min(self.smoothing_window, len(signal) // 4 * 2 + 1)  # keep odd
        win = max(win, 5)
        if win % 2 == 0:
            win += 1
        smoothed = savgol_filter(signal, window_length=win, polyorder=3)

        # Minimum distance between peaks: at least min_rep_frames
        peaks = self._find_peaks(smoothed, min_distance=self.min_rep_frames)

        boundaries = self._peaks_to_boundaries(peaks, ts.num_frames)
        reps = self._slice_reps(ts, boundaries)

        return SegmentationResult(
            reps=reps,
            boundaries=boundaries,
            indicator_feature=feat,
            peak_frames=peaks,
        )

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _auto_select_feature(self, ts: TimeSeries) -> str:
        """
        Pick the feature with the largest amplitude (max − min).
        That feature will have the clearest peak structure.
        """
        amplitudes = ts.data.max(axis=0) - ts.data.min(axis=0)
        best_idx = int(np.argmax(amplitudes))
        return ts.feature_names[best_idx]

    def _find_peaks(self, signal: np.ndarray, min_distance: int) -> List[int]:
        """
        Try peaks on raw signal, then on inverted signal.
        Returns whichever gives more detected peaks (≥ 2).
        """
        peaks_pos, _ = find_peaks(
            signal,
            distance=min_distance,
            prominence=self.peak_prominence,
        )
        peaks_neg, _ = find_peaks(
            -signal,
            distance=min_distance,
            prominence=self.peak_prominence,
        )

        # Prefer whichever detects more reps
        if len(peaks_pos) >= len(peaks_neg):
            return peaks_pos.tolist()
        return peaks_neg.tolist()

    def _peaks_to_boundaries(
        self,
        peaks: List[int],
        total_frames: int,
    ) -> List[Tuple[int, int]]:
        """
        Convert a list of peak frame indices into (start, end) rep boundaries.

        With peaks at [p0, p1, p2]:
          rep 0: (0,    p0)   ← approach to first peak
          rep 1: (p0,   p1)   ← peak-to-peak
          rep 2: (p1,   p2)   ← peak-to-peak
          rep 3: (p2,   end)  ← tail after last peak

        Segments shorter than min_rep_frames are dropped.
        """
        if len(peaks) < 2:
            return [(0, total_frames - 1)]

        # Build boundary list including start-of-sequence and end-of-sequence
        boundary_points = [0] + peaks + [total_frames - 1]
        raw_segments = [
            (boundary_points[i], boundary_points[i + 1])
            for i in range(len(boundary_points) - 1)
        ]

        # Keep only segments long enough to be a real rep
        valid = [
            (s, e) for s, e in raw_segments
            if (e - s) >= self.min_rep_frames
        ]
        return valid if valid else [(0, total_frames - 1)]

    def _slice_reps(
        self,
        ts: TimeSeries,
        boundaries: List[Tuple[int, int]],
    ) -> List[TimeSeries]:
        """Extract a sub-TimeSeries for each boundary pair."""
        reps = []
        for start, end in boundaries:
            end = min(end + 1, ts.num_frames)  # make end exclusive
            segment_data = ts.data[start:end].copy()
            reps.append(TimeSeries(
                data=segment_data,
                feature_names=ts.feature_names,
                fps=ts.fps,
            ))
        return reps
