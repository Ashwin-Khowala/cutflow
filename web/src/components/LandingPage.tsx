import React from 'react';

interface LandingPageProps {
  onLaunchStudio: () => void;
  onOpenSettings: () => void;
  onFileUpload: (file: File) => void;
}

export const LandingPage: React.FC<LandingPageProps> = ({
  onLaunchStudio,
  onOpenSettings,
  onFileUpload,
}) => {
  const [isDragging, setIsDragging] = React.useState(false);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      onFileUpload(e.dataTransfer.files[0]);
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      onFileUpload(e.target.files[0]);
    }
  };

  return (
    <div className="landing-container" style={{ minHeight: '100vh', background: '#07090e', color: '#f8fafc' }}>
      {/* Top Navigation */}
      <nav
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '1.25rem 2.5rem',
          borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
          background: 'rgba(7, 9, 14, 0.85)',
          backdropFilter: 'blur(16px)',
          position: 'sticky',
          top: 0,
          zIndex: 40,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
          <div
            style={{
              width: '36px',
              height: '36px',
              borderRadius: '9px',
              background: 'linear-gradient(135deg, #6366f1, #06b6d4)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 16px rgba(99, 102, 241, 0.4)',
              fontWeight: 800,
              fontSize: '1.1rem',
            }}
          >
            ✂
          </div>
          <div>
            <span style={{ fontSize: '1.2rem', fontWeight: 700, letterSpacing: '-0.02em' }}>CutFlow</span>
            <span
              style={{
                marginLeft: '0.5rem',
                fontSize: '0.68rem',
                padding: '2px 7px',
                borderRadius: '9999px',
                background: 'rgba(99, 102, 241, 0.15)',
                color: '#a5b4fc',
                border: '1px solid rgba(99, 102, 241, 0.3)',
                fontWeight: 600,
              }}
            >
              ENGINE
            </span>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '2rem' }}>
          <a
            href="#features"
            style={{ color: '#94a3b8', textDecoration: 'none', fontSize: '0.88rem', fontWeight: 500 }}
          >
            Pillars
          </a>
          <a
            href="#architecture"
            style={{ color: '#94a3b8', textDecoration: 'none', fontSize: '0.88rem', fontWeight: 500 }}
          >
            Architecture
          </a>
          <a
            href="#edit-plan"
            style={{ color: '#94a3b8', textDecoration: 'none', fontSize: '0.88rem', fontWeight: 500 }}
          >
            Edit Plan IR
          </a>
          <button
            onClick={onOpenSettings}
            style={{
              background: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              color: '#cbd5e1',
              borderRadius: '8px',
              padding: '7px 14px',
              fontSize: '0.85rem',
              cursor: 'pointer',
            }}
          >
            ⚙ Settings
          </button>
          <button
            onClick={onLaunchStudio}
            style={{
              background: 'linear-gradient(135deg, #6366f1, #4f46e5)',
              border: 'none',
              color: '#ffffff',
              borderRadius: '8px',
              padding: '8px 18px',
              fontSize: '0.88rem',
              fontWeight: 600,
              cursor: 'pointer',
              boxShadow: '0 0 20px rgba(99, 102, 241, 0.35)',
            }}
          >
            Launch Studio →
          </button>
        </div>
      </nav>

      {/* Hero Section */}
      <section
        style={{
          maxWidth: '1200px',
          margin: '0 auto',
          padding: '4.5rem 1.5rem 3rem 1.5rem',
          textAlign: 'center',
          position: 'relative',
        }}
      >
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.5rem',
            padding: '4px 14px',
            borderRadius: '9999px',
            background: 'rgba(99, 102, 241, 0.1)',
            border: '1px solid rgba(99, 102, 241, 0.25)',
            color: '#a5b4fc',
            fontSize: '0.82rem',
            fontWeight: 500,
            marginBottom: '1.5rem',
          }}
        >
          <span>✨ Open-Source AI Video Editing Engine</span>
          <span style={{ color: '#4b5563' }}>•</span>
          <span style={{ color: '#38bdf8' }}>Vercel OSS Program</span>
        </div>

        <h1
          style={{
            fontSize: '3.6rem',
            fontWeight: 800,
            lineHeight: 1.15,
            letterSpacing: '-0.03em',
            marginBottom: '1.5rem',
            background: 'linear-gradient(180deg, #ffffff 0%, #cbd5e1 60%, #94a3b8 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}
        >
          Turn Raw Takes into Polished Videos.
          <br />
          <span
            style={{
              background: 'linear-gradient(135deg, #6366f1 0%, #06b6d4 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}
          >
            Automatically.
          </span>
        </h1>

        <p
          style={{
            fontSize: '1.15rem',
            lineHeight: 1.6,
            color: '#94a3b8',
            maxWidth: '720px',
            margin: '0 auto 2.5rem auto',
          }}
        >
          The open-source engine that perceives audio boundaries, understands false starts and repeated takes
          with state-of-the-art LLMs, and compiles an open, inspectable <strong>Edit Plan JSON</strong> ready for FFmpeg,
          OpenCut, or DaVinci Resolve.
        </p>

        {/* Action Buttons */}
        <div style={{ display: 'flex', justifyContent: 'center', gap: '1rem', marginBottom: '3.5rem' }}>
          <button
            onClick={onLaunchStudio}
            style={{
              background: 'linear-gradient(135deg, #6366f1, #06b6d4)',
              border: 'none',
              color: '#ffffff',
              borderRadius: '10px',
              padding: '12px 28px',
              fontSize: '1rem',
              fontWeight: 600,
              cursor: 'pointer',
              boxShadow: '0 8px 24px rgba(99, 102, 241, 0.4)',
              transition: 'transform 0.15s ease',
            }}
          >
            Start Editing in Studio
          </button>
          <a
            href="https://github.com/Ashwin-Khowala/cutflow"
            target="_blank"
            rel="noreferrer"
            style={{
              background: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid rgba(255, 255, 255, 0.12)',
              color: '#f8fafc',
              borderRadius: '10px',
              padding: '12px 24px',
              fontSize: '1rem',
              fontWeight: 500,
              textDecoration: 'none',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.5rem',
            }}
          >
            <span>GitHub Repository</span>
            <span>↗</span>
          </a>
        </div>

        {/* Embedded Upload Hero Dropzone */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          style={{
            maxWidth: '760px',
            margin: '0 auto',
            padding: '2.5rem',
            borderRadius: '16px',
            background: isDragging ? 'rgba(99, 102, 241, 0.08)' : 'rgba(15, 23, 42, 0.6)',
            border: isDragging ? '2px dashed #6366f1' : '2px dashed rgba(255, 255, 255, 0.12)',
            boxShadow: '0 20px 50px rgba(0, 0, 0, 0.6)',
            backdropFilter: 'blur(12px)',
            transition: 'all 0.2s ease',
          }}
        >
          <div
            style={{
              width: '56px',
              height: '56px',
              borderRadius: '14px',
              background: 'rgba(99, 102, 241, 0.15)',
              border: '1px solid rgba(99, 102, 241, 0.3)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 1.25rem auto',
              fontSize: '1.5rem',
            }}
          >
            📁
          </div>
          <h3 style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: '0.5rem' }}>
            Drop your raw recording here
          </h3>
          <p style={{ fontSize: '0.88rem', color: '#94a3b8', marginBottom: '1.5rem' }}>
            Supports MP4, MOV, MKV, and WEBM • Up to 2GB • Audio extracted locally
          </p>

          <label
            style={{
              background: 'rgba(255, 255, 255, 0.08)',
              border: '1px solid rgba(255, 255, 255, 0.15)',
              color: '#ffffff',
              padding: '9px 20px',
              borderRadius: '8px',
              fontSize: '0.85rem',
              fontWeight: 500,
              cursor: 'pointer',
              display: 'inline-block',
            }}
          >
            Browse Video File
            <input
              type="file"
              accept="video/*"
              style={{ display: 'none' }}
              onChange={handleFileInput}
            />
          </label>
        </div>
      </section>

      {/* 3 Pillars Section */}
      <section
        id="features"
        style={{
          maxWidth: '1200px',
          margin: '4rem auto',
          padding: '2rem 1.5rem',
        }}
      >
        <div style={{ textAlign: 'center', marginBottom: '3rem' }}>
          <h2 style={{ fontSize: '2.2rem', fontWeight: 700, letterSpacing: '-0.02em', marginBottom: '0.75rem' }}>
            The 3-Pillar Editing Pipeline
          </h2>
          <p style={{ color: '#94a3b8', fontSize: '1rem', maxWidth: '600px', margin: '0 auto' }}>
            CutFlow separates video perception, semantic decision-making, and timeline compilation.
          </p>
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
            gap: '1.5rem',
          }}
        >
          {/* Pillar 1 */}
          <div
            style={{
              background: 'rgba(15, 20, 30, 0.7)',
              border: '1px solid rgba(255, 255, 255, 0.07)',
              borderRadius: '14px',
              padding: '2rem',
              boxShadow: '0 12px 30px rgba(0, 0, 0, 0.3)',
            }}
          >
            <div
              style={{
                width: '44px',
                height: '44px',
                borderRadius: '10px',
                background: 'rgba(6, 182, 212, 0.15)',
                border: '1px solid rgba(6, 182, 212, 0.3)',
                color: '#22d3ee',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '1.25rem',
                marginBottom: '1.25rem',
              }}
            >
              🎙️
            </div>
            <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#22d3ee', textTransform: 'uppercase', marginBottom: '0.4rem' }}>
              Pillar 01
            </div>
            <h3 style={{ fontSize: '1.3rem', fontWeight: 600, marginBottom: '0.75rem' }}>
              Perceive Acoustics & Speech
            </h3>
            <p style={{ fontSize: '0.88rem', color: '#94a3b8', lineHeight: 1.6 }}>
              Local Faster-Whisper transcription extracts word-level start/end timestamps. FFmpeg filtergraphs
              detect acoustic silence intervals while preserving natural cadence padding.
            </p>
          </div>

          {/* Pillar 2 */}
          <div
            style={{
              background: 'rgba(15, 20, 30, 0.7)',
              border: '1px solid rgba(255, 255, 255, 0.07)',
              borderRadius: '14px',
              padding: '2rem',
              boxShadow: '0 12px 30px rgba(0, 0, 0, 0.3)',
            }}
          >
            <div
              style={{
                width: '44px',
                height: '44px',
                borderRadius: '10px',
                background: 'rgba(99, 102, 241, 0.15)',
                border: '1px solid rgba(99, 102, 241, 0.3)',
                color: '#818cf8',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '1.25rem',
                marginBottom: '1.25rem',
              }}
            >
              🧠
            </div>
            <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#818cf8', textTransform: 'uppercase', marginBottom: '0.4rem' }}>
              Pillar 02
            </div>
            <h3 style={{ fontSize: '1.3rem', fontWeight: 600, marginBottom: '0.75rem' }}>
              Understand Semantic Retakes
            </h3>
            <p style={{ fontSize: '0.88rem', color: '#94a3b8', lineHeight: 1.6 }}>
              Evaluates spoken takes with Groq LPU (Llama 3.3 / GPT-OSS) or Google Gemini 2.0 Flash. Intelligently
              prunes stumbles, repeated sentences, and filler words, keeping your strongest delivery.
            </p>
          </div>

          {/* Pillar 3 */}
          <div
            style={{
              background: 'rgba(15, 20, 30, 0.7)',
              border: '1px solid rgba(255, 255, 255, 0.07)',
              borderRadius: '14px',
              padding: '2rem',
              boxShadow: '0 12px 30px rgba(0, 0, 0, 0.3)',
            }}
          >
            <div
              style={{
                width: '44px',
                height: '44px',
                borderRadius: '10px',
                background: 'rgba(16, 185, 129, 0.15)',
                border: '1px solid rgba(16, 185, 129, 0.3)',
                color: '#34d399',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '1.25rem',
                marginBottom: '1.25rem',
              }}
            >
              ⚡
            </div>
            <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#34d399', textTransform: 'uppercase', marginBottom: '0.4rem' }}>
              Pillar 03
            </div>
            <h3 style={{ fontSize: '1.3rem', fontWeight: 600, marginBottom: '0.75rem' }}>
              Compile & Render IR
            </h3>
            <p style={{ fontSize: '0.88rem', color: '#94a3b8', lineHeight: 1.6 }}>
              Produces a standardized Edit Plan JSON. Preview seamlessly in the Web Studio with instant Smart Skip,
              render via FFmpeg with audio crossfades, or export directly to CMX 3600 EDL for DaVinci Resolve.
            </p>
          </div>
        </div>
      </section>

      {/* Edit Plan Specification Preview */}
      <section
        id="edit-plan"
        style={{
          maxWidth: '1200px',
          margin: '3rem auto 6rem auto',
          padding: '2rem 1.5rem',
        }}
      >
        <div
          style={{
            background: '#0d1117',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            borderRadius: '16px',
            padding: '2rem',
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: '2.5rem',
            alignItems: 'center',
          }}
        >
          <div>
            <div
              style={{
                display: 'inline-block',
                padding: '3px 10px',
                borderRadius: '6px',
                background: 'rgba(99, 102, 241, 0.15)',
                color: '#a5b4fc',
                fontSize: '0.75rem',
                fontWeight: 600,
                marginBottom: '1rem',
              }}
            >
              INTERMEDIATE REPRESENTATION
            </div>
            <h3 style={{ fontSize: '1.8rem', fontWeight: 700, marginBottom: '1rem', lineHeight: 1.25 }}>
              Open, inspectable editing decisions.
            </h3>
            <p style={{ fontSize: '0.92rem', color: '#94a3b8', lineHeight: 1.6, marginBottom: '1.25rem' }}>
              Traditional AI editing tools are black boxes. CutFlow emits a clean, deterministic schema separating
              what to cut, what to keep, and why.
            </p>
            <ul style={{ listStyle: 'none', padding: 0, display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
              <li style={{ fontSize: '0.85rem', color: '#cbd5e1', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span style={{ color: '#10b981' }}>✓</span> Exact floating-point timecodes for frame precision
              </li>
              <li style={{ fontSize: '0.85rem', color: '#cbd5e1', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span style={{ color: '#10b981' }}>✓</span> Classification reasons (false start, filler, dead air)
              </li>
              <li style={{ fontSize: '0.85rem', color: '#cbd5e1', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span style={{ color: '#10b981' }}>✓</span> Human-in-the-loop overrides synced instantly
              </li>
              <li style={{ fontSize: '0.85rem', color: '#cbd5e1', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span style={{ color: '#10b981' }}>✓</span> Zero hardcoded secrets or vendor lock-in
              </li>
            </ul>
          </div>

          <div
            style={{
              background: 'rgba(0, 0, 0, 0.5)',
              borderRadius: '10px',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              padding: '1.25rem',
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: '0.78rem',
              color: '#38bdf8',
              maxHeight: '340px',
              overflowY: 'auto',
            }}
          >
            <pre style={{ margin: 0, lineHeight: 1.45 }}>
{`{
  "version": "1.0",
  "project_id": "cutflow_9f2a81",
  "source_video": "interview_raw.mp4",
  "source_duration": 184.5,
  "stats": {
    "clean_duration": 121.2,
    "time_saved": 63.3,
    "savings_percent": 34.3,
    "cuts_count": 9
  },
  "timeline": [
    {
      "id": "entry_001",
      "start": 0.0,
      "end": 12.4,
      "type": "a_roll",
      "action": "keep",
      "text": "Hello everyone, welcome back to the devlog."
    },
    {
      "id": "entry_002",
      "start": 12.4,
      "end": 16.8,
      "type": "cut",
      "action": "cut",
      "reason": "false_start",
      "text": "Today we are gonna... wait, let me start over."
    }
  ]
}`}
            </pre>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer
        style={{
          borderTop: '1px solid rgba(255, 255, 255, 0.06)',
          padding: '2.5rem 2rem',
          textAlign: 'center',
          color: '#64748b',
          fontSize: '0.85rem',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'center', gap: '1.5rem', marginBottom: '1rem' }}>
          <a href="https://github.com/Ashwin-Khowala/cutflow" style={{ color: '#94a3b8', textDecoration: 'none' }}>
            GitHub
          </a>
          <a href="/docs/EDIT_PLAN_SPEC.md" style={{ color: '#94a3b8', textDecoration: 'none' }}>
            Edit Plan Spec
          </a>
          <a href="/ROADMAP.md" style={{ color: '#94a3b8', textDecoration: 'none' }}>
            Roadmap
          </a>
          <a href="/SECURITY.md" style={{ color: '#94a3b8', textDecoration: 'none' }}>
            Security
          </a>
        </div>
        <p>CutFlow Engine • Released under the MIT License • Built for Vercel OSS Cohort</p>
      </footer>
    </div>
  );
};
