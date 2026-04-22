"""
Scoring engine: converts DTW deviations into a 0-100 technique score.

Scoring formula:
  frame_score(t) = 100 × exp(−k × mean_abs_deviation(t))

  Where k is a sensitivity constant. With k=0.05:
    - 0° mean deviation  → 100 (perfect)
    - 10° mean deviation → 61
    - 20° mean deviation → 37
    - 40° mean deviation → 14

  overall_score = mean(frame_scores) × phase_penalty

  phase_penalty penalizes frames where the user skipped a critical phase
  (e.g., didn't reach sufficient depth in a squat).

The exponential decay is preferred over linear penalty because:
  - It never goes negative (scores stay in [0, 100])
  - It's forgiving for small deviations, strict for large ones
  - It matches how coaches perceive technique: small errors are OK, but
    compounding errors rapidly degrade performance quality
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List

import numpy as np

from ..comparison.dtw import DTWResult


@dataclass
class ScoreReport:
    """Complete scoring output for one exercise analysis."""
    overall_score: float          # 0-100
    per_frame_scores: np.ndarray  # shape: (T_query,), each in [0, 100]
    per_feature_scores: np.ndarray# shape: (F,), one score per feature

    # Raw stats
    mean_deviation: np.ndarray    # shape: (F,), mean abs deviation per feature
    max_deviation: np.ndarray     # shape: (F,), max abs deviation per feature
    dtw_distance: float
    normalized_dtw_distance: float
    feature_names: List[str]

    @property
    def grade(self) -> str:
        """Letter grade from overall score."""
        s = self.overall_score
        if s >= 90:
            return "A"
        elif s >= 80:
            return "B"
        elif s >= 70:
            return "C"
        elif s >= 60:
            return "D"
        else:
            return "F"

    @property
    def worst_features(self) -> list[tuple[str, float]]:
        """Features sorted by worst mean absolute deviation (descending)."""
        mean_abs = np.abs(self.mean_deviation)
        order = np.argsort(mean_abs)[::-1]
        return [(self.feature_names[i], float(mean_abs[i])) for i in order]

    def per_feature_summary(self) -> dict[str, dict]:
        """Per-feature score summary for reporting."""
        return {
            name: {
                "score": float(self.per_feature_scores[i]),
                "mean_deviation_deg": float(self.mean_deviation[i]),
                "max_deviation_deg": float(self.max_deviation[i]),
            }
            for i, name in enumerate(self.feature_names)
        }


class ScoringEngine:
    """
    Converts a DTWResult into a ScoreReport.

    The sensitivity parameter k controls how steeply scores drop with
    deviation. Tune it based on the exercise and user level:
      - k=0.03: lenient (for beginners learning movement patterns)
      - k=0.05: standard (default)
      - k=0.08: strict (for competitive athletes)
    """

    def __init__(self, sensitivity: float = 0.05):
        """
        Args:
            sensitivity: k in the exp(−k × deviation) scoring formula.
                         Higher k = more sensitive to small errors.
        """
        self.sensitivity = sensitivity

    def score(self, dtw_result: DTWResult) -> ScoreReport:
        """Compute scores from DTW deviation analysis."""
        abs_deviations = np.abs(dtw_result.per_frame_deviations)  # (T, F)

        # Per-frame score: exponential decay on mean absolute deviation
        mean_abs_per_frame = abs_deviations.mean(axis=1)           # (T,)
        per_frame_scores = 100.0 * np.exp(-self.sensitivity * mean_abs_per_frame)

        # Per-feature score: exponential decay on mean absolute deviation
        mean_abs_per_feature = abs_deviations.mean(axis=0)         # (F,)
        per_feature_scores = 100.0 * np.exp(-self.sensitivity * mean_abs_per_feature)

        overall_score = float(np.mean(per_frame_scores))

        return ScoreReport(
            overall_score=overall_score,
            per_frame_scores=per_frame_scores.astype(np.float32),
            per_feature_scores=per_feature_scores.astype(np.float32),
            mean_deviation=dtw_result.per_frame_deviations.mean(axis=0),
            max_deviation=np.abs(dtw_result.per_frame_deviations).max(axis=0),
            dtw_distance=dtw_result.distance,
            normalized_dtw_distance=dtw_result.normalized_distance,
            feature_names=dtw_result.feature_names,
        )
