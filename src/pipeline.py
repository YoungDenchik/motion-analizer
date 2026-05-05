"""
Main analysis pipeline: orchestrates all stages end-to-end.

Pipeline stages:
  video → keypoints → features → time series
       → rep segmentation → per-rep DTW → score → feedback

Two primary modes:

  RECORD mode:
    Process a video, extract features, smooth, and save as a reference.
    The reference may contain 1 or more reps — the comparator averages
    them into a single canonical rep template.

  ANALYZE mode:
    Process a user's video, auto-detect rep boundaries, compare each rep
    individually against the reference template, then aggregate scores.
    The result is independent of how many reps the user performed.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
import time

import numpy as np

from .pose.detector import PoseDetector, extract_frames_from_video
from .pose.keypoints import PoseFrame
from .features.extractor import FeatureExtractor, FEATURE_NAMES
from .timeseries.builder import TimeSeries, build_time_series_from_array
from .timeseries.segmentation import RepSegmenter
from .comparison.dtw import DTWComparator
from .comparison.rep_comparator import RepComparator, RepComparisonResult
from .evaluation.scorer import ScoringEngine, ScoreReport
from .evaluation.classifier import ErrorClassifier, ErrorEvent
from .feedback.generator import FeedbackGenerator, FeedbackReport
from .reference.store import ReferenceStore, ReferenceSequence


@dataclass
class AnalysisResult:
    """Complete output of one exercise analysis session."""
    exercise_name: str
    overall_score: float
    grade: str
    duration_seconds: float
    frame_count: int
    detected_frame_count: int

    # Rep-level breakdown
    num_reps: int
    per_rep_scores: List[float]         # score per detected rep
    score_consistency: float            # std dev of per-rep scores (lower = more consistent)
    best_rep_index: int                 # 0-based index of best-scored rep
    worst_rep_index: int                # 0-based index of worst-scored rep

    # Frame-level data (concatenated across all reps, aligned to user video)
    per_frame_scores: np.ndarray        # shape: (detected_frame_count,)
    per_frame_deviations: np.ndarray    # shape: (detected_frame_count, F)

    # DTW / scoring
    dtw_distance: float
    normalized_dtw_distance: float

    error_events: List[ErrorEvent]
    feedback_report: FeedbackReport
    score_report: ScoreReport
    user_time_series: TimeSeries
    reference_time_series: TimeSeries
    rep_comparison: RepComparisonResult
    processing_time_seconds: float = 0.0

    def print_summary(self):
        self.feedback_report.print()

        print("  Rep breakdown:")
        for i, s in enumerate(self.per_rep_scores):
            marker = ""
            if i == self.best_rep_index:
                marker = "  <- best"
            elif i == self.worst_rep_index:
                marker = "  <- needs work"
            print(f"    Rep {i + 1}: {s:.1f}/100{marker}")

        print(f"\n  Consistency: {self.score_consistency:.1f} deg std dev "
              f"({'stable' if self.score_consistency < 5 else 'variable'})")
        print(f"  Frames detected: {self.detected_frame_count}/{self.frame_count}")
        print(f"  Duration: {self.duration_seconds:.1f}s")
        print(f"  Processing time: {self.processing_time_seconds:.2f}s")


class AnalysisPipeline:
    """
    Orchestrates the full fitness coaching analysis pipeline.

    Comparison is repetition-count-independent: the user can perform any
    number of reps and will be scored on technique quality, not rep count.
    """

    def __init__(
        self,
        references_dir: str | None = None,
        model_complexity: int = 1,
        sensitivity: float = 0.05,
        skip_frames: int = 0,
        smooth: bool = True,
    ):
        self.model_complexity = model_complexity
        self.skip_frames = skip_frames
        self.smooth = smooth

        self.extractor = FeatureExtractor(use_z=False)
        self.segmenter = RepSegmenter()
        self.rep_comparator = RepComparator(
            segmenter=self.segmenter,
            dtw_comparator=DTWComparator(),
            scoring_sensitivity=sensitivity,
        )
        self.scorer = ScoringEngine(sensitivity=sensitivity)
        self.classifier = ErrorClassifier()
        self.feedback_gen = FeedbackGenerator()
        self.store = ReferenceStore(references_dir) if references_dir else ReferenceStore()

    # ── Public API ────────────────────────────────────────────────────────────

    def record_reference(
        self,
        exercise_name: str,
        video_path: str,
        description: str = "",
        overwrite: bool = False,
    ) -> ReferenceSequence:
        """
        Extract features from a video and save as reference for an exercise.
        The reference may contain one or more reps — multiple reps are averaged
        into a canonical template during analysis.
        """
        print(f"[Pipeline] Recording reference for '{exercise_name}' from: {video_path}")
        time_series = self._process_video(video_path)

        if time_series.num_frames < 10:
            raise RuntimeError(
                f"Only {time_series.num_frames} frames detected in reference video. "
                "Ensure the person is clearly visible throughout."
            )

        # Report what was detected in the reference
        ref_seg = self.segmenter.segment(time_series)
        print(f"[Pipeline] Detected {len(ref_seg.reps)} rep(s) in reference "
              f"(indicator: {ref_seg.indicator_feature})")

        path = self.store.save(
            name=exercise_name,
            time_series=time_series,
            description=description,
            overwrite=overwrite,
        )
        print(f"[Pipeline] Reference saved: {path} ({time_series.num_frames} frames)")
        return self.store.load(exercise_name)

    def analyze_video(
        self,
        video_path: str,
        exercise_name: str,
    ) -> AnalysisResult:
        """
        Analyze a user's exercise video against a stored reference.

        The comparison is rep-count-independent: scores reflect technique
        quality averaged across however many reps the user performed.
        """
        t_start = time.time()
        print(f"[Pipeline] Analyzing '{exercise_name}' from: {video_path}")

        user_ts = self._process_video(video_path)

        if user_ts.num_frames < 5:
            raise RuntimeError(
                f"Insufficient pose detection ({user_ts.num_frames} frames). "
                "Check lighting and ensure the full body is visible."
            )

        print(f"[Pipeline] User sequence: {user_ts.num_frames} frames, "
              f"{user_ts.duration_seconds:.1f}s")

        # Auto-select the best-matching reference variant (handles multiple
        # references per exercise at different angles / technique styles).
        reference = self.store.find_best_match(user_ts, exercise_name)
        print(f"[Pipeline] Using reference: '{reference.name}' "
              f"({reference.time_series.num_frames} frames)")

        # ── Rep-aware comparison ──────────────────────────────────────────────
        rep_result = self.rep_comparator.compare(user_ts, reference.time_series)

        # Build aggregate DTWResult for scorer and classifier
        combined_dtw = rep_result.combined_dtw
        score_report = self.scorer.score(combined_dtw)

        # Override per-frame scores with the rep-aligned version
        score_report = ScoreReport(
            overall_score=rep_result.overall_score,
            per_frame_scores=rep_result.per_frame_scores,
            per_feature_scores=score_report.per_feature_scores,
            mean_deviation=combined_dtw.per_frame_deviations.mean(axis=0),
            max_deviation=np.abs(combined_dtw.per_frame_deviations).max(axis=0),
            dtw_distance=combined_dtw.distance,
            normalized_dtw_distance=combined_dtw.normalized_distance,
            feature_names=combined_dtw.feature_names,
        )

        error_events = self.classifier.classify(combined_dtw)
        feedback = self.feedback_gen.generate(error_events, score_report)

        processing_time = time.time() - t_start
        raw_frame_count = int(user_ts.num_frames * (self.skip_frames + 1))

        return AnalysisResult(
            exercise_name=exercise_name,
            overall_score=rep_result.overall_score,
            grade=score_report.grade,
            duration_seconds=user_ts.duration_seconds,
            frame_count=raw_frame_count,
            detected_frame_count=user_ts.num_frames,
            num_reps=rep_result.num_user_reps,
            per_rep_scores=rep_result.per_rep_scores,
            score_consistency=rep_result.score_std,
            best_rep_index=rep_result.best_rep_index,
            worst_rep_index=rep_result.worst_rep_index,
            per_frame_scores=rep_result.per_frame_scores,
            per_frame_deviations=rep_result.per_frame_deviations,
            dtw_distance=combined_dtw.distance,
            normalized_dtw_distance=combined_dtw.normalized_distance,
            error_events=error_events,
            feedback_report=feedback,
            score_report=score_report,
            user_time_series=user_ts,
            reference_time_series=reference.time_series,
            rep_comparison=rep_result,
            processing_time_seconds=processing_time,
        )

    def list_references(self) -> List[str]:
        return self.store.list_exercises()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _process_video(self, video_path: str) -> TimeSeries:
        """video → pose keypoints → joint angle features → TimeSeries."""
        with PoseDetector(model_complexity=self.model_complexity) as detector:
            pose_frames = extract_frames_from_video(
                video_path, detector, skip_frames=self.skip_frames
            )

        print(f"[Pipeline] Detected pose in {len(pose_frames)} frames")

        if not pose_frames:
            raise RuntimeError(f"No pose detected in video: {video_path}")

        feature_array = self.extractor.extract_sequence(pose_frames)
        return build_time_series_from_array(
            feature_array,
            feature_names=FEATURE_NAMES,
            smooth=self.smooth,
        )
