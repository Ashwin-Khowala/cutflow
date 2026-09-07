"""
Unit tests for the transcription and silence detection module.
"""

import json
import pytest
from unittest.mock import patch, MagicMock

from cutflow.transcriber import (
    Word,
    Segment,
    SilenceRegion,
    TranscriptionResult,
    _parse_timestamp,
    _parse_cli_output,
    _parse_moonshine_result,
    detect_silence,
    extract_audio,
)


def test_parse_timestamp():
    assert _parse_timestamp("00:05.230") == pytest.approx(5.230)
    assert _parse_timestamp("01:30.500") == pytest.approx(90.500)
    assert _parse_timestamp("01:05:10.000") == pytest.approx(3910.0)
    assert _parse_timestamp("42.5") == pytest.approx(42.5)


def test_parse_cli_output_timestamp_lines():
    sample_output = """
    [00:00.000 --> 00:03.500] Hello everyone and welcome.
    [00:04.000 --> 00:07.200] Today we are talking about video editing.
    """
    segments = _parse_cli_output(sample_output)
    assert len(segments) == 2
    assert segments[0].text == "Hello everyone and welcome."
    assert segments[0].start == pytest.approx(0.0)
    assert segments[0].end == pytest.approx(3.5)
    assert segments[1].text == "Today we are talking about video editing."
    assert segments[1].start == pytest.approx(4.0)
    assert segments[1].end == pytest.approx(7.2)


def test_parse_cli_output_json():
    sample_json = json.dumps({
        "segments": [
            {
                "text": "First line of speech",
                "start": 1.0,
                "end": 3.0,
                "words": [{"word": "First", "start": 1.0, "end": 1.5}]
            }
        ]
    })
    segments = _parse_cli_output(sample_json)
    assert len(segments) == 1
    assert segments[0].text == "First line of speech"
    assert len(segments[0].words) == 1
    assert segments[0].words[0].text == "First"


def test_transcription_result_serialization():
    seg = Segment(text="Test", start=0.0, end=1.5, words=[Word(text="Test", start=0.0, end=1.5)])
    sil = SilenceRegion(start=1.5, end=3.0, duration=1.5)
    res = TranscriptionResult(segments=[seg], silences=[sil], duration=3.0, audio_path="audio.wav")

    d = res.to_dict()
    assert d["duration"] == 3.0
    assert len(d["segments"]) == 1
    assert len(d["silences"]) == 1
    assert "Test" in res.to_json()


@patch("subprocess.run")
def test_detect_silence(mock_run):
    mock_run.return_value = MagicMock(
        returncode=0,
        stderr="""
        [silencedetect @ 000002] silence_start: 4.521
        [silencedetect @ 000002] silence_end: 7.123 | silence_duration: 2.602
        [silencedetect @ 000002] silence_start: 12.000
        [silencedetect @ 000002] silence_end: 14.500 | silence_duration: 2.500
        """
    )
    silences = detect_silence("test.wav", noise_threshold="-35dB", min_duration=0.8)
    assert len(silences) == 2
    assert silences[0].start == pytest.approx(4.521)
    assert silences[0].end == pytest.approx(7.123)
    assert silences[0].duration == pytest.approx(2.602)
    assert silences[1].start == pytest.approx(12.0)
