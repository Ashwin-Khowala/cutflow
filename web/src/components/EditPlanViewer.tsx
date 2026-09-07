import React, { useState } from 'react';
import type { EditPlan, ProjectData, CutProposal, TimelineEntry } from '../types';

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
  const [activeTab, setActiveTab] = useState<'json' | 'timeline' | 'edl'>('json');
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
      const res = await fetch(`/api/projects/${project.id}/export/edl`);
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
          width: '90%',
          maxWidth: '860px',
          maxHeight: '85vh',
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
                CutFlow Edit Plan (IR)
              </h3>
              <p style={{ margin: 0, fontSize: '0.8rem', color: '#94a3b8' }}>
                Open intermediate representation format • Version {plan.version}
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
            <div style={{ fontSize: '0.7rem', color: '#64748b', textTransform: 'uppercase' }}>Time Saved</div>
            <div style={{ fontSize: '1.1rem', fontWeight: 600, color: '#6366f1', fontFamily: 'JetBrains Mono, monospace' }}>
              {plan.stats.time_saved.toFixed(1)}s ({plan.stats.savings_percent.toFixed(0)}%)
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
              Timeline Entries ({plan.timeline.length})
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
