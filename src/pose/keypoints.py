"""
Keypoint data structures and landmark index constants.

MediaPipe Pose provides 33 body landmarks. We define named constants for the
indices we use in angle and feature computations.
"""

from dataclasses import dataclass, field
from enum import IntEnum
from typing import List, Optional
import numpy as np


class LandmarkIndex(IntEnum):
    """MediaPipe Pose landmark indices (0-based)."""
    NOSE = 0
    LEFT_EYE_INNER = 1
    LEFT_EYE = 2
    LEFT_EYE_OUTER = 3
    RIGHT_EYE_INNER = 4
    RIGHT_EYE = 5
    RIGHT_EYE_OUTER = 6
    LEFT_EAR = 7
    RIGHT_EAR = 8
    MOUTH_LEFT = 9
    MOUTH_RIGHT = 10
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    LEFT_ELBOW = 13
    RIGHT_ELBOW = 14
    LEFT_WRIST = 15
    RIGHT_WRIST = 16
    LEFT_PINKY = 17
    RIGHT_PINKY = 18
    LEFT_INDEX = 19
    RIGHT_INDEX = 20
    LEFT_THUMB = 21
    RIGHT_THUMB = 22
    LEFT_HIP = 23
    RIGHT_HIP = 24
    LEFT_KNEE = 25
    RIGHT_KNEE = 26
    LEFT_ANKLE = 27
    RIGHT_ANKLE = 28
    LEFT_HEEL = 29
    RIGHT_HEEL = 30
    LEFT_FOOT_INDEX = 31
    RIGHT_FOOT_INDEX = 32


@dataclass
class PoseLandmark:
    """Single body landmark with 3D coordinates and confidence."""
    x: float
    y: float
    z: float
    visibility: float = 1.0

    def as_array(self, use_z: bool = True) -> np.ndarray:
        if use_z:
            return np.array([self.x, self.y, self.z])
        return np.array([self.x, self.y])


@dataclass
class PoseFrame:
    """All landmarks for a single video frame."""
    landmarks: List[PoseLandmark]
    frame_index: int = 0
    timestamp_ms: float = 0.0

    def __post_init__(self):
        if len(self.landmarks) != 33:
            raise ValueError(f"Expected 33 landmarks, got {len(self.landmarks)}")

    def get(self, index: LandmarkIndex) -> PoseLandmark:
        return self.landmarks[int(index)]

    def as_array(self, use_z: bool = True) -> np.ndarray:
        """Returns shape (33, 3) or (33, 2)."""
        return np.array([lm.as_array(use_z) for lm in self.landmarks])

    def visibility_mask(self, threshold: float = 0.5) -> np.ndarray:
        """Boolean mask: True where landmark is visible."""
        return np.array([lm.visibility >= threshold for lm in self.landmarks])
