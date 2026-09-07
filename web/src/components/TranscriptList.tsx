import React, { useState } from 'react';
import type { Segment, CutProposal, SelectedClip } from '../types';
import { Check, X, Search, FileText, Scissors, ListFilter } from 'lucide-react';

interface TranscriptListProps {
  segments: Segment[];
  cuts: CutProposal[];
  currentTime: number;
  selectedClip?: SelectedClip | null;
  onSeek: (time: number) => void;
  onToggleCut: (segmentIndex: number) => void;
  onSelectClip?: (clip: SelectedClip | null) => void;
}

export const TranscriptList: React.FC<TranscriptListProps> = ({
  segments,
  cuts,
  currentTime,
  selectedClip,
  onSeek,
  onToggleCut,
  onSelectClip,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState<'diff' | 'all' | 'clean' | 'cuts'>('diff');

  const formatTimestamp = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const analyzedSegments = segments.map((seg, originalIndex) => {
    const cutMatch = cuts.find(
      (c) => seg.start >= c.start - 0.1 && seg.end <= c.end + 0.5
    );
    const isCut = !!cutMatch;
    const duration = Math.max(0.1, seg.end - seg.start);
    return { seg, originalIndex, cutMatch, isCut, duration };
  });

  const filteredSegments = analyzedSegments.filter(({ seg, isCut }) => {
    if (filterType === 'clean' && isCut) return false;
    if (filterType === 'cuts' && !isCut) return false;
    if (searchQuery && !seg.text.toLowerCase().includes(searchQuery.toLowerCase())) {
      return false;
    }
    return true;
  });

  const keptSegments = analyzedSegments.filter((s) => !s.isCut);
  const cutSegments = analyzedSegments.filter((s) => s.isCut);

  const keptSec = keptSegments.reduce((sum, s) => sum + s.duration, 0);
  const cutSec = cutSegments.reduce((sum, s) => sum + s.duration, 0);
  const totalSec = keptSec + cutSec;
  const savingsPercent = totalSec > 0 ? Math.round((cutSec / totalSec) * 100) : 0;

  const cleanWordCount = keptSegments.reduce(
    (sum, s) => sum + s.seg.text.split(/\s+/).filter(Boolean).length,
    0
  );
  const cutWordCount = cutSegments.reduce(
    (sum, s) => sum + s.seg.text.split(/\s+/).filter(Boolean).length,
    0
  );

  return (
    <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Header with Search & View Mode Switcher */}
      <div style={{ padding: '1.1rem 1.25rem', borderBottom: '1px solid var(--card-border)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
          <div>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <span>Transcript & Cuts</span>
              {filterType === 'diff' && (
                <span
                  style={{
                    fontSize: '0.65rem',
                    background: 'rgba(99, 102, 241, 0.2)',
                    border: '1px solid rgba(99, 102, 241, 0.4)',
                    color: '#a5b4fc',
                    padding: '1px 6px',
                    borderRadius: '10px',
                    fontWeight: 600,
                  }}
                >
                  Diff Mode
                </span>
              )}
            </h3>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.15rem' }}>
              {cuts.length} cuts planned • {cleanWordCount} words in clean take
            </p>
          </div>

          {/* Quick View Filter Pills */}
          <div
            style={{
              display: 'flex',
              background: 'rgba(0, 0, 0, 0.4)',
              padding: '0.2rem',
              borderRadius: '8px',
              border: '1px solid var(--card-border)',
            }}
          >
            <button
              onClick={() => setFilterType('diff')}
              title="View unified script diff with keeps and pruned takes"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.3rem',
                padding: '0.3rem 0.6rem',
                borderRadius: '6px',
                border: 'none',
                cursor: 'pointer',
                fontSize: '0.75rem',
                fontWeight: 600,
                background: filterType === 'diff' ? 'var(--accent-gradient)' : 'transparent',
                color: filterType === 'diff' ? 'white' : 'var(--text-muted)',
                boxShadow: filterType === 'diff' ? '0 2px 8px var(--accent-glow)' : 'none',
              }}
            >
              <span>⚡ Diff</span>
            </button>

            <button
              onClick={() => setFilterType('all')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.3rem',
                padding: '0.3rem 0.6rem',
                borderRadius: '6px',
                border: 'none',
                cursor: 'pointer',
                fontSize: '0.75rem',
                fontWeight: 600,
                background: filterType === 'all' ? 'rgba(255, 255, 255, 0.15)' : 'transparent',
                color: filterType === 'all' ? 'white' : 'var(--text-muted)',
              }}
            >
              <ListFilter size={12} />
              <span>All</span>
            </button>

            <button
              onClick={() => setFilterType('clean')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.3rem',
                padding: '0.3rem 0.6rem',
                borderRadius: '6px',
                border: 'none',
                cursor: 'pointer',
                fontSize: '0.75rem',
                fontWeight: 600,
                background: filterType === 'clean' ? 'var(--emerald)' : 'transparent',
                color: filterType === 'clean' ? 'white' : 'var(--text-muted)',
              }}
            >
              <FileText size={12} />
              <span>Clean</span>
            </button>

            <button
              onClick={() => setFilterType('cuts')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.3rem',
                padding: '0.3rem 0.6rem',
                borderRadius: '6px',
                border: 'none',
                cursor: 'pointer',
                fontSize: '0.75rem',
                fontWeight: 600,
                background: filterType === 'cuts' ? 'var(--rose)' : 'transparent',
                color: filterType === 'cuts' ? 'white' : 'var(--text-muted)',
              }}
            >
              <Scissors size={12} />
              <span>Cuts ({cuts.length})</span>
            </button>
          </div>
        </div>

        {/* Diff Metrics Banner */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'rgba(0, 0, 0, 0.3)',
            border: '1px solid rgba(255, 255, 255, 0.05)',
            borderRadius: '6px',
            padding: '0.4rem 0.6rem',
            marginBottom: '0.75rem',
            fontSize: '0.72rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ color: '#34d399', fontWeight: 600 }}>
              + {keptSec.toFixed(1)}s kept ({keptSegments.length} takes)
            </span>
            <span style={{ color: '#64748b' }}>•</span>
            <span style={{ color: '#fb7185', fontWeight: 600 }}>
              - {cutSec.toFixed(1)}s cuts ({cutSegments.length})
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <span style={{ color: '#38bdf8', fontWeight: 600 }}>
              📉 {savingsPercent}% trimmed
            </span>
            {cutWordCount > 0 && (
              <span style={{ color: '#64748b' }}>
                (-{cutWordCount} words)
              </span>
            )}
          </div>
        </div>

        {/* Search Bar */}
        <div style={{ position: 'relative' }}>
          <Search size={14} style={{ position: 'absolute', left: 10, top: 10, color: 'var(--text-dim)' }} />
          <input
            type="text"
            placeholder="Search transcript or cut words..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              width: '100%',
              padding: '0.45rem 0.6rem 0.45rem 2rem',
              borderRadius: '6px',
              border: '1px solid var(--card-border)',
              background: 'rgba(0, 0, 0, 0.3)',
              color: 'white',
              fontSize: '0.825rem',
            }}
          />
        </div>
      </div>

      {/* Segment Cards List */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '1rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '0.75rem',
        }}
      >
        {filteredSegments.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '3rem 1rem', color: 'var(--text-dim)', fontSize: '0.9rem' }}>
            No segments match your filter.
          </div>
        ) : (
          filteredSegments.map(({ seg, originalIndex, cutMatch, isCut, duration }, listIndex) => {
            const isActive = currentTime >= seg.start && currentTime < seg.end;
            const isSelected = selectedClip && Math.abs(selectedClip.start - seg.start) < 0.15;
            
            // Check if previous segment was a cut repetition/false_start
            const prevSegment = listIndex > 0 ? filteredSegments[listIndex - 1] : null;
            const isFollowUpToCut = !isCut && prevSegment && prevSegment.isCut && 
              ['repetition', 'false_start'].includes(prevSegment.cutMatch?.reason || '');

            return (
              <div
                key={`seg-${originalIndex}`}
                className={`segment-card ${isCut ? 'is-cut' : 'is-keep'} ${isActive ? 'is-active' : ''} ${isSelected ? 'is-selected' : ''}`}
                onClick={() => {
                  onSeek(seg.start);
                  onSelectClip?.({
                    id: `seg-${originalIndex}`,
                    type: isCut ? 'cut' : 'keep',
                    start: seg.start,
                    end: seg.end,
                    duration: seg.end - seg.start,
                    text: seg.text,
                    reason: cutMatch?.reason,
                    explanation: cutMatch?.explanation,
                    originalIndex,
                  });
                }}
                style={{
                  cursor: 'pointer',
                  border: isSelected ? '1px solid #a855f7' : undefined,
                  boxShadow: isSelected ? '0 0 10px rgba(168, 85, 247, 0.4)' : undefined,
                  borderLeftWidth: '4px',
                  borderLeftColor: isCut ? 'var(--rose)' : 'var(--emerald)',
                  background: isCut ? 'rgba(244, 63, 94, 0.07)' : 'rgba(255, 255, 255, 0.02)',
                }}
              >
                {/* Take Header with Diff Status */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.45rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
                    <span style={{ fontSize: '0.68rem', fontFamily: 'JetBrains Mono', color: '#64748b' }}>
                      #{originalIndex + 1}
                    </span>

                    {isCut ? (
                      <>
                        <span
                          style={{
                            fontFamily: 'JetBrains Mono',
                            fontSize: '0.68rem',
                            fontWeight: 700,
                            padding: '1px 5px',
                            borderRadius: '4px',
                            background: 'rgba(244, 63, 94, 0.25)',
                            color: '#fb7185',
                          }}
                        >
                          - CUT ({duration.toFixed(1)}s)
                        </span>
                        <span className={`badge-tag badge-${(cutMatch?.reason || 'cut').replace('_', '-')}`}>
                          ✂️ {(cutMatch?.reason || 'cut').replace('_', ' ')}
                        </span>
                      </>
                    ) : (
                      <>
                        <span
                          style={{
                            fontFamily: 'JetBrains Mono',
                            fontSize: '0.68rem',
                            fontWeight: 700,
                            padding: '1px 5px',
                            borderRadius: '4px',
                            background: 'rgba(16, 185, 129, 0.25)',
                            color: '#34d399',
                          }}
                        >
                          + KEEP ({duration.toFixed(1)}s)
                        </span>
                        {isFollowUpToCut && (
                          <span
                            style={{
                              fontSize: '0.65rem',
                              padding: '1px 5px',
                              borderRadius: '4px',
                              background: 'rgba(99, 102, 241, 0.2)',
                              color: '#a5b4fc',
                              fontWeight: 600,
                            }}
                          >
                            🔁 Final Kept Take
                          </span>
                        )}
                      </>
                    )}
                  </div>

                  <span style={{ fontFamily: 'JetBrains Mono', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                    {formatTimestamp(seg.start)} → {formatTimestamp(seg.end)}
                  </span>
                </div>

                {/* Transcript Script Text */}
                <p
                  style={{
                    fontSize: '0.9rem',
                    lineHeight: 1.45,
                    color: isCut ? '#fca5a5' : 'var(--text-main)',
                    textDecoration: isCut ? 'line-through' : 'none',
                    opacity: isCut ? 0.78 : 1,
                    marginBottom: '0.5rem',
                  }}
                >
                  {seg.text}
                </p>

                {cutMatch?.explanation && (
                  <p style={{ fontSize: '0.73rem', color: '#cbd5e1', marginBottom: '0.5rem', fontStyle: 'italic', background: 'rgba(0,0,0,0.25)', padding: '0.3rem 0.5rem', borderRadius: '4px' }}>
                    💡 {cutMatch.explanation}
                  </p>
                )}

                {/* Quick Action Footer */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.4rem' }}>
                  <span style={{ fontSize: '0.68rem', color: '#64748b' }}>
                    Click to seek • Press <kbd className="kbd-badge">{isCut ? 'R' : 'C'}</kbd> to toggle
                  </span>

                  <button
                    className="btn btn-outline"
                    style={{
                      padding: '0.2rem 0.55rem',
                      fontSize: '0.72rem',
                      borderRadius: '4px',
                    }}
                    onClick={(e) => {
                      e.stopPropagation();
                      onToggleCut(originalIndex);
                    }}
                  >
                    {isCut ? (
                      <>
                        <Check size={12} color="var(--emerald)" />
                        <span>Restore Take</span>
                      </>
                    ) : (
                      <>
                        <X size={12} color="var(--rose)" />
                        <span>Cut Take</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
