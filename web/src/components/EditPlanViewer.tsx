import React, { useState } from 'react';
import type { EditPlan, ProjectData, CutProposal, TimelineEntry } from '../types';
import { getExportEdlUrl } from '../api/client';

interface DiffEvent {
  id: string;
  type: 'keep' | 'cut';
  start: number;
  end: number;
  duration: number;
  text?: string;
  reason?: string;
  explanation?: string;
  cleanStart?: number;
  cleanEnd?: number;
}

interface EditPlanViewerProps {
  isOpen: boolean;
  onClose: () => void;
  project: ProjectData;
}

export const EditPlanViewer: React.FC<EditPlanViewerProps> = ({
  isOpen,
  onClose,
  project,
}) => {
  const [activeTab, setActiveTab] = useState<'diff' | 'timeline' | 'json'>('diff');
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  // Generate fallback plan if project.edit_plan is not yet populated
  const plan: EditPlan = project.edit_plan || {
    version: '1.0',
    project_id: project.id,
    source_video: project.video_filename,
    source_duration: project.transcript?.duration || 0,
    stats: {
      original_duration: project.analysis?.total_duration || 0,
      clean_duration: project.analysis?.kept_duration || 0,
      time_saved: project.analysis?.cut_duration || 0,
      savings_percent: project.analysis?.savings_percent || 0,
      cuts_count: project.analysis?.cuts?.length || 0,
      keeps_count: project.analysis?.keeps?.length || 0,
    },
    timeline: (project.analysis?.cuts || []).map((c: CutProposal, i: number) => ({
      id: `cut_${i}`,
      start: c.start,
      end: c.end,
      duration: (c.end - c.start),
      type: 'cut',
      action: c.action || 'cut',
      text: c.text,
      reason: c.reason,
      confidence: c.confidence,
    })),
    metadata: {
      generator: 'CutFlow Engine v0.2.0',
      created_at: new Date().toISOString(),
    },
  };

  const jsonString = JSON.stringify(plan, null, 2);

  // Compile chronological Diff events (Original Timeline vs Clean Cut)
  let cumulativeClean = 0;
  const rawKeeps: DiffEvent[] = (project.analysis?.keeps || []).map((k: any, i: number) => ({
    id: `keep_${i}`,
    type: 'keep',
    start: k.start,
    end: k.end,
    duration: k.end - k.start,
    text: k.text,
  }));

  const rawCuts: DiffEvent[] = (project.analysis?.cuts || []).map((c: any, i: number) => ({
    id: `cut_${i}`,
    type: 'cut',
    start: c.start,
    end: c.end,
    duration: c.end - c.start,
    text: c.text,
    reason: c.reason,
    explanation: c.explanation,
  }));

  const sortedEvents = [...rawKeeps, ...rawCuts].sort((a, b) => a.start - b.start);
  const diffEvents: DiffEvent[] = sortedEvents.map((ev) => {
    if (ev.type === 'keep') {
      const cleanStart = cumulativeClean;
      const cleanEnd = cumulativeClean + ev.duration;
      cumulativeClean += ev.duration;
      return { ...ev, cleanStart, cleanEnd };
    }
    return ev;
  });

  const handleCopy = () => {
    navigator.clipboard.writeText(jsonString);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadJson = () => {
    const blob = new Blob([jsonString], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `cutflow_plan_${project.id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleDownloadEdl = async () => {
    try {
      const edlUrl = getExportEdlUrl(project.id);
      const res = await fetch(edlUrl);
      if (!res.ok) throw new Error('EDL generation failed');
      const text = await res.text();
      const blob = new Blob([text], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `cutflow_${project.id}.edl`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      alert('Could not download EDL. Ensure the project is analyzed.');
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose} style={{ zIndex: 999 }}>
      <div
        className="modal-card edit-plan-modal"
        onClick={(e) => e.stopPropagation()}
        style={{
          width: '92%',
          maxWidth: '960px',
          maxHeight: '88vh',
          display: 'flex',
          flexDirection: 'column',
          background: '#0d1117',
          border: '1px solid rgba(255, 255, 255, 0.1)',
          borderRadius: '14px',
          padding: '1.5rem',
          boxShadow: '0 24px 60px rgba(0, 0, 0, 0.8)',
        }}
      >
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div
              style={{
                width: '34px',
                height: '34px',
                borderRadius: '8px',
                background: 'linear-gradient(135deg, #6366f1, #06b6d4)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#fff',
                fontSize: '1rem',
              }}
            >
              📄
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: '1.15rem', color: '#f8fafc', fontWeight: 600 }}>
                CutFlow Edit Plan & Diff Inspector
              </h3>
              <p style={{ margin: 0, fontSize: '0.8rem', color: '#94a3b8' }}>
                Universal Intermediate Representation IR • Version {plan.version}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#94a3b8',
              cursor: 'pointer',
              fontSize: '1.25rem',
              padding: '4px 8px',
            }}
          >
            ✕
          </button>
        </div>

        {/* Stats Row */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(4, 1fr)',
            gap: '0.75rem',
            marginBottom: '1.25rem',
          }}
        >
          <div style={{ background: 'rgba(255,255,255,0.03)', padding: '0.75rem', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.06)' }}>
            <div style={{ fontSize: '0.7rem', color: '#64748b', textTransform: 'uppercase' }}>Original Duration</div>
            <div style={{ fontSize: '1.1rem', fontWeight: 600, color: '#f8fafc', fontFamily: 'JetBrains Mono, monospace' }}>
              {plan.stats.original_duration.toFixed(1)}s
            </div>
          </div>
          <div style={{ background: 'rgba(255,255,255,0.03)', padding: '0.75rem', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.06)' }}>
            <div style={{ fontSize: '0.7rem', color: '#64748b', textTransform: 'uppercase' }}>Clean Duration</div>
            <div style={{ fontSize: '1.1rem', fontWeight: 600, color: '#10b981', fontFamily: 'JetBrains Mono, monospace' }}>
              {plan.stats.clean_duration.toFixed(1)}s
            </div>
          </div>
          <div style={{ background: 'rgba(255,255,255,0.03)', padding: '0.75rem', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.06)' }}>
            <div style={{ fontSize: '0.7rem', color: '#64748b', textTransform: 'uppercase' }}>Time Saved (Delta)</div>
            <div style={{ fontSize: '1.1rem', fontWeight: 600, color: '#6366f1', fontFamily: 'JetBrains Mono, monospace' }}>
              -{plan.stats.time_saved.toFixed(1)}s ({plan.stats.savings_percent.toFixed(0)}%)
            </div>
          </div>
          <div style={{ background: 'rgba(255,255,255,0.03)', padding: '0.75rem', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.06)' }}>
            <div style={{ fontSize: '0.7rem', color: '#64748b', textTransform: 'uppercase' }}>Total Cuts</div>
            <div style={{ fontSize: '1.1rem', fontWeight: 600, color: '#f43f5e', fontFamily: 'JetBrains Mono, monospace' }}>
              {plan.stats.cuts_count}
            </div>
          </div>
        </div>

        {/* Tab Selection */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button
              onClick={() => setActiveTab('diff')}
              style={{
                background: activeTab === 'diff' ? 'rgba(99, 102, 241, 0.2)' : 'transparent',
                border: activeTab === 'diff' ? '1px solid #6366f1' : '1px solid transparent',
                color: activeTab === 'diff' ? '#a5b4fc' : '#94a3b8',
                borderRadius: '6px',
                padding: '6px 12px',
                fontSize: '0.8rem',
                cursor: 'pointer',
                fontWeight: 600,
              }}
            >
              ⚡ Diff Inspector ({diffEvents.length} events)
            </button>
            <button
              onClick={() => setActiveTab('timeline')}
              style={{
                background: activeTab === 'timeline' ? 'rgba(99, 102, 241, 0.2)' : 'transparent',
                border: activeTab === 'timeline' ? '1px solid #6366f1' : '1px solid transparent',
                color: activeTab === 'timeline' ? '#a5b4fc' : '#94a3b8',
                borderRadius: '6px',
                padding: '6px 12px',
                fontSize: '0.8rem',
                cursor: 'pointer',
                fontWeight: 500,
              }}
            >
              Timeline Slices ({plan.timeline.length})
            </button>
            <button
              onClick={() => setActiveTab('json')}
              style={{
                background: activeTab === 'json' ? 'rgba(99, 102, 241, 0.2)' : 'transparent',
                border: activeTab === 'json' ? '1px solid #6366f1' : '1px solid transparent',
                color: activeTab === 'json' ? '#a5b4fc' : '#94a3b8',
                borderRadius: '6px',
                padding: '6px 12px',
                fontSize: '0.8rem',
                cursor: 'pointer',
                fontWeight: 500,
              }}
            >
              JSON Schema
            </button>
          </div>

          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button
              onClick={handleCopy}
              style={{
                background: 'rgba(255, 255, 255, 0.05)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                color: '#f8fafc',
                borderRadius: '6px',
                padding: '6px 12px',
                fontSize: '0.78rem',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '0.35rem',
              }}
            >
              {copied ? '✓ Copied' : '📋 Copy JSON'}
            </button>
            <button
              onClick={handleDownloadJson}
              style={{
                background: 'rgba(99, 102, 241, 0.15)',
                border: '1px solid rgba(99, 102, 241, 0.3)',
                color: '#a5b4fc',
                borderRadius: '6px',
                padding: '6px 12px',
                fontSize: '0.78rem',
                cursor: 'pointer',
              }}
            >
              ⬇ Download .json
            </button>
            <button
              onClick={handleDownloadEdl}
              style={{
                background: 'rgba(6, 182, 212, 0.15)',
                border: '1px solid rgba(6, 182, 212, 0.3)',
                color: '#67e8f9',
                borderRadius: '6px',
                padding: '6px 12px',
                fontSize: '0.78rem',
                cursor: 'pointer',
              }}
            >
              🎬 Export EDL
            </button>
          </div>
        </div>

        {/* Content Box */}
        <div
          style={{
            flex: 1,
            overflowY: 'auto',
            background: 'rgba(0, 0, 0, 0.4)',
            borderRadius: '8px',
            border: '1px solid rgba(255, 255, 255, 0.06)',
            padding: '1rem',
          }}
        >
          {activeTab === 'diff' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {/* Dual Track Visual Comparison */}
              <div
                style={{
                  background: 'rgba(255, 255, 255, 0.02)',
                  border: '1px solid rgba(255, 255, 255, 0.06)',
                  borderRadius: '10px',
                  padding: '1rem',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.6rem' }}>
                  <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                    Visual Timeline Diff (Before vs After)
                  </span>
                  <span style={{ fontSize: '0.75rem', fontFamily: 'JetBrains Mono, monospace', color: '#a5b4fc' }}>
                    {plan.stats.original_duration.toFixed(1)}s raw ➔ {plan.stats.clean_duration.toFixed(1)}s clean (-{plan.stats.time_saved.toFixed(1)}s)
                  </span>
                </div>

                {/* Original Timeline Track */}
                <div style={{ marginBottom: '0.6rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.68rem', color: '#64748b', marginBottom: '0.2rem' }}>
                    <span>Original Footage (All Takes + Dead Air)</span>
                    <span style={{ fontFamily: 'JetBrains Mono' }}>{plan.stats.original_duration.toFixed(1)}s</span>
                  </div>
                  <div
                    style={{
                      height: '16px',
                      background: '#090d16',
                      borderRadius: '4px',
                      overflow: 'hidden',
                      display: 'flex',
                      border: '1px solid rgba(255, 255, 255, 0.08)',
                    }}
                  >
                    {diffEvents.map((ev) => {
                      const totalDur = Math.max(0.1, plan.stats.original_duration);
                      const widthPct = Math.max(0.5, (ev.duration / totalDur) * 100);
                      return (
                        <div
                          key={`orig_${ev.id}`}
                          title={`${ev.type.toUpperCase()}: ${ev.start.toFixed(2)}s - ${ev.end.toFixed(2)}s (${ev.duration.toFixed(2)}s) ${ev.text || ''}`}
                          style={{
                            width: `${widthPct}%`,
                            height: '100%',
                            background: ev.type === 'keep' ? '#10b981' : '#f43f5e',
                            opacity: ev.type === 'keep' ? 0.85 : 0.65,
                            borderRight: '1px solid rgba(0,0,0,0.4)',
                          }}
                        />
                      );
                    })}
                  </div>
                </div>

                {/* Clean Output Track */}
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.68rem', color: '#64748b', marginBottom: '0.2rem' }}>
                    <span style={{ color: '#34d399', fontWeight: 600 }}>Final Rendered Clean Video (Gapless)</span>
                    <span style={{ fontFamily: 'JetBrains Mono', color: '#34d399' }}>{plan.stats.clean_duration.toFixed(1)}s</span>
                  </div>
                  <div
                    style={{
                      height: '16px',
                      background: '#090d16',
                      borderRadius: '4px',
                      overflow: 'hidden',
                      display: 'flex',
                      border: '1px solid rgba(16, 185, 129, 0.3)',
                    }}
                  >
                    {diffEvents
                      .filter((ev) => ev.type === 'keep')
                      .map((ev) => {
                        const totalClean = Math.max(0.1, plan.stats.clean_duration);
                        const widthPct = Math.max(0.5, (ev.duration / totalClean) * 100);
                        return (
                          <div
                            key={`clean_${ev.id}`}
                            title={`KEEP: ${ev.start.toFixed(2)}s - ${ev.end.toFixed(2)}s ➔ Output ${ev.cleanStart?.toFixed(2)}s - ${ev.cleanEnd?.toFixed(2)}s`}
                            style={{
                              width: `${widthPct}%`,
                              height: '100%',
                              background: '#10b981',
                              opacity: 0.9,
                              borderRight: '1px solid rgba(0,0,0,0.3)',
                            }}
                          />
                        );
                      })}
                  </div>
                </div>
              </div>

              {/* Sequential Diff Event Log */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0 0.25rem' }}>
                  <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                    Chronological Diff Log ({diffEvents.length} edits)
                  </span>
                  <div style={{ display: 'flex', gap: '1rem', fontSize: '0.72rem' }}>
                    <span style={{ color: '#34d399' }}>+ {plan.stats.keeps_count} Keeps</span>
                    <span style={{ color: '#fb7185' }}>- {plan.stats.cuts_count} Cuts</span>
                  </div>
                </div>

                {diffEvents.length === 0 ? (
                  <div style={{ textAlign: 'center', color: '#64748b', padding: '2rem' }}>
                    No diff events found.
                  </div>
                ) : (
                  diffEvents.map((ev, idx) => (
                    <div
                      key={ev.id || idx}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        background: ev.type === 'keep' ? 'rgba(16, 185, 129, 0.04)' : 'rgba(244, 63, 94, 0.05)',
                        border: '1px solid rgba(255, 255, 255, 0.05)',
                        borderLeft: ev.type === 'keep' ? '4px solid #10b981' : '4px solid #f43f5e',
                        borderRadius: '6px',
                        padding: '0.65rem 0.85rem',
                        gap: '1rem',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', minWidth: '180px' }}>
                        <span style={{ fontSize: '0.68rem', fontFamily: 'JetBrains Mono', color: '#64748b' }}>
                          #{idx + 1}
                        </span>
                        <span
                          style={{
                            fontSize: '0.7rem',
                            fontWeight: 700,
                            padding: '2px 6px',
                            borderRadius: '4px',
                            background: ev.type === 'keep' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(244, 63, 94, 0.2)',
                            color: ev.type === 'keep' ? '#34d399' : '#fb7185',
                            fontFamily: 'JetBrains Mono',
                          }}
                        >
                          {ev.type === 'keep' ? '+ KEEP' : '- CUT'}
                        </span>
                        <span
                          style={{
                            fontFamily: 'JetBrains Mono',
                            fontSize: '0.72rem',
                            color: ev.type === 'keep' ? '#a7f3d0' : '#fca5a5',
                            fontWeight: 600,
                          }}
                        >
                          {ev.type === 'keep' ? `+${ev.duration.toFixed(2)}s` : `-${ev.duration.toFixed(2)}s`}
                        </span>
                      </div>

                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div
                          style={{
                            fontSize: '0.82rem',
                            color: ev.type === 'keep' ? '#f1f5f9' : '#fca5a5',
                            textDecoration: ev.type === 'cut' ? 'line-through' : 'none',
                            opacity: ev.type === 'cut' ? 0.75 : 1,
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {ev.text || (ev.reason ? `[${ev.reason}]` : '[Dead Air / Silence]')}
                        </div>
                        {ev.explanation && (
                          <div style={{ fontSize: '0.7rem', color: '#94a3b8', marginTop: '0.15rem', fontStyle: 'italic' }}>
                            💡 {ev.explanation}
                          </div>
                        )}
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexShrink: 0 }}>
                        {ev.reason && (
                          <span
                            style={{
                              fontSize: '0.68rem',
                              padding: '2px 6px',
                              borderRadius: '4px',
                              background: 'rgba(245, 158, 11, 0.1)',
                              color: '#fbbf24',
                              border: '1px solid rgba(245, 158, 11, 0.2)',
                            }}
                          >
                            {ev.reason}
                          </span>
                        )}
                        <span
                          style={{
                            fontFamily: 'JetBrains Mono',
                            fontSize: '0.72rem',
                            color: '#94a3b8',
                          }}
                        >
                          {ev.start.toFixed(2)}s → {ev.end.toFixed(2)}s
                        </span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          {activeTab === 'json' && (
            <pre
              style={{
                margin: 0,
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: '0.78rem',
                lineHeight: '1.45',
                color: '#38bdf8',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
              }}
            >
              {jsonString}
            </pre>
          )}

          {activeTab === 'timeline' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {plan.timeline.length === 0 ? (
                <div style={{ textAlign: 'center', color: '#64748b', padding: '2rem' }}>
                  No timeline entries compiled yet.
                </div>
              ) : (
                plan.timeline.map((entry: TimelineEntry, idx: number) => (
                  <div
                    key={entry.id || idx}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      background: 'rgba(255, 255, 255, 0.02)',
                      border: '1px solid rgba(255, 255, 255, 0.05)',
                      borderRadius: '6px',
                      padding: '0.6rem 0.85rem',
                      gap: '1rem',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', minWidth: '160px' }}>
                      <span
                        style={{
                          fontSize: '0.68rem',
                          fontFamily: 'JetBrains Mono, monospace',
                          color: '#64748b',
                        }}
                      >
                        #{idx + 1}
                      </span>
                      <span
                        style={{
                          fontSize: '0.7rem',
                          padding: '2px 6px',
                          borderRadius: '4px',
                          textTransform: 'uppercase',
                          fontWeight: 600,
                          background:
                            entry.action === 'keep'
                              ? 'rgba(16, 185, 129, 0.15)'
                              : 'rgba(244, 63, 94, 0.15)',
                          color: entry.action === 'keep' ? '#34d399' : '#fb7185',
                        }}
                      >
                        {entry.action}
                      </span>
                      <span
                        style={{
                          fontFamily: 'JetBrains Mono, monospace',
                          fontSize: '0.75rem',
                          color: '#cbd5e1',
                        }}
                      >
                        {entry.start.toFixed(2)}s → {entry.end.toFixed(2)}s
                      </span>
                    </div>

                    <div
                      style={{
                        flex: 1,
                        fontSize: '0.8rem',
                        color: '#94a3b8',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {entry.text || (entry.reason ? `[Reason: ${entry.reason}]` : 'Silence/Gap')}
                    </div>

                    {entry.reason && (
                      <span
                        style={{
                          fontSize: '0.68rem',
                          padding: '2px 6px',
                          borderRadius: '4px',
                          background: 'rgba(245, 158, 11, 0.1)',
                          color: '#fbbf24',
                          border: '1px solid rgba(245, 158, 11, 0.2)',
                        }}
                      >
                        {entry.reason}
                      </span>
                    )}
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
