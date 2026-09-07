"""
CutFlow Projects Service — Management, persistence, cuts sync, and rendering for video projects.
"""

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

from fastapi import HTTPException

from cutflow.config import PROJECTS_DIR, UPLOAD_DIR
from cutflow.services.jobs import jobs
from cutflow.schemas import CutOverride, ProjectPatchRequest
from cutflow.transcriber import TranscriptionResult, Segment, Word, SilenceRegion
from cutflow.analyzer import (
    AnalysisResult,
    CutProposal,
    CutReason,
    KeepRegion,
    build_analysis_result,
)
from cutflow.cutter import apply_cuts
from cutflow.edit_plan import build_edit_plan_from_analysis


def _backfill_project_metadata(project_id: str, project_dir: Path) -> Optional[Dict[str, Any]]:
    """Infer and create project.json for projects created prior to metadata introduction."""
    transcript_path = project_dir / "transcript.json"
    analysis_path = project_dir / "analysis.json"
    edit_plan_path = project_dir / "edit_plan.json"

    if not transcript_path.exists() or not analysis_path.exists():
        return None

    try:
        with open(transcript_path, "r", encoding="utf-8") as f:
            transcript = json.load(f)
        with open(analysis_path, "r", encoding="utf-8") as f:
            analysis = json.load(f)

        source_video = ""
        if edit_plan_path.exists():
            try:
                with open(edit_plan_path, "r", encoding="utf-8") as f:
                    plan = json.load(f)
                    source_video = plan.get("source_video", "")
            except Exception:
                pass

        if not source_video and project_id in jobs:
            source_video = jobs[project_id].get("video_filename", "")

        if not source_video:
            # Look for any matching upload or media files
            for upload_file in UPLOAD_DIR.glob("*"):
                if upload_file.is_file() and (project_id in upload_file.name):
                    source_video = upload_file.name
                    break

        if not source_video:
            # Fallback to audio file stem if available
            audio_files = list(project_dir.glob("*_audio.wav"))
            if audio_files:
                stem = audio_files[0].stem.replace("_audio", "")
                source_video = f"{stem}.mp4"
            else:
                source_video = f"{project_id}_source.mp4"

        display_name = source_video
        if "_" in display_name and len(display_name.split("_")[0]) == 8:
            display_name = "_".join(display_name.split("_")[1:])

        mtime = project_dir.stat().st_mtime
        iso_time = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()

        duration = transcript.get("duration", 0.0)
        cuts = analysis.get("cuts", [])
        keeps = analysis.get("keeps", [])
        cut_duration = analysis.get("cut_duration", 0.0)

        rendered_file = project_dir / f"{project_id}_cut.mp4"
        is_rendered = rendered_file.exists()

        metadata = {
            "id": project_id,
            "name": display_name,
            "video_filename": source_video,
            "video_url": f"/media/uploads/{source_video}",
            "created_at": iso_time,
            "updated_at": iso_time,
            "status": "ready",
            "duration": round(duration, 2),
            "cuts_count": len(cuts),
            "keeps_count": len(keeps),
            "time_saved": round(cut_duration, 2),
            "savings_percent": round((cut_duration / max(duration, 0.001)) * 100, 1),
            "rendered": is_rendered,
            "rendered_url": f"/media/projects/{project_id}/{rendered_file.name}" if is_rendered else None,
            "provider": "groq",
            "model": "default",
        }

        with open(project_dir / "project.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        return metadata
    except Exception as e:
        print(f"Failed to backfill metadata for project {project_id}: {e}")
        return None


def list_projects() -> List[Dict[str, Any]]:
    """List all projects found in cutflow_data/projects, sorted by latest update."""
    results = []
    if not PROJECTS_DIR.exists():
        return results

    for p_dir in PROJECTS_DIR.iterdir():
        if not p_dir.is_dir():
            continue
        project_id = p_dir.name
        manifest_file = p_dir / "project.json"
        metadata = None

        if manifest_file.exists():
            try:
                with open(manifest_file, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
            except Exception:
                metadata = None

        if not metadata:
            metadata = _backfill_project_metadata(project_id, p_dir)

        if metadata:
            # Check if rendered output status changed on disk
            rendered_file = p_dir / f"{project_id}_cut.mp4"
            if rendered_file.exists() and not metadata.get("rendered"):
                metadata["rendered"] = True
                metadata["rendered_url"] = f"/media/projects/{project_id}/{rendered_file.name}"

            results.append(metadata)

    # Sort descending by updated_at or created_at
    results.sort(key=lambda p: p.get("updated_at") or p.get("created_at") or "", reverse=True)
    return results


def get_project(project_id: str) -> Dict[str, Any]:
    """Retrieve full project details, transcript, analysis, and edit plan."""
    project_dir = PROJECTS_DIR / project_id

    if not project_dir.exists():
        if project_id in jobs and jobs[project_id].get("result"):
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

    manifest_file = project_dir / "project.json"
    metadata = None
    if manifest_file.exists():
        try:
            with open(manifest_file, "r", encoding="utf-8") as f:
                metadata = json.load(f)
        except Exception:
            metadata = None

    if not metadata:
        metadata = _backfill_project_metadata(project_id, project_dir) or {}

    video_filename = metadata.get("video_filename") or jobs.get(project_id, {}).get("video_filename", "")
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
        "name": metadata.get("name", video_filename or project_id),
        "video_filename": video_filename,
        "video_url": f"/media/uploads/{video_filename}" if video_filename else "",
        "rendered_url": rendered_url,
        "metadata": metadata,
        "transcript": transcript,
        "analysis": analysis,
        "edit_plan": edit_plan,
    }


def update_project_metadata(project_id: str, patch: ProjectPatchRequest) -> Dict[str, Any]:
    """Update mutable metadata for a project (such as project name)."""
    project_dir = PROJECTS_DIR / project_id
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    manifest_file = project_dir / "project.json"
    metadata = {}
    if manifest_file.exists():
        try:
            with open(manifest_file, "r", encoding="utf-8") as f:
                metadata = json.load(f)
        except Exception:
            pass

    if patch.name is not None:
        metadata["name"] = patch.name

    metadata["updated_at"] = datetime.now(timezone.utc).isoformat()

    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    return metadata


def delete_project(project_id: str) -> Dict[str, Any]:
    """Delete a project directory and clear active job from memory."""
    project_dir = PROJECTS_DIR / project_id
    if not project_dir.exists():
        if project_id in jobs:
            del jobs[project_id]
            return {"status": "success", "message": "Project job removed from memory"}
        raise HTTPException(status_code=404, detail="Project not found")

    # Read manifest to find uploaded video
    manifest_file = project_dir / "project.json"
    video_filename = ""
    if manifest_file.exists():
        try:
            with open(manifest_file, "r", encoding="utf-8") as f:
                video_filename = json.load(f).get("video_filename", "")
        except Exception:
            pass

    # Remove project folder
    shutil.rmtree(project_dir, ignore_errors=True)

    # Clean in-memory job
    if project_id in jobs:
        del jobs[project_id]

    return {
        "status": "success",
        "message": f"Project {project_id} deleted successfully",
        "deleted_video_filename": video_filename,
    }


def get_project_transcript(project_id: str) -> Dict[str, Any]:
    """Retrieve raw transcription for a project."""
    project_dir = PROJECTS_DIR / project_id
    transcript_path = project_dir / "transcript.json"
    if not transcript_path.exists():
        raise HTTPException(status_code=404, detail="Transcript not found for project")
    with open(transcript_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_project_analysis(project_id: str) -> Dict[str, Any]:
    """Retrieve analysis JSON for a project."""
    project_dir = PROJECTS_DIR / project_id
    analysis_path = project_dir / "analysis.json"
    if not analysis_path.exists():
        raise HTTPException(status_code=404, detail="Analysis not found for project")
    with open(analysis_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_project_edit_plan(project_id: str) -> Dict[str, Any]:
    """Retrieve or generate universal Edit Plan IR JSON."""
    project_dir = PROJECTS_DIR / project_id
    edit_plan_path = project_dir / "edit_plan.json"
    if edit_plan_path.exists():
        with open(edit_plan_path, "r", encoding="utf-8") as f:
            return json.load(f)

    # Fallback to generating it
    full_proj = get_project(project_id)
    return full_proj["edit_plan"]


def update_project_cuts(project_id: str, cuts: List[CutOverride]) -> Dict[str, Any]:
    """Update cuts based on manual user overrides and synchronize Edit Plan."""
    project_dir = PROJECTS_DIR / project_id
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    analysis_file = project_dir / "analysis.json"
    transcript_file = project_dir / "transcript.json"

    if not transcript_file.exists():
        raise HTTPException(status_code=400, detail="Project transcript file missing")

    with open(transcript_file, "r", encoding="utf-8") as f:
        transcript_data = json.load(f)

    segments = [
        Segment(
            text=s["text"],
            start=s["start"],
            end=s["end"],
            words=[Word(text=w["text"], start=w["start"], end=w["end"]) for w in s.get("words", [])],
        )
        for s in transcript_data.get("segments", [])
    ]
    silences = [
        SilenceRegion(start=s["start"], end=s["end"], duration=s["duration"])
        for s in transcript_data.get("silences", [])
    ]
    transcription = TranscriptionResult(
        segments=segments,
        silences=silences,
        duration=transcript_data.get("duration", 0),
        audio_path="",
    )

    cut_proposals = []
    for c in cuts:
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
    video_filename = jobs.get(project_id, {}).get("video_filename", "video.mp4")
    if video_filename == "video.mp4":
        manifest_file = project_dir / "project.json"
        if manifest_file.exists():
            try:
                with open(manifest_file, "r", encoding="utf-8") as f:
                    video_filename = json.load(f).get("video_filename", "video.mp4")
            except Exception:
                pass

    updated_plan = build_edit_plan_from_analysis(
        project_id=project_id,
        source_video=video_filename,
        total_duration=transcription.duration,
        cuts=analysis_result.cuts,
        keeps=analysis_result.keeps,
        transcript_segments=transcription.segments,
    )
    with open(edit_plan_file, "w", encoding="utf-8") as f:
        f.write(updated_plan.to_json())

    # Update manifest
    manifest_file = project_dir / "project.json"
    if manifest_file.exists():
        try:
            with open(manifest_file, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            manifest["cuts_count"] = len(analysis_result.cuts)
            manifest["keeps_count"] = len(analysis_result.keeps)
            manifest["time_saved"] = round(analysis_result.cut_duration, 2)
            manifest["savings_percent"] = round(
                (analysis_result.cut_duration / max(transcription.duration, 0.001)) * 100, 1
            )
            manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
            with open(manifest_file, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2)
        except Exception:
            pass

    if project_id in jobs and jobs[project_id].get("result"):
        jobs[project_id]["result"]["analysis"] = analysis_result.to_dict()
        jobs[project_id]["result"]["edit_plan"] = updated_plan.to_dict()

    return {
        "status": "success",
        "analysis": analysis_result.to_dict(),
        "edit_plan": updated_plan.to_dict(),
    }


def render_project_video(project_id: str) -> Dict[str, Any]:
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

    # Determine original source video filename
    manifest_file = project_dir / "project.json"
    video_filename = ""
    if manifest_file.exists():
        try:
            with open(manifest_file, "r", encoding="utf-8") as f:
                video_filename = json.load(f).get("video_filename", "")
        except Exception:
            pass

    if not video_filename:
        video_filename = jobs.get(project_id, {}).get("video_filename", "")

    if not video_filename:
        edit_plan_file = project_dir / "edit_plan.json"
        if edit_plan_file.exists():
            try:
                with open(edit_plan_file, "r", encoding="utf-8") as f:
                    video_filename = json.load(f).get("source_video", "")
            except Exception:
                pass

    if not video_filename:
        matches = list(UPLOAD_DIR.glob(f"*{project_id}*"))
        if matches:
            video_filename = matches[0].name
        else:
            raise HTTPException(status_code=400, detail="Original video file not found")

    source_video = UPLOAD_DIR / video_filename
    if not source_video.exists():
        raise HTTPException(status_code=404, detail=f"Source video {video_filename} not found in uploads")

    output_filename = f"{project_id}_cut.mp4"
    output_path = project_dir / output_filename

    try:
        apply_cuts(str(source_video), analysis, output_path=str(output_path))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rendering failed: {str(e)}")

    rendered_url = f"/media/projects/{project_id}/{output_filename}"

    # Update manifest rendered status
    if manifest_file.exists():
        try:
            with open(manifest_file, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            manifest["rendered"] = True
            manifest["rendered_url"] = rendered_url
            manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
            with open(manifest_file, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2)
        except Exception:
            pass

    return {
        "status": "success",
        "rendered_url": rendered_url,
        "output_path": str(output_path),
        "saved_seconds": round(analysis.cut_duration, 2),
    }
