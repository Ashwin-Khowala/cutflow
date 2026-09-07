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


def test_silence_cut_inside_segment_no_orphan_keep():
    """
    Regression: A silence cut that falls inside a long Whisper segment should not
    create an orphan micro-keep sliver at the tail of that segment.

    Real-world case: Whisper segment [13.76->21.20] contains the text
    "So the system isn't optimizing for the messages sent."
    A silence is detected at 18.28->20.98 (inside the segment).
    An LLM/repetition cut for [0->13.76] follows.
    Result: the gap 20.62->21.20 (0.58s) should NOT appear as a keep region.
    """
    segments = [
        Segment(text="So, the system isn't optimizing for the messages sent.", start=0.0, end=13.76),
        Segment(text="So the system isn't optimizing for the messages sent.", start=13.76, end=21.20),
        Segment(text="It's optimizing for net expected revenue.", start=21.20, end=27.78),
        Segment(text="It's optimizing for net expected revenue.", start=27.78, end=31.42),
    ]
    transcription = TranscriptionResult(segments=segments, silences=[], duration=34.33, audio_path="audio.wav")

    # The silence cut lands inside segment[1]: 18.63 -> 20.62 is inside [13.76, 21.20]
    silence_cut = CutProposal(start=18.63, end=20.62, reason=CutReason.LONG_SILENCE, explanation="Dead air", text="[silence]", confidence=0.95)
    # The repetition cut covers segment[0] and segment[2]
    retake_cut_1 = CutProposal(start=0.0, end=13.76, reason=CutReason.REPEATED_TAKE, explanation="Repeated take", text="...", confidence=0.98)
    retake_cut_2 = CutProposal(start=21.20, end=27.78, reason=CutReason.REPEATED_TAKE, explanation="Repeated take", text="...", confidence=0.98)

    merged = _merge_overlapping_cuts(
        [retake_cut_1, silence_cut, retake_cut_2],
        transcription=transcription
    )

    # Build keeps from merged cuts
    from cutflow.analyzer import _build_keep_regions
    keeps = _build_keep_regions(merged, transcription)

    # There should be NO keep sliver of < 1s at 20.62->21.20
    orphan_slivers = [k for k in keeps if (k.end - k.start) < 1.0 and k.start > 15.0 and k.end < 22.0]
    assert len(orphan_slivers) == 0, f"Found orphan micro-sliver(s): {orphan_slivers}"

    # The keep for the good "So the system..." take should be present
    good_takes = [k for k in keeps if "So the system" in k.text or (k.start >= 13.76 and k.end <= 19.5)]
    assert len(good_takes) >= 1


def test_text_attribution_precision_with_overlap_check():
    """
    Regression: A short keep sliver inside a long Whisper segment should not inherit
    the full text of that parent segment. Without word timestamps, the overlap ratio
    check should prevent this.
    """
    from cutflow.analyzer import _get_text_in_range_precise

    # A single long Whisper segment 0->12s
    segments = [
        Segment(text="It's optimizing for net expected revenue.", start=0.0, end=12.0, words=[]),
    ]

    # Ask for text in the tail sliver 11.5->12.0 (0.5s) — only 4% of the 12s segment
    text = _get_text_in_range_precise(segments, 11.5, 12.0)
    # Should return empty because 0.5/12 = 4% overlap which is below the 30% segment threshold
    assert text == "", f"Expected empty text for micro-sliver, got: {repr(text)}"

    # But for a query that covers most of the segment (e.g., 1.0->12.0)
    text_full = _get_text_in_range_precise(segments, 1.0, 12.0)
    assert "optimizing" in text_full


def test_detect_long_silences_at_boundaries():
    """
    Test that detect_long_silences snaps to 0.0 at the beginning and total_duration
    at the end, preventing 0.35s orphan dead air clips.
    """
    silences = [
        SilenceRegion(start=0.0, end=2.0, duration=2.0),
        SilenceRegion(start=5.0, end=7.5, duration=2.5),
        SilenceRegion(start=10.0, end=12.0, duration=2.0),
    ]
    cuts = detect_long_silences(silences, max_silence=1.5, keep_gap=0.35, total_duration=12.0)
    assert len(cuts) == 3
    # Beginning silence must start at 0.0, not 0.35
    assert cuts[0].start == pytest.approx(0.0)
    # Middle silence keeps natural padding on both sides
    assert cuts[1].start == pytest.approx(5.35)
    assert cuts[1].end == pytest.approx(7.15)
    # End silence must extend through to total_duration (12.0), not 11.65
    assert cuts[2].end == pytest.approx(12.0)


def test_preroll_and_postroll_dead_air_trimmed():
    """
    Test that build_analysis_result automatically trims lead-in dead air before first
    speech and lead-out dead air after final speech.
    """
    segments = [
        Segment(text="Hello welcome to the demo.", start=2.0, end=5.0),
        Segment(text="And that concludes everything.", start=6.0, end=9.0),
    ]
    transcription = TranscriptionResult(
        segments=segments,
        silences=[],
        duration=12.0,
        audio_path="test.wav",
    )
    res = build_analysis_result(transcription, llm_analysis=[], filler_cuts=[], silence_cuts=[])

    # Should have preroll cut starting at 0.0 and postroll cut ending at 12.0
    assert any(c.start == pytest.approx(0.0) and "Preroll" in c.explanation for c in res.cuts)
    assert any(c.end == pytest.approx(12.0) and "Postroll" in c.explanation for c in res.cuts)

    # All keeps must contain real spoken words and not be empty orphan slivers
    assert len(res.keeps) >= 1
    assert res.keeps[0].start > 0.0  # Does not have an orphan 0.0 -> 0.35 clip!
    assert "Hello" in res.keeps[0].text
    assert res.keeps[-1].end < 12.0  # Does not have an orphan trailing clip!
    assert "concludes" in res.keeps[-1].text


def test_build_keep_regions_eliminates_wordless_clips():
    """
    Test that _build_keep_regions never emits empty dead air gaps as keep takes.
    """
    segments = [
        Segment(text="Actual spoken take.", start=3.0, end=6.0),
    ]
    transcription = TranscriptionResult(
        segments=segments,
        silences=[],
        duration=10.0,
        audio_path="test.wav",
    )
    # Cuts from 0.0->2.5 and 7.0->10.0 leave gaps [2.5, 3.0] and [6.0, 7.0]
    # which have no spoken words
    cuts = [
        CutProposal(start=0.0, end=2.5, reason=CutReason.LONG_SILENCE, explanation="silence", text="", confidence=0.95),
        CutProposal(start=7.0, end=10.0, reason=CutReason.LONG_SILENCE, explanation="silence", text="", confidence=0.95),
    ]
    keeps = _build_keep_regions(cuts, transcription)
    # Should only emit the region containing the actual speech [3.0, 6.0]
    assert len(keeps) == 1
    assert "Actual spoken take" in keeps[0].text

