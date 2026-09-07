"""
CutFlow Storage Service — Utilities for storage usage calculation and auto-cleanup.
"""

import shutil
import time
from typing import Dict, Any
from cutflow.config import UPLOAD_DIR, PROJECTS_DIR


def cleanup_storage(max_age_hours: float = 3.0, keep_latest_uploads: int = 5):
    """
    Purges old video uploads and temporary project directories from cutflow_data
    to keep disk usage minimal.
    """
    now = time.time()
    try:
        # 1. Clean uploads
        upload_files = sorted(
            [f for f in UPLOAD_DIR.glob("*") if f.is_file()],
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        for i, file_path in enumerate(upload_files):
            if i >= keep_latest_uploads:
                age_hours = (now - file_path.stat().st_mtime) / 3600.0
                if age_hours > max_age_hours:
                    try:
                        file_path.unlink()
                        print(f"🧹 Auto-cleaned old upload: {file_path.name}")
                    except Exception:
                        pass

        # 2. Clean old project directories
        project_dirs = sorted(
            [d for d in PROJECTS_DIR.iterdir() if d.is_dir()],
            key=lambda d: d.stat().st_mtime,
            reverse=True,
        )
        for i, p_dir in enumerate(project_dirs):
            if i >= keep_latest_uploads:
                age_hours = (now - p_dir.stat().st_mtime) / 3600.0
                if age_hours > max_age_hours:
                    try:
                        shutil.rmtree(p_dir, ignore_errors=True)
                        print(f"🧹 Auto-cleaned old project dir: {p_dir.name}")
                    except Exception:
                        pass
    except Exception as e:
        print(f"⚠️  Cleanup warning: {e}")


def get_storage_stats() -> Dict[str, Any]:
    """Calculate total MB used in uploads and projects."""
    upload_bytes = sum(f.stat().st_size for f in UPLOAD_DIR.glob("*") if f.is_file())
    project_bytes = sum(f.stat().st_size for f in PROJECTS_DIR.rglob("*") if f.is_file())
    total_mb = (upload_bytes + project_bytes) / (1024 * 1024)
    return {
        "upload_mb": round(upload_bytes / (1024 * 1024), 2),
        "projects_mb": round(project_bytes / (1024 * 1024), 2),
        "total_mb": round(total_mb, 2),
        "upload_count": len(list(UPLOAD_DIR.glob("*"))),
        "project_count": len(list(PROJECTS_DIR.iterdir())),
    }
