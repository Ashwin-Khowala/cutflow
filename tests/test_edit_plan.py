"""
Tests for EditPlan intermediate representation (IR) and serialization.
"""

import json
from cutflow.edit_plan import (
    TimelineEntry,
    EditPlanStats,
    EditPlan,
    build_edit_plan_from_analysis,
)


def test_edit_plan_creation_and_stats():
    cuts = [
        {
            "start": 5.0,
            "end": 8.0,
            "reason": "filler_words",
            "explanation": "Removed filler words",
            "text": "um like",
            "confidence": 0.95,
        }
    ]
    keeps = [
        {"start": 0.0, "end": 5.0, "text": "Hello world."},
        {"start": 8.0, "end": 15.0, "text": "This is a great video."},
    ]

    plan = build_edit_plan_from_analysis(
        project_id="test_proj_123",
        source_video="input.mp4",
        total_duration=15.0,
        cuts=cuts,
        keeps=keeps,
        provider="groq",
        model="gpt-oss-120b",
    )

    assert plan.project_id == "test_proj_123"
    assert plan.source_video == "input.mp4"
    assert len(plan.timeline) == 3
    assert plan.stats.original_duration == 15.0
    assert plan.stats.clean_duration == 12.0
    assert plan.stats.time_saved == 3.0
    assert plan.stats.cuts_count == 1
    assert plan.stats.keeps_count == 2


def test_edit_plan_json_serialization():
    plan = EditPlan(
        project_id="p1",
        source_video="test.mp4",
        source_duration=10.0,
        stats=EditPlanStats(10.0, 8.0, 2.0, 20.0, 1, 1),
        timeline=[
            TimelineEntry(
                id="entry_001",
                start=0.0,
                end=8.0,
                duration=8.0,
                type="a_roll",
                action="keep",
                text="Keep this section.",
            ),
            TimelineEntry(
                id="entry_002",
                start=8.0,
                end=10.0,
                duration=2.0,
                type="cut",
                action="cut",
                reason="false_start",
                text="Cut this stumble.",
            ),
        ],
    )

    json_str = plan.to_json()
    data = json.loads(json_str)

    assert data["project_id"] == "p1"
    assert data["stats"]["time_saved"] == 2.0
    assert len(data["timeline"]) == 2
    assert data["timeline"][0]["action"] == "keep"
    assert data["timeline"][1]["action"] == "cut"


def test_edit_plan_edl_export():
    plan = EditPlan(
        project_id="p1",
        source_video="test.mp4",
        source_duration=10.0,
        stats=EditPlanStats(10.0, 8.0, 2.0, 20.0, 1, 1),
        timeline=[
            TimelineEntry(
                id="entry_001",
                start=0.0,
                end=8.0,
                duration=8.0,
                type="a_roll",
                action="keep",
                text="Keep this section.",
            ),
            TimelineEntry(
                id="entry_002",
                start=8.0,
                end=10.0,
                duration=2.0,
                type="cut",
                action="cut",
                reason="false_start",
            ),
        ],
    )

    edl = plan.to_edl(title="MyProject", fps=30.0)
    assert "TITLE: MyProject" in edl
    assert "FCM: NON-DROP FRAME" in edl
    assert "001  AX       V     C" in edl
