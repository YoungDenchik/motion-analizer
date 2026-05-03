# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Activate the venv (always required — all tools live here)
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run demo (no video or camera needed — validates full pipeline)
python main.py demo

# Record a reference exercise
python main.py record squat --video reference.mp4 --overwrite

# Analyze a user video
python main.py analyze squat --video user.mp4

# Analyze and write annotated video
python main.py analyze squat --video user.mp4 --output result.mp4 --show

# List stored references
python main.py list
```

There are no automated tests. Use `python main.py demo` to validate pipeline integrity after changes — it runs the full stack on synthetic data and will raise if any stage is broken.

## Architecture

The system is a **linear pipeline** with one branch for video annotation:

```
video
  └─ PoseDetector          (src/pose/detector.py)         MediaPipe → 33 landmarks/frame
       └─ FeatureExtractor  (src/features/extractor.py)    landmarks → 9 joint angles/frame
            └─ TimeSeries   (src/timeseries/builder.py)    frames → smoothed (T × 9) array
                 └─ RepSegmenter  (src/timeseries/segmentation.py)  split into individual reps
                      └─ RepComparator  (src/comparison/rep_comparator.py)
                           ├─ DTWComparator  (src/comparison/dtw.py)  per-rep alignment
                           ├─ ScoringEngine  (src/evaluation/scorer.py)
                           ├─ ErrorClassifier  (src/evaluation/classifier.py)
                           └─ FeedbackGenerator  (src/feedback/generator.py)

Video annotation (separate second pass over the source video):
  AnalysisResult → VideoRenderer (src/visualization/renderer.py)
                        └─ FrameAnnotator (src/visualization/overlay.py)
```

`src/pipeline.py` is the only place that wires all stages together. `AnalysisPipeline.analyze_video()` and `AnalysisPipeline.record_reference()` are the two public entry points.

## Critical design invariants

**FEATURE_NAMES order is a global contract.** The list in `src/features/extractor.py` must stay stable — it determines column order in every `(T × F)` numpy array throughout the pipeline, the feedback rule keys in `src/feedback/generator.py`, the DTW weight dict in `src/comparison/dtw.py`, and the joint color mapping in `src/visualization/overlay.py`. Adding or reordering features breaks stored references (JSON arrays) and all downstream consumers simultaneously.

**Rep-count independence via segmentation-first.** The core insight: DTW must only ever compare one rep against one rep. `RepComparator.compare()` (rep_comparator.py) enforces this by segmenting both sequences before any DTW call, then resampling each user rep to the canonical reference length. Never bypass this by calling `DTWComparator.compare()` directly on unsegmented full-session sequences.

**`combined_dtw` is synthetic.** `RepComparisonResult.combined_dtw` builds a fake `DTWResult` by concatenating per-rep deviations and using an identity alignment path. It exists solely so `ScoringEngine` and `ErrorClassifier` can consume aggregated data without modification. It is not a real DTW result — do not use its `distance` or `path` fields for per-rep analysis.

**MediaPipe Tasks API only.** This project uses MediaPipe ≥ 0.10, which dropped `mp.solutions.pose` on Windows. All MediaPipe access goes through `mediapipe.tasks.python.vision`. Never import `mp.solutions.*` — it will raise `AttributeError` at module load time.

**Visualization is a second pass.** `VideoRenderer` re-reads the source video and re-runs `PoseDetector` (in `static_image_mode=True`) to get pixel-accurate landmark coordinates for drawing. The analysis pass stores feature vectors (joint angles), not pixel positions, so there is no way to skip re-detection in the render pass.

## Key data types

| Type | Shape / fields | Where defined |
|---|---|---|
| `PoseFrame` | 33 × `PoseLandmark(x,y,z,visibility)` | `src/pose/keypoints.py` |
| `TimeSeries` | `data: (T, F) float32`, `feature_names`, `fps` | `src/timeseries/builder.py` |
| `DTWResult` | `per_frame_deviations: (T, F)`, `path`, `distance` | `src/comparison/dtw.py` |
| `RepComparisonResult` | `rep_results[]`, `per_frame_deviations: (T_total, F)` | `src/comparison/rep_comparator.py` |
| `AnalysisResult` | `per_rep_scores[]`, `per_frame_deviations`, `feedback_report` | `src/pipeline.py` |

## MediaPipe model

`pose_landmarker_full.task` is downloaded automatically to the repo root on first run by `src/pose/detector.py:_ensure_model()`. It is gitignored. Do not commit it.

## Reference storage

Exercises are stored as JSON in `references/{name}.json`. The files are gitignored by default (see `.gitignore`). `ReferenceStore` in `src/reference/store.py` handles all CRUD. The JSON schema is owned by `TimeSeries.to_dict()` / `from_dict()` — changing that schema invalidates all stored references.
