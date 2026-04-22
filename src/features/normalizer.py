"""
Pose normalization to remove camera and scale dependencies.

The core problem: raw MediaPipe coordinates encode both the person's actual
movement AND irrelevant factors like:
  - Distance from camera (scale)
  - Camera height / angle (translation)
  - Person's height (scale)

Strategy - Hip-center normalization with torso-scale:
  1. Translate: move hip midpoint to origin
  2. Scale: divide by torso length (distance from hip center to shoulder center)
  3. This makes coordinates invariant to camera distance and person height

We operate on the (33, 3) array of landmarks and return a normalized copy.
"""

import numpy as np

from ..pose.keypoints import PoseFrame, LandmarkIndex


# Landmark indices for normalization reference points
_LEFT_HIP = int(LandmarkIndex.LEFT_HIP)
_RIGHT_HIP = int(LandmarkIndex.RIGHT_HIP)
_LEFT_SHOULDER = int(LandmarkIndex.LEFT_SHOULDER)
_RIGHT_SHOULDER = int(LandmarkIndex.RIGHT_SHOULDER)


def normalize_landmarks(pose_frame: PoseFrame, use_z: bool = True) -> np.ndarray:
    """
    Normalize a PoseFrame's landmarks into a scale/position-invariant coordinate
    system.

    Steps:
      1. Compute hip center (midpoint of left and right hip).
      2. Compute shoulder center (midpoint of left and right shoulder).
      3. Compute torso length = distance(hip_center, shoulder_center).
      4. Translate all landmarks so hip center is at origin.
      5. Scale all landmarks by 1/torso_length.

    Returns:
        np.ndarray of shape (33, 3) or (33, 2) with normalized coordinates.
    """
    coords = pose_frame.as_array(use_z=use_z)  # (33, D)

    hip_center = (coords[_LEFT_HIP] + coords[_RIGHT_HIP]) / 2.0
    shoulder_center = (coords[_LEFT_SHOULDER] + coords[_RIGHT_SHOULDER]) / 2.0

    torso_length = np.linalg.norm(shoulder_center - hip_center)
    if torso_length < 1e-6:
        # Fallback: avoid division by zero when landmarks collapse
        torso_length = 1.0

    normalized = (coords - hip_center) / torso_length
    return normalized
