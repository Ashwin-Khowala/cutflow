"""
CutFlow Web Server — Modular FastAPI application for CutFlow Studio.
Mounts modular domain routers (projects, media, system, agent) and maintains
full backward-compatibility for legacy endpoints.
"""

from fastapi import FastAPI, Form, HTTPException, BackgroundTasks, Response
from fastapi.middleware.cors import CORSMiddleware

from cutflow.config import load_env
from cutflow.schemas import ProcessRequest, UpdateCutsRequest
from cutflow.services.jobs import jobs, create_job, run_project_processing
from cutflow.services.projects import (
    get_project,
    get_project_edit_plan,
    update_project_cuts,
    render_project_video,
)
from cutflow.routers.projects import (
    router as projects_router,
    get_project_status,
    export_edl_endpoint,
)
from cutflow.routers.media import router as media_router
from cutflow.routers.system import router as system_router
from cutflow.routers.agent import router as agent_router

# Load environment on startup
load_env()

app = FastAPI(
    title="CutFlow API Server",
    description="AI-powered video preparation and intelligent rough-cut editor",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount modular routers
app.include_router(projects_router)
app.include_router(media_router)
app.include_router(system_router)
app.include_router(agent_router)


# --------------------------------------------------------------------------
# Backward-Compatibility Aliases for Legacy Frontend Calls
# --------------------------------------------------------------------------

@app.post("/api/process", tags=["legacy"])
async def legacy_process_endpoint(req: ProcessRequest, background_tasks: BackgroundTasks):
    """Legacy alias for POST /api/projects."""
    from cutflow.routers.projects import create_project
    return await create_project(req, background_tasks)


@app.get("/api/status/{project_id}", tags=["legacy"])
async def legacy_status_endpoint(project_id: str):
    """Legacy alias for GET /api/projects/{project_id}/status."""
    return await get_project_status(project_id)


@app.get("/api/project/{project_id}", tags=["legacy"])
async def legacy_get_project_endpoint(project_id: str):
    """Legacy alias for GET /api/projects/{project_id}."""
    return get_project(project_id)


@app.get("/api/project/{project_id}/edit-plan", tags=["legacy"])
async def legacy_get_edit_plan_endpoint(project_id: str):
    """Legacy alias for GET /api/projects/{project_id}/edit-plan."""
    return get_project_edit_plan(project_id)


@app.get("/api/project/{project_id}/export/edl", tags=["legacy"])
async def legacy_export_edl_endpoint(project_id: str):
    """Legacy alias for GET /api/projects/{project_id}/export/edl."""
    return await export_edl_endpoint(project_id)


@app.post("/api/cuts/update", tags=["legacy"])
async def legacy_update_cuts_endpoint(req: UpdateCutsRequest):
    """Legacy alias for POST /api/projects/{project_id}/cuts."""
    if not req.project_id:
        raise HTTPException(status_code=400, detail="project_id is required")
    return update_project_cuts(req.project_id, req.cuts)


@app.post("/api/render", tags=["legacy"])
async def legacy_render_endpoint(project_id: str = Form(...)):
    """Legacy alias for POST /api/projects/{project_id}/render."""
    return render_project_video(project_id)


@app.get("/")
async def root():
    return {
        "name": "CutFlow API Server",
        "version": "0.2.0",
        "status": "online",
        "docs_url": "/docs",
    }
