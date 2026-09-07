import React from 'react';
import type { SelectedClip } from '../types';
import { Scissors, Check, Play, X, Sparkles, Clock, AlertTriangle } from 'lucide-react';

interface SelectedClipBarProps {
  selectedClip: SelectedClip | null;
  shortClipsCount: number;
  onCutClip: (clip: SelectedClip) => void;
  onRestoreClip: (clip: SelectedClip) => void;
  onPlayClip: (clip: SelectedClip) => void;
  onDeselect: () => void;
  onCleanShortClips: () => void;
}

export const SelectedClipBar: React.FC<SelectedClipBarProps> = ({
  selectedClip,
  shortClipsCount,
  onCutClip,
  onRestoreClip,
  onPlayClip,
  onDeselect,
  onCleanShortClips,
}) => {
  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    const ms = Math.floor((seconds % 1) * 10);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}.${ms}`;
  };

  if (!selectedClip) {
    return (
      <div
        className="selected-clip-bar glass-panel"
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0.6rem 1rem',
          borderRadius: '8px',
          background: 'rgba(15, 23, 42, 0.65)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          fontSize: '0.8rem',
          color: 'var(--text-muted)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <span style={{ fontSize: '0.9rem' }}>💡</span>
          <span>Click any timeline slice or transcript take to inspect and remove unwanted clips.</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          {shortClipsCount > 0 && (
            <span
              style={{
                fontSize: '0.725rem',
                color: '#fbbf24',
                background: 'rgba(245, 158, 11, 0.15)',
                border: '1px solid rgba(245, 158, 11, 0.3)',
                padding: '0.2rem 0.5rem',
                borderRadius: '4px',
                display: 'flex',
                alignItems: 'center',
                gap: '0.3rem',
              }}
            >
              <AlertTriangle size={12} />
              {shortClipsCount} micro-clip{shortClipsCount > 1 ? 's' : ''} (&le;2.5s)
            </span>
          )}

          <button
            className="btn btn-outline"
            style={{
              padding: '0.3rem 0.65rem',
              fontSize: '0.75rem',
              borderRadius: '6px',
              borderColor: shortClipsCount > 0 ? 'rgba(168, 85, 247, 0.4)' : 'rgba(255, 255, 255, 0.1)',
              background: shortClipsCount > 0 ? 'rgba(168, 85, 247, 0.1)' : 'transparent',
              color: shortClipsCount > 0 ? '#c084fc' : 'var(--text-muted)',
            }}
            onClick={onCleanShortClips}
            title="Automatically cut all tiny fragmented clips under 2.5 seconds"
          >
            <Sparkles size={13} color="#a855f7" />
            <span>Clean Short Clips (&le;2.5s)</span>
          </button>
        </div>
      </div>
    );
  }

  const isKeep = selectedClip.type === 'keep';
  const isShort = selectedClip.duration <= 3.0;

  return (
    <div
      className="selected-clip-bar glass-panel"
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0.65rem 1rem',
        borderRadius: '8px',
        background: isKeep ? 'rgba(16, 185, 129, 0.08)' : 'rgba(244, 63, 94, 0.08)',
        border: `1px solid ${isKeep ? 'rgba(16, 185, 129, 0.35)' : 'rgba(244, 63, 94, 0.35)'}`,
        boxShadow: `0 0 16px ${isKeep ? 'rgba(16, 185, 129, 0.1)' : 'rgba(244, 63, 94, 0.1)'}`,
      }}
    >
      {/* Left: Clip Info & Metadata */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', minWidth: 0, flex: 1, marginRight: '1rem' }}>
        {/* Type Badge */}
        {isKeep ? (
          <span
            className="badge-tag"
            style={{
              background: 'rgba(16, 185, 129, 0.2)',
              color: '#34d399',
              border: '1px solid rgba(16, 185, 129, 0.4)',
              fontWeight: 700,
              fontSize: '0.72rem',
              whiteSpace: 'nowrap',
            }}
          >
            ✅ KEEP TAKE
          </span>
        ) : (
          <span
            className="badge-tag"
            style={{
              background: 'rgba(244, 63, 94, 0.2)',
              color: '#f87171',
              border: '1px solid rgba(244, 63, 94, 0.4)',
              fontWeight: 700,
              fontSize: '0.72rem',
              whiteSpace: 'nowrap',
            }}
          >
            ✂️ CUT [{(selectedClip.reason || 'cut').toUpperCase()}]
          </span>
        )}

        {/* Duration */}
        <span
          style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: '0.78rem',
            color: '#e2e8f0',
            display: 'flex',
            alignItems: 'center',
            gap: '0.25rem',
            whiteSpace: 'nowrap',
          }}
        >
          <Clock size={12} color="var(--text-muted)" />
          {selectedClip.duration.toFixed(2)}s
        </span>

        {/* Short warning tag if clip <= 3s */}
        {isShort && (
          <span
            style={{
              fontSize: '0.7rem',
              color: '#fbbf24',
              background: 'rgba(245, 158, 11, 0.2)',
              border: '1px solid rgba(245, 158, 11, 0.4)',
              padding: '0.15rem 0.45rem',
              borderRadius: '4px',
              fontWeight: 600,
              whiteSpace: 'nowrap',
            }}
          >
            ⚡ Short clip ({selectedClip.duration.toFixed(1)}s)
          </span>
        )}

        {/* Timecode Range */}
        <span
          style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: '0.75rem',
            color: 'var(--text-muted)',
            whiteSpace: 'nowrap',
          }}
        >
          {formatTime(selectedClip.start)} → {formatTime(selectedClip.end)}
        </span>

        {/* Speech text preview */}
        <span
          style={{
            fontSize: '0.8rem',
            color: 'var(--text-main)',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            flex: 1,
            opacity: 0.9,
          }}
          title={selectedClip.text || selectedClip.explanation}
        >
          "{selectedClip.text || selectedClip.explanation || '[Silence / Dead Air]'}"
        </span>
      </div>

      {/* Right: Actions */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexShrink: 0 }}>
        <button
          className="btn btn-outline"
          style={{
            padding: '0.35rem 0.65rem',
            fontSize: '0.75rem',
            borderRadius: '6px',
          }}
          onClick={() => onPlayClip(selectedClip)}
          title="Play this specific clip"
        >
          <Play size={12} fill="currentColor" />
          <span>Play</span>
        </button>

        {isKeep ? (
          <button
            className="btn btn-primary"
            style={{
              padding: '0.35rem 0.75rem',
              fontSize: '0.75rem',
              borderRadius: '6px',
              background: 'linear-gradient(135deg, #f43f5e, #e11d48)',
              border: 'none',
              color: 'white',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              gap: '0.35rem',
            }}
            onClick={() => onCutClip(selectedClip)}
            title="Remove/cut this clip from the final video (Shortcut: Delete)"
          >
            <Scissors size={13} />
            <span>Cut Clip (Del)</span>
          </button>
        ) : (
          <button
            className="btn btn-primary"
            style={{
              padding: '0.35rem 0.75rem',
              fontSize: '0.75rem',
              borderRadius: '6px',
              background: 'linear-gradient(135deg, #10b981, #059669)',
              border: 'none',
              color: 'white',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              gap: '0.35rem',
            }}
            onClick={() => onRestoreClip(selectedClip)}
            title="Restore this clip so it is kept in the final video"
          >
            <Check size={13} />
            <span>Restore Take</span>
          </button>
        )}

        <button
          className="btn btn-ghost"
          style={{
            padding: '0.35rem 0.45rem',
            borderRadius: '6px',
            color: 'var(--text-dim)',
          }}
          onClick={onDeselect}
          title="Deselect clip (Escape)"
        >
          <X size={14} />
        </button>
      </div>
    </div>
  );
};
