import React, { useRef, useEffect } from 'react';
import { Zap, Film, Scissors, AlertCircle } from 'lucide-react';
import type { CutProposal } from '../types';

interface VideoPlayerProps {
  src: string;
  currentTime: number;
  duration: number;
  autoSkipCuts: boolean;
  cuts: CutProposal[];
  onTimeUpdate: (time: number) => void;
  onDurationChange: (duration: number) => void;
  onToggleAutoSkip: () => void;
}

export const VideoPlayer: React.FC<VideoPlayerProps> = ({
  src,
  currentTime,
  duration,
  autoSkipCuts,
  cuts,
  onTimeUpdate,
  onDurationChange,
  onToggleAutoSkip,
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);

  // Sync external seek time with internal video element
  useEffect(() => {
    if (videoRef.current && Math.abs(videoRef.current.currentTime - currentTime) > 0.3) {
      videoRef.current.currentTime = currentTime;
    }
  }, [currentTime]);

  const activeCut = cuts.find((c) => currentTime >= c.start && currentTime < c.end);

  const handleTimeUpdate = () => {
    if (!videoRef.current) return;
    const cur = videoRef.current.currentTime;
    onTimeUpdate(cur);

    // Smart Auto-Skip: if playing inside a cut region, jump instantly to end of cut!
    if (autoSkipCuts && !videoRef.current.paused) {
      const cut = cuts.find((c) => cur >= c.start && cur < c.end - 0.05);
      if (cut) {
        videoRef.current.currentTime = cut.end;
      }
    }
  };

  const formatTimestamp = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
      {/* View Mode Switcher Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          background: 'rgba(0, 0, 0, 0.3)',
          padding: '0.4rem 0.6rem',
          borderRadius: '8px',
          border: '1px solid var(--card-border)',
        }}
      >
        <div style={{ display: 'flex', gap: '0.4rem' }}>
          <button
            onClick={() => {
              if (!autoSkipCuts) onToggleAutoSkip();
            }}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
              padding: '0.35rem 0.75rem',
              borderRadius: '6px',
              border: 'none',
              cursor: 'pointer',
              fontSize: '0.8rem',
              fontWeight: 600,
              background: autoSkipCuts ? 'var(--accent-primary)' : 'transparent',
              color: autoSkipCuts ? 'white' : 'var(--text-muted)',
              boxShadow: autoSkipCuts ? '0 0 10px var(--accent-glow)' : 'none',
              transition: 'all 0.2s ease',
            }}
          >
            <Scissors size={14} />
            <span>Cut Preview (Clean Takes)</span>
          </button>

          <button
            onClick={() => {
              if (autoSkipCuts) onToggleAutoSkip();
            }}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
              padding: '0.35rem 0.75rem',
              borderRadius: '6px',
              border: 'none',
              cursor: 'pointer',
              fontSize: '0.8rem',
              fontWeight: 600,
              background: !autoSkipCuts ? 'rgba(255, 255, 255, 0.12)' : 'transparent',
              color: !autoSkipCuts ? 'white' : 'var(--text-muted)',
              transition: 'all 0.2s ease',
            }}
          >
            <Film size={14} />
            <span>Original (Uncut)</span>
          </button>
        </div>

        <span
          style={{
            fontSize: '0.78rem',
            color: autoSkipCuts ? 'var(--emerald)' : 'var(--amber)',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            gap: '0.3rem',
          }}
        >
          {autoSkipCuts ? '⚡ Auto-skipping bad takes' : '👁️ Viewing full raw video'}
        </span>
      </div>

      {/* Video Viewport Container */}
      <div
        style={{
          position: 'relative',
          background: '#000000',
          borderRadius: '12px',
          overflow: 'hidden',
          aspectRatio: '16/9',
          boxShadow: '0 12px 36px rgba(0, 0, 0, 0.5)',
        }}
      >
        <video
          ref={videoRef}
          src={src}
          playsInline
          controls
          onTimeUpdate={handleTimeUpdate}
          onLoadedMetadata={() => {
            if (videoRef.current) {
              onDurationChange(videoRef.current.duration);
            }
          }}
          style={{ width: '100%', height: '100%', objectFit: 'contain' }}
        />

        {/* Active Cut Overlay Badge (when watching in Original Uncut mode) */}
        {!autoSkipCuts && activeCut && (
          <div
            style={{
              position: 'absolute',
              top: '12px',
              left: '12px',
              background: 'rgba(239, 68, 68, 0.9)',
              color: 'white',
              padding: '0.4rem 0.75rem',
              borderRadius: '6px',
              fontSize: '0.8rem',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
              backdropFilter: 'blur(8px)',
              boxShadow: '0 4px 16px rgba(0, 0, 0, 0.4)',
              pointerEvents: 'none',
              animation: 'fadeIn 0.2s ease',
            }}
          >
            <AlertCircle size={15} />
            <span>
              [CUT TAKING PLACE: {activeCut.reason.toUpperCase().replace('_', ' ')}]
            </span>
          </div>
        )}
      </div>

      {/* Auto-Skip Toggle & Time Info */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginTop: '0.25rem',
          padding: '0 0.25rem',
        }}
      >
        <label
          style={{
            fontSize: '0.85rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            cursor: 'pointer',
            userSelect: 'none',
          }}
        >
          <input
            type="checkbox"
            checked={autoSkipCuts}
            onChange={onToggleAutoSkip}
            style={{ accentColor: 'var(--accent-primary)', width: 16, height: 16 }}
          />
          <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <Zap size={14} color="var(--amber)" />
            <strong>Smart Auto-Skip:</strong> Jump over bad takes during playback
          </span>
        </label>

        <span
          style={{
            fontFamily: 'JetBrains Mono',
            fontSize: '0.85rem',
            color: 'var(--text-muted)',
          }}
        >
          {formatTimestamp(currentTime)} / {formatTimestamp(duration)}
        </span>
      </div>
    </div>
  );
};
