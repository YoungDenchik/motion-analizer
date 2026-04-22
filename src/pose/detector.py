"""
Pose detection using MediaPipe Tasks PoseLandmarker (MediaPipe >= 0.10).

MediaPipe 0.10 replaced the legacy `mp.solutions.pose` API with a Tasks-based
API that requires a `.task` model bundle. The model is downloaded automatically
on first use and cached locally.

Model: pose_landmarker_full — 33 landmarks, good accuracy, runs on CPU.
Alternatives: pose_landmarker_lite (faster), pose_landmarker_heavy (more accurate).
"""

from __future__ import annotations
import urllib.request
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import (
    PoseLandmarker,
    PoseLandmarkerOptions,
    RunningMode,
)
import mediapipe as mp

from .keypoints import PoseFrame, PoseLandmark


# Model bundle — downloaded once, cached in the project root
_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "pose_landmarker/pose_landmarker_full/float16/latest/"
    "pose_landmarker_full.task"
)
_MODEL_PATH = Path(__file__).parent.parent.parent / "pose_landmarker_full.task"


def _ensure_model() -> str:
    """Download the MediaPipe pose model if not already present."""
    if _MODEL_PATH.exists():
        return str(_MODEL_PATH)

    print(f"[PoseDetector] Downloading MediaPipe pose model (~6 MB)...")
    print(f"  Destination: {_MODEL_PATH}")
    try:
        urllib.request.urlretrieve(_MODEL_URL, _MODEL_PATH)
        print("[PoseDetector] Model downloaded successfully.")
    except Exception as e:
        raise RuntimeError(
            f"Failed to download MediaPipe model from {_MODEL_URL}.\n"
            f"  Error: {e}\n"
            f"  You can download it manually and place it at:\n"
            f"  {_MODEL_PATH}"
        ) from e
    return str(_MODEL_PATH)


class PoseDetector:
    """
    Wraps MediaPipe Tasks PoseLandmarker for frame-by-frame detection.

    Usage:
        with PoseDetector() as detector:
            pose = detector.detect(bgr_frame)
            if pose:
                ...
    """

    def __init__(
        self,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
        static_image_mode: bool = False,
        model_complexity: int = 1,  # kept for API compatibility, selects model variant
    ):
        model_path = _ensure_model()
        mode = RunningMode.IMAGE if static_image_mode else RunningMode.VIDEO

        options = PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=model_path),
            running_mode=mode,
            min_pose_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
            num_poses=1,
        )
        self._landmarker = PoseLandmarker.create_from_options(options)
        self._static_mode = static_image_mode
        self._frame_index = 0
        self._timestamp_ms = 0

    def detect(self, bgr_frame: np.ndarray) -> Optional[PoseFrame]:
        """
        Run pose estimation on a single BGR frame from cv2.VideoCapture.
        Returns None when no person is detected.
        """
        rgb = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        if self._static_mode:
            result = self._landmarker.detect(mp_image)
        else:
            self._timestamp_ms += 33  # ~30 fps
            result = self._landmarker.detect_for_video(mp_image, self._timestamp_ms)

        if not result.pose_landmarks:
            self._frame_index += 1
            return None

        raw_lms = result.pose_landmarks[0]  # first (and only) person
        landmarks = [
            PoseLandmark(
                x=lm.x,
                y=lm.y,
                z=lm.z,
                visibility=lm.visibility if lm.visibility is not None else 1.0,
            )
            for lm in raw_lms
        ]

        pose_frame = PoseFrame(landmarks=landmarks, frame_index=self._frame_index)
        self._frame_index += 1
        return pose_frame

    def reset(self):
        self._frame_index = 0
        self._timestamp_ms = 0

    def close(self):
        self._landmarker.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


def extract_frames_from_video(
    video_path: str,
    detector: PoseDetector,
    skip_frames: int = 0,
) -> list[PoseFrame]:
    """
    Process a video file and return all detected pose frames.

    Args:
        video_path: Path to video file, or '0' for webcam.
        detector: A PoseDetector instance.
        skip_frames: Process every (skip_frames+1)th frame. 0 = all frames.
    """
    source = int(video_path) if video_path.isdigit() else video_path
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video source: {video_path}")

    pose_frames: list[PoseFrame] = []
    raw_index = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if raw_index % (skip_frames + 1) == 0:
                result = detector.detect(frame)
                if result is not None:
                    pose_frames.append(result)

            raw_index += 1
    finally:
        cap.release()

    return pose_frames
