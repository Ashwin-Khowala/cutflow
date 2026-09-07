# Contributing to CutFlow

Thank you for your interest in contributing to CutFlow! CutFlow is an open-source AI video editing engine designed to turn raw video recordings into structured, publication-ready edits.

## Development Principles

1. **Safety First**: Never commit or hardcode API keys, secrets, or sensitive sample data.
2. **Deterministic & Inspectable**: Editing decisions are represented as structured JSON Edit Plans before any rendering occurs.
3. **Provider-Agnostic**: Core architecture cleanly separates speech recognition, LLM intelligence, and video rendering engines.

---

## Getting Started

### Prerequisites

- **Python 3.10+** (with `pip` and virtual environment support)
- **Node.js 18+** and `npm`
- **FFmpeg 6+** installed and available on your system `PATH`
- (Optional) API key for Groq or Google Gemini (configured via `.env` or in UI settings)

### Repository Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Ashwin-Khowala/cutflow.git
   cd cutflow
   ```

2. **Backend Setup**:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux / macOS:
   source .venv/bin/activate

   pip install -r requirements.txt
   pip install -e .
   ```

3. **Frontend Setup**:
   ```bash
   cd web
   npm install
   cd ..
   ```

4. **Environment Configuration**:
   ```bash
   cp .env.example .env
   # Add your GROQ_API_KEY or GEMINI_API_KEY if testing live LLM analysis
   ```

5. **Start Full Development Server**:
   ```bash
   python run.py
   ```
   This launches:
   - FastAPI Backend at `http://localhost:8000`
   - Vite React Frontend at `http://localhost:5173`

---

## Running Tests

### Python Backend Tests
```bash
pytest -v
```

### Frontend Build & Lint Check
```bash
cd web
npm run lint
npm run build
```

---

## Pull Request Guidelines

1. **Create a branch**: Use descriptive branch names like `feat/add-edl-export` or `fix/timeline-seek-glitch`.
2. **Write tests**: Add unit tests in `tests/` for backend changes and ensure existing tests pass.
3. **Verify secrets**: Run an audit to verify no keys, personal paths, or credentials are added.
4. **Follow code style**:
   - Python: Clean, type-hinted code following PEP 8.
   - TypeScript: Strict typing, modern React functional components with CSS classes.
5. **Open a PR**: Describe what changed, why it changed, and include screenshots or video clips if modifying the UI.

---

## Community & Questions

- Open an issue on GitHub for bug reports or feature suggestions.
- For security vulnerabilities, please refer to [SECURITY.md](SECURITY.md).
