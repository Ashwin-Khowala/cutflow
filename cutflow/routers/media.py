"""
CutFlow Media Router — Endpoints for uploading media and streaming video/audio files.
"""

import shutil
import uuid
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse

from cutflow.config import UPLOAD_DIR, PROJECTS_DIR
from cutflow.services.storage import cleanup_storage

router = APIRouter(tags=["media"])


@router.post("/api/upload")
async def upload_video(file: UploadFile = File(...)):
    """Upload a raw video file to the server."""
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


@router.get("/media/uploads/{filename}")
async def serve_upload(filename: str):
    """Stream an uploaded raw video file."""
    file_path = UPLOAD_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Uploaded file not found")
    return FileResponse(str(file_path))


@router.get("/media/projects/{project_id}/{filename}")
async def serve_project_media(project_id: str, filename: str):
    """Stream a rendered clean video or extracted audio file from a project folder."""
    file_path = PROJECTS_DIR / project_id / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Project media file not found")
    return FileResponse(str(file_path))
