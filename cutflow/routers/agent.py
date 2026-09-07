"""
CutFlow Agent Router — Conversational editing agent endpoints with LangGraph and project memory.
"""

from typing import Dict, Any
from fastapi import APIRouter, HTTPException

from cutflow.schemas import AgentChatRequest, AgentChatResponse
from cutflow.agent.memory import ProjectMemory
from cutflow.agent.workflow import run_editing_agent
from cutflow.services.projects import get_project

router = APIRouter(prefix="/api/projects/{project_id}/agent", tags=["agent"])


@router.post("/chat", response_model=AgentChatResponse)
async def agent_chat_endpoint(project_id: str, req: AgentChatRequest):
    """
    Send an editorial instruction or query to the LangGraph Editing Agent for this project.
    Can dynamically adjust cuts, restore takes, answer questions, and persist editorial memory.
    """
    try:
        result = run_editing_agent(
            project_id=project_id,
            message=req.message,
            provider=req.provider,
            model=req.model,
            api_key=req.api_key,
        )
        return AgentChatResponse(
            response=result["response"],
            action_taken=result["action_taken"],
            updated_cuts=result["updated_cuts"],
            edit_plan=result["edit_plan"],
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {str(e)}")


@router.get("/memory")
async def get_agent_memory(project_id: str) -> Dict[str, Any]:
    """Retrieve persistent memory, preferences, and dialogue history for this project."""
    # Ensure project exists
    get_project(project_id)
    memory = ProjectMemory(project_id)
    return memory.data


@router.delete("/memory")
async def reset_agent_memory(project_id: str):
    """Clear conversation history and reset agent memory for this project."""
    get_project(project_id)
    memory = ProjectMemory(project_id)
    memory.data["conversation_history"] = []
    memory.data["editorial_decisions"] = []
    memory.save()
    return {"status": "success", "message": "Project memory cleared"}
