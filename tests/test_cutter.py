"""
Unit tests for the cutter module and preview generator.
"""

import pytest
from unittest.mock import patch, MagicMock

from cutflow.analyzer import AnalysisResult, CutProposal, CutReason, KeepRegion
from cutflow.cutter import preview_cuts, apply_cuts


def test_preview_cuts_formatting():
    cuts = [
        CutProposal(
            start=1.2,
            end=3.5,
            reason=CutReason.FALSE_START,
            explanation="Incomplete take",
            text="Today we gonna...",
            confidence=0.92,
        )
    ]
    keeps = [
        KeepRegion(start=3.5, end=10.0, text="Today we are going to explore AI video editing.")
    ]
    analysis = AnalysisResult(
        cuts=cuts,
        keeps=keeps,
        total_duration=10.0,
        kept_duration=6.5,
        cut_duration=2.3,
        summary="Found 1 cut to propose.",
    )

    preview_text = preview_cuts(analysis)
    assert "PROPOSED CUT LIST" in preview_text
    assert "SEGMENTS TO CUT" in preview_text
    assert "false_start" in preview_text
    assert "Today we gonna..." in preview_text
    assert "SEGMENTS TO KEEP" in preview_text
    assert "Total: 10.0s → 6.5s" in preview_text


@patch("subprocess.run")
def test_apply_cuts_single_trim(mock_run, tmp_path):
    mock_run.return_value = MagicMock(returncode=0)
    fake_video = tmp_path / "test.mp4"
    fake_video.write_text("dummy")

    keeps = [KeepRegion(start=0.0, end=5.0, text="Clean video")]
    analysis = AnalysisResult(
        cuts=[],
        keeps=keeps,
        total_duration=5.0,
        kept_duration=5.0,
        cut_duration=0.0,
        summary="Clean",
    )

    out_path = tmp_path / "out.mp4"
    res = apply_cuts(str(fake_video), analysis, output_path=str(out_path))
    assert res == str(out_path)
