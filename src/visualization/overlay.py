"""
Frame annotation: draws pose skeleton, score meter, and feedback on video frames.

Visual design:
  - Skeleton joints/connections are color-coded by deviation severity:
      green  (< 8 deg)  — within technical tolerance
      yellow (8-12 deg) — technical error
      red    (> 12 deg) — critical / injury-risk
  - Score meter: vertical bar in the top-right corner
  - Active feedback cue: semi-transparent banner at the bottom
  - Key angle values: drawn near the corresponding joint

Color space: BGR (OpenCV convention throughout).
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
from mediapipe.tasks.python.vision import PoseLandmarksConnections

from ..evaluation.classifier import ErrorEvent, ErrorSeverity
from ..features.extractor import FEATURE_NAMES, CRITICAL_FEATURES
from ..pose.keypoints import LandmarkIndex, PoseFrame

# ── Color palette (BGR) ──────────────────────────────────────────────────────
C_GOOD = (60, 200, 60)        # green
C_WARNING = (0, 190, 255)     # amber/yellow
C_CRITICAL = (40, 40, 220)    # red
C_NEUTRAL = (160, 160, 160)   # grey (no data yet)
C_WHITE = (255, 255, 255)
C_BLACK = (0, 0, 0)
C_DARK = (30, 30, 30)
C_PANEL_BG = (20, 20, 20)

# Deviation thresholds that map to colors (in degrees)
THRESH_GOOD = 8.0
THRESH_WARN = 12.0

# MediaPipe skeleton connections — (start_idx, end_idx) pairs
_MP_CONNECTIONS = [
    (c.start, c.end) for c in PoseLandmarksConnections.POSE_LANDMARKS
]

# Maps a feature name to the landmark index that is the "vertex" of that angle.
# That landmark is highlighted when the corresponding feature deviates.
FEATURE_TO_VERTEX: Dict[str, LandmarkIndex] = {
    "left_knee_angle":      LandmarkIndex.LEFT_KNEE,
    "right_knee_angle":     LandmarkIndex.RIGHT_KNEE,
    "left_hip_angle":       LandmarkIndex.LEFT_HIP,
    "right_hip_angle":      LandmarkIndex.RIGHT_HIP,
    "left_elbow_angle":     LandmarkIndex.LEFT_ELBOW,
    "right_elbow_angle":    LandmarkIndex.RIGHT_ELBOW,
    "left_shoulder_angle":  LandmarkIndex.LEFT_SHOULDER,
    "right_shoulder_angle": LandmarkIndex.RIGHT_SHOULDER,
    # torso_lean affects the full spine, mapped to both hips in _joint_colors()
}

# Labels shown near joint vertices (short to avoid clutter)
FEATURE_SHORT_LABEL: Dict[str, str] = {
    "left_knee_angle":      "LK",
    "right_knee_angle":     "RK",
    "left_hip_angle":       "LH",
    "right_hip_angle":      "RH",
    "left_elbow_angle":     "LE",
    "right_elbow_angle":    "RE",
    "left_shoulder_angle":  "LS",
    "right_shoulder_angle": "RS",
    "torso_lean":           "BK",
}


def _deviation_to_color(deviation_deg: float) -> Tuple[int, int, int]:
    if deviation_deg < THRESH_GOOD:
        return C_GOOD
    elif deviation_deg < THRESH_WARN:
        return C_WARNING
    return C_CRITICAL


def compute_joint_colors(
    abs_deviations: np.ndarray,
    feature_names: List[str],
) -> Dict[int, Tuple[int, int, int]]:
    """
    Build a landmark_index → BGR color mapping from per-feature deviations.

    Each landmark gets the color of the worst-scoring feature it participates in.
    Landmarks not involved in any tracked feature are colored neutral grey.

    Args:
        abs_deviations: shape (F,), absolute deviation per feature in degrees.
        feature_names: ordered feature name list matching abs_deviations.
    """
    # Start all landmarks neutral
    colors: Dict[int, Tuple[int, int, int]] = {
        i: C_NEUTRAL for i in range(33)
    }

    feature_dev = dict(zip(feature_names, abs_deviations))

    for feat, lm in FEATURE_TO_VERTEX.items():
        dev = feature_dev.get(feat, 0.0)
        color = _deviation_to_color(dev)
        idx = int(lm)
        # Keep the worst color already assigned (critical > warning > good)
        existing = colors[idx]
        if existing == C_CRITICAL:
            continue
        if existing == C_WARNING and color == C_GOOD:
            continue
        colors[idx] = color

    # torso_lean: color left_hip, right_hip, left_shoulder, right_shoulder
    torso_dev = feature_dev.get("torso_lean", 0.0)
    torso_color = _deviation_to_color(torso_dev)
    for lm in (
        LandmarkIndex.LEFT_HIP, LandmarkIndex.RIGHT_HIP,
        LandmarkIndex.LEFT_SHOULDER, LandmarkIndex.RIGHT_SHOULDER,
    ):
        idx = int(lm)
        existing = colors[idx]
        if existing != C_CRITICAL:
            if existing != C_WARNING or torso_color == C_CRITICAL:
                colors[idx] = torso_color

    return colors


def _lm_to_px(
    landmark: "PoseLandmark",
    w: int,
    h: int,
) -> Tuple[int, int]:
    """Convert normalized [0,1] landmark to pixel coordinates."""
    return int(landmark.x * w), int(landmark.y * h)


class FrameAnnotator:
    """
    Draws pose skeleton, score panel, and feedback text onto a video frame.

    Create once, call annotate() for each frame.
    """

    def __init__(self, show_angles: bool = True, show_reference_ghost: bool = False):
        """
        Args:
            show_angles: Draw angle value labels near each joint vertex.
            show_reference_ghost: Draw reference pose as a ghost skeleton
                                  (requires reference_pose to be passed to annotate).
        """
        self.show_angles = show_angles
        self.show_reference_ghost = show_reference_ghost

    def annotate(
        self,
        frame: np.ndarray,
        pose_frame: PoseFrame,
        frame_score: float,
        abs_deviations: np.ndarray,
        feature_names: List[str],
        feature_values: Optional[np.ndarray] = None,
        active_errors: Optional[List[ErrorEvent]] = None,
        overall_score: Optional[float] = None,
        reference_pose: Optional[PoseFrame] = None,
    ) -> np.ndarray:
        """
        Produce a fully annotated copy of frame.

        Args:
            frame: BGR frame from cv2.VideoCapture.
            pose_frame: Detected pose for this frame.
            frame_score: Per-frame score in [0, 100].
            abs_deviations: shape (F,) absolute deviations per feature (degrees).
            feature_names: feature name list aligned with abs_deviations.
            feature_values: shape (F,) raw angle values for annotation labels.
            active_errors: Error events that are active at this frame.
            overall_score: Session-level aggregate score (shown in panel header).
            reference_pose: Optional reference pose to draw as ghost.

        Returns:
            Annotated BGR frame.
        """
        out = frame.copy()
        h, w = out.shape[:2]

        joint_colors = compute_joint_colors(abs_deviations, feature_names)

        if self.show_reference_ghost and reference_pose is not None:
            self._draw_skeleton(out, reference_pose, w, h,
                                default_color=(100, 100, 100), alpha=0.4, radius=4)

        self._draw_skeleton(out, pose_frame, w, h,
                            joint_colors=joint_colors, radius=7)

        if self.show_angles and feature_values is not None:
            self._draw_angle_labels(out, pose_frame, w, h,
                                    feature_values, abs_deviations, feature_names)

        self._draw_score_meter(out, w, h, frame_score, overall_score)
        self._draw_legend(out, w, h)

        if active_errors:
            self._draw_feedback_banner(out, w, h, active_errors)

        return out

    # ── Drawing sub-routines ─────────────────────────────────────────────────

    def _draw_skeleton(
        self,
        frame: np.ndarray,
        pose_frame: PoseFrame,
        w: int,
        h: int,
        joint_colors: Optional[Dict[int, Tuple[int, int, int]]] = None,
        default_color: Tuple[int, int, int] = C_NEUTRAL,
        alpha: float = 1.0,
        radius: int = 6,
    ):
        """Draw landmark circles and bone connections."""
        lms = pose_frame.landmarks
        vis_mask = pose_frame.visibility_mask(threshold=0.4)

        overlay = frame.copy() if alpha < 1.0 else frame

        # Draw connections (bones)
        for start_idx, end_idx in _MP_CONNECTIONS:
            if not (vis_mask[start_idx] and vis_mask[end_idx]):
                continue
            p1 = _lm_to_px(lms[start_idx], w, h)
            p2 = _lm_to_px(lms[end_idx], w, h)
            # Color the connection by the worst color of its two endpoints
            c1 = joint_colors.get(start_idx, default_color) if joint_colors else default_color
            c2 = joint_colors.get(end_idx, default_color) if joint_colors else default_color
            bone_color = _worse_color(c1, c2)
            cv2.line(overlay, p1, p2, bone_color, 2, cv2.LINE_AA)

        # Draw landmark circles
        for idx, lm in enumerate(lms):
            if not vis_mask[idx]:
                continue
            px, py = _lm_to_px(lm, w, h)
            color = joint_colors.get(idx, default_color) if joint_colors else default_color
            cv2.circle(overlay, (px, py), radius, color, -1, cv2.LINE_AA)
            cv2.circle(overlay, (px, py), radius + 1, C_BLACK, 1, cv2.LINE_AA)

        if alpha < 1.0:
            cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)

    def _draw_angle_labels(
        self,
        frame: np.ndarray,
        pose_frame: PoseFrame,
        w: int,
        h: int,
        feature_values: np.ndarray,
        abs_deviations: np.ndarray,
        feature_names: List[str],
    ):
        """Draw small angle value labels near each joint vertex."""
        feat_map = dict(zip(feature_names, zip(feature_values, abs_deviations)))

        for feat, lm_idx in FEATURE_TO_VERTEX.items():
            if feat not in feat_map:
                continue
            val, dev = feat_map[feat]
            lm = pose_frame.landmarks[int(lm_idx)]
            if lm.visibility < 0.4:
                continue

            px, py = _lm_to_px(lm, w, h)
            label = f"{FEATURE_SHORT_LABEL.get(feat, feat[:2])}: {val:.0f}"
            color = _deviation_to_color(dev)

            # Offset label to avoid overlap with the joint circle
            tx, ty = px + 10, py - 10
            _draw_text_with_bg(frame, label, (tx, ty), font_scale=0.38,
                               text_color=color, bg_color=C_DARK, thickness=1)

        # torso_lean: draw near hip center
        if "torso_lean" in feat_map:
            val, dev = feat_map["torso_lean"]
            left_hip = pose_frame.get(LandmarkIndex.LEFT_HIP)
            right_hip = pose_frame.get(LandmarkIndex.RIGHT_HIP)
            if left_hip.visibility > 0.4 and right_hip.visibility > 0.4:
                cx = int((left_hip.x + right_hip.x) / 2 * w) + 10
                cy = int((left_hip.y + right_hip.y) / 2 * h) - 20
                label = f"BK: {val:.0f}"
                color = _deviation_to_color(dev)
                _draw_text_with_bg(frame, label, (cx, cy), font_scale=0.38,
                                   text_color=color, bg_color=C_DARK, thickness=1)

    def _draw_score_meter(
        self,
        frame: np.ndarray,
        w: int,
        h: int,
        frame_score: float,
        overall_score: Optional[float],
    ):
        """
        Vertical score bar in the top-right corner.

        The bar fills from bottom to top proportional to the current frame score.
        Color transitions: red (0-60) → yellow (60-80) → green (80-100).
        """
        bar_w = 28
        bar_h = 160
        margin = 14
        x0 = w - margin - bar_w
        y0 = margin
        x1, y1 = x0 + bar_w, y0 + bar_h

        # Background panel
        cv2.rectangle(frame, (x0 - 6, y0 - 24), (x1 + 6, y1 + 6), C_PANEL_BG, -1)

        # Score label above bar
        score_label = f"{frame_score:.0f}"
        _draw_text_with_bg(frame, score_label,
                           (x0 + bar_w // 2 - 12, y0 - 6),
                           font_scale=0.55, text_color=C_WHITE,
                           bg_color=C_PANEL_BG, thickness=1)

        # Empty bar border
        cv2.rectangle(frame, (x0, y0), (x1, y1), (80, 80, 80), 1)

        # Filled portion
        fill_h = int(bar_h * frame_score / 100.0)
        if fill_h > 0:
            fy0 = y1 - fill_h
            bar_color = _score_to_color(frame_score)
            cv2.rectangle(frame, (x0, fy0), (x1, y1), bar_color, -1)

        # "SCORE" text below bar
        _draw_text_with_bg(frame, "SCORE",
                           (x0 - 2, y1 + 18),
                           font_scale=0.38, text_color=(180, 180, 180),
                           bg_color=C_PANEL_BG, thickness=1)

        # Overall session score (if provided)
        if overall_score is not None:
            ov_label = f"AVG {overall_score:.0f}"
            _draw_text_with_bg(frame, ov_label,
                               (x0 - 4, y1 + 34),
                               font_scale=0.36, text_color=(140, 200, 255),
                               bg_color=C_PANEL_BG, thickness=1)

    def _draw_legend(self, frame: np.ndarray, w: int, h: int):
        """Small color legend in bottom-right corner."""
        items = [
            (C_GOOD, "Good"),
            (C_WARNING, "Warning"),
            (C_CRITICAL, "Critical"),
        ]
        margin = 10
        line_h = 18
        x0 = w - 90
        y_start = h - margin - len(items) * line_h

        bg_x0 = x0 - 4
        bg_y0 = y_start - 4
        cv2.rectangle(frame,
                      (bg_x0, bg_y0),
                      (w - margin + 4, h - margin + 4),
                      C_PANEL_BG, -1)

        for i, (color, label) in enumerate(items):
            y = y_start + i * line_h
            cv2.circle(frame, (x0 + 6, y + 5), 5, color, -1)
            cv2.putText(frame, label, (x0 + 16, y + 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.36, C_WHITE, 1, cv2.LINE_AA)

    def _draw_feedback_banner(
        self,
        frame: np.ndarray,
        w: int,
        h: int,
        active_errors: List[ErrorEvent],
    ):
        """Semi-transparent feedback banner at the bottom of the frame."""
        if not active_errors:
            return

        # Pick the most severe active error
        active_errors = sorted(
            active_errors,
            key=lambda e: (0 if e.severity == ErrorSeverity.CRITICAL else 1,
                           -e.mean_deviation_deg)
        )
        top_error = active_errors[0]

        # Look up the coaching cue for this error
        from ..feedback.generator import _RULES
        from ..evaluation.classifier import ErrorDirection
        rule = _RULES.get((top_error.feature_name, top_error.direction))
        if rule is None:
            return

        cue_text = rule["cue"]
        severity_tag = "CRITICAL" if top_error.severity == ErrorSeverity.CRITICAL else "FORM TIP"
        banner_color = C_CRITICAL if top_error.severity == ErrorSeverity.CRITICAL else C_WARNING

        banner_h = 52
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, h - banner_h), (w, h), C_DARK, -1)
        cv2.addWeighted(overlay, 0.78, frame, 0.22, 0, frame)

        # Severity tag
        cv2.putText(frame, f"[{severity_tag}]",
                    (12, h - banner_h + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, banner_color, 1, cv2.LINE_AA)

        # Cue text — wrap if too long
        max_chars = w // 10
        if len(cue_text) > max_chars:
            cue_text = cue_text[:max_chars - 3] + "..."

        cv2.putText(frame, cue_text,
                    (12, h - banner_h + 42),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.58, C_WHITE, 1, cv2.LINE_AA)

        # Deviation indicator on the right
        dev_text = f"{top_error.mean_deviation_deg:.1f} deg off"
        tw, _ = cv2.getTextSize(dev_text, cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)[:2]
        cv2.putText(frame, dev_text,
                    (w - tw[0] - 10 if isinstance(tw, tuple) else w - 120, h - banner_h + 34),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, banner_color, 1, cv2.LINE_AA)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _draw_text_with_bg(
    frame: np.ndarray,
    text: str,
    origin: Tuple[int, int],
    font_scale: float = 0.5,
    text_color: Tuple[int, int, int] = C_WHITE,
    bg_color: Tuple[int, int, int] = C_BLACK,
    thickness: int = 1,
):
    font = cv2.FONT_HERSHEY_SIMPLEX
    (tw, th), baseline = cv2.getTextSize(text, font, font_scale, thickness)
    x, y = origin
    pad = 2
    cv2.rectangle(frame, (x - pad, y - th - pad), (x + tw + pad, y + baseline + pad),
                  bg_color, -1)
    cv2.putText(frame, text, (x, y), font, font_scale, text_color, thickness, cv2.LINE_AA)


def _worse_color(
    c1: Tuple[int, int, int],
    c2: Tuple[int, int, int],
) -> Tuple[int, int, int]:
    """Return the higher-severity color of two."""
    rank = {id(C_GOOD): 0, id(C_NEUTRAL): 0, id(C_WARNING): 1, id(C_CRITICAL): 2}
    r1 = 2 if c1 == C_CRITICAL else (1 if c1 == C_WARNING else 0)
    r2 = 2 if c2 == C_CRITICAL else (1 if c2 == C_WARNING else 0)
    return c1 if r1 >= r2 else c2


def _score_to_color(score: float) -> Tuple[int, int, int]:
    """Interpolate bar color from red (0) through yellow (60) to green (100)."""
    if score >= 80:
        # green
        t = (score - 80) / 20.0
        r = int(60 * (1 - t))
        g = int(180 + 20 * t)
        b = int(60 * (1 - t))
        return (b, g, r)
    elif score >= 60:
        # yellow
        t = (score - 60) / 20.0
        return (0, int(160 + 40 * t), int(230 - 40 * t))
    else:
        # red
        return C_CRITICAL
