import React, { useState } from 'react';
import type { CutProposal, KeepRegion, SilenceRegion } from '../types';
import { Waveform } from './Waveform';

interface TimelineProps {
  duration: number;
  currentTime: number;
  keeps: KeepRegion[];
  cuts: CutProposal[];
  silences?: SilenceRegion[];
  onSeek: (time: number) => void;
}

export const Timeline: React.FC<TimelineProps> = ({
  duration,
  currentTime,
  keeps,
  cuts,
  silences = [],
  onSeek,
}) => {
  const [hoverTime, setHoverTime] = useState<number | null>(null);
  const [hoverX, setHoverX] = useState<number>(0);

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = Math.max(0, Math.min(e.clientX - rect.left, rect.width));
    const percentage = x / rect.width;
    setHoverTime(percentage * duration);
    setHoverX(x);
  };

  const handleMouseLeave = () => {
    setHoverTime(null);
  };

  const handleTimelineClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const percentage = Math.max(0, Math.min(1, clickX / rect.width));
    onSeek(percentage * duration);
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    const ms = Math.floor((seconds % 1) * 10);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}.${ms}`;
  };

  const progressPercent = duration > 0 ? (currentTime / duration) * 100 : 0;

  // Generate ruler tick marks
  const tickInterval = duration > 120 ? 15 : (duration > 60 ? 10 : 5);
  const ticksCount = Math.floor(duration / tickInterval);
  const ticks = Array.from({ length: ticksCount + 1 }, (_, i) => i * tickInterval);

  return (
    <div
      className="multi-track-timeline"
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '0.4rem',
        background: 'rgba(10, 14, 23, 0.95)',
        border: '1px solid rgba(255, 255, 255, 0.08)',
        borderRadius: '10px',
        padding: '0.75rem',
        position: 'relative',
        userSelect: 'none',
      }}
    >
      {/* Timecode Ruler */}
      <div
        className="timeline-ruler"
        style={{
          height: '20px',
          position: 'relative',
          borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
          fontSize: '0.68rem',
          fontFamily: 'JetBrains Mono, monospace',
          color: '#64748b',
        }}
      >
        {ticks.map((t) => {
          const leftPercent = duration > 0 ? (t / duration) * 100 : 0;
          return (
            <div
              key={`tick-${t}`}
              style={{
                position: 'absolute',
                left: `${leftPercent}%`,
                transform: 'translateX(-50%)',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
              }}
            >
              <span>{formatTime(t)}</span>
              <div style={{ width: '1px', height: '4px', background: 'rgba(255,255,255,0.2)', marginTop: '2px' }} />
            </div>
          );
        })}
      </div>

      {/* Main Track Area */}
      <div
        className="timeline-track-wrapper"
        onClick={handleTimelineClick}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
        style={{
          position: 'relative',
          cursor: 'pointer',
          borderRadius: '6px',
          overflow: 'hidden',
        }}
      >
        {/* Track 1: Visual Segment Blocks */}
        <div
          className="timeline-track segments-track"
          style={{
            height: '24px',
            position: 'relative',
            background: 'rgba(255, 255, 255, 0.03)',
            borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
          }}
        >
          {/* Keep Slices (Green) */}
          {keeps.map((k, idx) => {
            const left = duration > 0 ? (k.start / duration) * 100 : 0;
            const width = duration > 0 ? ((k.end - k.start) / duration) * 100 : 0;
            return (
              <div
                key={`keep-${idx}`}
                className="timeline-slice keep"
                style={{
                  position: 'absolute',
                  left: `${left}%`,
                  width: `${width}%`,
                  height: '100%',
                  background: 'rgba(16, 185, 129, 0.45)',
                  borderLeft: '1px solid rgba(16, 185, 129, 0.8)',
                  borderRight: '1px solid rgba(16, 185, 129, 0.8)',
                }}
                title={`Keep Take: ${k.start.toFixed(1)}s → ${k.end.toFixed(1)}s: ${k.text}`}
              />
            );
          })}

          {/* Cut Slices (Red/Rose) */}
          {cuts.map((c, idx) => {
            if (c.action === 'keep') return null;
            const left = duration > 0 ? (c.start / duration) * 100 : 0;
            const width = duration > 0 ? ((c.end - c.start) / duration) * 100 : 0;
            return (
              <div
                key={`cut-${idx}`}
                className="timeline-slice cut"
                style={{
                  position: 'absolute',
                  left: `${left}%`,
                  width: `${width}%`,
                  height: '100%',
                  background: 'rgba(244, 63, 94, 0.55)',
                  borderLeft: '1px solid rgba(244, 63, 94, 0.9)',
                  borderRight: '1px solid rgba(244, 63, 94, 0.9)',
                }}
                title={`Cut [${c.reason}]: ${c.start.toFixed(1)}s → ${c.end.toFixed(1)}s: ${c.text || c.explanation}`}
              />
            );
          })}
        </div>

        {/* Track 2: Audio Waveform */}
        <Waveform
          duration={duration}
          currentTime={currentTime}
          cuts={cuts}
          silences={silences}
          onSeek={onSeek}
          height={48}
        />

        {/* Playhead Needle spanning both tracks */}
        <div
          className="timeline-needle"
          style={{
            position: 'absolute',
            top: 0,
            bottom: 0,
            left: `${progressPercent}%`,
            width: '2px',
            background: '#ffffff',
            boxShadow: '0 0 8px rgba(255, 255, 255, 0.9)',
            pointerEvents: 'none',
            zIndex: 10,
          }}
        >
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: '-4px',
              width: '10px',
              height: '10px',
              background: '#6366f1',
              borderRadius: '50%',
              boxShadow: '0 0 6px #6366f1',
            }}
          />
        </div>

        {/* Hover Timecode Tooltip */}
        {hoverTime !== null && (
          <div
            style={{
              position: 'absolute',
              top: '4px',
              left: `${hoverX}px`,
              transform: 'translateX(-50%)',
              background: 'rgba(15, 23, 42, 0.9)',
              border: '1px solid rgba(255, 255, 255, 0.2)',
              borderRadius: '4px',
              padding: '2px 6px',
              fontSize: '0.68rem',
              fontFamily: 'JetBrains Mono, monospace',
              color: '#38bdf8',
              pointerEvents: 'none',
              zIndex: 20,
            }}
          >
            {formatTime(hoverTime)}
          </div>
        )}
      </div>
    </div>
  );
};
