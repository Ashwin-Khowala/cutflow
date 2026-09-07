import React from 'react';

interface StatsBarProps {
  totalDuration: number;
  cutDuration: number;
  cutsCount: number;
}

export const StatsBar: React.FC<StatsBarProps> = ({
  totalDuration,
  cutDuration,
  cutsCount,
}) => {
  const keptDuration = Math.max(0, totalDuration - cutDuration);
  const savingsPercent = totalDuration > 0 ? ((cutDuration / totalDuration) * 100).toFixed(0) : '0';

  return (
    <div className="stats-grid">
      <div className="stat-item">
        <div className="label">Original</div>
        <div className="value">{totalDuration.toFixed(1)}s</div>
      </div>

      <div className="stat-item">
        <div className="label">Clean Video</div>
        <div className="value" style={{ color: 'var(--emerald)' }}>
          {keptDuration.toFixed(1)}s
        </div>
      </div>

      <div className="stat-item">
        <div className="label">Time Saved</div>
        <div className="value" style={{ color: 'var(--amber)' }}>
          {cutDuration.toFixed(1)}s ({savingsPercent}%)
        </div>
      </div>

      <div className="stat-item">
        <div className="label">Cuts Detected</div>
        <div className="value" style={{ color: '#818cf8' }}>
          {cutsCount}
        </div>
      </div>
    </div>
  );
};
