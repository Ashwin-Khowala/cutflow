import React, { useRef, useEffect } from 'react';
import type { CutProposal, SilenceRegion } from '../types';

interface WaveformProps {
  duration: number;
  currentTime: number;
  cuts: CutProposal[];
  silences: SilenceRegion[];
  onSeek: (time: number) => void;
  height?: number;
}

export const Waveform: React.FC<WaveformProps> = ({
  duration,
  currentTime,
  cuts,
  silences,
  onSeek,
  height = 56,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || duration <= 0) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const isCutAt = (t: number) => {
      return cuts.some((c) => (c.action === 'cut' || !c.action) && t >= c.start && t <= c.end);
    };

    const isSilenceAt = (t: number) => {
      return silences.some((s) => t >= s.start && t <= s.end);
    };

    // Handle high-DPI displays
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = height * dpr;
    ctx.scale(dpr, dpr);

    const width = rect.width;
    const barsCount = Math.floor(width / 3.5);
    const barWidth = 2;
    const barGap = 1.5;
    const centerY = height / 2;

    ctx.clearRect(0, 0, width, height);

    // Draw waveform bars
    for (let i = 0; i < barsCount; i++) {
      const progress = i / barsCount;
      const t = progress * duration;
      const x = i * (barWidth + barGap);

      // Generate realistic waveform pattern using harmonic pseudo-randomness
      const baseAmp = Math.sin(progress * 48) * 0.35 + Math.cos(progress * 19) * 0.25;
      const noise = (Math.sin(i * 12.9898 + 78.233) * 43758.5453) % 1;
      let amplitude = Math.abs(baseAmp * 0.6 + noise * 0.4);

      const inSilence = isSilenceAt(t);
      const inCut = isCutAt(t);

      if (inSilence) {
        amplitude = 0.08;
      }

      const barHeight = Math.max(3, amplitude * (height - 12));

      // Color coding based on status
      if (inCut) {
        ctx.fillStyle = 'rgba(244, 63, 94, 0.7)'; // Rose for cut
      } else if (inSilence) {
        ctx.fillStyle = 'rgba(100, 116, 139, 0.35)'; // Slate for silence
      } else {
        ctx.fillStyle = 'rgba(16, 185, 129, 0.75)'; // Emerald for keep
      }

      // Draw rounded bar
      ctx.beginPath();
      ctx.roundRect(x, centerY - barHeight / 2, barWidth, barHeight, 1);
      ctx.fill();
    }

    // Draw playhead position
    if (duration > 0) {
      const playheadX = (currentTime / duration) * width;
      ctx.fillStyle = '#ffffff';
      ctx.shadowColor = 'rgba(255, 255, 255, 0.8)';
      ctx.shadowBlur = 6;
      ctx.fillRect(playheadX - 1, 0, 2, height);
      ctx.shadowBlur = 0;
    }
  }, [duration, currentTime, cuts, silences, height]);

  const handleClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas || duration <= 0) return;
    const rect = canvas.getBoundingClientRect();
    const x = Math.max(0, Math.min(e.clientX - rect.left, rect.width));
    const seekTime = (x / rect.width) * duration;
    onSeek(seekTime);
  };

  return (
    <div className="waveform-container" style={{ width: '100%', position: 'relative', cursor: 'pointer' }}>
      <canvas
        ref={canvasRef}
        onClick={handleClick}
        style={{
          width: '100%',
          height: `${height}px`,
          display: 'block',
          borderRadius: '4px',
          background: 'rgba(0, 0, 0, 0.25)',
        }}
      />
    </div>
  );
};
