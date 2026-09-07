import React, { useRef, useState } from 'react';
import { UploadCloud, Video, Wand2, ShieldCheck, Zap } from 'lucide-react';

interface UploadHeroProps {
  onFileUpload: (file: File) => void;
}

export const UploadHero: React.FC<UploadHeroProps> = ({ onFileUpload }) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      onFileUpload(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      onFileUpload(e.target.files[0]);
    }
  };

  return (
    <div style={{ padding: '3rem 2rem', maxWidth: '960px', margin: '0 auto', width: '100%' }}>
      <div
        className="glass-panel"
        style={{
          border: isDragOver
            ? '2px dashed var(--accent-primary)'
            : '2px dashed rgba(99, 102, 241, 0.35)',
          background: isDragOver ? 'rgba(99, 102, 241, 0.08)' : 'var(--card-bg)',
          padding: '4rem 2rem',
          textAlign: 'center',
          borderRadius: '24px',
          cursor: 'pointer',
          transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
        }}
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragOver(true);
        }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <div
          style={{
            width: '80px',
            height: '80px',
            borderRadius: '20px',
            background: 'var(--accent-gradient)',
            margin: '0 auto 1.5rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 8px 32px var(--accent-glow)',
          }}
        >
          <UploadCloud size={40} color="#ffffff" />
        </div>

        <h2 style={{ fontSize: '2rem', fontWeight: 800, marginBottom: '0.75rem', letterSpacing: '-0.5px' }}>
          Drop your raw video recording here
        </h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '1.05rem', maxWidth: '540px', margin: '0 auto 2rem' }}>
          CutFlow uses <strong>Moonshine Speech-to-Text</strong> and <strong>Gemini AI</strong> to automatically eliminate your false starts, repeated takes, fillers, and silence.
        </p>

        <input
          ref={fileInputRef}
          type="file"
          accept="video/*,audio/*"
          style={{ display: 'none' }}
          onChange={handleFileChange}
        />

        <button className="btn btn-primary" style={{ padding: '0.75rem 1.75rem', fontSize: '1rem' }}>
          <Video size={18} />
          <span>Browse Video File</span>
        </button>
      </div>

      {/* Feature Pills */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: '1.25rem',
          marginTop: '2.5rem',
        }}
      >
        <div className="glass-panel" style={{ padding: '1.25rem', borderRadius: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', color: '#818cf8', marginBottom: '0.4rem', fontWeight: 700 }}>
            <Wand2 size={18} />
            <span>Semantic Retake Detection</span>
          </div>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            Detects repeated attempts at the same line and automatically selects the cleanest, final version.
          </p>
        </div>

        <div className="glass-panel" style={{ padding: '1.25rem', borderRadius: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', color: '#06b6d4', marginBottom: '0.4rem', fontWeight: 700 }}>
            <Zap size={18} />
            <span>Live Auto-Skip Preview</span>
          </div>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            Preview your clean edit immediately inside the browser player before rendering.
          </p>
        </div>

        <div className="glass-panel" style={{ padding: '1.25rem', borderRadius: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', color: '#10b981', marginBottom: '0.4rem', fontWeight: 700 }}>
            <ShieldCheck size={18} />
            <span>Non-Destructive Slicing</span>
          </div>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            You keep 100% control with one-click override toggles on every sentence before FFmpeg export.
          </p>
        </div>
      </div>
    </div>
  );
};
