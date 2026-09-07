"""
CutFlow Projects Router — Full RESTful API for project lifecycle, analysis, cuts, and exports.
"""

import uuid
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Response
from pydantic import BaseModel

from cutflow.config import UPLOAD_DIR
from cutflow.schemas import (
    ProcessRequest,
    ProjectMetadata,
    ProjectPatchRequest,
    UpdateCutsRequest,
    CutOverride,
)
from cutflow.services.jobs import create_job, get_job, run_project_processing
from cutflow.services.projects import (
    list_projects,
    get_project,
    update_project_metadata,
    delete_project,
    get_project_transcript,
    get_project_analysis,
    get_project_edit_plan,
    update_project_cuts,
    render_project_video,
)
from cutflow.edit_plan import build_edit_plan_from_analysis

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=List[Dict[str, Any]])
async def list_all_projects():
    """List all created projects with summary metadata, sorted by recency."""
    return list_projects()


@router.post("")
async def create_project(req: ProcessRequest, background_tasks: BackgroundTasks):
    """Start asynchronous transcription & analysis of an uploaded video into a new project."""
    video_path = UPLOAD_DIR / req.video_filename
    if not video_path.exists():
        raise HTTPException(status_code=404, detail=f"Video file '{req.video_filename}' not found in uploads")

    project_id = str(uuid.uuid4())[:8]
    create_job(project_id, req.video_filename)

    background_tasks.add_task(
        run_project_processing,
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


@router.get("/{project_id}")
async def get_single_project(project_id: str):
    """Retrieve full project details including metadata, transcript, analysis, and edit plan."""
    return get_project(project_id)


@router.patch("/{project_id}")
async def patch_single_project(project_id: str, patch: ProjectPatchRequest):
    """Update mutable project metadata, such as display name."""
    return update_project_metadata(project_id, patch)


@router.delete("/{project_id}")
async def delete_single_project(project_id: str):
    """Delete project directory, artifacts, and in-memory job."""
    return delete_project(project_id)


@router.get("/{project_id}/status")
async def get_project_status(project_id: str):
    """Get the current background processing progress/status for a project."""
    job = get_job(project_id)
    if job:
        return job

    # If already finished and on disk
    try:
        proj = get_project(project_id)
        return {
            "id": project_id,
            "status": "ready",
            "progress": 100,
            "message": "Project is ready",
            "result": proj,
            "error": None,
        }
    except Exception:
        raise HTTPException(status_code=404, detail="Project not found")


@router.get("/{project_id}/transcript")
async def get_transcript_endpoint(project_id: str):
    """Retrieve speech-to-text transcript data for the project."""
    return get_project_transcript(project_id)


@router.get("/{project_id}/analysis")
async def get_analysis_endpoint(project_id: str):
    """Retrieve AI cuts analysis and semantic classification for the project."""
    return get_project_analysis(project_id)


@router.get("/{project_id}/edit-plan")
async def get_edit_plan_endpoint(project_id: str):
    """Retrieve the universal structured Edit Plan IR JSON for the project."""
    return get_project_edit_plan(project_id)


@router.post("/{project_id}/cuts")
async def update_cuts_endpoint(project_id: str, req: UpdateCutsRequest):
    """Update cuts proposals based on user overrides and synchronize Edit Plan."""
    return update_project_cuts(project_id, req.cuts)


@router.post("/{project_id}/render")
async def render_video_endpoint(project_id: str):
    """Apply approved cuts using ffmpeg and render final clean video."""
    return render_project_video(project_id)


@router.get("/{project_id}/export/edl")
async def export_edl_endpoint(project_id: str):
    """Export the edit plan as a CMX 3600 EDL file for Premiere Pro / DaVinci Resolve."""
    proj = get_project(project_id)
    plan_dict = proj.get("edit_plan")
    if not plan_dict:
        raise HTTPException(status_code=400, detail="Edit plan not available for project")

    # Reconstruct EditPlan object to use .to_edl()
    plan_obj = build_edit_plan_from_analysis(
        project_id=project_id,
        source_video=proj.get("video_filename", "video.mp4"),
        total_duration=proj.get("transcript", {}).get("duration", 0.0),
        cuts=proj.get("analysis", {}).get("cuts", []),
        keeps=proj.get("analysis", {}).get("keeps", []),
    )

    edl_content = plan_obj.to_edl(title=f"CutFlow_{project_id}")
    return Response(
        content=edl_content,
        media_type="text/plain",
        headers={
            "Content-Disposition": f"attachment; filename=cutflow_{project_id}.edl"
        },
    )


@router.get("/{project_id}/export/json")
async def export_json_endpoint(project_id: str):
    """Export the universal Edit Plan IR as a downloadable JSON file."""
    plan = get_project_edit_plan(project_id)
    return Response(
        content=str(plan).replace("'", '"'),
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=cutflow_{project_id}_plan.json"
        },
    )
