"""
Unit tests for the Analyzer module: false starts, repeated takes, and filler detection.
"""

import pytest
from unittest.mock import patch, MagicMock

from cutflow.transcriber import Segment, SilenceRegion, TranscriptionResult, Word
from cutflow.analyzer import (
    CutProposal,
    CutReason,
    detect_filler_segments,
    detect_long_silences,
    detect_repetition_candidates,
    detect_meta_talk_and_cues,
    _merge_overlapping_cuts,
    _build_keep_regions,
    build_analysis_result,
    analyze_with_llm,
)


def test_detect_meta_talk_and_cues():
    segments = [
        Segment(text="Wait, let me start over.", start=2.0, end=3.5),
        Segment(text="Here is the actual content.", start=4.0, end=6.0),
    ]
    cuts = detect_meta_talk_and_cues(segments)
    assert len(cuts) >= 1
    assert "Wait" in cuts[0].text
    assert cuts[0].reason == CutReason.FALSE_START


def test_detect_repetition_candidates():
    segments = [
        Segment(text="Welcome back everybody today we are...", start=0.0, end=2.0),
        Segment(text="Welcome back everybody today we are going to talk about video editing.", start=2.5, end=6.5),
        Segment(text="Next point is simple.", start=7.0, end=9.0),
    ]
    cuts = detect_repetition_candidates(segments)
    assert len(cuts) == 1
    assert cuts[0].start == pytest.approx(0.0)
    assert cuts[0].end == pytest.approx(2.0)
    assert cuts[0].reason in (CutReason.REPEATED_TAKE, CutReason.FALSE_START)


def test_detect_filler_segments():
    segments = [
        Segment(text="Um, uh...", start=0.5, end=1.8),
        Segment(text="This is an important actual statement.", start=2.0, end=5.0),
        Segment(text="like, you know", start=5.2, end=6.5),
        Segment(text="I like video editing.", start=6.8, end=8.5),
    ]
    cuts = detect_filler_segments(segments)
    assert len(cuts) == 2
    assert cuts[0].text == "Um, uh..."
    assert cuts[0].reason == CutReason.FILLER_WORDS
    assert cuts[1].text == "like, you know"
    # "I like video editing" should NOT be cut
    assert not any(c.text == "I like video editing." for c in cuts)


def test_detect_long_silences():
    silences = [
        SilenceRegion(start=1.0, end=4.0, duration=3.0),
        SilenceRegion(start=6.0, end=6.5, duration=0.5),  # Below threshold
    ]
    cuts = detect_long_silences(silences, max_silence=1.5, keep_gap=0.3)
    assert len(cuts) == 1
    assert cuts[0].start == pytest.approx(1.3)
    assert cuts[0].end == pytest.approx(3.7)
    assert cuts[0].reason == CutReason.LONG_SILENCE


def test_merge_overlapping_cuts():
    cuts = [
        CutProposal(start=1.0, end=3.0, reason=CutReason.FALSE_START, explanation="Take 1", text="Hello", confidence=0.8),
        CutProposal(start=2.8, end=4.5, reason=CutReason.FALSE_START, explanation="Take 2", text="Hello world", confidence=0.9),
        CutProposal(start=6.0, end=7.0, reason=CutReason.FILLER_WORDS, explanation="Um", text="um", confidence=0.95),
    ]
    merged = _merge_overlapping_cuts(cuts)
    assert len(merged) == 2
    assert merged[0].start == pytest.approx(1.0)
    assert merged[0].end == pytest.approx(4.5)
    assert merged[1].start == pytest.approx(6.0)


def test_build_keep_regions():
    segments = [
        Segment(text="Start intro", start=0.0, end=2.0),
        Segment(text="False start take", start=2.0, end=4.0),
        Segment(text="Real good line", start=4.5, end=7.0),
    ]
    transcription = TranscriptionResult(
        segments=segments,
        silences=[],
        duration=7.0,
        audio_path="test.wav",
    )
    cuts = [
        CutProposal(start=2.0, end=4.0, reason=CutReason.FALSE_START, explanation="Bad take", text="False start take", confidence=0.9)
    ]
    keeps = _build_keep_regions(cuts, transcription)
    assert len(keeps) == 2
    assert keeps[0].start == pytest.approx(0.0)
    assert keeps[0].end == pytest.approx(2.0)
    assert keeps[1].start == pytest.approx(4.0)
    assert keeps[1].end == pytest.approx(7.0)


def test_build_analysis_result():
    segments = [
        Segment(text="So today we're going to—", start=0.0, end=2.0),
        Segment(text="So today we're going to talk about CutFlow.", start=2.5, end=6.0),
    ]
    transcription = TranscriptionResult(
        segments=segments,
        silences=[],
        duration=6.0,
        audio_path="test.wav",
    )
    llm_analysis = [
        {
            "action": "cut",
            "segments": [0],
            "reason": "false_start",
            "explanation": "Speaker stopped before completing sentence",
            "confidence": 0.9,
        }
    ]
    res = build_analysis_result(transcription, llm_analysis, filler_cuts=[], silence_cuts=[])
    assert len(res.cuts) == 1
    assert res.cuts[0].start == pytest.approx(0.0)
    assert res.cuts[0].end == pytest.approx(2.0)
    assert res.total_duration == pytest.approx(6.0)
    assert res.kept_duration == pytest.approx(4.0)
    assert res.cut_duration == pytest.approx(2.0)


@patch("groq.Groq")
def test_analyze_with_llm_groq(mock_groq_class):
    mock_client = MagicMock()
    mock_groq_class.return_value = mock_client
    
    mock_choice = MagicMock()
    mock_choice.message.content = '{"cuts": [{"action": "cut", "segments": [0], "reason": "false_start", "explanation": "Restart take", "confidence": 0.95}]}'
    mock_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

    segments = [
        Segment(text="First bad take", start=0.0, end=1.5),
        Segment(text="Good final take", start=2.0, end=4.0),
    ]
    transcription = TranscriptionResult(segments=segments, silences=[], duration=4.0, audio_path="audio.wav")

    res = analyze_with_llm(
        transcription,
        api_key="gsk_test_12345",
        provider="groq",
        model="openai/gpt-oss-120b"
    )
    assert len(res) == 1
    assert res[0]["action"] == "cut"
    assert res[0]["reason"] == "false_start"


def test_detect_repetition_with_lead_in_words():
    """Verify that 'I made this' followed by 'then again I made this xyz' is detected as a repetition."""
    segments = [
        Segment(text="I made this", start=1.0, end=2.5),
        Segment(text="then again I made this xyz for the demo", start=3.0, end=6.0),
    ]
    cuts = detect_repetition_candidates(segments)
    assert len(cuts) >= 1
    assert cuts[0].start == pytest.approx(1.0)
    assert cuts[0].end == pytest.approx(2.5)
    assert cuts[0].reason == CutReason.REPEATED_TAKE


def test_detect_intra_segment_repetition():
    """Verify repetition occurring inside a single segment is detected."""
    segments = [
        Segment(text="I made this then again I made this xyz", start=1.0, end=5.0),
    ]
    cuts = detect_repetition_candidates(segments)
    assert len(cuts) == 1
    assert cuts[0].reason == CutReason.REPEATED_TAKE
    assert "i made this" in cuts[0].text.lower()


def test_bridge_micro_gap_between_cuts():
    """Verify micro-gaps (<=1.8s with <=3 words) between cuts are bridged."""
    segments = [
        Segment(text="First failed take", start=1.0, end=3.0),
        Segment(text="um", start=3.5, end=4.0),
        Segment(text="Dead air pause", start=4.5, end=6.5),
    ]
    transcription = TranscriptionResult(segments=segments, silences=[], duration=8.0, audio_path="audio.wav")
    cuts = [
        CutProposal(start=1.0, end=3.0, reason=CutReason.FALSE_START, explanation="Take 1", text="First failed take", confidence=0.9),
        CutProposal(start=4.5, end=6.5, reason=CutReason.LONG_SILENCE, explanation="Silence", text="[silence]", confidence=0.9),
    ]
    merged = _merge_overlapping_cuts(cuts, transcription=transcription)
    # The 1.5s gap between 3.0 and 4.5 contains only "um", so it should be bridged into 1 continuous cut
    assert len(merged) == 1
    assert merged[0].start == pytest.approx(1.0)
    assert merged[0].end == pytest.approx(6.5)


def test_preserve_valid_content():
    """Verify normal complete sentences with pauses are not cut."""
    from cutflow.analyzer import detect_abandoned_sentences
    segments = [
        Segment(text="We built this because", start=1.0, end=2.5),
        Segment(text="it was an open source project.", start=3.0, end=5.0),
    ]
    cuts = detect_abandoned_sentences(segments)
    # Neither segment should be cut because there is no meta-talk or retake
    assert len(cuts) == 0


def test_preserve_sentences_with_shared_subject():
    """Verify that consecutive sentences sharing a subject across periods are NOT cut."""
    segments = [
        Segment(text="the AI can help resolve them. The AI guardrails are meant to not bombard the user", start=1.0, end=6.0),
    ]
    cuts = detect_repetition_candidates(segments)
    assert len(cuts) == 0


def test_preserve_completed_short_sentence():
    """Verify short completed sentences like 'a message.' are not cut due to stopword matches."""
    segments = [
        Segment(text="I never wanted it to become something like if the payment fails, then immediately send", start=1.0, end=4.0),
        Segment(text="a message.", start=4.0, end=5.0),
        Segment(text="That's a very naive way of thinking.", start=5.0, end=8.0),
    ]
    cuts = detect_repetition_candidates(segments)
    assert not any("message" in c.text for c in cuts)


def test_sub_second_gap_island_elimination():
    """Verify sub-second micro-gaps (e.g. 0.6s or 0.25s) between cuts are unconditionally merged into 1 continuous cut."""
    cuts = [
        CutProposal(start=10.0, end=14.0, reason=CutReason.LONG_SILENCE, explanation="Silence 1", text="[silence]", confidence=0.95),
        CutProposal(start=14.6, end=18.0, reason=CutReason.FALSE_START, explanation="Restart", text="bad take", confidence=0.95),
    ]
    merged = _merge_overlapping_cuts(cuts)
    assert len(merged) == 1
    assert merged[0].start == pytest.approx(10.0)
    assert merged[0].end == pytest.approx(18.0)


def test_retake_detection_with_word_variation():
    """Verify a retake with slight verbal variation ('I gave it also added' -> 'I also added') is detected."""
    segments = [
        Segment(text="I gave it also added the support for voice calls", start=1.0, end=4.0),
        Segment(text="I also added the support for voice interactions which can communicate", start=4.5, end=8.0),
    ]
    cuts = detect_repetition_candidates(segments)
    assert len(cuts) == 1
    assert cuts[0].start == pytest.approx(1.0)
    assert cuts[0].end == pytest.approx(4.0)



