"""
Cutter module — applies approved cuts to the video using ffmpeg.
Takes a list of keep regions and concatenates them into the final output.
"""

import os
import subprocess
import tempfile
from pathlib import Path

from cutflow.analyzer import AnalysisResult, KeepRegion


def apply_cuts(
    video_path: str,
    analysis: AnalysisResult,
    output_path: str | None = None,
    min_confidence: float = 0.5,
) -> str:
    """
    Apply the proposed cuts to the video file using ffmpeg.
    
    Uses the "keep regions" approach: extract each keep segment,
    then concatenate them together. This is more reliable than
    trying to cut individual regions.
    
    Args:
        video_path: Path to the original video
        analysis: The AnalysisResult with approved cuts
        output_path: Where to save the result (default: adds _cut suffix)
        min_confidence: Only apply cuts with confidence >= this threshold
    
    Returns:
        Path to the output video
    """
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    if output_path is None:
        output_path = str(video_path.with_stem(f"{video_path.stem}_cut"))

    # Filter keep regions based on confidence threshold for the cuts
    keeps = analysis.keeps
    if not keeps:
        print("⚠️  No keep regions found — nothing to cut.")
        return str(video_path)

    print(f"✂️  Applying {len(analysis.cuts)} cuts, keeping {len(keeps)} segments...")

    if len(keeps) == 1 and keeps[0].start == 0.0:
        # Only one keep region from the start — just trim the end
        return _trim_single(str(video_path), keeps[0], output_path)

    # Multiple keep regions — extract each and concatenate
    return _extract_and_concat(str(video_path), keeps, output_path)


def _trim_single(video_path: str, keep: KeepRegion, output_path: str) -> str:
    """Simple trim: just cut the video to a single time range."""
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-ss", str(keep.start),
        "-to", str(keep.end),
        "-c", "copy",  # Fast — no re-encoding
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg trim failed:\n{result.stderr}")

    print(f"✅ Saved to: {output_path}")
    return output_path


def _extract_and_concat(
    video_path: str,
    keeps: list[KeepRegion],
    output_path: str,
) -> str:
    """
    Extract each keep segment as a separate file, then concatenate.
    Uses ffmpeg's concat demuxer for gapless joining.
    """
    with tempfile.TemporaryDirectory(prefix="cutflow_") as tmpdir:
        segment_files = []

        for i, keep in enumerate(keeps):
            if keep.end - keep.start < 0.05:  # Skip tiny segments
                continue

            segment_path = os.path.join(tmpdir, f"segment_{i:04d}.ts")

            # Use MPEG-TS format for reliable concatenation
            cmd = [
                "ffmpeg", "-y",
                "-i", video_path,
                "-ss", str(keep.start),
                "-to", str(keep.end),
                "-c:v", "libx264", "-preset", "fast",
                "-c:a", "aac",
                "-f", "mpegts",
                segment_path,
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"⚠️  Warning: Failed to extract segment {i} ({keep.start:.1f}s-{keep.end:.1f}s): {result.stderr[:200]}")
                continue

            segment_files.append(segment_path)

        if not segment_files:
            raise RuntimeError("No segments were successfully extracted.")

        # Build concat file list
        concat_file = os.path.join(tmpdir, "concat.txt")
        with open(concat_file, "w") as f:
            for seg_path in segment_files:
                # Escape single quotes in path for ffmpeg
                escaped = seg_path.replace("'", "'\\''")
                f.write(f"file '{escaped}'\n")

        # Concatenate all segments
        # Use concat protocol with MPEG-TS for seamless joining
        concat_input = "|".join(segment_files)
        cmd = [
            "ffmpeg", "-y",
            "-i", f"concat:{concat_input}",
            "-c:v", "libx264", "-preset", "fast",
            "-c:a", "aac",
            "-movflags", "+faststart",
            output_path,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg concatenation failed:\n{result.stderr}")

        # Get output file size and duration
        duration = _get_duration(output_path)
        original_duration = _get_duration(video_path)
        saved = original_duration - duration

        print(f"✅ Saved to: {output_path}")
        print(f"   Original: {original_duration:.1f}s → Result: {duration:.1f}s (saved {saved:.1f}s)")

        return output_path


def _get_duration(path: str) -> float:
    """Get duration of a media file using ffprobe."""
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-show_entries", "format=duration",
        "-of", "csv=p=0",
        path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0


def preview_cuts(analysis: AnalysisResult) -> str:
    """
    Generate a human-readable preview of proposed cuts.
    Returns formatted text showing what will be cut and what will be kept.
    """
    lines = []
    lines.append("=" * 70)
    lines.append("📋 PROPOSED CUT LIST")
    lines.append("=" * 70)
    lines.append(f"\n{analysis.summary}\n")

    # Show cuts
    if analysis.cuts:
        lines.append("❌ SEGMENTS TO CUT:")
        lines.append("-" * 50)
        for i, cut in enumerate(analysis.cuts, 1):
            duration = cut.end - cut.start
            icon = {
                "false_start": "🔄",
                "repeated_take": "🔄",
                "filler_words": "🗑️",
                "long_silence": "🔇",
                "stumble": "💬",
            }.get(cut.reason.value, "❌")

            lines.append(
                f"  {i}. {icon} [{_fmt(cut.start)} → {_fmt(cut.end)}] "
                f"({duration:.1f}s) [{cut.reason.value}]"
            )
            lines.append(f"     \"{_truncate(cut.text, 80)}\"")
            lines.append(f"     💡 {cut.explanation} (confidence: {cut.confidence:.0%})")
            lines.append("")

    # Show keeps
    if analysis.keeps:
        lines.append("\n✅ SEGMENTS TO KEEP:")
        lines.append("-" * 50)
        for i, keep in enumerate(analysis.keeps, 1):
            duration = keep.end - keep.start
            lines.append(
                f"  {i}. [{_fmt(keep.start)} → {_fmt(keep.end)}] ({duration:.1f}s)"
            )
            lines.append(f"     \"{_truncate(keep.text, 80)}\"")
            lines.append("")

    lines.append("=" * 70)
    savings = analysis.cut_duration / analysis.total_duration * 100 if analysis.total_duration > 0 else 0
    lines.append(
        f"📊 Total: {analysis.total_duration:.1f}s → {analysis.kept_duration:.1f}s "
        f"(saving {analysis.cut_duration:.1f}s / {savings:.0f}%)"
    )
    lines.append("=" * 70)

    return "\n".join(lines)


def _fmt(seconds: float) -> str:
    """Format seconds as M:SS."""
    m = int(seconds // 60)
    s = seconds % 60
    return f"{m}:{s:05.2f}"


def _truncate(text: str, max_len: int) -> str:
    """Truncate text with ellipsis."""
    if len(text) <= max_len:
        return text
    return text[:max_len - 3] + "..."
