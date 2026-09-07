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
    Detect genuine abandoned thoughts (e.g. segments that stop abruptly
    and are followed by a meta-talk cue or an explicit restart).
    Conservative to avoid cutting normal conversational pauses or casual phrasing.
    """
    cuts = []
    n = len(segments)

    combined_meta = "|".join(f"(?:{p})" for p in META_TALK_PATTERNS)
    for i in range(n - 1):
        s = segments[i]
        text = s.text.strip()
        words = text.split()
        if not words:
            continue

        # Only check very short segments (1-3 words) that end without terminal punctuation
        if len(words) <= 3 and not text.endswith((".", "!", "?")):
            next_s = segments[i + 1]
            # Only cut if immediately followed by explicit meta-talk/director cue
            if re.search(combined_meta, next_s.text, re.IGNORECASE):
                cuts.append(CutProposal(
                    start=s.start,
                    end=s.end,
                    reason=CutReason.FALSE_START,
                    explanation=f"Abandoned fragment before meta-talk: \"{text}\"",
                    text=text,
                    confidence=0.90,
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
    max_silence: float = 1.8,
    keep_gap: float = 0.35,
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


COMMON_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with",
    "is", "was", "are", "were", "it", "that", "this", "i", "you", "we", "he", "she",
    "they", "my", "your", "so", "as", "be", "by", "do", "did", "have", "had", "has",
    "if", "then", "like", "will", "would", "can", "could", "all"
}


def detect_repetition_candidates(
    segments: list[Segment],
    similarity_threshold: float = 0.55,
) -> list[CutProposal]:
    """
    Algorithmic repetition & false start detector.
    Detects:
    1. Cross-segment restarts where the speaker retries a phrase with or without leading restart words
       (e.g. 'I made this' followed by 'then again I made this xyz').
    2. Intra-segment restarts where the speaker restarts within a single transcript segment.
    3. Contiguous subphrase and n-gram overlap between consecutive takes.
    """
    import difflib

    cuts = []
    n = len(segments)

    # 1. Intra-segment repetition detection
    for seg in segments:
        raw_words = seg.text.split()
        clean_words = [re.sub(r"[^\w]", "", w).lower() for w in raw_words if re.sub(r"[^\w]", "", w)]
        nw = len(clean_words)
        if nw < 4:
            continue

        found_intra = False
        for plen in range(min(5, nw // 2), 1, -1):
            if found_intra:
                break
            for i in range(nw - plen * 2 + 1):
                p1 = clean_words[i:i + plen]

                # Ensure p1 contains at least one non-stopword or plen >= 3
                if plen == 2 and all(w in COMMON_STOPWORDS for w in p1):
                    continue

                # Look ahead within next 4 words (typical connector length: "then again", "wait", etc.)
                for j in range(i + plen, min(i + plen + 5, nw - plen + 1)):
                    p2 = clean_words[j:j + plen]
                    if p1 == p2:
                        # Check for sentence-ending punctuation between i and j in raw words
                        between_raw = " ".join(raw_words[i:j])
                        if any(term in between_raw for term in [".", "!", "?", ";"]):
                            # Crossed a sentence boundary — natural topic continuation, not a restart!
                            continue

                        # Found genuine repetition inside a single segment!
                        if seg.words and len(seg.words) == nw:
                            c_start = seg.words[i].start
                            c_end = seg.words[j - 1].end
                        else:
                            c_start = seg.start + (i / nw) * (seg.end - seg.start)
                            c_end = seg.start + (j / nw) * (seg.end - seg.start)

                        cut_text = " ".join(raw_words[i:j])
                        cuts.append(CutProposal(
                            start=c_start,
                            end=c_end,
                            reason=CutReason.REPEATED_TAKE,
                            explanation=f"Intra-segment repetition: \"{cut_text}\" restarted as \"{' '.join(p2)}\"",
                            text=cut_text,
                            confidence=0.92,
                        ))
                        found_intra = True
                        break

    # 2. Inter-segment repetition detection (look ahead up to 2 segments)
    for i in range(n - 1):
        s1 = segments[i]
        raw_w1 = s1.text.split()
        words1 = [re.sub(r"[^\w]", "", w).lower() for w in raw_w1 if re.sub(r"[^\w]", "", w)]
        if not words1:
            continue

        has_terminal = s1.text.strip().endswith((".", "!", "?"))
        len1 = len(words1)

        for j in range(i + 1, min(i + 3, n)):
            s2 = segments[j]
            words2 = [re.sub(r"[^\w]", "", w).lower() for w in s2.text.split() if re.sub(r"[^\w]", "", w)]
            if not words2:
                continue

            len2 = len(words2)
            is_match = False
            match_len = 0

            # Find longest common contiguous word sequence between s1 and s2
            m = difflib.SequenceMatcher(None, words1, words2).find_longest_match(0, len1, 0, len2)

            # Match must start near the beginning of s2 (offset <= 3, allowing lead-ins like "then again", "so")
            if m.size > 0 and m.b <= 3:
                matched_words = words1[m.a:m.a + m.size]
                has_substantive = any(w not in COMMON_STOPWORDS for w in matched_words)

                # Short take: >= 2 words, covers >= 45% of s1, has substantive word, not a finished sentence
                if len1 <= 4 and m.size >= 2 and (m.size / len1 >= 0.45) and has_substantive and not has_terminal:
                    is_match = True
                    match_len = m.size
                # Medium/long take: >= 4 words or >= 35% of s1 with substantive content
                elif len1 > 4 and (m.size >= 4 or (m.size >= 3 and m.size / len1 >= 0.35)) and has_substantive:
                    is_match = True
                    match_len = m.size

            # Fuzzy sequence match if significant take overlap
            if not is_match and not has_terminal:
                clean_t1 = " ".join(words1)
                clean_t2 = " ".join(words2[:len1 + 4])
                ratio = difflib.SequenceMatcher(None, clean_t1, clean_t2).ratio()
                if ratio >= 0.65:
                    is_match = True
                    match_len = len1

            if is_match:
                cuts.append(CutProposal(
                    start=s1.start,
                    end=s1.end,
                    reason=CutReason.REPEATED_TAKE,
                    explanation=f"Repeated take / restarted in take [{j}]: \"{s2.text[:45]}...\"",
                    text=s1.text,
                    confidence=0.95,
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

    prompt = f"""You are a master rough-cut video editor. Your sole mission is to remove FAILED TAKES, RESTARTS, and OUTTAKES while strictly PRESERVING all intended spoken content.
You are NOT a summary engine or blog editor. You MUST NOT cut content just because it sounds informal, casual, repetitive in theme, or because another sentence explained it better.

RAW TRANSCRIPT (Numbered lines with segment indices [0], [1], ... and timecodes):
{transcript_text}

CRITICAL EDITING PRINCIPLES:
1. MULTI-TAKE RESTARTS & FALSE STARTS (CRITICAL):
   - Whenever the speaker attempts to say a line or sentence, stumbles or retries it (e.g. Take 1: "I made this...", Take 2: "Then again I made this xyz..."), CUT THE EARLIER FAILED ATTEMPT ([action: 'cut']).
   - Notice that speakers frequently start their re-take with connector words like "then again", "so", "actually", "wait let me say", "I mean". Cut the earlier take!
   - KEEP ONLY THE FINAL, MOST ARTICULATE, COMPLETE TAKE ([action: 'keep']).

2. STRICT CONTENT PRESERVATION (DO NOT CENSOR OR SUMMARIZE):
   - DO NOT remove sentences because they seem "redundant in meaning" or "don't make sense to you". Real creators speak casually, tell anecdotes, and repeat words for emphasis.
   - If the speaker articulated a thought cleanly and did not restart it, YOU MUST KEEP IT.
   - When in doubt, ALWAYS KEEP the segment. Only cut when there is an unmistakable stumble or retake.

3. OUTTAKES & META-TALK:
   - Cut any off-script meta-commentary: "Wait", "Let me start over", "Hold on", "Scratch that", "Sorry", "Take two", "Can I say that again", coughing, or clearing throat.

4. ELIMINATE AWKWARD 1-2 SECOND ISLANDS:
   - Do not leave tiny 1-2 second fragments stranded between two cuts or silences. If an isolated word or hesitation sits between cuts, mark it for cutting too.

OUTPUT FORMAT:
Respond ONLY with a JSON object containing a "cuts" array. Every cut decision must specify segment indices, action ('cut' or 'keep'), reason ('repeated_take', 'false_start', 'stumble'), and explanation.

JSON Schema:
{{
  "cuts": [
    {{"action": "cut", "segments": [0], "reason": "repeated_take", "explanation": "Failed take, restarted cleanly in segment [1]", "confidence": 0.98}},
    {{"action": "keep", "segments": [1], "reason": "repeated_take", "explanation": "Clean complete delivery of sentence", "confidence": 0.98}},
    {{"action": "cut", "segments": [4], "reason": "stumble", "explanation": "Meta-commentary ('Wait let me redo that')", "confidence": 0.99}}
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
        duration = end - start
        text = " ".join(s.text for s in cut_segments)

        reason_str = item.get("reason", "false_start")
        try:
            reason = CutReason(reason_str)
        except ValueError:
            reason = CutReason.FALSE_START

        # Safety Guard: If an LLM flags a long segment (> 6s or > 15 words) as stumble or filler,
        # never discard the entire multi-sentence explanation if an algorithmic cut already pinpointed
        # the exact sub-phrase stumble!
        if duration > 6.0 and reason in (CutReason.STUMBLE, CutReason.FILLER_WORDS):
            has_sub_cut = any(
                c.start >= start - 0.5 and c.end <= end + 0.5
                for c in all_cuts
            )
            if has_sub_cut:
                # Keep surgical cut already found; preserve the rest of the good speech
                continue

        all_cuts.append(CutProposal(
            start=start,
            end=end,
            reason=reason,
            explanation=item.get("explanation", ""),
            text=text,
            confidence=float(item.get("confidence", 0.7)),
        ))

    # Sort cuts by start time and merge overlapping / micro-gaps
    all_cuts.sort(key=lambda c: (c.start, c.end))
    merged_cuts = _merge_overlapping_cuts(all_cuts, transcription=transcription, bridge_max_gap=2.5, bridge_max_words=5)

    # Build keep regions (strictly the gaps between merged cuts)
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


def _merge_overlapping_cuts(
    cuts: list[CutProposal],
    transcription: TranscriptionResult | None = None,
    bridge_max_gap: float = 2.5,
    bridge_max_words: int = 5,
) -> list[CutProposal]:
    """
    Merge overlapping cut regions and iteratively bridge micro-gaps.
    Eliminates awkward 1-2 second island clips between cuts:
    - Cascades iteratively until all close cuts are unified.
    - Sub-second micro-gaps (<= 1.2s) with transcript are bridged (no video jump-cut blips).
    - Gaps <= bridge_max_gap (2.5s) containing dead air or <= bridge_max_words are bridged.
    """
    if not cuts:
        return []

    merged = sorted(cuts, key=lambda c: (c.start, c.end))

    # Iterative cascading merge until convergence
    changed = True
    while changed:
        changed = False
        new_merged = [merged[0]]

        for cut in merged[1:]:
            last = new_merged[-1]
            gap = cut.start - last.end

            should_merge = False
            # 1. Overlapping or sub-second micro-gap (<= 0.8s): unconditionally bridge!
            if gap <= 0.8:
                should_merge = True
            # 2. Short gap (<= bridge_max_gap): bridge if transcription shows few words or dead air
            elif transcription is not None and gap <= bridge_max_gap:
                text_between = _get_text_in_range(transcription.segments, last.end, cut.start).strip()
                words_between = text_between.split()
                if len(words_between) <= bridge_max_words or gap <= 1.8:
                    should_merge = True

            if should_merge:
                new_merged[-1] = CutProposal(
                    start=last.start,
                    end=max(last.end, cut.end),
                    reason=last.reason if last.confidence >= cut.confidence else cut.reason,
                    explanation=f"{last.explanation}; {cut.explanation}",
                    text=f"{last.text} | {cut.text}",
                    confidence=max(last.confidence, cut.confidence),
                )
                changed = True
            else:
                new_merged.append(cut)

        merged = new_merged

    return merged


def _build_keep_regions(
    cuts: list[CutProposal],
    transcription: TranscriptionResult,
) -> list[KeepRegion]:
    """
    Build keep regions strictly from the gaps between the final merged cuts.
    Guarantees that visual keep slices and timeline cuts are 100% complementary.
    """
    keeps = []
    current_start = 0.0
    total_duration = transcription.duration

    for cut in cuts:
        gap_dur = cut.start - current_start
        if gap_dur > 0.05:
            text = _get_text_in_range(transcription.segments, current_start, cut.start).strip()
            keeps.append(KeepRegion(
                start=current_start,
                end=cut.start,
                text=text,
            ))
        current_start = cut.end

    # Final keep region after last cut
    if current_start < total_duration - 0.05:
        text = _get_text_in_range(transcription.segments, current_start, total_duration).strip()
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
