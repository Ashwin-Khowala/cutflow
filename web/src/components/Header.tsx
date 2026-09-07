import React from 'react';
import { Film, Settings as SettingsIcon, Plus, Download, Sparkles, FileCode, Home, Folder } from 'lucide-react';

interface HeaderProps {
  onHomeClick?: () => void;
  onNewProject: () => void;
  onOpenProjects?: () => void;
  onOpenSettings: () => void;
  onOpenEditPlan?: () => void;
  onExport: () => void;
  hasProject: boolean;
  isRendering: boolean;
  provider?: string;
  projectName?: string;
}

export const Header: React.FC<HeaderProps> = ({
  onHomeClick,
  onNewProject,
  onOpenProjects,
  onOpenSettings,
  onOpenEditPlan,
  onExport,
  hasProject,
  isRendering,
  provider = 'groq',
  projectName,
}) => {
  return (
    <header className="app-header">
      <div className="brand-container">
        {onHomeClick && (
          <button
            className="btn btn-icon"
            onClick={onHomeClick}
            title="Return to Landing Page"
            style={{
              background: 'transparent',
              border: 'none',
              color: '#94a3b8',
              cursor: 'pointer',
              padding: '6px',
              display: 'flex',
              alignItems: 'center',
            }}
          >
            <Home size={18} />
          </button>
        )}
        <div className="brand-icon">
          <Film size={18} />
        </div>
        <div className="brand-title">
          <span>CutFlow Studio</span>
          <span className="brand-badge">
            <Sparkles size={10} style={{ display: 'inline', marginRight: 3 }} />
            {provider === 'gemini' ? 'Gemini 2.0 Flash' : 'Groq LPU'}
          </span>
        </div>
        {projectName && (
          <span
            style={{
              marginLeft: '0.75rem',
              fontSize: '0.8rem',
              color: '#94a3b8',
              background: 'rgba(255, 255, 255, 0.04)',
              padding: '3px 8px',
              borderRadius: '4px',
              maxWidth: '200px',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            {projectName}
          </span>
        )}
      </div>

      <div className="header-actions">
        {hasProject && onOpenEditPlan && (
          <button
            className="btn btn-outline"
            onClick={onOpenEditPlan}
            title="Inspect Edit Plan JSON & EDL"
            style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}
          >
            <FileCode size={15} />
            <span>Edit Plan IR</span>
          </button>
        )}

        {onOpenProjects && (
          <button className="btn btn-outline" onClick={onOpenProjects} title="Open Projects Manager" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <Folder size={15} />
            <span>Projects</span>
          </button>
        )}

        <button className="btn btn-outline" onClick={onOpenSettings} title="Settings">
          <SettingsIcon size={15} />
          <span>Settings</span>
        </button>

        <button className="btn btn-primary" onClick={onNewProject}>
          <Plus size={15} />
          <span>New Video</span>
        </button>

        {hasProject && (
          <button
            className="btn btn-success"
            onClick={onExport}
            disabled={isRendering}
          >
            <Download size={15} />
            <span>{isRendering ? 'Rendering...' : 'Render MP4'}</span>
          </button>
        )}
      </div>
    </header>
  );
};
