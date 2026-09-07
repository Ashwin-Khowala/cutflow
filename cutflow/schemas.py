"""
CutFlow Pydantic Schemas — Request and response models for all API endpoints.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class CutOverride(BaseModel):
    start: float
    end: float
    reason: str = "manual_cut"
    action: str = "cut"  # "cut" or "keep"
    text: str = ""
    explanation: str = ""
    confidence: float = 1.0


class UpdateCutsRequest(BaseModel):
    project_id: Optional[str] = None
    cuts: List[CutOverride] = Field(default_factory=list)


class ProcessRequest(BaseModel):
    video_filename: str
    api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    provider: str = "groq"  # "groq" or "gemini"
    model: Optional[str] = None
    silence_threshold: str = "-35dB"
    silence_min_duration: float = 0.8
    max_silence: float = 1.5


class ProjectMetadata(BaseModel):
    id: str
    name: str
    video_filename: str
    video_url: str
    created_at: str
    updated_at: str
    status: str = "ready"
    duration: float = 0.0
    cuts_count: int = 0
    keeps_count: int = 0
    time_saved: float = 0.0
    savings_percent: float = 0.0
    rendered: bool = False
    rendered_url: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None


class ProjectPatchRequest(BaseModel):
    name: Optional[str] = None


class ReanalyzeRequest(BaseModel):
    api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    provider: str = "groq"
    model: Optional[str] = None
    max_silence: float = 1.5
    instruction: Optional[str] = None


class AgentChatRequest(BaseModel):
    message: str
    api_key: Optional[str] = None
    provider: str = "groq"
    model: Optional[str] = None


class AgentChatResponse(BaseModel):
    response: str
    action_taken: str = "none"  # "none", "cuts_updated", "reanalyzed"
    updated_cuts: Optional[List[Dict[str, Any]]] = None
    edit_plan: Optional[Dict[str, Any]] = None


class StorageStats(BaseModel):
    upload_mb: float
    projects_mb: float
    total_mb: float
    upload_count: int
    project_count: int
