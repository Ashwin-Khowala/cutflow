"""
CutFlow Jobs Service — Background task management and progress tracking.
"""

import os
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

from cutflow.config import PROJECTS_DIR, load_env
from cutflow.transcriber import run_full_transcription
from cutflow.analyzer import analyze_transcript
from cutflow.edit_plan import build_edit_plan_from_analysis

# In-memory job state tracking
jobs: Dict[str, Dict[str, Any]] = {}


def create_job(project_id: str, video_filename: str) -> Dict[str, Any]:
    job_data = {
        "id": project_id,
        "video_filename": video_filename,
        "video_url": f"/media/uploads/{video_filename}",
        "status": "pending",
        "stage_index": 1,
        "progress": 0,
        "message": "Starting processing pipeline...",
        "result": None,
        "error": None,
    }
    jobs[project_id] = job_data
    return job_data


def get_job(project_id: str) -> Optional[Dict[str, Any]]:
    return jobs.get(project_id)


async def run_project_processing(
    project_id: str,
    video_path: Path,
    api_key: Optional[str],
    groq_api_key: Optional[str],
    provider: str,
    model: Optional[str],
    silence_threshold: str,
    silence_min_duration: float,
    max_silence: float,
):
    """
    Executes the full background pipeline: STT transcription, semantic analysis,
    and Edit Plan generation, saving persistent manifests to cutflow_data/projects/{project_id}.
    """
    project_dir = PROJECTS_DIR / project_id
    project_dir.mkdir(exist_ok=True)
    load_env()

    if project_id not in jobs:
        create_job(project_id, video_path.name)

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

        now_iso = datetime.now(timezone.utc).isoformat()
        # Derive display project name from original filename
        display_name = video_path.name
        if "_" in display_name and len(display_name.split("_")[0]) == 8:
            display_name = "_".join(display_name.split("_")[1:])

        # Save persistent project manifest
        manifest = {
            "id": project_id,
            "name": display_name,
            "video_filename": video_path.name,
            "video_url": f"/media/uploads/{video_path.name}",
            "created_at": now_iso,
            "updated_at": now_iso,
            "status": "ready",
            "duration": round(transcription.duration, 2),
            "cuts_count": len(analysis.cuts),
            "keeps_count": len(analysis.keeps),
            "time_saved": round(analysis.cut_duration, 2),
            "savings_percent": round((analysis.cut_duration / max(transcription.duration, 0.001)) * 100, 1),
            "rendered": False,
            "rendered_url": None,
            "provider": provider,
            "model": model or "default",
        }
        manifest_file = project_dir / "project.json"
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        jobs[project_id]["status"] = "ready"
        jobs[project_id]["stage_index"] = 4
        jobs[project_id]["progress"] = 100
        jobs[project_id]["message"] = "Analysis ready for review."
        jobs[project_id]["result"] = {
            "transcript": transcription.to_dict(),
            "analysis": analysis.to_dict(),
            "edit_plan": edit_plan.to_dict(),
            "project": manifest,
        }

    except Exception as e:
        jobs[project_id]["status"] = "failed"
        jobs[project_id]["error"] = str(e)
        jobs[project_id]["message"] = f"Processing failed: {str(e)}"
