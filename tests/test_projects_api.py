"""
Tests for Modular Project Endpoints & LangGraph Agent System.
"""

import json
import pytest
from fastapi.testclient import TestClient
from pathlib import Path

from cutflow.server import app
from cutflow.config import PROJECTS_DIR

client = TestClient(app)


def test_list_projects():
    response = client.get("/api/projects")
    assert response.status_code == 200
    projects = response.json()
    assert isinstance(projects, list)
    # Check if existing local project is discovered
    if (PROJECTS_DIR / "10a0f587").exists():
        match = [p for p in projects if p["id"] == "10a0f587"]
        assert len(match) == 1
        assert "duration" in match[0]
        assert "cuts_count" in match[0]


def test_get_existing_project():
    if not (PROJECTS_DIR / "10a0f587").exists():
        pytest.skip("Project 10a0f587 not present on local disk")

    response = client.get("/api/projects/10a0f587")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "10a0f587"
    assert "transcript" in data
    assert "analysis" in data
    assert "edit_plan" in data


def test_project_sub_endpoints():
    if not (PROJECTS_DIR / "10a0f587").exists():
        pytest.skip("Project 10a0f587 not present on local disk")

    # Transcript
    t_res = client.get("/api/projects/10a0f587/transcript")
    assert t_res.status_code == 200
    assert "segments" in t_res.json()

    # Analysis
    a_res = client.get("/api/projects/10a0f587/analysis")
    assert a_res.status_code == 200
    assert "cuts" in a_res.json()

    # Edit Plan
    e_res = client.get("/api/projects/10a0f587/edit-plan")
    assert e_res.status_code == 200
    assert e_res.json()["version"] == "1.0"

    # EDL Export
    edl_res = client.get("/api/projects/10a0f587/export/edl")
    assert edl_res.status_code == 200
    assert "TITLE: CutFlow_10a0f587" in edl_res.text


def test_patch_project_name():
    if not (PROJECTS_DIR / "10a0f587").exists():
        pytest.skip("Project 10a0f587 not present on local disk")

    res = client.patch("/api/projects/10a0f587", json={"name": "Custom Test Name"})
    assert res.status_code == 200
    assert res.json()["name"] == "Custom Test Name"

    # Verify updated via get
    get_res = client.get("/api/projects/10a0f587")
    assert get_res.json()["name"] == "Custom Test Name"


def test_update_cuts_per_project():
    if not (PROJECTS_DIR / "10a0f587").exists():
        pytest.skip("Project 10a0f587 not present on local disk")

    cuts_payload = {
        "cuts": [
            {
                "start": 0.0,
                "end": 2.5,
                "reason": "manual_cut",
                "action": "cut",
                "text": "Intro stumble",
                "explanation": "Test manual cut",
                "confidence": 1.0,
            }
        ]
    }
    res = client.post("/api/projects/10a0f587/cuts", json=cuts_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert len(data["analysis"]["cuts"]) == 1
    assert data["analysis"]["cuts"][0]["start"] == 0.0


def test_agent_memory_and_query():
    if not (PROJECTS_DIR / "10a0f587").exists():
        pytest.skip("Project 10a0f587 not present on local disk")

    # Get memory
    mem_res = client.get("/api/projects/10a0f587/agent/memory")
    assert mem_res.status_code == 200
    mem_data = mem_res.json()
    assert "preferences" in mem_data

    # Query agent
    chat_res = client.post(
        "/api/projects/10a0f587/agent/chat",
        json={"message": "What cuts did you make and why?"},
    )
    assert chat_res.status_code == 200
    chat_data = chat_res.json()
    assert "response" in chat_data
    assert "action_taken" in chat_data
