"""
CutFlow Web Server — FastAPI backend for the web dashboard.
Provides REST APIs for uploading, analyzing, reviewing cuts, and exporting clean video.
"""

import asyncio
import json
import os
import shutil
import sys
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any

# Fix Windows console encoding for emoji and unicode output
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from cutflow.transcriber import run_full_transcription, TranscriptionResult, Segment, SilenceRegion, Word
from cutflow.analyzer import (
    analyze_transcript,
    AnalysisResult,
    CutProposal,
    CutReason,
    KeepRegion,
    build_analysis_result,
    detect_filler_segments,
    detect_long_silences,
    analyze_with_llm,
)
from cutflow.cutter import apply_cuts
from cutflow.edit_plan import build_edit_plan_from_analysis, EditPlan

# Directory for projects and uploaded media
DATA_DIR = Path("cutflow_data")
DATA_DIR.mkdir(exist_ok=True)
UPLOAD_DIR = DATA_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
PROJECTS_DIR = DATA_DIR / "projects"
PROJECTS_DIR.mkdir(exist_ok=True)

app = FastAPI(title="CutFlow API Server", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job state tracking
jobs: Dict[str, Dict[str, Any]] = {}
def _load_env_if_needed():
    """Load .env file if environment variables are not already present."""
    env_path = Path(".env")
    if env_path.exists():
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k, v = k.strip(), v.strip().strip('"').strip("'")
                        if k not in os.environ:
                            os.environ[k] = v
        except Exception:
            pass

_load_env_if_needed()


def cleanup_storage(max_age_hours: float = 3.0, keep_latest_uploads: int = 5):
    """
    Purges old video uploads and temporary project directories from cutflow_data
    to keep disk usage minimal.
    """
    import time
    now = time.time()
    try:
        # 1. Clean uploads
        upload_files = sorted(
            [f for f in UPLOAD_DIR.glob("*") if f.is_file()],
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        for i, file_path in enumerate(upload_files):
            if i >= keep_latest_uploads:
                age_hours = (now - file_path.stat().st_mtime) / 3600.0
                if age_hours > max_age_hours:
                    try:
                        file_path.unlink()
                        print(f"🧹 Auto-cleaned old upload: {file_path.name}")
                    except Exception:
                        pass

        # 2. Clean old project directories
        project_dirs = sorted(
            [d for d in PROJECTS_DIR.iterdir() if d.is_dir()],
            key=lambda d: d.stat().st_mtime,
            reverse=True,
        )
        for i, p_dir in enumerate(project_dirs):
            if i >= keep_latest_uploads:
                age_hours = (now - p_dir.stat().st_mtime) / 3600.0
                if age_hours > max_age_hours:
                    try:
                        shutil.rmtree(p_dir, ignore_errors=True)
                        print(f"🧹 Auto-cleaned old project dir: {p_dir.name}")
                    except Exception:
                        pass
    except Exception as e:
        print(f"⚠️  Cleanup warning: {e}")


def get_storage_stats() -> dict:
    """Calculate total MB used in uploads and projects."""
    upload_bytes = sum(f.stat().st_size for f in UPLOAD_DIR.glob("*") if f.is_file())
    project_bytes = sum(f.stat().st_size for f in PROJECTS_DIR.rglob("*") if f.is_file())
    total_mb = (upload_bytes + project_bytes) / (1024 * 1024)
    return {
        "upload_mb": round(upload_bytes / (1024 * 1024), 2),
        "projects_mb": round(project_bytes / (1024 * 1024), 2),
        "total_mb": round(total_mb, 2),
        "upload_count": len(list(UPLOAD_DIR.glob("*"))),
        "project_count": len(list(PROJECTS_DIR.iterdir())),
    }


class CutOverride(BaseModel):
    start: float
    end: float
    reason: str
    action: str  # "cut" or "keep"
    text: str = ""
    explanation: str = ""
    confidence: float = 1.0


class UpdateCutsRequest(BaseModel):
    project_id: str
    cuts: List[CutOverride]


class ProcessRequest(BaseModel):
    video_filename: str
    api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    provider: str = "groq"  # "groq" or "gemini"
    model: Optional[str] = None
    silence_threshold: str = "-35dB"
    silence_min_duration: float = 0.8
    max_silence: float = 1.5


@app.get("/api/storage/info")
async def get_storage_info():
    """Return storage usage information."""
    return get_storage_stats()


@app.post("/api/storage/cleanup")
async def manual_cleanup(keep_recent: int = 1):
    """Purge all non-recent uploads and project files immediately."""
    cleanup_storage(max_age_hours=0.01, keep_latest_uploads=keep_recent)
    return {"status": "success", "stats": get_storage_stats()}


@app.get("/api/models")
async def get_supported_models():
    """Return supported LLM providers and models."""
    return {
        "providers": [
            {
                "id": "groq",
                "name": "Groq (Ultra-Fast LPU Inference)",
                "recommended": True,
                "docs_url": "https://console.groq.com/docs/models",
                "models": [
                    {
                        "id": "openai/gpt-oss-120b",
                        "name": "OpenAI GPT-OSS 120B",
                        "description": "Recommended. Flagship 120B parameter OpenAI model on Groq. Deep reasoning & exact JSON.",
                        "context_window": 128000
                    },
                    {
                        "id": "openai/gpt-oss-20b",
                        "name": "OpenAI GPT-OSS 20B",
                        "description": "Fast 20B parameter OpenAI open model on Groq.",
                        "context_window": 32768
                    },
                    {
                        "id": "qwen/qwen3.6-27b",
                        "name": "Qwen 3.6 27B",
                        "description": "Multimodal capable high-speed model on Groq.",
                        "context_window": 32768
                    },
                    {
                        "id": "groq/compound",
                        "name": "Groq Compound",
                        "description": "Groq compound reasoning system.",
                        "context_window": 128000
                    },
                    {
                        "id": "groq/compound-mini",
                        "name": "Groq Compound Mini",
                        "description": "Compact Groq compound system.",
                        "context_window": 128000
                    }
                ]
            },
            {
                "id": "gemini",
                "name": "Google Gemini",
                "recommended": False,
                "docs_url": "https://ai.google.dev/gemini-api/docs/models",
                "models": [
                    {
                        "id": "gemini-2.0-flash",
                        "name": "Gemini 2.0 Flash",
                        "description": "Fast and intelligent next-gen model.",
                        "context_window": 1000000
                    },
                    {
                        "id": "gemini-1.5-flash",
                        "name": "Gemini 1.5 Flash",
                        "description": "Cost-efficient high-speed model.",
                        "context_window": 1000000
                    },
                    {
                        "id": "gemini-1.5-pro",
                        "name": "Gemini 1.5 Pro",
                        "description": "Maximum reasoning capability.",
                        "context_window": 2000000
                    }
                ]
            }
        ]
    }


@app.post("/api/upload")
async def upload_video(file: UploadFile = File(...)):
    """Upload a raw video file to the server."""
    # Run a quick auto-cleanup of stale files on upload
    cleanup_storage()

    file_id = str(uuid.uuid4())[:8]
    ext = Path(file.filename).suffix or ".mp4"
    saved_filename = f"{file_id}_{file.filename}"
    target_path = UPLOAD_DIR / saved_filename

    with open(target_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {
        "status": "success",
        "video_filename": saved_filename,
        "video_url": f"/media/uploads/{saved_filename}",
        "original_name": file.filename,
    }


async def _run_processing_task(
    project_id: str,
    video_path: Path,
    api_key: Optional[str],
    groq_api_key: Optional[str],
    provider: str,
    model: Optional[str],
    silence_threshold: str,
    silence_min_duration: float,
    max_silence: float
):
    project_dir = PROJECTS_DIR / project_id
    project_dir.mkdir(exist_ok=True)
    _load_env_if_needed()

    def stt_progress(pct: float, msg: str):
        # Scale STT phase from 5% to 55%
        overall = 5.0 + (pct / 100.0) * 50.0
        jobs[project_id]["status"] = "transcribing"
        jobs[project_id]["stage_index"] = 2
        jobs[project_id]["progress"] = round(overall, 1)
        jobs[project_id]["message"] = msg

    def analysis_progress(pct: float, msg: str):
        # Scale Analysis phase from 55% to 95%
        overall = 55.0 + (pct / 100.0) * 40.0
        jobs[project_id]["status"] = "analyzing"
        jobs[project_id]["stage_index"] = 4
        jobs[project_id]["progress"] = round(overall, 1)
        jobs[project_id]["message"] = msg

    try:
        # Determine Groq key for STT from request or environment
        effective_groq_key = (
            groq_api_key
            or (api_key if (api_key and api_key.startswith("gsk_")) else None)
            or os.environ.get("GROQ_API_KEY")
        )
        stt_backend = "groq_whisper" if effective_groq_key else "moonshine"
        backend_label = "Groq Whisper (whisper-large-v3-turbo)" if effective_groq_key else "Moonshine (offline)"

        jobs[project_id]["status"] = "transcribing"
        jobs[project_id]["stage_index"] = 1
        jobs[project_id]["progress"] = 5
        jobs[project_id]["message"] = f"Extracting audio & transcribing with {backend_label}..."

        transcription = run_full_transcription(
            str(video_path),
            output_dir=str(project_dir),
            silence_threshold=silence_threshold,
            silence_min_duration=silence_min_duration,
            progress_callback=stt_progress,
            stt_backend=stt_backend,
            groq_api_key=effective_groq_key,
        )

        transcript_file = project_dir / "transcript.json"
        with open(transcript_file, "w", encoding="utf-8") as f:
            f.write(transcription.to_json())

        jobs[project_id]["status"] = "analyzing"
        jobs[project_id]["stage_index"] = 3
        jobs[project_id]["progress"] = 60
        jobs[project_id]["message"] = f"Analyzing script structure & storyline with {provider.upper()} ({model or 'default'})..."

        # For analysis, if provider is groq and api_key was empty, use effective_groq_key
        effective_analysis_key = api_key or (effective_groq_key if provider == "groq" else os.environ.get("GEMINI_API_KEY"))

        analysis = analyze_transcript(
            transcription,
            api_key=effective_analysis_key,
            provider=provider,
            model=model,
            max_silence=max_silence,
            progress_callback=analysis_progress,
        )

        analysis_file = project_dir / "analysis.json"
        with open(analysis_file, "w", encoding="utf-8") as f:
            f.write(analysis.to_json())

        # Generate universal Edit Plan IR
        edit_plan = build_edit_plan_from_analysis(
            project_id=project_id,
            source_video=video_path.name,
            total_duration=transcription.duration,
            cuts=analysis.cuts,
            keeps=analysis.keeps,
            transcript_segments=transcription.segments,
            provider=provider,
            model=model,
        )
        edit_plan_file = project_dir / "edit_plan.json"
        with open(edit_plan_file, "w", encoding="utf-8") as f:
            f.write(edit_plan.to_json())

        jobs[project_id]["status"] = "ready"
        jobs[project_id]["stage_index"] = 4
        jobs[project_id]["progress"] = 100
        jobs[project_id]["message"] = "Analysis ready for review."
        jobs[project_id]["result"] = {
            "transcript": transcription.to_dict(),
            "analysis": analysis.to_dict(),
            "edit_plan": edit_plan.to_dict(),
        }

    except Exception as e:
        jobs[project_id]["status"] = "failed"
        jobs[project_id]["error"] = str(e)
        jobs[project_id]["message"] = f"Processing failed: {str(e)}"


@app.post("/api/process")
async def start_process(req: ProcessRequest, background_tasks: BackgroundTasks):
    """Start asynchronous transcription & analysis of an uploaded video."""
    video_path = UPLOAD_DIR / req.video_filename
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video file not found")

    project_id = str(uuid.uuid4())[:8]
    jobs[project_id] = {
        "id": project_id,
        "video_filename": req.video_filename,
        "video_url": f"/media/uploads/{req.video_filename}",
        "status": "pending",
        "stage_index": 1,
        "progress": 0,
        "message": "Starting processing pipeline...",
        "result": None,
        "error": None,
    }

    background_tasks.add_task(
        _run_processing_task,
        project_id,
        video_path,
        req.api_key,
        req.groq_api_key,
        req.provider,
        req.model,
        req.silence_threshold,
        req.silence_min_duration,
        req.max_silence,
    )

    return {"project_id": project_id, "status": "pending"}


@app.get("/api/status/{project_id}")
async def get_status(project_id: str):
    """Get the current progress status of a video processing job."""
    if project_id not in jobs:
        raise HTTPException(status_code=404, detail="Project not found")
    return jobs[project_id]


@app.get("/api/project/{project_id}")
async def get_project(project_id: str):
    """Retrieve full project details, transcript, and analysis."""
    project_dir = PROJECTS_DIR / project_id
    if not project_dir.exists():
        if project_id in jobs and jobs[project_id]["result"]:
            return jobs[project_id]
        raise HTTPException(status_code=404, detail="Project not found")

    transcript_path = project_dir / "transcript.json"
    analysis_path = project_dir / "analysis.json"

    if not transcript_path.exists() or not analysis_path.exists():
        raise HTTPException(status_code=400, detail="Project data is incomplete")

    with open(transcript_path, "r", encoding="utf-8") as f:
        transcript = json.load(f)
    with open(analysis_path, "r", encoding="utf-8") as f:
        analysis = json.load(f)

    video_filename = jobs.get(project_id, {}).get("video_filename", "")
    rendered_filename = f"{project_id}_cut.mp4"
    rendered_path = project_dir / rendered_filename
    rendered_url = f"/media/projects/{project_id}/{rendered_filename}" if rendered_path.exists() else None

    edit_plan_path = project_dir / "edit_plan.json"
    edit_plan = None
    if edit_plan_path.exists():
        try:
            with open(edit_plan_path, "r", encoding="utf-8") as f:
                edit_plan = json.load(f)
        except Exception:
            pass
    if not edit_plan:
        plan_obj = build_edit_plan_from_analysis(
            project_id=project_id,
            source_video=video_filename,
            total_duration=transcript.get("duration", 0.0),
            cuts=analysis.get("cuts", []),
            keeps=analysis.get("keeps", []),
        )
        edit_plan = plan_obj.to_dict()
        try:
            with open(edit_plan_path, "w", encoding="utf-8") as f:
                f.write(plan_obj.to_json())
        except Exception:
            pass

    return {
        "id": project_id,
        "video_filename": video_filename,
        "video_url": f"/media/uploads/{video_filename}" if video_filename else "",
        "rendered_url": rendered_url,
        "transcript": transcript,
        "analysis": analysis,
        "edit_plan": edit_plan,
    }


@app.get("/api/project/{project_id}/edit-plan")
async def get_edit_plan(project_id: str):
    """Retrieve the universal structured Edit Plan JSON for a project."""
    project_dir = PROJECTS_DIR / project_id
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    edit_plan_path = project_dir / "edit_plan.json"
    if edit_plan_path.exists():
        with open(edit_plan_path, "r", encoding="utf-8") as f:
            return json.load(f)

    transcript_path = project_dir / "transcript.json"
    analysis_path = project_dir / "analysis.json"
    if not transcript_path.exists() or not analysis_path.exists():
        raise HTTPException(status_code=400, detail="Project data is incomplete")

    with open(transcript_path, "r", encoding="utf-8") as f:
        transcript = json.load(f)
    with open(analysis_path, "r", encoding="utf-8") as f:
        analysis = json.load(f)

    video_filename = jobs.get(project_id, {}).get("video_filename", "")
    plan = build_edit_plan_from_analysis(
        project_id=project_id,
        source_video=video_filename,
        total_duration=transcript.get("duration", 0.0),
        cuts=analysis.get("cuts", []),
        keeps=analysis.get("keeps", []),
    )
    with open(edit_plan_path, "w", encoding="utf-8") as f:
        f.write(plan.to_json())
    return plan.to_dict()


@app.get("/api/project/{project_id}/export/edl")
async def export_edl(project_id: str):
    """Export the edit plan as a CMX 3600 EDL file for Premiere / DaVinci Resolve."""
    project_dir = PROJECTS_DIR / project_id
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    transcript_path = project_dir / "transcript.json"
    analysis_path = project_dir / "analysis.json"
    if not transcript_path.exists() or not analysis_path.exists():
        raise HTTPException(status_code=400, detail="Project data is incomplete")

    with open(transcript_path, "r", encoding="utf-8") as f:
        transcript = json.load(f)
    with open(analysis_path, "r", encoding="utf-8") as f:
        analysis = json.load(f)

    video_filename = jobs.get(project_id, {}).get("video_filename", "video.mp4")
    plan = build_edit_plan_from_analysis(
        project_id=project_id,
        source_video=video_filename,
        total_duration=transcript.get("duration", 0.0),
        cuts=analysis.get("cuts", []),
        keeps=analysis.get("keeps", []),
    )

    edl_content = plan.to_edl(title=f"CutFlow_{project_id}")
    return Response(
        content=edl_content,
        media_type="text/plain",
        headers={
            "Content-Disposition": f"attachment; filename=cutflow_{project_id}.edl"
        },
    )


@app.post("/api/cuts/update")
async def update_cuts(req: UpdateCutsRequest):
    """Update cuts based on manual user overrides from the Web UI."""
    project_dir = PROJECTS_DIR / req.project_id
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    analysis_file = project_dir / "analysis.json"
    transcript_file = project_dir / "transcript.json"

    with open(transcript_file, "r", encoding="utf-8") as f:
        transcript_data = json.load(f)

    # Reconstruct segments
    segments = [
        Segment(
            text=s["text"],
            start=s["start"],
            end=s["end"],
            words=[Word(text=w["text"], start=w["start"], end=w["end"]) for w in s.get("words", [])]
        )
        for s in transcript_data.get("segments", [])
    ]
    transcription = TranscriptionResult(
        segments=segments,
        silences=[],
        duration=transcript_data.get("duration", 0),
        audio_path="",
    )

    # Convert overrides to CutProposals
    cut_proposals = []
    for c in req.cuts:
        if c.action == "cut":
            try:
                reason = CutReason(c.reason)
            except ValueError:
                reason = CutReason.FALSE_START
            cut_proposals.append(
                CutProposal(
                    start=c.start,
                    end=c.end,
                    reason=reason,
                    explanation=c.explanation or "User manual cut",
                    text=c.text,
                    confidence=c.confidence,
                )
            )

    analysis_result = build_analysis_result(
        transcription=transcription,
        llm_analysis=[],
        filler_cuts=cut_proposals,
        silence_cuts=[],
    )

    with open(analysis_file, "w", encoding="utf-8") as f:
        f.write(analysis_result.to_json())

    # Sync Edit Plan
    edit_plan_file = project_dir / "edit_plan.json"
    video_filename = jobs.get(req.project_id, {}).get("video_filename", "video.mp4")
    updated_plan = build_edit_plan_from_analysis(
        project_id=req.project_id,
        source_video=video_filename,
        total_duration=transcription.duration,
        cuts=analysis_result.cuts,
        keeps=analysis_result.keeps,
        transcript_segments=transcription.segments,
    )
    with open(edit_plan_file, "w", encoding="utf-8") as f:
        f.write(updated_plan.to_json())

    if req.project_id in jobs and jobs[req.project_id]["result"]:
        jobs[req.project_id]["result"]["analysis"] = analysis_result.to_dict()
        jobs[req.project_id]["result"]["edit_plan"] = updated_plan.to_dict()

    return {
        "status": "success",
        "analysis": analysis_result.to_dict(),
        "edit_plan": updated_plan.to_dict(),
    }


@app.post("/api/render")
async def render_clean_video(project_id: str = Form(...)):
    """Apply approved cuts and render the final clean video using ffmpeg."""
    project_dir = PROJECTS_DIR / project_id
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    analysis_file = project_dir / "analysis.json"
    if not analysis_file.exists():
        raise HTTPException(status_code=400, detail="Analysis not found")

    with open(analysis_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    cuts = [
        CutProposal(
            start=c["start"],
            end=c["end"],
            reason=CutReason(c["reason"]),
            explanation=c["explanation"],
            text=c["text"],
            confidence=c["confidence"],
        )
        for c in data.get("cuts", [])
    ]
    keeps = [
        KeepRegion(start=k["start"], end=k["end"], text=k["text"])
        for k in data.get("keeps", [])
    ]

    analysis = AnalysisResult(
        cuts=cuts,
        keeps=keeps,
        total_duration=data.get("total_duration", 0),
        kept_duration=data.get("kept_duration", 0),
        cut_duration=data.get("cut_duration", 0),
        summary=data.get("summary", ""),
    )

    video_filename = jobs.get(project_id, {}).get("video_filename", "")
    if not video_filename:
        # Find video in uploads
        matches = list(UPLOAD_DIR.glob(f"{project_id}_*"))
        if matches:
            video_filename = matches[0].name
        else:
            raise HTTPException(status_code=400, detail="Original video file not found")

    source_video = UPLOAD_DIR / video_filename
    output_filename = f"{project_id}_cut.mp4"
    output_path = project_dir / output_filename

    try:
        apply_cuts(str(source_video), analysis, output_path=str(output_path))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rendering failed: {str(e)}")

    rendered_url = f"/media/projects/{project_id}/{output_filename}"
    return {
        "status": "success",
        "rendered_url": rendered_url,
        "output_path": str(output_path),
        "saved_seconds": round(analysis.cut_duration, 2),
    }


# Static file streaming for uploaded and rendered media
@app.get("/media/uploads/{filename}")
async def serve_upload(filename: str):
    file_path = UPLOAD_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(str(file_path))


@app.get("/")
async def root():
    return {
        "name": "CutFlow API Server",
        "version": "0.1.0",
        "status": "online"
    }
