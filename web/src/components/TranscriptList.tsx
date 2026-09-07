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
  const [filterType, setFilterType] = useState<'all' | 'clean' | 'cuts'>('all');

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
    return { seg, originalIndex, cutMatch, isCut };
  });

  const filteredSegments = analyzedSegments.filter(({ seg, isCut }) => {
    if (filterType === 'clean' && isCut) return false;
    if (filterType === 'cuts' && !isCut) return false;
    if (searchQuery && !seg.text.toLowerCase().includes(searchQuery.toLowerCase())) {
      return false;
    }
    return true;
  });

  const cleanWordCount = analyzedSegments
    .filter((s) => !s.isCut)
    .reduce((sum, s) => sum + s.seg.text.split(/\s+/).filter(Boolean).length, 0);

  return (
    <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Header with Search & View Mode Switcher */}
      <div style={{ padding: '1.25rem', borderBottom: '1px solid var(--card-border)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.85rem' }}>
          <div>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>Transcript & Cuts</h3>
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
                background: filterType === 'all' ? 'var(--accent-primary)' : 'transparent',
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
              <span>Clean Flow</span>
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

        {/* Search Bar */}
        <div style={{ position: 'relative' }}>
          <Search size={14} style={{ position: 'absolute', left: 10, top: 10, color: 'var(--text-dim)' }} />
          <input
            type="text"
            placeholder="Search transcript..."
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
          filteredSegments.map(({ seg, originalIndex, cutMatch, isCut }) => {
            const isActive = currentTime >= seg.start && currentTime < seg.end;
            const isSelected = selectedClip && Math.abs(selectedClip.start - seg.start) < 0.15;

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
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
                  <div>
                    {isCut ? (
                      <span className={`badge-tag badge-${(cutMatch?.reason || 'cut').replace('_', '-')}`}>
                        ✂️ {(cutMatch?.reason || 'cut').replace('_', ' ')}
                      </span>
                    ) : (
                      <span className="badge-tag badge-keep">
                        ✅ Keep
                      </span>
                    )}
                  </div>
                  <span style={{ fontFamily: 'JetBrains Mono', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    {formatTimestamp(seg.start)} → {formatTimestamp(seg.end)}
                  </span>
                </div>

                <p style={{ fontSize: '0.925rem', lineHeight: 1.45, color: isCut ? '#fca5a5' : 'var(--text-main)', marginBottom: '0.6rem' }}>
                  {seg.text}
                </p>

                {cutMatch?.explanation && (
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.5rem', fontStyle: 'italic' }}>
                    💡 {cutMatch.explanation}
                  </p>
                )}

                <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                  <button
                    className="btn btn-outline"
                    style={{
                      padding: '0.25rem 0.6rem',
                      fontSize: '0.75rem',
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
