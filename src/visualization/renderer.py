"""
Video renderer: second-pass over the source video to produce an annotated output.

Architecture: two-pass design
  Pass 1 (analysis): extract keypoints → features → DTW → scores (done by pipeline)
  Pass 2 (render):   re-read video, re-detect pose for pixel-accurate drawing,
                     overlay per-frame scores/deviations from the analysis result.

Why re-run pose detection in pass 2?
  The analysis stores features (joint angles) but not raw pixel coordinates.
  Drawing requires pixel positions. Re-running MediaPipe is fast on a recorded
  video (static_image_mode=True disables tracking overhead).

Frame mapping:
  If skip_frames=1 was used during analysis, every 2nd raw frame was processed.
  We map raw video frame index → analysis frame index with:
    analysis_idx = raw_idx // (skip_frames + 1)
  For unanalyzed frames, we carry forward the last known analysis state.

Output format:
  MP4 with H.264 encoding via OpenCV VideoWriter (fourcc='mp4v').
  Falls back to 'XVID' (.avi) if mp4v is unavailable on the platform.
"""

from __future__ import annotations
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from ..pose.detector import PoseDetector
from ..evaluation.classifier import ErrorEvent
from ..pipeline import AnalysisResult
from .overlay import FrameAnnotator


class VideoRenderer:
    """
    Produces an annotated video from a completed AnalysisResult.

    Usage:
        renderer = VideoRenderer()
        renderer.render(
            video_path="my_squat.mp4",
            result=analysis_result,
            output_path="my_squat_annotated.mp4",
        )
    """

    def __init__(
        self,
        show_angles: bool = True,
        show_reference_ghost: bool = False,
        model_complexity: int = 1,
    ):
        self.annotator = FrameAnnotator(
            show_angles=show_angles,
            show_reference_ghost=show_reference_ghost,
        )
        self.model_complexity = model_complexity

    def render(
        self,
        video_path: str,
        result: AnalysisResult,
        output_path: str,
        skip_frames: int = 0,
        show: bool = False,
    ) -> Path:
        """
        Write an annotated copy of video_path to output_path.

        Args:
            video_path: Source video (same file used for analysis).
            result: The AnalysisResult produced by AnalysisPipeline.analyze_video().
            output_path: Destination path for the annotated video (.mp4).
            skip_frames: Must match the skip_frames value used during analysis.
            show: If True, display each frame in a live window while rendering.
                  Press 'q' to abort early.

        Returns:
            Path to the output file.
        """
        cap = cv2.VideoCapture(int(video_path) if video_path.isdigit() else video_path)
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        out_path = Path(output_path)
        writer = self._make_writer(out_path, fps, w, h)

        # Pre-build a lookup: analysis_frame_idx → list of ErrorEvents active there
        active_at: dict[int, list[ErrorEvent]] = {}
        for event in result.error_events:
            for f in range(event.start_frame, event.end_frame + 1):
                active_at.setdefault(f, []).append(event)

        # Per-frame absolute deviations stored on the result (shape: T × F)
        per_frame_abs_devs = np.abs(result.per_frame_deviations)

        print(f"[Renderer] Rendering {result.exercise_name} → {out_path}")
        print(f"[Renderer] Video: {w}×{h} @ {fps:.1f}fps")

        raw_idx = 0
        analysis_idx = 0
        frame_score = 100.0
        feature_names = result.score_report.feature_names
        static_abs_devs = np.abs(result.score_report.mean_deviation)  # fallback

        with PoseDetector(
            model_complexity=self.model_complexity,
            static_image_mode=True,
        ) as detector:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                is_analysis_frame = (raw_idx % (skip_frames + 1) == 0)

                if is_analysis_frame and analysis_idx < result.detected_frame_count:
                    # Update per-frame score
                    scores = result.per_frame_scores
                    if analysis_idx < len(scores):
                        frame_score = float(scores[analysis_idx])

                    # Active errors at this analysis frame
                    active_errors = active_at.get(analysis_idx, [])

                    # Detect pose for pixel-accurate drawing
                    pose_frame = detector.detect(frame)

                    if pose_frame is not None:
                        # Real per-frame per-feature absolute deviations
                        if analysis_idx < len(per_frame_abs_devs):
                            abs_devs = per_frame_abs_devs[analysis_idx]
                        else:
                            abs_devs = static_abs_devs

                        annotated = self.annotator.annotate(
                            frame=frame,
                            pose_frame=pose_frame,
                            frame_score=frame_score,
                            abs_deviations=abs_devs,
                            feature_names=feature_names,
                            active_errors=active_errors if active_errors else None,
                            overall_score=result.overall_score,
                        )
                    else:
                        # No pose detected this frame — draw plain score overlay
                        annotated = frame.copy()
                        self._draw_no_pose_warning(annotated, frame_score, result.overall_score)

                    analysis_idx += 1
                else:
                    # Carry-forward frame: just re-draw last score without new detection
                    annotated = frame.copy()
                    self._draw_carryforward(annotated, frame_score, result.overall_score)

                writer.write(annotated)

                if show:
                    cv2.imshow(f"AI Trainer — {result.exercise_name}", annotated)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        print("[Renderer] Aborted by user.")
                        break

                raw_idx += 1

        cap.release()
        writer.release()
        if show:
            cv2.destroyAllWindows()

        print(f"[Renderer] Done. Output: {out_path} ({raw_idx} frames)")
        return out_path

    # ── Static helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _make_writer(
        path: Path,
        fps: float,
        w: int,
        h: int,
    ) -> cv2.VideoWriter:
        path.parent.mkdir(parents=True, exist_ok=True)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(path), fourcc, fps, (w, h))
        if not writer.isOpened():
            # Fallback to XVID .avi
            avi_path = path.with_suffix(".avi")
            fourcc = cv2.VideoWriter_fourcc(*"XVID")
            writer = cv2.VideoWriter(str(avi_path), fourcc, fps, (w, h))
            if not writer.isOpened():
                raise RuntimeError("Cannot open VideoWriter. Check codec availability.")
            print(f"[Renderer] mp4v unavailable, writing to {avi_path}")
        return writer

    @staticmethod
    def _draw_no_pose_warning(frame: np.ndarray, frame_score: float, overall: float):
        h, w = frame.shape[:2]
        cv2.putText(frame, "No pose detected", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 220), 2, cv2.LINE_AA)

    @staticmethod
    def _draw_carryforward(frame: np.ndarray, frame_score: float, overall: float):
        """Minimal overlay for frames that weren't in the analysis set."""
        h, w = frame.shape[:2]
        label = f"Score: {frame_score:.0f}"
        cv2.putText(frame, label, (w - 110, 24),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1, cv2.LINE_AA)
