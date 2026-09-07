"""
Edit Plan module — defines the universal Intermediate Representation (IR)
for AI-generated video editing decisions.

The Edit Plan is provider-agnostic, inspectable, and can be serialized to JSON,
compiled to FFmpeg filtergraphs, or exported to industry-standard formats like EDL.
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Literal, Optional, List, Dict, Any


@dataclass
class TimelineEntry:
    """A discrete temporal segment in the compiled edit timeline."""
    id: str
    start: float
    end: float
    duration: float
    type: Literal["a_roll", "b_roll", "silence", "cut"]
    action: Literal["keep", "cut", "replace"]
    text: str = ""
    reason: str = ""
    confidence: float = 1.0
    effects: Dict[str, Any] = field(default_factory=dict)
    words: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "start": round(self.start, 3),
            "end": round(self.end, 3),
            "duration": round(self.duration, 3),
            "type": self.type,
            "action": self.action,
            "text": self.text,
            "reason": self.reason,
            "confidence": round(self.confidence, 2),
            "effects": self.effects,
            "words": self.words,
        }


@dataclass
class EditPlanStats:
    """Summary statistics for the edit plan."""
    original_duration: float
    clean_duration: float
    time_saved: float
    savings_percent: float
    cuts_count: int
    keeps_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_duration": round(self.original_duration, 2),
            "clean_duration": round(self.clean_duration, 2),
            "time_saved": round(self.time_saved, 2),
            "savings_percent": round(self.savings_percent, 1),
            "cuts_count": self.cuts_count,
            "keeps_count": self.keeps_count,
        }


@dataclass
class EditPlan:
    """
    Universal AI Video Edit Plan (IR).
    Represents all editorial decisions made on a video source.
    """
    version: str = "1.0"
    project_id: str = ""
    source_video: str = ""
    source_duration: float = 0.0
    stats: EditPlanStats = field(
        default_factory=lambda: EditPlanStats(0.0, 0.0, 0.0, 0.0, 0, 0)
    )
    timeline: List[TimelineEntry] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "project_id": self.project_id,
            "source_video": self.source_video,
            "source_duration": round(self.source_duration, 3),
            "stats": self.stats.to_dict(),
            "timeline": [entry.to_dict() for entry in self.timeline],
            "metadata": self.metadata,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def to_edl(self, title: str = "CutFlow Edit", fps: float = 30.0) -> str:
        """
        Export the plan as a standard CMX 3600 Edit Decision List (EDL)
        compatible with DaVinci Resolve, Final Cut Pro, and Adobe Premiere.
        """
        def _sec_to_tc(seconds: float) -> str:
            hrs = int(seconds // 3600)
            mins = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            frames = int(round((seconds - int(seconds)) * fps))
            if frames >= int(fps):
                frames = 0
                secs += 1
            return f"{hrs:02d}:{mins:02d}:{secs:02d}:{frames:02d}"

        lines = [
            f"TITLE: {title}",
            f"FCM: NON-DROP FRAME",
            "",
        ]

        keep_entries = [e for e in self.timeline if e.action == "keep"]
        rec_in_sec = 0.0

        for idx, entry in enumerate(keep_entries, 1):
            src_in = _sec_to_tc(entry.start)
            src_out = _sec_to_tc(entry.end)
            dur = entry.duration
            rec_in = _sec_to_tc(rec_in_sec)
            rec_out = _sec_to_tc(rec_in_sec + dur)
            rec_in_sec += dur

            lines.append(
                f"{idx:03d}  AX       V     C        {src_in} {src_out} {rec_in} {rec_out}"
            )
            lines.append(
                f"{idx:03d}  AX       A     C        {src_in} {src_out} {rec_in} {rec_out}"
            )
            if entry.text:
                clean_comment = entry.text.replace("\n", " ").strip()[:60]
                lines.append(f"* FROM CLIP: {self.source_video}")
                lines.append(f"* COMMENT: {clean_comment}")
            lines.append("")

        return "\n".join(lines)


def build_edit_plan_from_analysis(
    project_id: str,
    source_video: str,
    total_duration: float,
    cuts: List[Any],
    keeps: List[Any],
    transcript_segments: Optional[List[Any]] = None,
    provider: str = "cutflow",
    model: str = "default",
) -> EditPlan:
    """
    Build a unified EditPlan instance by fusing cut regions, keep regions,
    and transcript segments chronologically.
    """
    timeline_entries: List[TimelineEntry] = []
    
    # Normalize cuts
    norm_cuts = []
    for c in cuts:
        if isinstance(c, dict):
            norm_cuts.append({
                "start": float(c.get("start", 0)),
                "end": float(c.get("end", 0)),
                "reason": str(c.get("reason", "cut")),
                "explanation": str(c.get("explanation", "")),
                "text": str(c.get("text", "")),
                "confidence": float(c.get("confidence", 1.0)),
            })
        else:
            reason_val = getattr(c.reason, "value", str(c.reason)) if hasattr(c, "reason") else "cut"
            norm_cuts.append({
                "start": float(getattr(c, "start", 0)),
                "end": float(getattr(c, "end", 0)),
                "reason": reason_val,
                "explanation": getattr(c, "explanation", ""),
                "text": getattr(c, "text", ""),
                "confidence": float(getattr(c, "confidence", 1.0)),
            })

    # Normalize keeps
    norm_keeps = []
    for k in keeps:
        if isinstance(k, dict):
            norm_keeps.append({
                "start": float(k.get("start", 0)),
                "end": float(k.get("end", 0)),
                "text": str(k.get("text", "")),
            })
        else:
            norm_keeps.append({
                "start": float(getattr(k, "start", 0)),
                "end": float(getattr(k, "end", 0)),
                "text": getattr(k, "text", ""),
            })

    # Combine into chronological timeline entries
    raw_events = []
    for c in norm_cuts:
        raw_events.append({
            "start": c["start"],
            "end": c["end"],
            "action": "cut",
            "type": "cut",
            "reason": c["reason"],
            "explanation": c["explanation"],
            "text": c["text"],
            "confidence": c["confidence"],
        })

    for k in norm_keeps:
        raw_events.append({
            "start": k["start"],
            "end": k["end"],
            "action": "keep",
            "type": "a_roll",
            "reason": "",
            "explanation": "",
            "text": k["text"],
            "confidence": 1.0,
        })

    # Sort events chronologically
    raw_events.sort(key=lambda x: (x["start"], x["end"]))

    for idx, ev in enumerate(raw_events):
        start = max(0.0, ev["start"])
        end = min(total_duration, ev["end"]) if total_duration > 0 else ev["end"]
        duration = max(0.0, end - start)
        if duration <= 0.01:
            continue

        entry_type = "a_roll" if ev["action"] == "keep" else ("silence" if ev.get("reason") == "long_silence" else "cut")
        timeline_entries.append(
            TimelineEntry(
                id=f"entry_{idx:03d}",
                start=start,
                end=end,
                duration=duration,
                type=entry_type,
                action=ev["action"],
                text=ev["text"],
                reason=ev.get("reason", ""),
                confidence=ev.get("confidence", 1.0),
            )
        )

    # Compute overall statistics
    kept_duration = sum(e.duration for e in timeline_entries if e.action == "keep")
    cut_duration = sum(e.duration for e in timeline_entries if e.action == "cut")
    cuts_count = sum(1 for e in timeline_entries if e.action == "cut")
    keeps_count = sum(1 for e in timeline_entries if e.action == "keep")
    time_saved = cut_duration
    savings_pct = (time_saved / total_duration * 100.0) if total_duration > 0 else 0.0

    stats = EditPlanStats(
        original_duration=total_duration,
        clean_duration=kept_duration,
        time_saved=time_saved,
        savings_percent=savings_pct,
        cuts_count=cuts_count,
        keeps_count=keeps_count,
    )

    metadata = {
        "generator": "CutFlow Engine v0.2.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "provider": provider,
        "model": model,
        "spec_url": "https://github.com/Ashwin-Khowala/cutflow/blob/main/docs/EDIT_PLAN_SPEC.md",
    }

    return EditPlan(
        version="1.0",
        project_id=project_id,
        source_video=source_video,
        source_duration=total_duration,
        stats=stats,
        timeline=timeline_entries,
        metadata=metadata,
    )
