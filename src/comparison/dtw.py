"""
Dynamic Time Warping (DTW) comparison of exercise time series.

Why DTW?
  Classic Euclidean distance requires sequences of identical length and
  assumes frame-to-frame temporal alignment. Real exercises don't work that
  way — someone might perform a squat in 1.5s vs 2.5s, pause at the bottom,
  or accelerate differently. DTW finds the optimal alignment path between
  two sequences, warping the time axis to minimize total distance.

Implementation:
  We use fastdtw, an O(N) approximation of exact DTW with a Sakoe-Chiba
  band constraint. This makes it suitable for sequences up to ~500 frames
  in near-real time.

  Exact DTW is O(N²) in time and space — impractical for sequences >200
  frames when comparing in real time.

Distance metric:
  Per-frame distance = mean absolute deviation across all features.
  This treats all features equally; feature weighting can be added later
  to emphasize injury-critical angles (e.g., torso lean, knee angle).

Output:
  DTWResult contains:
  - distance: the total alignment cost (lower = more similar)
  - path: list of (query_idx, ref_idx) pairs giving the optimal alignment
  - per_frame_deviations: for each query frame, the feature-wise error
    at the aligned reference frame
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple

import numpy as np
from fastdtw import fastdtw
from scipy.spatial.distance import euclidean

from ..timeseries.builder import TimeSeries


@dataclass
class DTWResult:
    """Output of a DTW comparison between a query and reference sequence."""
    distance: float
    path: List[Tuple[int, int]]         # (query_idx, ref_idx) alignment pairs

    # Per-frame analysis aligned to the query sequence
    per_frame_deviations: np.ndarray    # shape: (T_query, F) — signed deviations
    per_frame_distances: np.ndarray     # shape: (T_query,)   — scalar per frame

    query_length: int
    reference_length: int
    feature_names: List[str]

    @property
    def mean_deviation(self) -> np.ndarray:
        """Mean signed deviation per feature across all frames. Shape: (F,)."""
        return self.per_frame_deviations.mean(axis=0)

    @property
    def max_deviation(self) -> np.ndarray:
        """Maximum absolute deviation per feature. Shape: (F,)."""
        return np.abs(self.per_frame_deviations).max(axis=0)

    @property
    def normalized_distance(self) -> float:
        """
        DTW distance normalized by path length.
        Comparable across sequences of different lengths.
        """
        return self.distance / max(len(self.path), 1)


class DTWComparator:
    """
    Compares a user's exercise time series against a reference sequence.

    The comparator computes:
      1. The DTW alignment path (optimal temporal warping)
      2. Per-frame deviations for each query frame
      3. A normalized distance score

    Feature weighting:
      Different joints contribute differently to technique quality.
      For example, torso lean and knee angles are more critical for injury
      prevention than elbow angles in a squat. Weights can be provided to
      reflect this clinical priority.
    """

    # Default weights: critical features get 2×, others get 1×
    DEFAULT_WEIGHTS = {
        "left_knee_angle": 2.0,
        "right_knee_angle": 2.0,
        "torso_lean": 2.5,
        "left_hip_angle": 1.5,
        "right_hip_angle": 1.5,
        "left_elbow_angle": 1.0,
        "right_elbow_angle": 1.0,
        "left_shoulder_angle": 1.0,
        "right_shoulder_angle": 1.0,
    }

    def __init__(self, feature_weights: dict[str, float] | None = None, radius: int = 10):
        """
        Args:
            feature_weights: Per-feature importance weights. None = equal weights.
            radius: fastdtw band radius. Larger = more flexible alignment,
                    slower. 10 is a good default for exercise sequences.
        """
        self.radius = radius
        self._feature_weights: dict[str, float] | None = feature_weights

    def _build_weight_vector(self, feature_names: list[str]) -> np.ndarray:
        """Build a weight array aligned with feature_names."""
        if self._feature_weights is None:
            weights = self.DEFAULT_WEIGHTS
        else:
            weights = self._feature_weights
        return np.array(
            [weights.get(name, 1.0) for name in feature_names],
            dtype=np.float32,
        )

    def compare(self, query: TimeSeries, reference: TimeSeries) -> DTWResult:
        """
        Align query sequence to reference using DTW.

        Both sequences must have the same feature_names (same features,
        same order). The reference and query can have different lengths.

        Returns:
            DTWResult with alignment path and per-frame deviation analysis.
        """
        if query.feature_names != reference.feature_names:
            raise ValueError(
                f"Feature name mismatch:\n"
                f"  query:     {query.feature_names}\n"
                f"  reference: {reference.feature_names}"
            )

        weights = self._build_weight_vector(query.feature_names)
        q_data = query.data      # (T_q, F)
        r_data = reference.data  # (T_r, F)

        # Weighted distance function for fastdtw
        def weighted_distance(a: np.ndarray, b: np.ndarray) -> float:
            return float(np.sum(weights * np.abs(a - b)))

        distance, path = fastdtw(q_data, r_data, radius=self.radius, dist=weighted_distance)

        # Compute per-frame deviations aligned to the query
        # Each query frame maps to one (or more) reference frames via the path.
        # We take the first reference frame mapped to each query frame.
        query_to_ref: dict[int, int] = {}
        for q_idx, r_idx in path:
            if q_idx not in query_to_ref:
                query_to_ref[q_idx] = r_idx

        T_q = query.num_frames
        F = query.num_features
        per_frame_deviations = np.zeros((T_q, F), dtype=np.float32)
        per_frame_distances = np.zeros(T_q, dtype=np.float32)

        for q_idx in range(T_q):
            r_idx = query_to_ref.get(q_idx, 0)
            deviation = q_data[q_idx] - r_data[r_idx]     # signed, (F,)
            per_frame_deviations[q_idx] = deviation
            per_frame_distances[q_idx] = float(np.mean(np.abs(deviation)))

        return DTWResult(
            distance=float(distance),
            path=list(path),
            per_frame_deviations=per_frame_deviations,
            per_frame_distances=per_frame_distances,
            query_length=T_q,
            reference_length=reference.num_frames,
            feature_names=query.feature_names,
        )
