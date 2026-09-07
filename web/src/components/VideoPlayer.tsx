import { useRef, useEffect, useState, forwardRef, useImperativeHandle } from 'react';
import { Zap, Film, Scissors, AlertCircle, Maximize2, Minimize2, Tv } from 'lucide-react';
import type { CutProposal } from '../types';

export interface VideoPlayerHandle {
  play: () => void;
  pause: () => void;
  togglePlay: () => void;
  seekRelative: (seconds: number) => void;
  seekTo: (time: number) => void;
  toggleMute: () => void;
  toggleFullscreen: () => void;
  isPlaying: () => boolean;
}

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

export type PlayerSizeMode = 'compact' | 'standard' | 'expanded';

export const VideoPlayer = forwardRef<VideoPlayerHandle, VideoPlayerProps>(({
  src,
  currentTime,
  duration,
  autoSkipCuts,
  cuts,
  onTimeUpdate,
  onDurationChange,
  onToggleAutoSkip,
}, ref) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [sizeMode, setSizeMode] = useState<PlayerSizeMode>(() => {
    return (localStorage.getItem('cutflow_player_size') as PlayerSizeMode) || 'standard';
  });

  const handleSetSizeMode = (mode: PlayerSizeMode) => {
    setSizeMode(mode);
    localStorage.setItem('cutflow_player_size', mode);
  };

  // Expose imperative playback controls to parent component for keyboard shortcuts
  useImperativeHandle(ref, () => ({
    play: () => {
      videoRef.current?.play().catch(() => {});
    },
    pause: () => {
      videoRef.current?.pause();
    },
    togglePlay: () => {
      if (!videoRef.current) return;
      if (videoRef.current.paused) {
        videoRef.current.play().catch(() => {});
      } else {
        videoRef.current.pause();
      }
    },
    seekRelative: (seconds: number) => {
      if (!videoRef.current) return;
      const target = Math.max(0, Math.min(videoRef.current.duration || 0, videoRef.current.currentTime + seconds));
      videoRef.current.currentTime = target;
      onTimeUpdate(target);
    },
    seekTo: (time: number) => {
      if (!videoRef.current) return;
      const target = Math.max(0, Math.min(videoRef.current.duration || 0, time));
      videoRef.current.currentTime = target;
      onTimeUpdate(target);
    },
    toggleMute: () => {
      if (videoRef.current) {
        videoRef.current.muted = !videoRef.current.muted;
      }
    },
    toggleFullscreen: () => {
      if (!videoRef.current) return;
      if (document.fullscreenElement) {
        document.exitFullscreen().catch(() => {});
      } else {
        videoRef.current.requestFullscreen().catch(() => {});
      }
    },
    isPlaying: () => {
      return !!videoRef.current && !videoRef.current.paused;
    },
  }));

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

  // Height limits based on size mode to strictly prevent ballooning/zooming
  const heightLimits = {
    compact: 'min(34vh, 290px)',
    standard: 'min(42vh, 370px)',
    expanded: 'min(52vh, 470px)',
  };

  const currentMaxHeight = heightLimits[sizeMode];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
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

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
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

          {/* Size Mode Switcher */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              background: 'rgba(255, 255, 255, 0.04)',
              borderRadius: '6px',
              padding: '2px',
              border: '1px solid rgba(255, 255, 255, 0.08)',
            }}
            title="Video Preview Window Size"
          >
            <button
              onClick={() => handleSetSizeMode('compact')}
              title="Compact Preview (300px)"
              style={{
                background: sizeMode === 'compact' ? 'rgba(255, 255, 255, 0.15)' : 'transparent',
                border: 'none',
                color: sizeMode === 'compact' ? '#ffffff' : '#94a3b8',
                borderRadius: '4px',
                padding: '3px 6px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
              }}
            >
              <Minimize2 size={13} />
            </button>
            <button
              onClick={() => handleSetSizeMode('standard')}
              title="Standard Preview (380px)"
              style={{
                background: sizeMode === 'standard' ? 'rgba(255, 255, 255, 0.15)' : 'transparent',
                border: 'none',
                color: sizeMode === 'standard' ? '#ffffff' : '#94a3b8',
                borderRadius: '4px',
                padding: '3px 6px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
              }}
            >
              <Tv size={13} />
            </button>
            <button
              onClick={() => handleSetSizeMode('expanded')}
              title="Expanded Preview (480px)"
              style={{
                background: sizeMode === 'expanded' ? 'rgba(255, 255, 255, 0.15)' : 'transparent',
                border: 'none',
                color: sizeMode === 'expanded' ? '#ffffff' : '#94a3b8',
                borderRadius: '4px',
                padding: '3px 6px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
              }}
            >
              <Maximize2 size={13} />
            </button>
          </div>
        </div>
      </div>

      {/* Video Viewport Container — constrained height to avoid sudden zoom/ballooning */}
      <div
        style={{
          position: 'relative',
          background: '#000000',
          borderRadius: '12px',
          overflow: 'hidden',
          width: '100%',
          height: currentMaxHeight,
          maxHeight: currentMaxHeight,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 12px 36px rgba(0, 0, 0, 0.5)',
          transition: 'height 0.2s ease, max-height 0.2s ease',
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
          style={{
            width: '100%',
            height: '100%',
            maxHeight: currentMaxHeight,
            objectFit: 'contain',
          }}
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

      {/* Auto-Skip Toggle & Time Info & Keyboard Hint */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginTop: '0.15rem',
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
            <span
              style={{
                fontSize: '0.7rem',
                color: '#94a3b8',
                background: 'rgba(255,255,255,0.06)',
                padding: '1px 5px',
                borderRadius: '4px',
                fontFamily: 'monospace',
                marginLeft: '4px',
              }}
            >
              A
            </span>
          </span>
        </label>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span
            style={{
              fontSize: '0.72rem',
              color: '#64748b',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}
          >
            <span>Play/Pause:</span>
            <kbd style={{ background: 'rgba(255,255,255,0.08)', padding: '1px 4px', borderRadius: '3px', fontFamily: 'monospace' }}>Space</kbd>
            <span style={{ marginLeft: 4 }}>Cut:</span>
            <kbd style={{ background: 'rgba(255,255,255,0.08)', padding: '1px 4px', borderRadius: '3px', fontFamily: 'monospace' }}>C</kbd>
          </span>

          <span
            style={{
              fontFamily: 'JetBrains Mono',
              fontSize: '0.85rem',
              color: 'var(--text-muted)',
              fontWeight: 500,
            }}
          >
            {formatTimestamp(currentTime)} / {formatTimestamp(duration)}
          </span>
        </div>
      </div>
    </div>
  );
});

VideoPlayer.displayName = 'VideoPlayer';
