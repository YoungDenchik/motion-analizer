# AI Fitness Coach

An AI-powered fitness coaching application that analyzes exercise technique from video using computer vision and time-series analysis. Acts as a virtual personal trainer: detects pose, tracks movement, compares it to a reference, and gives actionable feedback.

## Pipeline

```
video → pose keypoints → joint angles → time series
      → rep segmentation → per-rep DTW → score → feedback
```

## Features

- **Pose detection** — MediaPipe 33-point body landmark detection
- **Biomechanical features** — 9 joint angles (knee, hip, elbow, shoulder, torso lean)
- **Scale/position invariant** — hip-center normalization removes camera distance and user height
- **Rep-count independent** — segments reps automatically; scores technique regardless of how many reps the user performs
- **DTW comparison** — Dynamic Time Warping handles different execution speeds
- **0–100 scoring** — per-rep and aggregate, with letter grade
- **Error classification** — Critical (injury risk) vs Technical (efficiency)
- **Actionable feedback** — coach-style verbal cues, prioritized by severity
- **Video annotation** — color-coded skeleton overlay, score meter, live feedback banner

## Requirements

- Python 3.11+
- Webcam or video file (standard smartphone camera is sufficient)

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
```

The MediaPipe pose model (~6 MB) is downloaded automatically on first run.

## Usage

### Record a reference exercise

```bash
# From a video file
python main.py record squat --video reference_squat.mp4

# From webcam
python main.py record squat --video 0

# Overwrite an existing reference
python main.py record squat --video reference_squat.mp4 --overwrite
```

The reference can contain **one or more reps** — multiple reps are averaged into a single canonical template.

### Analyze a user video

```bash
# Text report only
python main.py analyze squat --video my_squat.mp4

# Save annotated video
python main.py analyze squat --video my_squat.mp4 --output result.mp4

# Show live window while rendering
python main.py analyze squat --video my_squat.mp4 --output result.mp4 --show
```

### List stored references

```bash
python main.py list
```

### Run demo (no video needed)

```bash
python main.py demo
```

Simulates 1 reference rep vs 3 user reps with injected form errors to verify the full pipeline.

## CLI options

| Flag | Default | Description |
|---|---|---|
| `--model 0\|1\|2` | `1` | MediaPipe complexity: 0=lite, 1=full, 2=heavy |
| `--sensitivity` | `0.05` | Scoring strictness. Higher = stricter |
| `--skip-frames N` | `0` | Process every N+1 frames (use `1` to halve frame count) |
| `--output path` | — | Save annotated output video |
| `--show` | — | Display annotated video in a live window |
| `--no-angles` | — | Hide angle labels on output video |
| `--overwrite` | — | Replace existing reference |

## Project structure

```
ai_trainer/
├── main.py                        # CLI entry point
├── requirements.txt
├── references/                    # Stored reference JSON files
└── src/
    ├── pose/
    │   ├── keypoints.py           # PoseFrame, PoseLandmark data structures
    │   └── detector.py            # MediaPipe Tasks PoseLandmarker wrapper
    ├── features/
    │   ├── normalizer.py          # Hip-center + torso-scale normalization
    │   └── extractor.py           # Joint angle extraction (9 features)
    ├── timeseries/
    │   ├── builder.py             # TimeSeries dataclass, smoothing, resampling
    │   └── segmentation.py        # Rep boundary detection via peak finding
    ├── comparison/
    │   ├── dtw.py                 # DTW comparator with feature weighting
    │   └── rep_comparator.py      # Rep-count-independent comparison
    ├── evaluation/
    │   ├── scorer.py              # 0-100 exponential scoring engine
    │   └── classifier.py          # Critical / Technical error classification
    ├── feedback/
    │   └── generator.py           # Rule-based coaching feedback
    ├── reference/
    │   └── store.py               # Reference JSON storage (CRUD)
    ├── visualization/
    │   ├── overlay.py             # Frame annotation (skeleton, score, banner)
    │   └── renderer.py            # Two-pass annotated video writer
    └── pipeline.py                # Orchestrates all stages
```

## Scoring

| Score | Grade | Meaning |
|---|---|---|
| 90–100 | A | Excellent — near-perfect form |
| 80–89 | B | Good — minor refinements needed |
| 70–79 | C | Decent — consistent practice will help |
| 60–69 | D | Needs work — focus on the cues |
| < 60 | F | Significant issues — consider coaching |

**Formula:** `score = 100 × exp(−0.05 × mean_deviation_degrees)`

## Video annotation legend

| Color | Meaning |
|---|---|
| Green joint/bone | < 8° deviation from reference |
| Yellow joint/bone | 8–12° deviation (technical error) |
| Red joint/bone | > 12° deviation (critical / injury risk) |

The score bar (top-right) shows the current frame score. The bottom banner displays the highest-priority active coaching cue.

## Design notes

**Why joint angles instead of raw coordinates?**
Raw coordinates encode camera position, user distance, and user height. Joint angles (e.g. `hip → knee → ankle`) are pure biomechanics — a 90° knee angle is 90° regardless of where the camera is placed.

**Why rep segmentation before DTW?**
Without segmentation, comparing 3 user reps against 1 reference rep forces DTW to warp 180 frames against 60, producing a score that reflects rep-count mismatch rather than technique quality. Segmenting first isolates each rep so every comparison is 1-vs-1.

**Why FastDTW instead of exact DTW?**
Exact DTW is O(N²). For a 3-second clip at 30 fps (90 frames), that is 8 100 cell evaluations per comparison. FastDTW with a Sakoe-Chiba band is O(N), enabling near-real-time post-session analysis.
