"""
FastAPI backend for AI Fitness Coach.

Wraps the existing AnalysisPipeline in an async-friendly HTTP API.
Long-running analysis is dispatched to a ThreadPoolExecutor so the event
loop stays free to handle polling requests while analysis runs.

Endpoints
─────────
  GET  /api/references              list stored exercise names
  POST /api/references/record       record a new reference from an uploaded video
  DELETE /api/references/{name}     delete a stored reference

  POST /api/analyze                 start analysis → returns {job_id}
  GET  /api/status/{job_id}         poll until status == "done" | "error"
"""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from src.pipeline import AnalysisPipeline
from src.visualization.renderer import VideoRenderer

# ── App setup ─────────────────────────────────────────────────────────────────

app = FastAPI(title="AI Fitness Coach API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Thread pool for synchronous pipeline calls (analysis can take 30–120 s)
_executor = ThreadPoolExecutor(max_workers=2)

# Lazy singleton pipeline instance
_pipeline: Optional[AnalysisPipeline] = None


def get_pipeline() -> AnalysisPipeline:
    global _pipeline
    if _pipeline is None:
        print("[API] Initialising AnalysisPipeline…")
        _pipeline = AnalysisPipeline()
    return _pipeline


# In-memory job store: {job_id: {"status": str, "result": dict, "error": str}}
_jobs: dict[str, dict] = {}


# ── Serialisation ──────────────────────────────────────────────────────────────

def _ser(result) -> dict:
    """Convert AnalysisResult to a JSON-serialisable dict."""
    return {
        "exercise_name": result.exercise_name,
        "overall_score": round(float(result.overall_score), 1),
        "grade": result.grade,
        "duration_seconds": round(float(result.duration_seconds), 1),
        "frame_count": int(result.frame_count),
        "detected_frame_count": int(result.detected_frame_count),
        "num_reps": int(result.num_reps),
        "per_rep_scores": [round(float(s), 1) for s in result.per_rep_scores],
        "score_consistency": round(float(result.score_consistency), 1),
        "best_rep_index": int(result.best_rep_index),
        "worst_rep_index": int(result.worst_rep_index),
        "dtw_distance": round(float(result.dtw_distance), 2),
        "normalized_dtw_distance": round(float(result.normalized_dtw_distance), 3),
        "processing_time_seconds": round(float(result.processing_time_seconds), 2),
        "has_annotated_video": False,  # set to True by _run_analysis after render
        "render_error": None,          # populated if render fails
        "error_events": [
            {
                "feature_name": e.feature_name,
                "severity": e.severity.value,
                "direction": e.direction.value,
                "mean_deviation_deg": round(float(e.mean_deviation_deg), 1),
                "max_deviation_deg": round(float(e.max_deviation_deg), 1),
                "affected_frame_ratio": round(float(e.affected_frame_ratio), 2),
                "start_frame": int(e.start_frame),
                "end_frame": int(e.end_frame),
            }
            for e in result.error_events
        ],
        "feedback": {
            "grade_message": result.feedback_report.grade_message,
            "summary": result.feedback_report.summary,
            "items": [
                {
                    "cue": item.cue,
                    "explanation": item.explanation,
                    "severity": item.severity.value,
                    "feature": item.feature,
                    "mean_deviation_deg": round(float(item.mean_deviation_deg), 1),
                }
                for item in result.feedback_report.items
            ],
        },
    }


# ── Video transcoding ─────────────────────────────────────────────────────────

def _ffmpeg_exe() -> Optional[str]:
    """Return an ffmpeg binary path: bundled via imageio-ffmpeg, or system PATH."""
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    return shutil.which("ffmpeg")


def _transcode_h264(src: Path) -> Optional[Path]:
    """
    Re-encode src to H.264 MP4 for guaranteed browser playback.
    Uses imageio-ffmpeg's bundled binary so no system install is required.
    Returns the new path on success, None on failure.
    The caller is responsible for deleting src afterwards.
    """
    ffmpeg = _ffmpeg_exe()
    if ffmpeg is None:
        print("[API] ffmpeg not found — cannot transcode to H.264")
        return None
    fd, dst = tempfile.mkstemp(suffix=".mp4")
    os.close(fd)
    try:
        r = subprocess.run(
            [
                ffmpeg, "-y", "-i", str(src),
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-movflags", "+faststart",  # moov atom at front — required for browser streaming
                dst,
            ],
            capture_output=True,
            timeout=600,
        )
        if r.returncode == 0:
            print(f"[API] Transcoded {src.name} → H.264 ({Path(dst).stat().st_size // 1024} KB)")
            return Path(dst)
        print(f"[API] ffmpeg failed (rc={r.returncode}): {r.stderr.decode()[-300:]}")
    except Exception as e:
        print(f"[API] ffmpeg error: {e}")
    Path(dst).unlink(missing_ok=True)
    return None


# ── Background job runner ─────────────────────────────────────────────────────

def _run_analysis(job_id: str, video_path: str, exercise: str) -> None:
    """Synchronous worker — runs in a thread pool."""
    annotated_path: Optional[str] = None
    try:
        result = get_pipeline().analyze_video(video_path, exercise)
        serialized = _ser(result)

        # Render annotated video (best-effort — analysis result is returned even if render fails)
        raw_path: Optional[str] = None
        try:
            fd, raw_path = tempfile.mkstemp(suffix=".mp4")
            os.close(fd)
            # render() returns the actual path written (may switch to .avi if mp4v fails)
            rendered = VideoRenderer().render(video_path, result, raw_path)
            print(f"[API] Render complete: {rendered} ({rendered.stat().st_size // 1024} KB)")
            # If renderer switched to .avi fallback, the original mkstemp .mp4 is now empty
            if str(rendered) != raw_path:
                Path(raw_path).unlink(missing_ok=True)
            # Transcode to H.264 MP4 so every browser can play it
            h264 = _transcode_h264(rendered)
            if h264:
                rendered.unlink(missing_ok=True)
                annotated_path = str(h264)
            else:
                annotated_path = str(rendered)
            serialized["has_annotated_video"] = True
            print(f"[API] Annotated video ready: {annotated_path}")
        except Exception as render_err:
            import traceback
            print(f"[API] Video render failed:\n{traceback.format_exc()}")
            serialized["render_error"] = str(render_err)
            # Clean up both possible temp files
            for p in [raw_path, annotated_path]:
                if p:
                    Path(p).unlink(missing_ok=True)
            annotated_path = None

        job: dict = {"status": "done", "result": serialized}
        if annotated_path:
            job["_video_path"] = annotated_path
        _jobs[job_id] = job

    except Exception as exc:
        _jobs[job_id] = {"status": "error", "error": str(exc)}
    finally:
        Path(video_path).unlink(missing_ok=True)


def _run_record(job_id: str, video_path: str, name: str,
                description: str, overwrite: bool) -> None:
    """Synchronous worker for reference recording."""
    try:
        ref = get_pipeline().record_reference(name, video_path, description, overwrite)
        _jobs[job_id] = {
            "status": "done",
            "result": {
                "name": ref.name,
                "description": ref.description,
                "num_frames": ref.time_series.num_frames,
                "fps": ref.time_series.fps,
            },
        }
    except Exception as exc:
        _jobs[job_id] = {"status": "error", "error": str(exc)}
    finally:
        Path(video_path).unlink(missing_ok=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _save_upload(video: UploadFile) -> str:
    """Save an uploaded file to a temp path and return the path."""
    suffix = Path(video.filename or "video").suffix or ".mp4"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    content = await video.read()
    tmp.write(content)
    tmp.close()
    return tmp.name


def _dispatch(fn, *args) -> None:
    """Fire-and-forget: run fn(*args) in the thread pool."""
    asyncio.get_event_loop().run_in_executor(_executor, fn, *args)


# ── Reference endpoints ───────────────────────────────────────────────────────

@app.get("/api/references")
def list_references():
    exercises = get_pipeline().list_references()
    return {"exercises": exercises}


@app.post("/api/references/record")
async def record_reference(
    name: str = Form(...),
    description: str = Form(""),
    overwrite: bool = Form(False),
    video: UploadFile = File(...),
):
    """
    Record a reference exercise from an uploaded video.
    Returns a job_id; poll /api/status/{job_id} for the result.
    """
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "pending"}
    tmp_path = await _save_upload(video)
    _dispatch(_run_record, job_id, tmp_path, name, description, overwrite)
    return {"job_id": job_id}


@app.delete("/api/references/{name}")
def delete_reference(name: str):
    try:
        get_pipeline().store.delete(name)
        return {"success": True}
    except FileNotFoundError:
        raise HTTPException(404, f"Reference '{name}' not found")


# ── Analysis endpoints ────────────────────────────────────────────────────────

@app.post("/api/analyze")
async def analyze_video(
    exercise: str = Form(...),
    video: UploadFile = File(...),
):
    """
    Start an async analysis job. Returns {job_id} immediately.
    Poll GET /api/status/{job_id} until status is "done" or "error".
    """
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "pending"}
    tmp_path = await _save_upload(video)
    _dispatch(_run_analysis, job_id, tmp_path, exercise)
    return {"job_id": job_id}


@app.get("/api/status/{job_id}")
def get_status(job_id: str):
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(404, "Job not found")
    return job


@app.get("/api/video/{job_id}")
def get_annotated_video(job_id: str):
    job = _jobs.get(job_id)
    if not job or "_video_path" not in job:
        raise HTTPException(404, "No annotated video for this job")
    path = Path(job["_video_path"])
    if not path.exists():
        raise HTTPException(410, "Video file has been cleaned up")
    mime = "video/mp4" if path.suffix == ".mp4" else "video/x-msvideo"
    return FileResponse(str(path), media_type=mime)


# ── Dev entrypoint ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=False)
