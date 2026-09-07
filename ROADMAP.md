# CutFlow Roadmap

CutFlow is evolving from an automated rough-cut generator into an **open-source AI video editing engine** that bridges raw audiovisual perception with deterministic, multi-track editing timelines.

---

## 🎯 Current Milestone: Phase 1 — Understand & Edit Plan Engine (v0.2.0)

- [x] **Acoustic Perception**: Audio extraction & silence boundary detection via FFmpeg filtergraphs.
- [x] **Word-Level Transcription**: Faster-Whisper integration with exact start/end word timestamps.
- [x] **Semantic Decision Making**: Multi-provider LLM analysis (Groq Llama-3.3/GPT-OSS, Google Gemini 2.0 Flash) with retry mechanisms and fallback heuristics.
- [x] **Deterministic Stitching**: Frame-accurate FFmpeg concat filtering with audio crossfades to prevent clicks.
- [x] **Web Studio UI**: Dark-mode CapCut/OpenCut style timeline with audio waveform, synchronized sentence playback, and one-click export.
- [x] **Structured Edit Plan (IR)**: Universal JSON intermediate representation for timeline entries, cuts, and actions.
- [x] **Zero-Secret Architecture**: Strictly no hardcoded API credentials; isolated browser storage or server `.env`.

---

## 🚀 Near-Term Milestone: Phase 2 — Multi-Modal Enhancements (v0.3.0)

- [ ] **EDL & FCPXML Export**: Native export to DaVinci Resolve, Final Cut Pro, and Adobe Premiere timelines.
- [ ] **B-Roll Prompt Extraction**: Automatically highlight visual concepts mentioned in the speech and generate image/video generation prompts (Flux / Kling / Veo).
- [ ] **Dynamic Subtitles & Word Karaoke**: Burn-in or export animated `.ass` / `.vtt` subtitles styled for short-form video (TikTok / Reels / Shorts).
- [ ] **Visual Pacing & Filler Cam**: Automatic zoom-in / zoom-out keyframing on emphasize words to break talking-head monotony.
- [ ] **Browser WebAssembly Waveform**: Instant offline audio waveform decoding directly in the client.

---

## 🔮 Long-Term Vision: Phase 3 — Autonomous AI Editing Agent (v0.4.0+)

- [ ] **OpenCut Integration**: Seamlessly pipe CutFlow Edit Plans directly into OpenCut project files for finishing.
- [ ] **Model Context Protocol (MCP) Server**: Expose CutFlow as an MCP tool so external coding & creative AI agents can direct video editing workflows programmatically.
- [ ] **Multi-Camera & Speaker Diarization**: Detect multiple speakers and auto-switch camera angles in podcast or interview recordings.
- [ ] **Remotion Web Rendering**: Cloud-native, code-based video rendering powered by Vercel serverless execution.
