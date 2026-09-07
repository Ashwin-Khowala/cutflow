"""
CutFlow LangGraph Video Editing Agent Workflow.
Orchestrates multi-turn user editing instructions with project memory and precise cut manipulation.
"""

import json
import os
import re
from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END

from cutflow.agent.memory import ProjectMemory
from cutflow.schemas import CutOverride
from cutflow.services.projects import (
    get_project,
    get_project_transcript,
    get_project_analysis,
    update_project_cuts,
)


class CutFlowAgentState(TypedDict):
    project_id: str
    user_instruction: str
    provider: str
    model: Optional[str]
    api_key: Optional[str]
    transcript: Dict[str, Any]
    current_cuts: List[Dict[str, Any]]
    memory_context: str
    intent: str  # "query", "edit_cuts", "restore_takes", "adjust_pacing", "general"
    suggested_cuts: List[Dict[str, Any]]
    response_message: str
    action_taken: str


def _call_llm_json(prompt: str, provider: str, model: Optional[str], api_key: Optional[str]) -> Optional[Dict[str, Any]]:
    """Helper to query Groq or Gemini for structured JSON responses."""
    if provider == "gemini":
        try:
            from google import genai
            from google.genai import types

            effective_key = api_key or os.environ.get("GEMINI_API_KEY")
            if not effective_key:
                return None
            client = genai.Client(api_key=effective_key)
            m = model or "gemini-2.0-flash"
            resp = client.models.generate_content(
                model=m,
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )
            raw = resp.text.strip()
            return json.loads(raw)
        except Exception as e:
            print(f"Gemini agent call error: {e}")
            return None
    else:
        try:
            from groq import Groq

            effective_key = api_key or os.environ.get("GROQ_API_KEY")
            if not effective_key:
                return None
            client = Groq(api_key=effective_key)
            m = model or "openai/gpt-oss-120b"
            resp = client.chat.completions.create(
                model=m,
                messages=[
                    {
                        "role": "system",
                        "content": "You are CutFlow AI, an elite video editing agent. Respond ONLY with valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
            )
            raw = resp.choices[0].message.content.strip()
            return json.loads(raw)
        except Exception as e:
            print(f"Groq agent call error: {e}")
            return None


def intent_analyzer_node(state: CutFlowAgentState) -> Dict[str, Any]:
    """Classifies user directive and inspects whether cuts need modification."""
    instruction = state["user_instruction"].lower()
    intent = "general"

    if any(w in instruction for w in ["cut", "remove", "trim", "delete", "drop", "stumble"]):
        intent = "edit_cuts"
    elif any(w in instruction for w in ["keep", "restore", "undo", "bring back", "un-cut", "uncut"]):
        intent = "restore_takes"
    elif any(w in instruction for w in ["pause", "silence", "pacing", "pace", "fast", "tight"]):
        intent = "adjust_pacing"
    elif any(w in instruction for w in ["why", "what", "how many", "show me", "explain", "stats"]):
        intent = "query"

    return {"intent": intent}


def cut_planner_node(state: CutFlowAgentState) -> Dict[str, Any]:
    """Plans timestamp-level cut modifications according to user instruction and transcript context."""
    intent = state.get("intent", "general")
    instruction = state["user_instruction"]
    transcript = state.get("transcript", {})
    current_cuts = state.get("current_cuts", [])
    memory_context = state.get("memory_context", "")

    # For pure queries, formulate a helpful editorial answer without touching cuts
    if intent == "query":
        total_cuts = len(current_cuts)
        duration = transcript.get("duration", 0)
        cut_duration = sum(c.get("end", 0) - c.get("start", 0) for c in current_cuts)
        reasons_count: Dict[str, int] = {}
        for c in current_cuts:
            r = c.get("reason", "unknown")
            reasons_count[r] = reasons_count.get(r, 0) + 1

        reasons_summary = ", ".join(f"{count} {reason}" for reason, count in reasons_count.items())

        answer = (
            f"Currently CutFlow has proposed {total_cuts} cuts ({cut_duration:.1f}s saved from {duration:.1f}s total). "
            f"Breakdown: {reasons_summary or 'no cuts active'}. "
            f"You can instruct me to restore any section or cut additional phrases."
        )
        return {
            "suggested_cuts": current_cuts,
            "response_message": answer,
            "action_taken": "none",
        }

    # Format condensed transcript segments for LLM
    segments_summary = [
        {
            "start": round(s.get("start", 0), 2),
            "end": round(s.get("end", 0), 2),
            "text": s.get("text", "").strip(),
        }
        for s in transcript.get("segments", [])[:80]
    ]

    prompt = f"""
You are the CutFlow Editing Agent. The user wants to adjust video cuts.

{memory_context}

VIDEO TRANSCRIPT SEGMENTS:
{json.dumps(segments_summary, indent=1)}

CURRENT PROPOSED CUTS (list of {{start, end, reason, text, explanation}}):
{json.dumps(current_cuts, indent=1)}

USER INSTRUCTION:
"{instruction}"

TASK:
1. Determine how the cuts should be modified (add new cuts, remove cuts to restore takes, or adjust bounds).
2. Return a JSON object with:
   - "explanation": Short, friendly message explaining what you modified for the user.
   - "action": "cuts_updated" if you modified cuts, or "none" if no cuts were changed.
   - "cuts": Complete updated list of all active cuts [{{start: float, end: float, reason: str, text: str, explanation: str}}].
   
Rules:
- Keep start and end numbers accurate based on transcript timestamps.
- Only cut unnecessary speech (false starts, repeated takes, filler words, awkward silences).
- If the user says "keep" or "restore" something, remove any cut overlapping that speech range.
"""

    llm_result = _call_llm_json(
        prompt,
        provider=state.get("provider", "groq"),
        model=state.get("model"),
        api_key=state.get("api_key"),
    )

    if llm_result and "cuts" in llm_result and isinstance(llm_result["cuts"], list):
        return {
            "suggested_cuts": llm_result["cuts"],
            "response_message": llm_result.get("explanation", "I have updated the cuts according to your instruction."),
            "action_taken": llm_result.get("action", "cuts_updated"),
        }

    # Fallback if LLM unavailable
    return {
        "suggested_cuts": current_cuts,
        "response_message": f"Understood: '{instruction}'. To apply fine-grained edits, ensure your LLM API key is configured.",
        "action_taken": "none",
    }


def apply_and_sync_node(state: CutFlowAgentState) -> Dict[str, Any]:
    """Applies valid updated cuts to the project and saves memory."""
    project_id = state["project_id"]
    action_taken = state.get("action_taken", "none")
    suggested_cuts = state.get("suggested_cuts", [])
    response_message = state.get("response_message", "")

    memory = ProjectMemory(project_id)

    if action_taken == "cuts_updated" and suggested_cuts:
        overrides = [
            CutOverride(
                start=float(c["start"]),
                end=float(c["end"]),
                reason=c.get("reason", "manual_cut"),
                action="cut",
                text=c.get("text", ""),
                explanation=c.get("explanation", "AI Agent cut override"),
                confidence=float(c.get("confidence", 1.0)),
            )
            for c in suggested_cuts
        ]
        update_project_cuts(project_id, overrides)
        memory.record_decision(
            action="cuts_updated",
            details={"cuts_count": len(overrides)},
            rationale=state["user_instruction"],
        )

    memory.add_turn(
        role="user",
        content=state["user_instruction"],
        action_taken=action_taken,
    )
    memory.add_turn(
        role="assistant",
        content=response_message,
        action_taken=action_taken,
    )

    return state


def build_editing_graph():
    """Builds and compiles the LangGraph state graph for CutFlow Editing Agent."""
    builder = StateGraph(CutFlowAgentState)

    builder.add_node("intent_analyzer", intent_analyzer_node)
    builder.add_node("cut_planner", cut_planner_node)
    builder.add_node("apply_and_sync", apply_and_sync_node)

    builder.set_entry_point("intent_analyzer")
    builder.add_edge("intent_analyzer", "cut_planner")
    builder.add_edge("cut_planner", "apply_and_sync")
    builder.add_edge("apply_and_sync", END)

    return builder.compile()


# Singleton compiled graph
editing_agent_graph = build_editing_graph()


def run_editing_agent(
    project_id: str,
    message: str,
    provider: str = "groq",
    model: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Runs the compiled LangGraph video editing agent on a project."""
    project_data = get_project(project_id)
    transcript = project_data.get("transcript", {})
    analysis = project_data.get("analysis", {})
    current_cuts = analysis.get("cuts", [])

    memory = ProjectMemory(project_id)
    memory_context = memory.get_context_prompt()

    initial_state: CutFlowAgentState = {
        "project_id": project_id,
        "user_instruction": message,
        "provider": provider,
        "model": model,
        "api_key": api_key,
        "transcript": transcript,
        "current_cuts": current_cuts,
        "memory_context": memory_context,
        "intent": "",
        "suggested_cuts": current_cuts,
        "response_message": "",
        "action_taken": "none",
    }

    final_state = editing_agent_graph.invoke(initial_state)

    updated_proj = get_project(project_id)
    return {
        "response": final_state.get("response_message", "Edit processed."),
        "action_taken": final_state.get("action_taken", "none"),
        "updated_cuts": updated_proj.get("analysis", {}).get("cuts", []),
        "edit_plan": updated_proj.get("edit_plan"),
    }
