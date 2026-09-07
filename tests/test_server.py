"""
Tests for FastAPI Web Server endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from cutflow.server import app, jobs

client = TestClient(app)


def test_root_api_status():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "online"


def test_upload_video(tmp_path):
    fake_file_content = b"fake video bytes"
    response = client.post(
        "/api/upload",
        files={"file": ("test_video.mp4", fake_file_content, "video/mp4")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "test_video.mp4" in data["video_filename"]
    assert "/media/uploads/" in data["video_url"]


def test_get_status_not_found():
    response = client.get("/api/status/non_existent_project")
    assert response.status_code == 404


def test_get_status_existing():
    jobs["test_proj_1"] = {
        "id": "test_proj_1",
        "status": "ready",
        "message": "Done",
        "result": None,
        "error": None
    }
    response = client.get("/api/status/test_proj_1")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_get_supported_models():
    response = client.get("/api/models")
    assert response.status_code == 200
    data = response.json()
    assert "providers" in data
    assert any(p["id"] == "groq" for p in data["providers"])
    assert any(p["id"] == "gemini" for p in data["providers"])


def test_storage_endpoints():
    info_res = client.get("/api/storage/info")
    assert info_res.status_code == 200
    info_data = info_res.json()
    assert "total_mb" in info_data
    assert "upload_count" in info_data

    cleanup_res = client.post("/api/storage/cleanup")
    assert cleanup_res.status_code == 200
    assert cleanup_res.json()["status"] == "success"

