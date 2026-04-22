"""
Biomechanical feature extraction from pose landmarks.

Why joint angles instead of raw coordinates?
- Angles are invariant to global position and orientation
- They directly capture what matters for technique assessment
- They match how coaches and physiotherapists describe movement

Angle computation: for three points A-B-C, the angle at B is:
    θ = arccos( (BA · BC) / (|BA| × |BC|) )

This gives the interior angle at the vertex B in [0°, 180°].

Features extracted (9 angles):
  - left_knee_angle:    left_hip - left_knee - left_ankle
  - right_knee_angle:   right_hip - right_knee - right_ankle
  - left_hip_angle:     left_shoulder - left_hip - left_knee
  - right_hip_angle:    right_shoulder - right_hip - right_knee
  - left_elbow_angle:   left_shoulder - left_elbow - left_wrist
  - right_elbow_angle:  right_shoulder - right_elbow - right_wrist
  - left_shoulder_angle: left_elbow - left_shoulder - left_hip
  - right_shoulder_angle: right_elbow - right_shoulder - right_hip
  - torso_lean:         angle of (hip_center → shoulder_center) from vertical

The torso_lean feature is critical for exercises like squats and deadlifts
where back angle is a primary injury-risk indicator.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List

import numpy as np

from ..pose.keypoints import LandmarkIndex, PoseFrame
from .normalizer import normalize_landmarks


# Named feature slots — order matters; kept stable across all pipeline stages.
FEATURE_NAMES: List[str] = [
    "left_knee_angle",
    "right_knee_angle",
    "left_hip_angle",
    "right_hip_angle",
    "left_elbow_angle",
    "right_elbow_angle",
    "left_shoulder_angle",
    "right_shoulder_angle",
    "torso_lean",
]

NUM_FEATURES = len(FEATURE_NAMES)

# Severity metadata: which features are critical (injury risk) vs technical
CRITICAL_FEATURES = {"left_knee_angle", "right_knee_angle", "torso_lean"}
TECHNICAL_FEATURES = {
    "left_hip_angle",
    "right_hip_angle",
    "left_elbow_angle",
    "right_elbow_angle",
    "left_shoulder_angle",
    "right_shoulder_angle",
}


@dataclass
class FeatureVector:
    """Named feature vector for a single frame."""
    values: np.ndarray  # shape: (NUM_FEATURES,)
    feature_names: List[str]

    def __getitem__(self, name: str) -> float:
        idx = self.feature_names.index(name)
        return float(self.values[idx])

    def as_dict(self) -> dict:
        return dict(zip(self.feature_names, self.values.tolist()))


def _angle_at_vertex(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """
    Compute interior angle at point b formed by rays b→a and b→c.
    Uses only x, y coordinates (2D projection) to handle z-axis noise.
    Returns angle in degrees [0, 180].
    """
    ba = a[:2] - b[:2]
    bc = c[:2] - b[:2]
    norm_ba = np.linalg.norm(ba)
    norm_bc = np.linalg.norm(bc)
    if norm_ba < 1e-8 or norm_bc < 1e-8:
        return 0.0
    cos_angle = np.dot(ba, bc) / (norm_ba * norm_bc)
    return float(np.degrees(np.arccos(np.clip(cos_angle, -1.0, 1.0))))


def _torso_lean_angle(coords: np.ndarray) -> float:
    """
    Angle of torso from vertical (0° = perfectly upright).
    Computed from hip-center → shoulder-center vector vs. the upward axis.

    In image coordinates (y increases downward), vertical is [0, -1].
    We convert to a standard frame where up is positive.
    """
    left_hip = coords[int(LandmarkIndex.LEFT_HIP)][:2]
    right_hip = coords[int(LandmarkIndex.RIGHT_HIP)][:2]
    left_shoulder = coords[int(LandmarkIndex.LEFT_SHOULDER)][:2]
    right_shoulder = coords[int(LandmarkIndex.RIGHT_SHOULDER)][:2]

    hip_center = (left_hip + right_hip) / 2.0
    shoulder_center = (left_shoulder + right_shoulder) / 2.0

    # Spine vector: hip → shoulder (should point "up" in image = negative y)
    spine = shoulder_center - hip_center
    vertical = np.array([0.0, -1.0])  # "up" in image coords

    norm_spine = np.linalg.norm(spine)
    if norm_spine < 1e-8:
        return 0.0
    cos_a = np.dot(spine / norm_spine, vertical)
    return float(np.degrees(np.arccos(np.clip(cos_a, -1.0, 1.0))))


class FeatureExtractor:
    """
    Converts a PoseFrame into a FeatureVector of joint angles.

    Normalization is applied before angle extraction so that the computed
    angles reflect true body geometry rather than camera projection artifacts.
    """

    def __init__(self, use_z: bool = False):
        """
        Args:
            use_z: Include depth (z) coordinate in angle computation.
                   Disabled by default — MediaPipe's z is less reliable than
                   x/y and can introduce noise on standard cameras.
        """
        self.use_z = use_z

    def extract(self, pose_frame: PoseFrame) -> FeatureVector:
        """Extract joint angle features from a single pose frame."""
        coords = normalize_landmarks(pose_frame, use_z=self.use_z)
        return FeatureVector(
            values=self._compute_angles(coords),
            feature_names=FEATURE_NAMES,
        )

    def extract_sequence(self, pose_frames: list[PoseFrame]) -> np.ndarray:
        """
        Extract features from a sequence of frames.

        Returns:
            np.ndarray of shape (T, NUM_FEATURES) — the multivariate time series.
        """
        vectors = [self.extract(f).values for f in pose_frames]
        if not vectors:
            return np.empty((0, NUM_FEATURES))
        return np.stack(vectors, axis=0)

    def _compute_angles(self, coords: np.ndarray) -> np.ndarray:
        """Compute all joint angles from normalized (33, D) coordinate array."""
        L = LandmarkIndex

        angles = np.array([
            # Knee angles: hip - knee - ankle
            _angle_at_vertex(
                coords[int(L.LEFT_HIP)],
                coords[int(L.LEFT_KNEE)],
                coords[int(L.LEFT_ANKLE)],
            ),
            _angle_at_vertex(
                coords[int(L.RIGHT_HIP)],
                coords[int(L.RIGHT_KNEE)],
                coords[int(L.RIGHT_ANKLE)],
            ),
            # Hip angles: shoulder - hip - knee
            _angle_at_vertex(
                coords[int(L.LEFT_SHOULDER)],
                coords[int(L.LEFT_HIP)],
                coords[int(L.LEFT_KNEE)],
            ),
            _angle_at_vertex(
                coords[int(L.RIGHT_SHOULDER)],
                coords[int(L.RIGHT_HIP)],
                coords[int(L.RIGHT_KNEE)],
            ),
            # Elbow angles: shoulder - elbow - wrist
            _angle_at_vertex(
                coords[int(L.LEFT_SHOULDER)],
                coords[int(L.LEFT_ELBOW)],
                coords[int(L.LEFT_WRIST)],
            ),
            _angle_at_vertex(
                coords[int(L.RIGHT_SHOULDER)],
                coords[int(L.RIGHT_ELBOW)],
                coords[int(L.RIGHT_WRIST)],
            ),
            # Shoulder angles: elbow - shoulder - hip
            _angle_at_vertex(
                coords[int(L.LEFT_ELBOW)],
                coords[int(L.LEFT_SHOULDER)],
                coords[int(L.LEFT_HIP)],
            ),
            _angle_at_vertex(
                coords[int(L.RIGHT_ELBOW)],
                coords[int(L.RIGHT_SHOULDER)],
                coords[int(L.RIGHT_HIP)],
            ),
            # Torso lean from vertical
            _torso_lean_angle(coords),
        ], dtype=np.float32)

        return angles
