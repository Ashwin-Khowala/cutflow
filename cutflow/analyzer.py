"""
Analyzer module — uses an LLM (Gemini) to detect false starts, repeated takes,
and filler words in a transcript, then produces a proposed cut list.
"""

import json
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from cutflow.transcriber import TranscriptionResult, Segment, SilenceRegion


class CutReason(str, Enum):
    FALSE_START = "false_start"        # Incomplete sentence, restarted
    REPEATED_TAKE = "repeated_take"    # Same line said again (worse version)
    FILLER_WORDS = "filler_words"      # "um", "uh", standalone fillers
    LONG_SILENCE = "long_silence"      # Dead air
    STUMBLE = "stumble"                # Mid-sentence stumble/correction


@dataclass
class CutProposal:
    """A proposed cut — a region to remove from the video."""
    start: float          # seconds
    end: float            # seconds
    reason: CutReason
    explanation: str      # human-readable explanation
    text: str             # the text being cut
    confidence: float     # 0.0 to 1.0


@dataclass
class KeepRegion:
    """A region to keep — the 'good take'."""
    start: float
    end: float
    text: str
    segment_indices: list[int] = field(default_factory=list)


@dataclass
class AnalysisResult:
    """Full analysis output with proposed cuts and keeps."""
    cuts: list[CutProposal]
    keeps: list[KeepRegion]
    total_duration: float
    kept_duration: float
    cut_duration: float
    summary: str

    def to_dict(self) -> dict:
        return {
            "summary": self.summary,
            "total_duration": round(self.total_duration, 2),
            "kept_duration": round(self.kept_duration, 2),
            "cut_duration": round(self.cut_duration, 2),
            "savings_percent": round((self.cut_duration / self.total_duration) * 100, 1) if self.total_duration > 0 else 0,
            "cuts": [
                {
                    "start": round(c.start, 3),
                    "end": round(c.end, 3),
                    "duration": round(c.end - c.start, 3),
                    "reason": c.reason.value,
                    "explanation": c.explanation,
                    "text": c.text,
                    "confidence": round(c.confidence, 2),
                }
                for c in self.cuts
            ],
            "keeps": [
                {
                    "start": round(k.start, 3),
                    "end": round(k.end, 3),
                    "duration": round(k.end - k.start, 3),
                    "text": k.text,
                }
                for k in self.keeps
            ],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


# Common filler words/phrases to detect
FILLER_PATTERNS = [
    r"\bum+\b",
    r"\buh+\b",
    r"\bah+\b",
    r"\beh+\b",
    r"\bhmm+\b",
    r"\blike\b(?=\s*,|\s+(?:um|uh|you know))",  # "like" when used as filler
    r"\byou know\b",
    r"\bI mean\b",
    r"\bbasically\b",
    r"\bactually\b(?=\s*,)",  # "actually," used as filler
    r"\bso+\b(?=\s*,\s*(?:um|uh|like))",  # "so, um..."
]

# Meta-talk, self-corrections, and director cues commonly uttered in raw takes
META_TALK_PATTERNS = [
    r"\b(?:wait|hold on|hold up|hang on)\b",
    r"\b(?:let me start over|let me restart|start over|start again|start from the top)\b",
    r"\b(?:let me redo that|let me redo|redo that|redo this)\b",
    r"\b(?:let me try again|let me try that again|try again|try that again)\b",
    r"\b(?:scratch that|cut that|scrap that)\b",
    r"\b(?:take (?:two|three|four|2|3|4|one more))\b",
    r"\b(?:one more time|once again|from the top)\b",
    r"\b(?:sorry about that|sorry,?\s+let me|my bad|oops)\b",
    r"\b(?:no wait|uh wait|wait a second|wait a minute)\b",
    r"\b(?:mic check|testing 1 2 3|test test|can you hear me)\b",
]


def detect_meta_talk_and_cues(segments: list[Segment]) -> list[CutProposal]:
    """
    Detect meta-talk, self-corrections, and director cues (e.g. 'Wait, let me start over',
    'Scratch that', 'Take two') which are obvious outtakes.
    """
    combined_pattern = "|".join(f"(?:{p})" for p in META_TALK_PATTERNS)
    meta_re = re.compile(combined_pattern, re.IGNORECASE)

    cuts = []
    for i, seg in enumerate(segments):
        text = seg.text.strip()
        if not text:
            continue

        if meta_re.search(text):
            cuts.append(CutProposal(
                start=seg.start,
                end=seg.end,
                reason=CutReason.FALSE_START,
                explanation=f"Outtake / meta-talk cue: \"{text}\"",
                text=text,
                confidence=0.98,
            ))
            # If the previous segment was very short or incomplete, cut it too as part of the failed take
            if i > 0:
                prev_seg = segments[i - 1]
                prev_words = prev_seg.text.strip().split()
                if len(prev_words) <= 5 and prev_seg.end <= seg.start + 1.0:
                    cuts.append(CutProposal(
                        start=prev_seg.start,
                        end=prev_seg.end,
                        reason=CutReason.FALSE_START,
                        explanation=f"Failed take preceding meta-talk: \"{prev_seg.text}\"",
                        text=prev_seg.text,
                        confidence=0.92,
                    ))

    return cuts


def detect_abandoned_sentences(segments: list[Segment]) -> list[CutProposal]:
    """
    Detect abandoned partial thoughts (e.g. segments that trail off mid-sentence
    ending in conjunctions or prepositions with no terminal punctuation).
    """
    trailing_words = {"and", "but", "so", "because", "with", "to", "the", "a", "an", "that", "if", "when", "or"}
    cuts = []
    n = len(segments)

    for i in range(n - 1):
        s = segments[i]
        text = s.text.strip()
        words = text.split()
        if not words:
            continue

        last_word = re.sub(r"[^\w]", "", words[-1]).lower()
        # If segment is short and ends on an unresolved trailing connector
        if len(words) <= 4 and last_word in trailing_words and not text.endswith((".", "!", "?")):
            next_s = segments[i + 1]
            # If next segment starts fresh after a gap or with a capital letter
            if next_s.start > s.end + 0.3:
                cuts.append(CutProposal(
                    start=s.start,
                    end=s.end,
                    reason=CutReason.FALSE_START,
                    explanation=f"Abandoned incomplete thought: \"{text}\"",
                    text=text,
                    confidence=0.88,
                ))

    return cuts


def detect_filler_segments(
    segments: list[Segment],
    filler_patterns: list[str] | None = None,
) -> list[CutProposal]:
    """
    Detect segments that are purely filler words.
    Only flags segments where the ENTIRE content is filler — doesn't cut
    filler words embedded in otherwise good sentences.
    """
    patterns = filler_patterns or FILLER_PATTERNS
    combined_pattern = "|".join(f"(?:{p})" for p in patterns)
    filler_re = re.compile(combined_pattern, re.IGNORECASE)

    cuts = []
    for seg in segments:
        text = seg.text.strip()
        if not text:
            continue

        # Check if the segment is almost entirely filler
        cleaned = filler_re.sub("", text).strip()
        cleaned = re.sub(r"[,.\s]+", "", cleaned)

        if len(cleaned) < 3 and len(text) > 1 and seg.start > 0 and seg.end > seg.start:
            cuts.append(CutProposal(
                start=seg.start,
                end=seg.end,
                reason=CutReason.FILLER_WORDS,
                explanation=f"Filler-only segment: \"{text}\"",
                text=text,
                confidence=0.9,
            ))

    return cuts


def detect_long_silences(
    silences: list[SilenceRegion],
    max_silence: float = 1.5,
    keep_gap: float = 0.3,
) -> list[CutProposal]:
    """
    Flag silences longer than max_silence seconds for cutting.
    Keeps a small gap (keep_gap) at the boundaries for natural pacing.
    """
    cuts = []
    for s in silences:
        if s.duration > max_silence:
            # Keep a small gap at start and end for natural feel
            cut_start = s.start + keep_gap
            cut_end = s.end - keep_gap
            if cut_end > cut_start:
                cuts.append(CutProposal(
                    start=cut_start,
                    end=cut_end,
                    reason=CutReason.LONG_SILENCE,
                    explanation=f"Dead air: {s.duration:.1f}s silence",
                    text="[silence]",
                    confidence=0.95,
                ))

    return cuts


def detect_repetition_candidates(
    segments: list[Segment],
    similarity_threshold: float = 0.60,
) -> list[CutProposal]:
    """
    Algorithmic repetition & false start detector.
    Looks for consecutive segments or segments within a 3-segment sliding window
    that restart the same sentence, phrase, or opening words.
    """
    import difflib

    cuts = []
    n = len(segments)

    for i in range(n - 1):
        s1 = segments[i]
        text1 = s1.text.strip().lower()
        # Clean punctuation for comparison
        clean_text1 = re.sub(r"[^\w\s]", "", text1).strip()
        words1 = clean_text1.split()

        if not words1:
            continue

        # Check against upcoming segments (up to 3 segments ahead)
        for j in range(i + 1, min(i + 4, n)):
            s2 = segments[j]
            text2 = s2.text.strip().lower()
            clean_text2 = re.sub(r"[^\w\s]", "", text2).strip()
            words2 = clean_text2.split()

            if not words2:
                continue

            # 1. Check matching prefix (e.g. "So today we...", "So today we are going to...")
            min_len = min(len(words1), len(words2))
            common_prefix_len = 0
            for k in range(min_len):
                if words1[k] == words2[k]:
                    common_prefix_len += 1
                else:
                    break

            is_prefix_restart = (
                (common_prefix_len >= 2 and common_prefix_len / max(1, len(words1)) >= 0.4)
                or (common_prefix_len >= 3)
            )

            # 2. Sequence similarity ratio (fuzzy matching)
            seq_ratio = difflib.SequenceMatcher(None, clean_text1, clean_text2).ratio()

            # 3. Short stumble detection (s1 is 1-3 words, followed immediately by a longer take)
            is_stumble_restart = len(words1) <= 3 and len(words2) >= 4 and any(w in words2[:3] for w in words1)

            if is_prefix_restart or seq_ratio >= similarity_threshold or is_stumble_restart:
                reason = CutReason.REPEATED_TAKE if seq_ratio >= 0.75 else CutReason.FALSE_START
                conf = 0.90 if is_prefix_restart else (0.85 if is_stumble_restart else round(min(0.95, seq_ratio), 2))
                cuts.append(CutProposal(
                    start=s1.start,
                    end=s1.end,
                    reason=reason,
                    explanation=f"Repeated take / restarted in take [{j}]: \"{s2.text[:45]}...\"",
                    text=s1.text,
                    confidence=conf,
                ))
                break

    return cuts


def _load_env_if_needed():
    """Load .env file if environment variables are not already present."""
    env_path = Path(".env")
    if env_path.exists():
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k, v = k.strip(), v.strip().strip('"').strip("'")
                        if k not in os.environ:
                            os.environ[k] = v
        except Exception:
            pass


def analyze_with_llm(
    transcription: TranscriptionResult,
    api_key: str | None = None,
    provider: str = "gemini",
    model: str | None = None,
) -> list[dict]:
    """
    Use an LLM (Groq or Gemini) to analyze the transcript with full script comprehension.
    Identifies false starts, retakes, stumbles, abandoned thoughts, and outtakes.
    """
    _load_env_if_needed()

    # Auto-detect provider if Groq API key is passed (starts with gsk_)
    if api_key and api_key.startswith("gsk_"):
        provider = "groq"

    # Build the full transcript text with numbered indices and timestamps
    transcript_lines = []
    for i, seg in enumerate(transcription.segments):
        start = _format_time(seg.start)
        end = _format_time(seg.end)
        transcript_lines.append(f"[{i}] [{start} → {end}] {seg.text}")

    transcript_text = "\n".join(transcript_lines)

    prompt = f"""You are a master video editor performing rough-cut editing on a creator's raw, unedited video transcript.

YOUR MISSION:
Understand the intended message, script storyline, and narrative continuity of the speaker.
Identify all OBVIOUS OUTTAKES, FAILED TAKES, RESTARTS, AND STUMBLES so the final video sounds 100% polished, natural, and confident.

RAW TRANSCRIPT (Numbered lines with segment indices [0], [1], ... and timecodes):
{transcript_text}

EDITING DIRECTIVES (SCRIPT COMPREHENSION):
1. MULTI-TAKE RESTARTS (CRITICAL):
   - Whenever the speaker attempts to say the same line, point, or sentence 2 or more times (e.g. Take 1 stumbles or is incomplete, Take 2 is better), CUT ALL EARLIER ATTEMPTS ([action: 'cut']).
   - KEEP ONLY THE FINAL, MOST ARTICULATE, COMPLETE TAKE ([action: 'keep']).
2. FALSE STARTS & ABANDONED THOUGHTS:
   - When a sentence cuts off or trails off mid-phrase (e.g. "Today we are...", "Because when..."), followed by a restart, MARK THE ABANDONED SEGMENT AS "cut".
3. META-TALK & DIRECTOR CUES:
   - Cut any off-script meta-commentary: "Wait", "Let me start over", "Hold on", "Scratch that", "Sorry", "Take two", "Can I say that again", laughter at mistakes, or mic checks.
4. NARRATIVE CONTINUITY:
   - Understand the flow of ideas. If a segment repeats an idea that was just articulated better in the subsequent sentence, remove the redundant attempt.
5. PRESERVE INTENDED CONTENT:
   - Keep all valid narrative points, explanations, and demonstrations that form the real substance of the video.

OUTPUT FORMAT:
Respond ONLY with a JSON object containing a "cuts" array. Every cut decision must specify segment indices, action ('cut' or 'keep'), reason ('repeated_take', 'false_start', 'stumble'), and explanation.

JSON Schema:
{{
  "cuts": [
    {{"action": "cut", "segments": [0, 1], "reason": "repeated_take", "explanation": "Speaker stumbled on opening line twice before delivering clean version in take [2]", "confidence": 0.98}},
    {{"action": "keep", "segments": [2], "reason": "repeated_take", "explanation": "Polished, complete delivery of introduction", "confidence": 0.98}},
    {{"action": "cut", "segments": [5], "reason": "false_start", "explanation": "Abandoned partial sentence before restarting", "confidence": 0.95}},
    {{"action": "cut", "segments": [8], "reason": "stumble", "explanation": "Meta-commentary ('Wait let me redo that')", "confidence": 0.99}}
  ]
}}"""

    # --- GROQ PROVIDER ---
    if provider.lower() == "groq":
        groq_key = api_key or os.environ.get("GROQ_API_KEY")
        if not groq_key:
            print("⚠️  No Groq API key found. Set GROQ_API_KEY env var or pass in Settings.")
            print("   Skipping LLM analysis — only filler, meta-talk, and silence detection will run.")
            return []

        selected_model = model or os.environ.get("GROQ_MODEL") or "openai/gpt-oss-120b"
        print(f"🚀 Analyzing script semantics with Groq (Model: {selected_model})...")

        try:
            from groq import Groq
            client = Groq(api_key=groq_key)

            completion = client.chat.completions.create(
                model=selected_model,
                messages=[
                    {"role": "system", "content": "You are a specialized AI video editing assistant. You must analyze the script structure and output only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
            )

            content = completion.choices[0].message.content or "{}"
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                return parsed.get("cuts", parsed.get("actions", parsed.get("analysis", [])))
            elif isinstance(parsed, list):
                return parsed
            return []

        except Exception as e:
            print(f"⚠️  Groq LLM analysis failed: {e}")
            return []

    # --- GEMINI PROVIDER ---
    gemini_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not gemini_key:
        print("⚠️  No Gemini API key found. Set GEMINI_API_KEY or GOOGLE_API_KEY env var.")
        print("   Skipping LLM analysis — only filler, meta-talk, and silence detection will run.")
        return []

    selected_model = model or os.environ.get("GEMINI_MODEL") or "gemini-2.0-flash"
    print(f"✨ Analyzing script semantics with Gemini (Model: {selected_model})...")

    try:
        from google import genai
        client = genai.Client(api_key=gemini_key)

        response = client.models.generate_content(
            model=selected_model,
            contents=prompt,
        )

        response_text = response.text.strip()
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        analysis = json.loads(response_text)
        if isinstance(analysis, dict):
            return analysis.get("cuts", analysis.get("actions", analysis.get("analysis", [])))
        elif isinstance(analysis, list):
            return analysis
        return []

    except Exception as e:
        print(f"⚠️  Gemini LLM analysis failed: {e}")
        return []


def build_analysis_result(
    transcription: TranscriptionResult,
    llm_analysis: list[dict],
    filler_cuts: list[CutProposal],
    silence_cuts: list[CutProposal],
    repetition_cuts: list[CutProposal] | None = None,
    meta_talk_cuts: list[CutProposal] | None = None,
    abandoned_cuts: list[CutProposal] | None = None,
) -> AnalysisResult:
    """
    Combine LLM analysis with filler/silence detection, meta-talk outtakes,
    abandoned thought fragments, and algorithmic repetition detection
    into a unified AnalysisResult.
    """
    all_cuts = (
        list(filler_cuts)
        + list(silence_cuts)
        + (list(repetition_cuts) if repetition_cuts else [])
        + (list(meta_talk_cuts) if meta_talk_cuts else [])
        + (list(abandoned_cuts) if abandoned_cuts else [])
    )
    segments = transcription.segments

    # Process LLM analysis into CutProposals
    for item in llm_analysis:
        if item.get("action") != "cut":
            continue

        seg_indices = item.get("segments", [])
        if not seg_indices:
            continue

        # Get time range from the segments being cut
        cut_segments = [segments[i] for i in seg_indices if i < len(segments)]
        if not cut_segments:
            continue

        start = min(s.start for s in cut_segments)
        end = max(s.end for s in cut_segments)
        text = " ".join(s.text for s in cut_segments)

        reason_str = item.get("reason", "false_start")
        try:
            reason = CutReason(reason_str)
        except ValueError:
            reason = CutReason.FALSE_START

        all_cuts.append(CutProposal(
            start=start,
            end=end,
            reason=reason,
            explanation=item.get("explanation", ""),
            text=text,
            confidence=float(item.get("confidence", 0.7)),
        ))

    # Sort cuts by start time and merge overlapping
    all_cuts.sort(key=lambda c: c.start)
    merged_cuts = _merge_overlapping_cuts(all_cuts)

    # Build keep regions (everything NOT cut)
    keeps = _build_keep_regions(merged_cuts, transcription)

    # Calculate durations
    total_duration = transcription.duration
    cut_duration = sum(c.end - c.start for c in merged_cuts)
    kept_duration = total_duration - cut_duration

    # Build summary
    n_false_starts = sum(1 for c in merged_cuts if c.reason in (CutReason.FALSE_START, CutReason.REPEATED_TAKE, CutReason.STUMBLE))
    n_fillers = sum(1 for c in merged_cuts if c.reason == CutReason.FILLER_WORDS)
    n_silences = sum(1 for c in merged_cuts if c.reason == CutReason.LONG_SILENCE)

    summary = (
        f"Found {len(merged_cuts)} cuts to propose: "
        f"{n_false_starts} false starts/retakes/outtakes, {n_fillers} filler segments, {n_silences} long silences. "
        f"Would reduce {total_duration:.1f}s → {kept_duration:.1f}s "
        f"(saving {cut_duration:.1f}s / {(cut_duration / max(0.1, total_duration) * 100):.0f}%)."
    )

    return AnalysisResult(
        cuts=merged_cuts,
        keeps=keeps,
        total_duration=total_duration,
        kept_duration=kept_duration,
        cut_duration=cut_duration,
        summary=summary,
    )


def _merge_overlapping_cuts(cuts: list[CutProposal]) -> list[CutProposal]:
    """Merge overlapping cut regions."""
    if not cuts:
        return []

    merged = [cuts[0]]
    for cut in cuts[1:]:
        last = merged[-1]
        if cut.start <= last.end + 0.1:  # 100ms overlap tolerance
            # Merge: extend the end, keep higher confidence
            merged[-1] = CutProposal(
                start=last.start,
                end=max(last.end, cut.end),
                reason=last.reason if last.confidence >= cut.confidence else cut.reason,
                explanation=f"{last.explanation}; {cut.explanation}",
                text=f"{last.text} | {cut.text}",
                confidence=max(last.confidence, cut.confidence),
            )
        else:
            merged.append(cut)

    return merged


def _build_keep_regions(
    cuts: list[CutProposal],
    transcription: TranscriptionResult,
) -> list[KeepRegion]:
    """Build keep regions from the gaps between cuts."""
    keeps = []
    current_start = 0.0
    total_duration = transcription.duration

    for cut in cuts:
        if cut.start > current_start + 0.05:  # Skip tiny gaps
            # Find transcript text for this keep region
            text = _get_text_in_range(transcription.segments, current_start, cut.start)
            keeps.append(KeepRegion(
                start=current_start,
                end=cut.start,
                text=text,
            ))
        current_start = cut.end

    # Final keep region after last cut
    if current_start < total_duration - 0.05:
        text = _get_text_in_range(transcription.segments, current_start, total_duration)
        keeps.append(KeepRegion(
            start=current_start,
            end=total_duration,
            text=text,
        ))

    return keeps


def _get_text_in_range(segments: list[Segment], start: float, end: float) -> str:
    """Get concatenated text from segments that fall within a time range."""
    texts = []
    for seg in segments:
        # Segment overlaps with our range
        if seg.end > start and seg.start < end:
            texts.append(seg.text.strip())
    return " ".join(texts) if texts else ""


def _format_time(seconds: float) -> str:
    """Format seconds as MM:SS.mmm"""
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes:02d}:{secs:06.3f}"


def analyze_transcript(
    transcription: TranscriptionResult,
    api_key: str | None = None,
    provider: str = "gemini",
    model: str | None = None,
    max_silence: float = 1.5,
    progress_callback=None,
) -> AnalysisResult:
    """
    Full analysis pipeline with script comprehension:
    1. Detect filler-only segments
    2. Detect meta-talk outtakes & director cues ('Wait', 'Hold on', 'Scratch that')
    3. Detect abandoned partial thought fragments
    4. Detect algorithmic repetition & restart candidates
    5. Analyze script narrative flow & multi-take restarts with LLM
    6. Merge everything into an optimized proposed cut list
    """
    if progress_callback:
        progress_callback(10.0, "Detecting filler words & meta-talk...")
    print("🔍 Detecting filler words and meta-talk cues...")
    filler_cuts = detect_filler_segments(transcription.segments)
    meta_talk_cuts = detect_meta_talk_and_cues(transcription.segments)
    abandoned_cuts = detect_abandoned_sentences(transcription.segments)
    print(f"   Found {len(filler_cuts)} fillers, {len(meta_talk_cuts)} meta-talk cues, {len(abandoned_cuts)} abandoned fragments")

    if progress_callback:
        progress_callback(25.0, "Analyzing silence and dead air boundaries...")
    print("🔇 Analyzing silence regions...")
    silence_cuts = detect_long_silences(transcription.silences, max_silence=max_silence)
    print(f"   Found {len(silence_cuts)} cuttable silences")

    if progress_callback:
        progress_callback(45.0, "Scanning for phrase repetitions and stumbles...")
    print("🔁 Scanning for repetition and false start patterns...")
    repetition_cuts = detect_repetition_candidates(transcription.segments)
    print(f"   Found {len(repetition_cuts)} candidate repeated takes")

    if progress_callback:
        progress_callback(65.0, f"Analyzing script storyline & takes with {provider.upper()}...")
    print(f"🧠 Analyzing script storyline with {provider.upper()} for false starts and retakes...")
    llm_analysis = analyze_with_llm(transcription, api_key=api_key, provider=provider, model=model)
    n_llm_cuts = sum(1 for item in llm_analysis if item.get("action") == "cut")
    print(f"   LLM identified {n_llm_cuts} regions to cut")

    if progress_callback:
        progress_callback(95.0, "Building and optimizing proposed cut list...")
    print("📋 Building cut list...")
    result = build_analysis_result(
        transcription,
        llm_analysis,
        filler_cuts,
        silence_cuts,
        repetition_cuts=repetition_cuts,
        meta_talk_cuts=meta_talk_cuts,
        abandoned_cuts=abandoned_cuts,
    )
    print(f"✅ {result.summary}")

    return result
