"""
Error classification: labels technique deviations by type and severity.

Two severity levels:
  CRITICAL  — injury risk, should be corrected immediately
              (e.g., excessive torso lean, knee cave, hyperextension)
  TECHNICAL — efficiency/effectiveness issues, important but not urgent
              (e.g., insufficient range of motion, asymmetry)

Two error directions:
  ABOVE_REFERENCE — angle is too large compared to reference
  BELOW_REFERENCE — angle is too small (e.g., not enough depth)

Error events are generated when a feature's mean deviation across a
sustained window exceeds a threshold. This prevents one-frame spikes
(tracking noise) from generating false errors.

Thresholds are in degrees since features are joint angles.
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import List

import numpy as np

from ..comparison.dtw import DTWResult
from ..features.extractor import CRITICAL_FEATURES, TECHNICAL_FEATURES


class ErrorSeverity(Enum):
    CRITICAL = "critical"
    TECHNICAL = "technical"


class ErrorDirection(Enum):
    ABOVE_REFERENCE = "above"  # user angle > reference angle
    BELOW_REFERENCE = "below"  # user angle < reference angle


@dataclass
class ErrorEvent:
    """A detected technique deviation for a specific feature."""
    feature_name: str
    severity: ErrorSeverity
    direction: ErrorDirection
    mean_deviation_deg: float     # Average deviation magnitude in degrees
    max_deviation_deg: float      # Worst-case deviation magnitude
    affected_frame_ratio: float   # Fraction of frames where error was present
    start_frame: int
    end_frame: int


# Thresholds in degrees — deviation must exceed this to count as an error.
# These are intentionally conservative to avoid over-correcting beginners.
CRITICAL_THRESHOLD_DEG = 12.0   # >12° deviation from reference = critical
TECHNICAL_THRESHOLD_DEG = 8.0   # >8° deviation = technical error
SUSTAINED_WINDOW = 3            # Error must persist across N consecutive frames


class ErrorClassifier:
    """
    Classifies DTW deviations into ErrorEvents.

    Algorithm:
      1. For each feature, examine per-frame signed deviations.
      2. Smooth deviations with a short moving window to reject noise.
      3. Find contiguous segments where |deviation| > threshold.
      4. For each segment, create an ErrorEvent with severity and direction.
    """

    def __init__(
        self,
        critical_threshold: float = CRITICAL_THRESHOLD_DEG,
        technical_threshold: float = TECHNICAL_THRESHOLD_DEG,
        sustained_window: int = SUSTAINED_WINDOW,
    ):
        self.critical_threshold = critical_threshold
        self.technical_threshold = technical_threshold
        self.sustained_window = sustained_window

    def classify(self, dtw_result: DTWResult) -> List[ErrorEvent]:
        """
        Identify and classify all technique errors in a DTW comparison result.

        Returns a list of ErrorEvents, one per sustained deviation segment
        per feature. Sorted by severity (critical first) then by deviation.
        """
        deviations = dtw_result.per_frame_deviations  # (T, F)
        feature_names = dtw_result.feature_names
        T = deviations.shape[0]

        events: List[ErrorEvent] = []

        for f_idx, feature_name in enumerate(feature_names):
            feature_dev = deviations[:, f_idx]  # (T,) signed deviations

            # Determine severity and threshold for this feature
            if feature_name in CRITICAL_FEATURES:
                threshold = self.critical_threshold
                severity = ErrorSeverity.CRITICAL
            else:
                threshold = self.technical_threshold
                severity = ErrorSeverity.TECHNICAL

            # Find frames where |deviation| exceeds threshold
            above_threshold = np.abs(feature_dev) > threshold

            # Find contiguous error segments using run-length encoding
            segments = self._find_segments(above_threshold, min_length=self.sustained_window)

            for start, end in segments:
                seg_dev = feature_dev[start:end + 1]
                mean_dev = float(np.mean(seg_dev))
                max_abs_dev = float(np.max(np.abs(seg_dev)))
                direction = (
                    ErrorDirection.ABOVE_REFERENCE
                    if mean_dev > 0
                    else ErrorDirection.BELOW_REFERENCE
                )
                affected_ratio = float(above_threshold[start:end + 1].mean())

                events.append(ErrorEvent(
                    feature_name=feature_name,
                    severity=severity,
                    direction=direction,
                    mean_deviation_deg=abs(mean_dev),
                    max_deviation_deg=max_abs_dev,
                    affected_frame_ratio=affected_ratio,
                    start_frame=int(start),
                    end_frame=int(end),
                ))

        # Sort: critical first, then by mean deviation descending
        events.sort(
            key=lambda e: (
                0 if e.severity == ErrorSeverity.CRITICAL else 1,
                -e.mean_deviation_deg,
            )
        )
        return events

    @staticmethod
    def _find_segments(mask: np.ndarray, min_length: int) -> list[tuple[int, int]]:
        """
        Find contiguous True segments in a boolean array.
        Returns list of (start, end) inclusive index pairs.
        Segments shorter than min_length are excluded.
        """
        segments = []
        in_segment = False
        start = 0

        for i, val in enumerate(mask):
            if val and not in_segment:
                in_segment = True
                start = i
            elif not val and in_segment:
                in_segment = False
                if i - start >= min_length:
                    segments.append((start, i - 1))

        # Handle segment extending to end of array
        if in_segment and len(mask) - start >= min_length:
            segments.append((start, len(mask) - 1))

        return segments
