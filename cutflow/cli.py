"""
CutFlow CLI — the command-line interface for the video prep tool.

Usage:
    cutflow prep <video_file>              # Full pipeline: transcribe → analyze → propose cuts
    cutflow transcribe <video_file>        # Just transcribe (save transcript JSON)
    cutflow analyze <transcript_json>      # Analyze existing transcript
    cutflow cut <video_file> <cuts_json>   # Apply a saved cut list
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Fix Windows console encoding for emoji/unicode output
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def cmd_prep(args):
    """Full pipeline: transcribe → analyze → preview cuts → optionally apply."""
    from cutflow.transcriber import run_full_transcription
    from cutflow.analyzer import analyze_transcript
    from cutflow.cutter import preview_cuts, apply_cuts

    video_path = args.video
    if not os.path.exists(video_path):
        print(f"❌ File not found: {video_path}")
        sys.exit(1)

    output_dir = args.output_dir or str(Path(video_path).parent / "cutflow_output")
    os.makedirs(output_dir, exist_ok=True)

    # Step 1: Transcribe
    print("\n" + "=" * 60)
    print("📝 STEP 1: Transcription")
    print("=" * 60)
    transcription = run_full_transcription(
        video_path,
        output_dir=output_dir,
        silence_threshold=args.silence_threshold,
        silence_min_duration=args.silence_min_duration,
    )

    # Save transcript
    transcript_path = os.path.join(output_dir, "transcript.json")
    with open(transcript_path, "w", encoding="utf-8") as f:
        f.write(transcription.to_json())
    print(f"💾 Transcript saved: {transcript_path}")

    # Step 2: Analyze
    print("\n" + "=" * 60)
    print("🔍 STEP 2: Analysis")
    print("=" * 60)
    analysis = analyze_transcript(
        transcription,
        api_key=args.api_key,
        max_silence=args.max_silence,
    )

    # Save analysis
    analysis_path = os.path.join(output_dir, "analysis.json")
    with open(analysis_path, "w", encoding="utf-8") as f:
        f.write(analysis.to_json())
    print(f"💾 Analysis saved: {analysis_path}")

    # Step 3: Preview
    print("\n")
    preview = preview_cuts(analysis)
    print(preview)

    # Save preview
    preview_path = os.path.join(output_dir, "cut_preview.txt")
    with open(preview_path, "w", encoding="utf-8") as f:
        f.write(preview)

    if not analysis.cuts:
        print("\n✨ No cuts proposed — your recording looks clean!")
        return

    # Step 4: Ask for confirmation (unless --auto flag)
    if args.auto:
        print("\n🤖 Auto mode: applying cuts without confirmation...")
    else:
        print("\n" + "-" * 60)
        response = input("Apply these cuts? [y/N/e(dit)] ").strip().lower()
        if response == "e":
            print(f"\n📝 Edit the analysis file and re-run:")
            print(f"   cutflow cut \"{video_path}\" \"{analysis_path}\"")
            return
        elif response != "y":
            print("\n⏭️  Skipped. You can apply later with:")
            print(f"   cutflow cut \"{video_path}\" \"{analysis_path}\"")
            return

    # Step 5: Apply cuts
    print("\n" + "=" * 60)
    print("✂️  STEP 3: Applying Cuts")
    print("=" * 60)
    output_video = args.output or os.path.join(
        output_dir,
        f"{Path(video_path).stem}_cut{Path(video_path).suffix}"
    )
    apply_cuts(video_path, analysis, output_path=output_video)


def cmd_transcribe(args):
    """Just transcribe a video file."""
    from cutflow.transcriber import run_full_transcription

    video_path = args.video
    if not os.path.exists(video_path):
        print(f"❌ File not found: {video_path}")
        sys.exit(1)

    output_dir = args.output_dir or str(Path(video_path).parent)
    transcription = run_full_transcription(video_path, output_dir=output_dir)

    # Save or print
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(transcription.to_json())
        print(f"\n💾 Saved to: {args.output}")
    else:
        output_path = os.path.join(output_dir, f"{Path(video_path).stem}_transcript.json")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(transcription.to_json())
        print(f"\n💾 Saved to: {output_path}")


def cmd_analyze(args):
    """Analyze an existing transcript JSON."""
    from cutflow.transcriber import TranscriptionResult, Segment, SilenceRegion, Word
    from cutflow.analyzer import analyze_transcript
    from cutflow.cutter import preview_cuts

    transcript_path = args.transcript
    if not os.path.exists(transcript_path):
        print(f"❌ File not found: {transcript_path}")
        sys.exit(1)

    with open(transcript_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Reconstruct TranscriptionResult from JSON
    segments = []
    for s in data.get("segments", []):
        words = [Word(text=w["text"], start=w["start"], end=w["end"]) for w in s.get("words", [])]
        segments.append(Segment(text=s["text"], start=s["start"], end=s["end"], words=words))

    silences = [
        SilenceRegion(start=s["start"], end=s["end"], duration=s["duration"])
        for s in data.get("silences", [])
    ]

    transcription = TranscriptionResult(
        segments=segments,
        silences=silences,
        duration=data.get("duration", 0),
        audio_path=data.get("audio_path", ""),
    )

    analysis = analyze_transcript(transcription, api_key=args.api_key)

    # Show preview
    print("\n")
    preview = preview_cuts(analysis)
    print(preview)

    # Save
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(analysis.to_json())
        print(f"\n💾 Analysis saved to: {args.output}")


def cmd_cut(args):
    """Apply a saved analysis/cut list to a video."""
    from cutflow.analyzer import AnalysisResult, CutProposal, CutReason, KeepRegion
    from cutflow.cutter import apply_cuts, preview_cuts

    video_path = args.video
    analysis_path = args.analysis

    if not os.path.exists(video_path):
        print(f"❌ Video not found: {video_path}")
        sys.exit(1)
    if not os.path.exists(analysis_path):
        print(f"❌ Analysis file not found: {analysis_path}")
        sys.exit(1)

    with open(analysis_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Reconstruct AnalysisResult from JSON
    cuts = []
    for c in data.get("cuts", []):
        cuts.append(CutProposal(
            start=c["start"],
            end=c["end"],
            reason=CutReason(c["reason"]),
            explanation=c["explanation"],
            text=c["text"],
            confidence=c["confidence"],
        ))

    keeps = []
    for k in data.get("keeps", []):
        keeps.append(KeepRegion(
            start=k["start"],
            end=k["end"],
            text=k["text"],
        ))

    analysis = AnalysisResult(
        cuts=cuts,
        keeps=keeps,
        total_duration=data.get("total_duration", 0),
        kept_duration=data.get("kept_duration", 0),
        cut_duration=data.get("cut_duration", 0),
        summary=data.get("summary", ""),
    )

    output_path = args.output or str(
        Path(video_path).with_stem(f"{Path(video_path).stem}_cut")
    )

    apply_cuts(video_path, analysis, output_path=output_path)


def cmd_web(args):
    """Launch the CutFlow interactive web dashboard."""
    import uvicorn
    host = args.host
    port = args.port
    print("\n" + "=" * 60)
    print("🚀 CutFlow Studio Web Dashboard")
    print("=" * 60)
    print(f"👉 Open in your browser: http://{host}:{port}\n")
    uvicorn.run("cutflow.server:app", host=host, port=port, reload=args.reload)


def main():
    parser = argparse.ArgumentParser(
        prog="cutflow",
        description="🎬 CutFlow — AI-powered video prep tool. Removes false starts, filler words, and dead air.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- web command ---
    web_parser = subparsers.add_parser(
        "web",
        help="Launch the interactive Web Dashboard",
    )
    web_parser.add_argument("--host", default="127.0.0.1", help="Host address (default: 127.0.0.1)")
    web_parser.add_argument("--port", type=int, default=8000, help="Port (default: 8000)")
    web_parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")

    # --- prep command ---
    prep_parser = subparsers.add_parser(
        "prep",
        help="Full pipeline: transcribe → analyze → propose cuts → apply",
    )
    prep_parser.add_argument("video", help="Path to video file")
    prep_parser.add_argument("-o", "--output", help="Output video path")
    prep_parser.add_argument("--output-dir", help="Directory for intermediate files")
    prep_parser.add_argument("--api-key", help="Gemini API key (or set GEMINI_API_KEY env var)")
    prep_parser.add_argument("--auto", action="store_true", help="Apply cuts without confirmation")
    prep_parser.add_argument("--silence-threshold", default="-35dB", help="Silence detection threshold (default: -35dB)")
    prep_parser.add_argument("--silence-min-duration", type=float, default=0.8, help="Min silence duration in seconds (default: 0.8)")
    prep_parser.add_argument("--max-silence", type=float, default=1.5, help="Max allowed silence before cutting (default: 1.5s)")

    # --- transcribe command ---
    transcribe_parser = subparsers.add_parser(
        "transcribe",
        help="Transcribe a video file with word-level timestamps",
    )
    transcribe_parser.add_argument("video", help="Path to video file")
    transcribe_parser.add_argument("-o", "--output", help="Output JSON path")
    transcribe_parser.add_argument("--output-dir", help="Directory for audio extraction")

    # --- analyze command ---
    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Analyze an existing transcript for false starts and fillers",
    )
    analyze_parser.add_argument("transcript", help="Path to transcript JSON")
    analyze_parser.add_argument("-o", "--output", help="Output analysis JSON path")
    analyze_parser.add_argument("--api-key", help="Gemini API key (or set GEMINI_API_KEY env var)")

    # --- cut command ---
    cut_parser = subparsers.add_parser(
        "cut",
        help="Apply a saved cut list to a video",
    )
    cut_parser.add_argument("video", help="Path to video file")
    cut_parser.add_argument("analysis", help="Path to analysis JSON")
    cut_parser.add_argument("-o", "--output", help="Output video path")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    commands = {
        "web": cmd_web,
        "prep": cmd_prep,
        "transcribe": cmd_transcribe,
        "analyze": cmd_analyze,
        "cut": cmd_cut,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
