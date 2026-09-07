# 🎬 CutFlow — Open-Source AI Video Editing Engine

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![React 18 + Vite](https://img.shields.io/badge/react-18_Vite-61DAFB.svg?logo=react&logoColor=black)](https://vitejs.dev/)
[![Security: Zero Secrets](https://img.shields.io/badge/security-zero_hardcoded_secrets-success.svg)](SECURITY.md)

**Turn raw recordings into publication-ready video edits using speech recognition, semantic LLM reasoning, and deterministic timeline compilation.**

[Live Studio Demo](#-quick-start) • [Architecture](#-engine-architecture) • [Edit Plan IR](#-structured-edit-plan-ir) • [Roadmap](ROADMAP.md) • [Contributing](CONTRIBUTING.md)

</div>

---

## 💡 What is CutFlow?

Video editing today is trapped between two extremes:
1. **Manual NLE Timelines** (Premiere, DaVinci, Final Cut) — powerful but require tedious scrubbing and cutting false starts, stumbles, and dead air frame-by-frame.
2. **Proprietary Closed-Source AI Video SaaS** (Descript, HeyGen, CapCut) — black-box workflows locked behind expensive subscriptions that hoard your raw media.

**CutFlow is the open-source engine that bridges speech, video perception, and deterministic timeline editing.** 

Instead of jumping straight to lossy rendering, CutFlow perceives raw audio and speech, understands retakes and semantic stumbles with state-of-the-art LLMs, and compiles an **inspectable, provider-agnostic Edit Plan JSON**. You can preview, tweak, and render directly via FFmpeg or export downstream to editors like OpenCut, Premiere, and DaVinci Resolve.

---

## ⚡ The 3-Pillar Engine Architecture

```
┌─────────────────┐      ┌─────────────────────────┐      ┌────────────────────────┐
│  1. PERCEIVE    │ ───► │  2. UNDERSTAND          │ ───► │  3. COMPILE & RENDER   │
│                 │      │                         │      │                        │
│ • FFmpeg Audio  │      │ • Word Timestamps       │      │ • Edit Plan JSON (IR)  │
│ • Silence Detect│      │ • False Start Detection │      │ • Frame-Accurate Concat│
│ • Faster-Whisper│      │ • Groq & Gemini Agents  │      │ • Studio Preview Sync  │
└─────────────────┘      └─────────────────────────┘      └────────────────────────┘
```

1. **Perception**: Extracts acoustic features, detects true silence intervals (`silencedetect`), and computes word-level timestamped transcripts using Whisper/Moonshine.
2. **Semantic Understanding**: Evaluates consecutive takes, stumbles, and filler words using fast local or cloud LLMs (Groq Llama 3.3 / GPT-OSS, Gemini 2.0 Flash) backed by deterministic heuristics.
3. **Compilation & Rendering**: Emits an open **Edit Plan IR** (Intermediate Representation) mapping keep/cut intervals and renders seamless transitions via FFmpeg filtergraphs with audio crossfades.

---

## ✨ Features

- **🧠 Intelligent Retake & False-Start Pruning:** Identifies when you fumble a line and retry it, keeping only your best take.
- **🔇 Natural Silence Truncation:** Drops dead-air without creating jarring, robotic jump-cuts by preserving natural acoustic padding.
- **📄 Universal Edit Plan JSON:** Inspectable, reproducible intermediate representation for every edit decision.
- **🎨 Modern Studio Workspace:** CapCut/Descript-inspired dark interface with canvas audio waveform, multi-track timeline, instant auto-skip preview, and inline transcript toggles.
- **🔒 Zero-Secret Architecture:** Absolutely no hardcoded API keys. All keys remain in local environment variables (`.env`) or temporary browser session storage.
- **🌐 Deployable on Vercel:** Clean split between a lightweight, responsive client and headless rendering engine.

---

## 📋 Structured Edit Plan (IR)

CutFlow introduces an open intermediate format for video editing decisions:

```json
{
  "version": "1.0",
  "project_id": "proj_9f2a81b",
  "source_video": "raw_recording.mp4",
  "source_duration": 142.6,
  "stats": {
    "original_duration": 142.6,
    "clean_duration": 94.2,
    "time_saved": 48.4,
    "cuts_count": 8
  },
  "timeline": [
    {
      "id": "entry_0",
      "start": 0.0,
      "end": 14.2,
      "type": "a_roll",
      "action": "keep",
      "text": "Welcome back to the channel. Today we're building an AI editor.",
      "confidence": 0.98
    },
    {
      "id": "entry_1",
      "start": 14.2,
      "end": 18.5,
      "type": "cut",
      "action": "cut",
      "reason": "false_start",
      "text": "Today we're gonna... wait, let me start over.",
      "confidence": 0.92
    }
  ]
}
```

This format can be fetched via `GET /api/project/{id}/edit-plan` and passed directly into downstream tools or custom rendering backends.

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+**
- **Node.js 18+** & `npm`
- **FFmpeg** on system `PATH` (`ffmpeg -version`)

### 1. Clone & Setup Environment

```bash
git clone https://github.com/Ashwin-Khowala/cutflow.git
cd cutflow

# Setup Python Virtual Environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux / macOS:
source .venv/bin/activate

pip install -r requirements.txt
pip install -e .
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your favorite LLM provider (Groq or Gemini)
# Or configure keys at runtime directly inside the Web Studio Settings dialog
```

### 3. Start Development Server

```bash
python run.py
```

- **Web Studio:** [http://localhost:5173](http://localhost:5173)
- **FastAPI Engine API:** [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 📟 CLI Power-User Mode

CutFlow can run entirely headless inside CLI scripts or automated ingestion pipelines:

```bash
# Full pipeline: Transcribe, analyze retakes, preview cuts, and render:
cutflow prep "raw_recording.mp4"

# Non-interactive automated execution:
cutflow prep "raw_recording.mp4" --auto

# Transcribe only:
cutflow transcribe "raw_recording.mp4" -o "transcript.json"

# Analyze an existing transcript:
cutflow analyze "transcript.json" -o "analysis.json"

# Compile and cut using an existing plan:
cutflow cut "raw_recording.mp4" "analysis.json" -o "clean_output.mp4"
```

---

## 🧪 Testing

CutFlow maintains strict unit test coverage across speech detection, prompt parsing, cut alignment, and API routes:

```bash
# Run backend test suite
pytest -v

# Run frontend build & linting
cd web
npm run lint
npm run build
```

---

## 🗺️ Project Structure

```
cutflow/
├── cutflow/               # Core Python Engine
│   ├── analyzer.py        # LLM semantic reasoning & false-start detector
│   ├── transcriber.py     # Audio extraction & speech-to-text
│   ├── cutter.py          # Frame-accurate FFmpeg slicing & concat engine
│   ├── edit_plan.py       # Universal Edit Plan IR schema & serializers
│   ├── server.py          # FastAPI REST endpoints
│   └── cli.py             # Headless CLI interface
├── web/                   # Studio Web App (React 18 + TypeScript + Vite)
│   ├── src/
│   │   ├── components/    # LandingPage, StudioHeader, VideoPlayer, Timeline, Waveform, TranscriptList
│   │   ├── types/         # TypeScript interfaces for timeline & edit plans
│   │   ├── App.tsx        # Studio workspace
│   │   └── index.css      # Dark-mode design system
│   ├── vercel.json        # Vercel deployment configuration
│   └── vite.config.ts
├── tests/                 # Automated test suites
├── docs/                  # Architecture & specifications
├── LICENSE                # MIT License
├── CODE_OF_CONDUCT.md     # Contributor Covenant v2.1
├── CONTRIBUTING.md        # Contribution guidelines
├── SECURITY.md            # Responsible disclosure & zero-secret policy
└── ROADMAP.md             # Public development milestones
```

---

## 🤝 Contributing

Contributions are warmly welcomed! Please read our [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) before submitting pull requests.

## 📄 License

CutFlow is open source under the [MIT License](LICENSE).
