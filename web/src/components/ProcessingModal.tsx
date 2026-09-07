import React from 'react';
import { Mic, Scissors, Sparkles, AudioWaveform, CheckCircle2, Loader2 } from 'lucide-react';

interface ProcessingModalProps {
  title: string;
  message: string;
  progress?: number | null;
  stageIndex?: number;
}

const STAGES = [
  { label: 'Extract Audio', icon: AudioWaveform },
  { label: 'Moonshine STT', icon: Mic },
  { label: 'Detect Silence', icon: Scissors },
  { label: 'AI Retake Analysis', icon: Sparkles },
];

export const ProcessingModal: React.FC<ProcessingModalProps> = ({
  title,
  message,
  progress,
  stageIndex = 1,
}) => {
  const currentProgress = typeof progress === 'number' ? Math.max(0, Math.min(100, Math.round(progress))) : null;

  return (
    <div className="modal-backdrop">
      <div
        className="modal-content"
        style={{
          textAlign: 'center',
          maxWidth: '520px',
          padding: '2rem 1.75rem',
          borderRadius: '16px',
        }}
      >
        {/* Animated Icon */}
        <div
          style={{
            width: '64px',
            height: '64px',
            borderRadius: '50%',
            background: 'rgba(99, 102, 241, 0.12)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 1.25rem',
            border: '1px solid rgba(99, 102, 241, 0.3)',
          }}
        >
          <Loader2
            size={32}
            className="spinner-icon"
            style={{ color: 'var(--accent-secondary)', animation: 'spin 1.5s linear infinite' }}
          />
        </div>

        <h3 style={{ fontSize: '1.4rem', fontWeight: 800, marginBottom: '0.4rem', letterSpacing: '-0.3px' }}>
          {title}
        </h3>

        <p
          style={{
            color: 'var(--text-muted)',
            fontSize: '0.92rem',
            lineHeight: 1.5,
            minHeight: '44px',
            marginBottom: '1.25rem',
          }}
        >
          {message}
        </p>

        {/* 4-Stage Stepper */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(4, 1fr)',
            gap: '0.5rem',
            marginBottom: '1.5rem',
            padding: '0.75rem 0.5rem',
            background: 'rgba(0, 0, 0, 0.25)',
            borderRadius: '10px',
            border: '1px solid var(--card-border)',
          }}
        >
          {STAGES.map((s, idx) => {
            const stepNum = idx + 1;
            const isCompleted = stageIndex > stepNum || (currentProgress !== null && currentProgress >= 100);
            const isCurrent = stageIndex === stepNum && !isCompleted;
            const Icon = s.icon;

            return (
              <div
                key={s.label}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: '0.35rem',
                  opacity: isCompleted || isCurrent ? 1 : 0.4,
                  transition: 'all 0.3s ease',
                }}
              >
                <div
                  style={{
                    width: '32px',
                    height: '32px',
                    borderRadius: '50%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    background: isCompleted
                      ? 'var(--emerald)'
                      : isCurrent
                      ? 'var(--accent-primary)'
                      : 'rgba(255, 255, 255, 0.08)',
                    color: 'white',
                    boxShadow: isCurrent ? '0 0 12px var(--accent-glow)' : 'none',
                    transition: 'all 0.3s ease',
                  }}
                >
                  {isCompleted ? <CheckCircle2 size={16} /> : <Icon size={16} />}
                </div>
                <span
                  style={{
                    fontSize: '0.72rem',
                    fontWeight: isCurrent ? 700 : 500,
                    color: isCurrent ? 'white' : 'var(--text-muted)',
                    textAlign: 'center',
                    lineHeight: 1.2,
                  }}
                >
                  {s.label}
                </span>
              </div>
            );
          })}
        </div>

        {/* Live Progress Bar */}
        <div style={{ textAlign: 'left' }}>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              fontSize: '0.85rem',
              marginBottom: '0.45rem',
              color: 'var(--text-main)',
              fontWeight: 600,
            }}
          >
            <span>Processing Status</span>
            <span style={{ fontFamily: 'JetBrains Mono', color: 'var(--accent-secondary)' }}>
              {currentProgress !== null ? `${currentProgress}%` : 'Processing...'}
            </span>
          </div>
          <div
            style={{
              width: '100%',
              height: '10px',
              borderRadius: '9999px',
              background: 'rgba(255, 255, 255, 0.08)',
              overflow: 'hidden',
              position: 'relative',
            }}
          >
            <div
              style={{
                height: '100%',
                width: `${currentProgress ?? 35}%`,
                background: 'var(--accent-gradient)',
                borderRadius: '9999px',
                boxShadow: '0 0 14px var(--accent-glow)',
                transition: 'width 0.3s ease-out',
              }}
            />
          </div>
        </div>
      </div>
    </div>
  );
};
