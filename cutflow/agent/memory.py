"""
CutFlow Project Memory — Persistent agent memory per project.
Tracks conversational turns, user preferences, and editorial rationale.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
from cutflow.config import PROJECTS_DIR


class ProjectMemory:
    """Manages persistent memory and conversational context for a CutFlow project."""

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.project_dir = PROJECTS_DIR / project_id
        self.memory_file = self.project_dir / "memory.json"
        self.data: Dict[str, Any] = {
            "project_id": project_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "preferences": {
                "pacing": "natural",  # "fast", "natural", "relaxed"
                "remove_short_pauses": False,
                "strictness": "medium",  # "low", "medium", "high"
            },
            "conversation_history": [],
            "editorial_decisions": [],
        }
        self.load()

    def load(self):
        if self.memory_file.exists():
            try:
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    self.data.update(loaded)
            except Exception as e:
                print(f"Warning: Failed to load memory for {self.project_id}: {e}")

    def save(self):
        self.project_dir.mkdir(exist_ok=True)
        try:
            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save memory for {self.project_id}: {e}")

    def add_turn(self, role: str, content: str, action_taken: str = "none"):
        turn = {
            "role": role,
            "content": content,
            "action_taken": action_taken,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.data.setdefault("conversation_history", []).append(turn)
        # Keep last 25 turns to prevent unbounded growth
        if len(self.data["conversation_history"]) > 25:
            self.data["conversation_history"] = self.data["conversation_history"][-25:]
        self.save()

    def record_decision(self, action: str, details: Dict[str, Any], rationale: str = ""):
        decision = {
            "action": action,
            "details": details,
            "rationale": rationale,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.data.setdefault("editorial_decisions", []).append(decision)
        if len(self.data["editorial_decisions"]) > 50:
            self.data["editorial_decisions"] = self.data["editorial_decisions"][-50:]
        self.save()

    def update_preference(self, key: str, value: Any):
        self.data.setdefault("preferences", {})[key] = value
        self.save()

    def get_context_prompt(self) -> str:
        """Returns a formatted summary of user preferences and recent dialogue for LLM prompting."""
        prefs = self.data.get("preferences", {})
        recent_turns = self.data.get("conversation_history", [])[-5:]
        recent_decisions = self.data.get("editorial_decisions", [])[-5:]

        context_lines = [
            f"User Editorial Preferences: {json.dumps(prefs)}",
        ]

        if recent_turns:
            context_lines.append("Recent Agent Interactions:")
            for t in recent_turns:
                context_lines.append(f"- {t['role'].upper()}: {t['content']}")

        if recent_decisions:
            context_lines.append("Recent Editorial Decisions:")
            for d in recent_decisions:
                context_lines.append(f"- {d['action']}: {d.get('rationale', '')}")

        return "\n".join(context_lines)
