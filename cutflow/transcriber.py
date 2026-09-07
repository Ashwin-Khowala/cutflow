"""
Transcription module — multi-backend speech-to-text (Groq Whisper or Moonshine)
and ffmpeg for silence detection.

STT backends (in order of accuracy):
  groq_whisper  — Groq API whisper-large-v3-turbo or whisper-large-v3
                  (highest accuracy, requires API key, ~2s for 30min file)
  moonshine     — Usable (quantized medium-streaming, on-device, offline)
"""

import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field, asdict
from pathlib import Path

# Fix Windows console encoding for emoji and unicode output
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


@dataclass
class Word:
    """A single transcribed word with timing."""
    text: str
    start: float  # seconds
    end: float    # seconds


@dataclass
class Segment:
    """A contiguous segment of speech."""
    text: str
    start: float
    end: float
    words: list[Word] = field(default_factory=list)


@dataclass
class SilenceRegion:
    """A detected silence region."""
    start: float
    end: float
    duration: float


@dataclass
class TranscriptionResult:
    """Full transcription output with segments, words, and silence map."""
    segments: list[Segment]
    silences: list[SilenceRegion]
    duration: float  # total audio duration in seconds
    audio_path: str

    def to_dict(self) -> dict:
        return {
            "duration": self.duration,
            "audio_path": self.audio_path,
            "segments": [
                {
                    "text": s.text,
                    "start": round(s.start, 3),
                    "end": round(s.end, 3),
                    "words": [
                        {"text": w.text, "start": round(w.start, 3), "end": round(w.end, 3)}
                        for w in s.words
                    ],
                }
                for s in self.segments
            ],
            "silences": [
                {"start": round(s.start, 3), "end": round(s.end, 3), "duration": round(s.duration, 3)}
                for s in self.silences
            ],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


def extract_audio(video_path: str, output_dir: str | None = None) -> str:
    """
    Extract audio from video as 16kHz mono WAV (optimal for Moonshine and Whisper).
    Returns path to the extracted WAV file.
    """
    video_path = Path(video_path).resolve()
    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        audio_path = str(Path(output_dir) / f"{video_path.stem}_audio.wav")
    else:
        audio_path = str(video_path.parent / f"{video_path.stem}_audio.wav")

    # If the input is already the destination audio file, no extraction needed
    if Path(audio_path).resolve() == video_path:
        return str(video_path)

    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-ar", "16000",   # 16kHz sample rate
        "-ac", "1",        # mono
        "-c:a", "pcm_s16le",
        audio_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg audio extraction failed:\n{result.stderr}")

    return audio_path


def get_audio_duration(audio_path: str) -> float:
    """Get duration of an audio/video file in seconds using ffprobe."""
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-show_entries", "format=duration",
        "-of", "csv=p=0",
        audio_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed:\n{result.stderr}")
    return float(result.stdout.strip())


def detect_silence(
    audio_path: str,
    noise_threshold: str = "-35dB",
    min_duration: float = 0.8,
) -> list[SilenceRegion]:
    """
    Detect silent regions in audio using ffmpeg's silencedetect filter.
    
    Args:
        audio_path: Path to audio file
        noise_threshold: Volume below which is considered silence (default -35dB)
        min_duration: Minimum silence duration in seconds (default 0.8s)
    
    Returns:
        List of SilenceRegion objects
    """
    cmd = [
        "ffmpeg",
        "-i", audio_path,
        "-af", f"silencedetect=n={noise_threshold}:d={min_duration}",
        "-f", "null",
        "-",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    stderr = result.stderr

    # Parse silence_start and silence_end from ffmpeg output
    silences = []
    starts = re.findall(r"silence_start: ([\d.]+)", stderr)
    ends = re.findall(r"silence_end: ([\d.]+) \| silence_duration: ([\d.]+)", stderr)

    for i, start_str in enumerate(starts):
        start = float(start_str)
        if i < len(ends):
            end = float(ends[i][0])
            duration = float(ends[i][1])
        else:
            # Silence extends to end of file
            end = get_audio_duration(audio_path)
            duration = end - start

        silences.append(SilenceRegion(start=start, end=end, duration=duration))

    return silences


# ─── Groq Whisper transcription ───────────────────────────────────────────────

GROQ_WHISPER_CHUNK_BYTES = 24 * 1024 * 1024   # 24 MB — below Groq's 25MB limit
_GROQ_WHISPER_DEFAULT_MODEL = "whisper-large-v3-turbo"  # fast + highly accurate
_GROQ_WHISPER_PRECISE_MODEL = "whisper-large-v3"         # maximum accuracy


def _transcribe_via_groq_whisper(
    audio_path: str,
    api_key: str,
    model: str = _GROQ_WHISPER_DEFAULT_MODEL,
    progress_callback=None,
) -> list[Segment]:
    """
    Transcribe audio using Groq's cloud Whisper API (whisper-large-v3-turbo by default).
    Automatically splits files larger than Groq's 25 MB limit into sub-chunks.
    Returns word-level Segment objects.
    """
    from groq import Groq

    if progress_callback:
        progress_callback(10.0, f"Connecting to Groq Whisper ({model})...")

    client = Groq(api_key=api_key)
    audio_path = str(Path(audio_path).resolve())
    file_size = Path(audio_path).stat().st_size

    if file_size <= GROQ_WHISPER_CHUNK_BYTES:
        # Single file — send directly
        if progress_callback:
            progress_callback(25.0, "Transcribing with Groq Whisper (single pass)...")
        segments = _groq_transcribe_file(client, audio_path, model, offset_sec=0.0)
        if progress_callback:
            progress_callback(85.0, "Groq Whisper transcription complete.")
        return segments

    # File is too large — split at silence boundaries using ffmpeg segment
    duration = get_audio_duration(audio_path)
    # Choose chunk duration so each chunk stays well below 25 MB
    # 16kHz mono PCM = 32 kB/s → 24 MB ≈ 750 s per chunk
    target_chunk_sec = 600  # 10 minutes
    num_chunks = max(1, int(duration / target_chunk_sec) + 1)

    if progress_callback:
        progress_callback(15.0, f"Splitting audio into {num_chunks} chunks for Groq Whisper...")

    import tempfile, shutil
    tmp_dir = tempfile.mkdtemp(prefix="cutflow_groq_")
    try:
        chunk_pattern = str(Path(tmp_dir) / "chunk_%03d.wav")
        subprocess.run([
            "ffmpeg", "-y", "-i", audio_path,
            "-f", "segment",
            "-segment_time", str(target_chunk_sec),
            "-c", "copy",
            chunk_pattern,
        ], capture_output=True, check=True)

        chunk_files = sorted(Path(tmp_dir).glob("chunk_*.wav"))
        all_segments: list[Segment] = []
        offset_sec = 0.0

        for i, chunk_path in enumerate(chunk_files):
            if progress_callback:
                pct = 15.0 + ((i + 1) / len(chunk_files)) * 70.0
                progress_callback(
                    round(pct, 1),
                    f"Transcribing chunk {i + 1}/{len(chunk_files)} with Groq Whisper...",
                )
            chunk_segs = _groq_transcribe_file(client, str(chunk_path), model, offset_sec=offset_sec)
            all_segments.extend(chunk_segs)
            offset_sec += get_audio_duration(str(chunk_path))

        if progress_callback:
            progress_callback(85.0, "Groq Whisper chunked transcription complete.")
        return all_segments
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _groq_transcribe_file(
    client,
    wav_path: str,
    model: str = _GROQ_WHISPER_DEFAULT_MODEL,
    offset_sec: float = 0.0,
) -> list[Segment]:
    """Send a single WAV file to Groq Whisper and parse the response into Segments."""
    with open(wav_path, "rb") as f:
        resp = client.audio.transcriptions.create(
            model=model,
            file=(Path(wav_path).name, f, "audio/wav"),
            response_format="verbose_json",
            timestamp_granularities=["segment", "word"],
            temperature=0.0,
        )

    # Extract all words
    raw_words = getattr(resp, "words", None) or (resp.get("words", []) if isinstance(resp, dict) else [])
    all_words: list[Word] = []
    for w in (raw_words or []):
        w_text = w.get("word", "") if isinstance(w, dict) else getattr(w, "word", "")
        w_start = float(w.get("start", 0.0) if isinstance(w, dict) else getattr(w, "start", 0.0)) + offset_sec
        w_end = float(w.get("end", 0.0) if isinstance(w, dict) else getattr(w, "end", 0.0)) + offset_sec
        if w_text:
            all_words.append(Word(text=str(w_text).strip(), start=w_start, end=w_end))

    # Extract segments
    raw_segs = getattr(resp, "segments", None) or (resp.get("segments", []) if isinstance(resp, dict) else [])
    segments: list[Segment] = []

    for seg in (raw_segs or []):
        text = str(seg.get("text", "") if isinstance(seg, dict) else getattr(seg, "text", "")).strip()
        if not text:
            continue
        seg_start = float(seg.get("start", 0.0) if isinstance(seg, dict) else getattr(seg, "start", 0.0)) + offset_sec
        seg_end = float(seg.get("end", 0.0) if isinstance(seg, dict) else getattr(seg, "end", 0.0)) + offset_sec

        # Assign words that fall within this segment
        seg_words = [w for w in all_words if (seg_start - 0.1) <= w.start <= (seg_end + 0.1)]
        segments.append(Segment(text=text, start=seg_start, end=seg_end, words=seg_words))

    # Fallback if no segments returned but full text exists
    if not segments:
        full_text = getattr(resp, "text", None) or (resp.get("text", "") if isinstance(resp, dict) else "")
        if full_text:
            duration = get_audio_duration(wav_path)
            segments.append(Segment(text=str(full_text).strip(), start=offset_sec, end=offset_sec + duration, words=all_words))

    return segments


# ─── Moonshine transcription (local, offline fallback) ────────────────────────

def _transcribe_via_moonshine(
    audio_path: str,
    chunk_duration: float = 30.0,
    progress_callback=None,
) -> list[Segment]:
    """
    Transcribe using Moonshine Python API (medium-streaming-en model).
    Enables MOONSHINE_FLAG_SPELLING_MODE for improved word spelling accuracy.
    Chunks long audio for stable memory usage.
    """
    import moonshine_voice

    if progress_callback:
        progress_callback(5.0, "Loading Moonshine STT model (offline mode)...")

    model_path, model_arch = moonshine_voice.get_model_for_language(
        "en", include_word_timestamps=True
    )
    transcriber = moonshine_voice.Transcriber(model_path=model_path, model_arch=model_arch)

    # Enable spelling mode for improved lexical accuracy
    spelling_flag = moonshine_voice.Transcriber.MOONSHINE_FLAG_SPELLING_MODE

    if progress_callback:
        progress_callback(15.0, "Reading audio stream...")
    audio_data, sr = moonshine_voice.load_wav_file(audio_path)
    total_samples = len(audio_data)

    if total_samples == 0:
        return []

    chunk_samples = int(chunk_duration * sr)

    if total_samples <= chunk_samples * 1.2:
        if progress_callback:
            progress_callback(30.0, "Transcribing speech with Moonshine (offline)...")
        transcript = transcriber.transcribe_without_streaming(
            audio_data, sample_rate=sr, flags=spelling_flag
        )
        return _extract_segments_from_transcript(transcript, offset_sec=0.0)

    num_chunks = max(1, (total_samples + chunk_samples - 1) // chunk_samples)
    all_segments: list[Segment] = []

    for chunk_idx in range(num_chunks):
        start_sample = chunk_idx * chunk_samples
        end_sample = min(total_samples, (chunk_idx + 1) * chunk_samples)
        chunk_audio = audio_data[start_sample:end_sample]
        offset_sec = start_sample / sr

        if progress_callback:
            percent = 15.0 + ((chunk_idx + 1) / num_chunks) * 70.0
            progress_callback(
                round(percent, 1),
                f"Moonshine chunk {chunk_idx + 1}/{num_chunks} ({int(offset_sec)}s — {int(end_sample / sr)}s)...",
            )

        transcript = transcriber.transcribe_without_streaming(
            chunk_audio, sample_rate=sr, flags=spelling_flag
        )
        chunk_segs = _extract_segments_from_transcript(transcript, offset_sec=offset_sec)
        all_segments.extend(chunk_segs)

    return all_segments


# Keep old name as thin alias so existing callers don't break
def transcribe_audio(
    audio_path: str,
    chunk_duration: float = 30.0,
    progress_callback=None,
    stt_backend: str = "moonshine",
    groq_api_key: str | None = None,
) -> list[Segment]:
    """
    Transcribe audio using the selected STT backend.

    stt_backend options:
      'groq_whisper'  — Groq cloud Whisper (requires groq_api_key; best accuracy)
      'moonshine'     — On-device Moonshine medium-streaming (offline fallback)
    """
    audio_path = str(Path(audio_path).resolve())

    if stt_backend == "groq_whisper" and groq_api_key:
        try:
            return _transcribe_via_groq_whisper(
                audio_path, api_key=groq_api_key, progress_callback=progress_callback
            )
        except Exception as e:
            print(f"⚠️  Groq Whisper failed ({e}), falling back to Moonshine...")

    # Local Moonshine fallback
    try:
        return _transcribe_via_moonshine(
            audio_path, chunk_duration=chunk_duration, progress_callback=progress_callback
        )
    except Exception as e:
        print(f"ℹ️  Moonshine Python API error ({e}), trying CLI...")

    if progress_callback:
        progress_callback(50.0, "Transcribing with Moonshine CLI...")
    return _transcribe_via_cli(audio_path)


def _extract_segments_from_transcript(transcript, offset_sec: float = 0.0) -> list[Segment]:
    """Helper to convert Moonshine Transcript object into Segment and Word list with timestamp offset."""
    segments = []
    for line in getattr(transcript, "lines", []):
        line_start = float(getattr(line, "start_time", 0.0)) + offset_sec
        dur = float(getattr(line, "duration", 0.0))
        line_end = line_start + dur
        text = str(getattr(line, "text", "")).strip()

        words_list = []
        for w in (getattr(line, "words", None) or []):
            if isinstance(w, (list, tuple)) and len(w) >= 2:
                w_start = float(w[1]) + offset_sec
                w_end = float(w[1] + w[2] if len(w) > 2 else 0.0) + offset_sec
                words_list.append(Word(text=str(w[0]), start=w_start, end=w_end))
            else:
                w_text = getattr(w, "word", getattr(w, "text", ""))
                w_start = float(getattr(w, "start", line_start)) + offset_sec
                w_end = float(getattr(w, "end", w_start)) + offset_sec
                words_list.append(Word(text=w_text, start=w_start, end=w_end))

        if text:
            segments.append(Segment(text=text, start=line_start, end=line_end, words=words_list))

    return segments


def _transcribe_via_cli(audio_path: str) -> list[Segment]:
    """Transcribe using moonshine-voice CLI tool."""
    # Correct CLI syntax: moonshine-voice transcribe --wav-path <file> --word-timestamps
    cmd = ["moonshine-voice", "transcribe", "--wav-path", audio_path, "--word-timestamps"]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        # Fallback: try without word timestamps
        cmd = ["moonshine-voice", "transcribe", "--wav-path", audio_path]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(
                f"moonshine-voice CLI failed:\n{result.stderr}\n"
                "Make sure moonshine-voice is installed: pip install moonshine-voice"
            )

    return _parse_cli_output(result.stdout)


def _parse_moonshine_result(result) -> list[Segment]:
    """Parse result from Moonshine Python API into our Segment format."""
    segments = []

    # Handle different result formats
    if isinstance(result, dict):
        raw_segments = result.get("segments", result.get("results", []))
    elif isinstance(result, list):
        raw_segments = result
    elif isinstance(result, str):
        # Plain text result — create a single segment
        return [Segment(text=result.strip(), start=0.0, end=0.0, words=[])]
    else:
        # Try to iterate
        raw_segments = list(result)

    for seg in raw_segments:
        if isinstance(seg, dict):
            words = []
            for w in seg.get("words", []):
                words.append(Word(
                    text=w.get("word", w.get("text", "")),
                    start=float(w.get("start", 0)),
                    end=float(w.get("end", 0)),
                ))
            segments.append(Segment(
                text=seg.get("text", ""),
                start=float(seg.get("start", 0)),
                end=float(seg.get("end", 0)),
                words=words,
            ))
        elif hasattr(seg, "text"):
            words = []
            if hasattr(seg, "words"):
                for w in seg.words:
                    words.append(Word(
                        text=getattr(w, "word", getattr(w, "text", "")),
                        start=float(getattr(w, "start", 0)),
                        end=float(getattr(w, "end", 0)),
                    ))
            segments.append(Segment(
                text=seg.text,
                start=float(getattr(seg, "start", 0)),
                end=float(getattr(seg, "end", 0)),
                words=words,
            ))

    return segments


def _parse_cli_output(output: str) -> list[Segment]:
    """Parse moonshine-voice CLI text output into segments."""
    segments = []

    # Try parsing as JSON first
    try:
        data = json.loads(output)
        return _parse_moonshine_result(data)
    except (json.JSONDecodeError, ValueError):
        pass

    # Parse timestamped text lines: [00:00.000 --> 00:05.230] Hello world
    timestamp_pattern = re.compile(
        r"\[(\d+:\d+\.\d+)\s*-->\s*(\d+:\d+\.\d+)\]\s*(.*)"
    )

    for line in output.strip().split("\n"):
        line = line.strip()
        if not line:
            continue

        match = timestamp_pattern.match(line)
        if match:
            start = _parse_timestamp(match.group(1))
            end = _parse_timestamp(match.group(2))
            text = match.group(3).strip()
            segments.append(Segment(text=text, start=start, end=end, words=[]))
        elif line and not line.startswith("#"):
            # Plain text line — append as segment without timestamps
            segments.append(Segment(text=line, start=0.0, end=0.0, words=[]))

    return segments


def _parse_timestamp(ts: str) -> float:
    """Parse timestamp like '00:05.230' or '00:01:05.230' into seconds."""
    parts = ts.split(":")
    if len(parts) == 2:
        minutes, seconds = parts
        return float(minutes) * 60 + float(seconds)
    elif len(parts) == 3:
        hours, minutes, seconds = parts
        return float(hours) * 3600 + float(minutes) * 60 + float(seconds)
    return float(ts)


def run_full_transcription(
    video_path: str,
    output_dir: str | None = None,
    silence_threshold: str = "-35dB",
    silence_min_duration: float = 0.8,
    progress_callback=None,
    stt_backend: str = "moonshine",
    groq_api_key: str | None = None,
) -> TranscriptionResult:
    """
    Run the complete transcription pipeline:
    1. Extract audio from video
    2. Transcribe using the selected STT backend:
       - 'groq_whisper' (default when key available): Groq cloud Whisper large-v3-turbo
       - 'moonshine': On-device Moonshine medium-streaming (offline)
    3. Detect silence regions with ffmpeg

    Returns a TranscriptionResult with everything combined.
    """
    if progress_callback:
        progress_callback(5.0, "Extracting 16kHz audio from video...")
    print(f"📎 Extracting audio from: {video_path}")
    audio_path = extract_audio(video_path, output_dir)

    backend_label = "Groq Whisper" if (stt_backend == "groq_whisper" and groq_api_key) else "Moonshine (offline)"
    print(f"🎙️  Transcribing with {backend_label}...")
    segments = transcribe_audio(
        audio_path,
        chunk_duration=30.0,
        progress_callback=progress_callback,
        stt_backend=stt_backend,
        groq_api_key=groq_api_key,
    )

    if progress_callback:
        progress_callback(85.0, "Detecting silence and dead air regions...")
    print(f"🔇 Detecting silence regions...")
    silences = detect_silence(audio_path, silence_threshold, silence_min_duration)

    duration = get_audio_duration(audio_path)

    result = TranscriptionResult(
        segments=segments,
        silences=silences,
        duration=duration,
        audio_path=audio_path,
    )

    if progress_callback:
        progress_callback(100.0, "Transcription and silence mapping complete.")

    print(f"✅ Transcription complete: {len(segments)} segments, {len(silences)} silence regions, {duration:.1f}s total")
    return result
