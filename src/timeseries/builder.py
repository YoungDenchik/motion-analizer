"""
Time series construction and resampling.

An exercise performed at different speeds produces sequences of different
lengths. Before DTW comparison, we need sequences that:
  1. Represent the same movement phases (not just same length)
  2. Have consistent temporal resolution

We use two representations:
  - Raw: the unmodified extracted feature sequence (T × F)
  - Resampled: interpolated to a fixed number of frames (useful for
    visualization and for exercises with very different durations)

DTW handles variable-length sequences natively, so resampling is optional
and only used when explicitly requested.
"""

from __future__ import annotations
from dataclasses import dataclass

import numpy as np
from scipy.interpolate import interp1d


@dataclass
class TimeSeries:
    """A multivariate time series representing one exercise repetition."""
    data: np.ndarray          # shape: (T, F) — T frames, F features
    feature_names: list[str]
    fps: float = 30.0         # approximate frames per second

    @property
    def num_frames(self) -> int:
        return self.data.shape[0]

    @property
    def num_features(self) -> int:
        return self.data.shape[1]

    @property
    def duration_seconds(self) -> float:
        return self.num_frames / max(self.fps, 1e-6)

    def resample(self, target_length: int) -> "TimeSeries":
        """
        Resample to exactly target_length frames using cubic interpolation.

        Use when you need fixed-length output (e.g., visualization, neural
        network input). Not needed for DTW comparison.
        """
        if self.num_frames == target_length:
            return self
        if self.num_frames < 2:
            return self

        t_orig = np.linspace(0, 1, self.num_frames)
        t_new = np.linspace(0, 1, target_length)

        interpolator = interp1d(
            t_orig, self.data, axis=0, kind="cubic", fill_value="extrapolate"
        )
        resampled = interpolator(t_new).astype(np.float32)
        return TimeSeries(
            data=resampled,
            feature_names=self.feature_names,
            fps=self.fps * (target_length / self.num_frames),
        )

    def smooth(self, window: int = 3) -> "TimeSeries":
        """
        Apply moving average smoothing to reduce per-frame jitter.

        MediaPipe already smooths landmarks, but computed angles can still
        have frame-to-frame noise. A small window (3-5) helps.
        """
        if window < 2 or self.num_frames < window:
            return self
        kernel = np.ones(window) / window
        smoothed = np.apply_along_axis(
            lambda col: np.convolve(col, kernel, mode="same"),
            axis=0,
            arr=self.data,
        )
        return TimeSeries(
            data=smoothed.astype(np.float32),
            feature_names=self.feature_names,
            fps=self.fps,
        )

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dict for reference storage."""
        return {
            "data": self.data.tolist(),
            "feature_names": self.feature_names,
            "fps": self.fps,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "TimeSeries":
        """Deserialize from a stored dict."""
        return cls(
            data=np.array(d["data"], dtype=np.float32),
            feature_names=d["feature_names"],
            fps=float(d.get("fps", 30.0)),
        )


class TimeSeriesBuilder:
    """
    Accumulates FeatureVectors frame-by-frame and builds a TimeSeries.

    Useful for streaming / real-time mode where frames arrive one at a time.
    """

    def __init__(self, feature_names: list[str], fps: float = 30.0):
        self._frames: list[np.ndarray] = []
        self.feature_names = feature_names
        self.fps = fps

    def add_frame(self, feature_values: np.ndarray) -> None:
        self._frames.append(feature_values.copy())

    def build(self, smooth: bool = True, smooth_window: int = 3) -> TimeSeries:
        """
        Assemble accumulated frames into a TimeSeries.

        Args:
            smooth: Apply moving-average smoothing.
            smooth_window: Window size for smoothing.
        """
        if not self._frames:
            data = np.empty((0, len(self.feature_names)), dtype=np.float32)
        else:
            data = np.stack(self._frames, axis=0).astype(np.float32)

        ts = TimeSeries(data=data, feature_names=self.feature_names, fps=self.fps)
        if smooth and ts.num_frames >= smooth_window:
            ts = ts.smooth(smooth_window)
        return ts

    def reset(self):
        self._frames.clear()


def build_time_series_from_array(
    feature_array: np.ndarray,
    feature_names: list[str],
    fps: float = 30.0,
    smooth: bool = True,
    smooth_window: int = 3,
) -> TimeSeries:
    """Convenience function: wrap a (T, F) array directly into a TimeSeries."""
    ts = TimeSeries(
        data=feature_array.astype(np.float32),
        feature_names=feature_names,
        fps=fps,
    )
    if smooth and ts.num_frames >= smooth_window:
        ts = ts.smooth(smooth_window)
    return ts
