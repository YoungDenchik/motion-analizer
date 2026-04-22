"""
AI Fitness Coach — Command-line interface.

Commands:
  record   Record a reference exercise from a video
  analyze  Analyze a user video against a stored reference
  list     List all stored reference exercises
  demo     Run a self-test using synthetic data (no video needed)

Examples:
  # Record a squat reference from a video file
  python main.py record squat --video reference_squat.mp4

  # Record from webcam (device 0)
  python main.py record squat --video 0

  # Analyze a user's squat
  python main.py analyze squat --video my_squat.mp4

  # List stored references
  python main.py list

  # Run demo with synthetic data (tests pipeline without a camera)
  python main.py demo
"""

import argparse
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Synthetic demo: verifies the full pipeline without a real video
# ---------------------------------------------------------------------------
def run_demo():
    """
    Verify the full rep-aware pipeline with synthetic data.

    Simulates:
      - Reference: 1 perfect squat rep (60 frames)
      - User:      3 squat reps (210 frames) with form errors
        Rep 1: good form
        Rep 2: knee doesn't reach depth + forward lean
        Rep 3: asymmetric knees

    Expected: three separate scores, one per rep — NOT a collapsed
    score penalised by the rep-count mismatch.
    """
    import numpy as np
    from src.timeseries.builder import build_time_series_from_array
    from src.features.extractor import FEATURE_NAMES, NUM_FEATURES
    from src.comparison.rep_comparator import RepComparator
    from src.evaluation.scorer import ScoringEngine
    from src.evaluation.classifier import ErrorClassifier
    from src.feedback.generator import FeedbackGenerator

    print("\n" + "=" * 60)
    print("  AI FITNESS COACH — DEMO MODE (rep-aware)")
    print("  Reference: 1 rep   |   User: 3 reps")
    print("=" * 60 + "\n")

    FRAMES_PER_REP = 60   # ~2 s at 30 fps
    F = NUM_FEATURES

    def _squat_rep(frames, knee_offset=0.0, torso_offset=0.0, asym=0.0):
        """One squat rep as a sinusoidal angle trajectory."""
        t = np.linspace(0, 2 * np.pi, frames)
        data = np.zeros((frames, F), dtype=np.float32)
        data[:, 0] = 140 + 50 * np.sin(t) + knee_offset        # left_knee
        data[:, 1] = 140 + 50 * np.sin(t) + knee_offset + asym # right_knee
        data[:, 2] = 100 + 40 * np.sin(t)                       # left_hip
        data[:, 3] = 100 + 40 * np.sin(t)                       # right_hip
        data[:, 4] = 170.0                                       # left_elbow
        data[:, 5] = 170.0                                       # right_elbow
        data[:, 6] = 60.0                                        # left_shoulder
        data[:, 7] = 60.0                                        # right_shoulder
        data[:, 8] = 5 + 10 * np.sin(t) + torso_offset          # torso_lean
        return data

    # Reference: 1 clean rep
    ref_data = _squat_rep(FRAMES_PER_REP)

    # User: 3 reps concatenated, with a 5-frame pause (standing) between each
    pause = np.tile(
        _squat_rep(1, knee_offset=0, torso_offset=0)[-1],
        (5, 1)
    )
    rep1 = _squat_rep(FRAMES_PER_REP, knee_offset=0,   torso_offset=0)   # good
    rep2 = _squat_rep(FRAMES_PER_REP, knee_offset=-15, torso_offset=12)  # knee+lean error
    rep3 = _squat_rep(FRAMES_PER_REP, knee_offset=-5,  torso_offset=0,   asym=18) # asymmetry
    user_data = np.concatenate([rep1, pause, rep2, pause, rep3], axis=0)

    ref_ts  = build_time_series_from_array(ref_data,  FEATURE_NAMES, fps=30.0, smooth=True)
    user_ts = build_time_series_from_array(user_data, FEATURE_NAMES, fps=30.0, smooth=True)

    print(f"Reference: {ref_ts.num_frames} frames  ({ref_ts.duration_seconds:.1f}s)")
    print(f"User:      {user_ts.num_frames} frames  ({user_ts.duration_seconds:.1f}s)\n")

    # ── Rep-aware comparison ──────────────────────────────────────────────────
    print("Segmenting and comparing reps...")
    rep_comparator = RepComparator()
    result = rep_comparator.compare(user_ts, ref_ts)

    print(f"\nReference reps detected: {result.num_reference_reps}")
    print(f"User reps detected:      {result.num_user_reps}")

    print("\n" + "-" * 60)
    print("  PER-REP SCORES")
    print("-" * 60)
    for i, r in enumerate(result.rep_results):
        bar_len = int(r.score / 5)
        bar = "#" * bar_len + "-" * (20 - bar_len)
        tag = ""
        if i == result.best_rep_index:
            tag = "  <- best"
        elif i == result.worst_rep_index:
            tag = "  <- needs work"
        print(f"  Rep {i + 1}: [{bar}] {r.score:5.1f}/100  "
              f"({r.dtw_result.normalized_distance:.2f} norm. dist){tag}")

    print(f"\n  Overall score: {result.overall_score:.1f}/100")
    print(f"  Consistency:   {result.score_std:.1f} deg std dev")

    # ── Aggregate error classification ────────────────────────────────────────
    print("\n" + "-" * 60)
    print("  FEEDBACK")
    print("-" * 60)
    combined_dtw = result.combined_dtw
    scorer = ScoringEngine(sensitivity=0.05)
    score_report = scorer.score(combined_dtw)
    classifier = ErrorClassifier()
    events = classifier.classify(combined_dtw)
    gen = FeedbackGenerator()
    feedback = gen.generate(events, score_report)
    feedback.print()

    print("Per-feature breakdown:")
    for feat, info in score_report.per_feature_summary().items():
        bar_len = int(info["score"] / 5)
        bar = "#" * bar_len + "-" * (20 - bar_len)
        print(f"  {feat:<25} [{bar}] {info['score']:5.1f}  "
              f"(avg {info['mean_deviation_deg']:+.1f} deg, "
              f"max {info['max_deviation_deg']:.1f} deg)")

    print("\nDemo complete. Rep-aware pipeline working correctly.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ai_trainer",
        description="AI-powered fitness coaching via pose analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # record
    rec = sub.add_parser("record", help="Record a reference exercise from a video")
    rec.add_argument("exercise", help="Exercise name (e.g. squat, deadlift)")
    rec.add_argument("--video", required=True, help="Video file path or webcam index (0)")
    rec.add_argument("--description", default="", help="Description of this reference")
    rec.add_argument("--overwrite", action="store_true", help="Overwrite existing reference")
    rec.add_argument("--skip-frames", type=int, default=0,
                     help="Process every N+1 frames (0=all). Use 1 for 15fps from 30fps video.")

    # analyze
    ana = sub.add_parser("analyze", help="Analyze user video against stored reference")
    ana.add_argument("exercise", help="Exercise name to compare against")
    ana.add_argument("--video", required=True, help="Video file path or webcam index (0)")
    ana.add_argument("--sensitivity", type=float, default=0.05,
                     help="Scoring sensitivity (default 0.05). Higher = stricter.")
    ana.add_argument("--skip-frames", type=int, default=0,
                     help="Process every N+1 frames.")
    ana.add_argument("--model", type=int, default=1, choices=[0, 1, 2],
                     help="MediaPipe model complexity: 0=lite, 1=full, 2=heavy")
    ana.add_argument("--output", default=None,
                     help="Path for annotated output video (e.g. result.mp4). "
                          "Omit to skip rendering.")
    ana.add_argument("--show", action="store_true",
                     help="Display annotated video in a live window while rendering.")
    ana.add_argument("--no-angles", action="store_true",
                     help="Hide angle value labels on the output video.")

    # list
    sub.add_parser("list", help="List all stored reference exercises")

    # demo
    sub.add_parser("demo", help="Run pipeline demo with synthetic data (no video needed)")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "demo":
        run_demo()
        return

    if args.command == "list":
        from src.pipeline import AnalysisPipeline
        pipeline = AnalysisPipeline()
        refs = pipeline.list_references()
        if refs:
            print(f"\nStored references ({len(refs)}):")
            for name in refs:
                print(f"  • {name}")
        else:
            print("\nNo references stored yet. Use 'record' to create one.")
        return

    if args.command == "record":
        from src.pipeline import AnalysisPipeline
        pipeline = AnalysisPipeline(skip_frames=args.skip_frames)
        try:
            ref = pipeline.record_reference(
                exercise_name=args.exercise,
                video_path=args.video,
                description=args.description,
                overwrite=args.overwrite,
            )
            print(f"\nSuccess! Reference '{ref.name}' saved "
                  f"({ref.time_series.num_frames} frames, "
                  f"{ref.time_series.duration_seconds:.1f}s)")
        except (FileExistsError, RuntimeError) as e:
            print(f"\nError: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "analyze":
        from src.pipeline import AnalysisPipeline
        from src.visualization.renderer import VideoRenderer

        pipeline = AnalysisPipeline(
            model_complexity=args.model,
            sensitivity=args.sensitivity,
            skip_frames=args.skip_frames,
        )
        try:
            result = pipeline.analyze_video(
                video_path=args.video,
                exercise_name=args.exercise,
            )
            result.print_summary()

            if args.output or args.show:
                renderer = VideoRenderer(
                    show_angles=not args.no_angles,
                    model_complexity=args.model,
                )
                out_path = args.output or "annotated_output.mp4"
                renderer.render(
                    video_path=args.video,
                    result=result,
                    output_path=out_path,
                    skip_frames=args.skip_frames,
                    show=args.show,
                )
                print(f"\nAnnotated video saved to: {out_path}")

        except (FileNotFoundError, RuntimeError) as e:
            print(f"\nError: {e}", file=sys.stderr)
            sys.exit(1)



if __name__ == "__main__":
    main()
