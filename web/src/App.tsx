import { useState } from 'react';
import { Header } from './components/Header';
import { LandingPage } from './components/LandingPage';
import { UploadHero } from './components/UploadHero';
import { VideoPlayer } from './components/VideoPlayer';
import { Timeline } from './components/Timeline';
import { TranscriptList } from './components/TranscriptList';
import { StatsBar } from './components/StatsBar';
import { SettingsModal } from './components/SettingsModal';
import { ProcessingModal } from './components/ProcessingModal';
import { EditPlanViewer } from './components/EditPlanViewer';
import type { ProjectData, CutProposal, Settings } from './types';
import './App.css';

const API_BASE = import.meta.env.VITE_API_URL || '';

function App() {
  const [currentView, setCurrentView] = useState<'landing' | 'studio'>('landing');
  const [project, setProject] = useState<ProjectData | null>(null);
  const [cuts, setCuts] = useState<CutProposal[]>([]);
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [duration, setDuration] = useState<number>(0);
  const [autoSkipCuts, setAutoSkipCuts] = useState<boolean>(true);
  const [isSettingsOpen, setIsSettingsOpen] = useState<boolean>(false);
  const [isEditPlanOpen, setIsEditPlanOpen] = useState<boolean>(false);
  const [processingState, setProcessingState] = useState<{
    isOpen: boolean;
    title: string;
    message: string;
    progress?: number | null;
    stageIndex?: number;
  }>({
    isOpen: false,
    title: '',
    message: '',
    progress: null,
    stageIndex: 1,
  });
  const [isRendering, setIsRendering] = useState<boolean>(false);

  // Settings in localStorage — STRICTLY zero hardcoded keys
  const [settings, setSettings] = useState<Settings>(() => {
    return {
      provider: (localStorage.getItem('cutflow_provider') as 'groq' | 'gemini') || 'groq',
      model: localStorage.getItem('cutflow_model') || 'openai/gpt-oss-120b',
      groqApiKey: localStorage.getItem('cutflow_groq_api_key') || '',
      geminiApiKey: localStorage.getItem('cutflow_gemini_api_key') || '',
      silenceThreshold: localStorage.getItem('cutflow_silence_thresh') || '-35dB',
      maxSilence: parseFloat(localStorage.getItem('cutflow_max_silence') || '1.5'),
    };
  });

  const handleSaveSettings = (newSettings: Settings) => {
    setSettings(newSettings);
    localStorage.setItem('cutflow_provider', newSettings.provider);
    localStorage.setItem('cutflow_model', newSettings.model);
    localStorage.setItem('cutflow_groq_api_key', newSettings.groqApiKey);
    localStorage.setItem('cutflow_gemini_api_key', newSettings.geminiApiKey);
    localStorage.setItem('cutflow_silence_thresh', newSettings.silenceThreshold);
    localStorage.setItem('cutflow_max_silence', String(newSettings.maxSilence));
  };

  const handleFileUpload = async (file: File) => {
    setCurrentView('studio');
    setProcessingState({
      isOpen: true,
      title: 'Uploading Media',
      message: `Uploading ${file.name} to CutFlow engine...`,
      progress: 0,
      stageIndex: 1,
    });

    const formData = new FormData();
    formData.append('file', file);

    try {
      // Use XMLHttpRequest for real-time progress events
      const uploadData: any = await new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open('POST', `${API_BASE}/api/upload`);

        xhr.upload.onprogress = (e) => {
          if (e.lengthComputable) {
            const percent = Math.round((e.loaded / e.total) * 100);
            setProcessingState((prev) => ({
              ...prev,
              progress: percent,
              message: `Uploading ${file.name} (${percent}%)...`,
              stageIndex: 1,
            }));
          }
        };

        xhr.onload = () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            try {
              resolve(JSON.parse(xhr.responseText));
            } catch {
              reject(new Error('Invalid upload response'));
            }
          } else {
            reject(new Error(`Upload failed with status ${xhr.status}`));
          }
        };

        xhr.onerror = () => reject(new Error('Network error during upload'));
        xhr.send(formData);
      });

      const activeApiKey = settings.provider === 'groq' ? settings.groqApiKey : settings.geminiApiKey;
      const sttBackendLabel = settings.groqApiKey ? 'Groq Whisper' : 'Faster-Whisper';

      setProcessingState({
        isOpen: true,
        title: 'Processing Speech & Audio',
        message: `Transcribing with ${sttBackendLabel} & analyzing with ${settings.provider.toUpperCase()}...`,
        progress: 5,
        stageIndex: 1,
      });

      const processRes = await fetch(`${API_BASE}/api/process`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          video_filename: uploadData.video_filename,
          api_key: activeApiKey || null,
          groq_api_key: settings.groqApiKey || null,
          provider: settings.provider,
          model: settings.model,
          silence_threshold: settings.silenceThreshold,
          max_silence: settings.maxSilence,
        }),
      });

      if (!processRes.ok) {
        throw new Error('Processing job start failed');
      }

      const processData = await processRes.json();
      pollProjectStatus(processData.project_id);
    } catch (err: any) {
      alert(`Error: ${err.message}`);
      setProcessingState({ isOpen: false, title: '', message: '', progress: null, stageIndex: 1 });
    }
  };

  const pollProjectStatus = (projectId: string) => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE}/api/status/${projectId}`);
        const data = await res.json();

        setProcessingState((prev) => ({
          ...prev,
          message: data.message || 'Processing audio and analyzing semantics...',
          progress: typeof data.progress === 'number' ? data.progress : prev.progress,
          stageIndex: typeof data.stage_index === 'number' ? data.stage_index : prev.stageIndex,
        }));

        if (data.status === 'ready') {
          clearInterval(interval);
          setProcessingState({ isOpen: false, title: '', message: '', progress: null, stageIndex: 1 });
          loadProject(projectId);
        } else if (data.status === 'failed') {
          clearInterval(interval);
          alert(`Processing failed: ${data.error}`);
          setProcessingState({ isOpen: false, title: '', message: '', progress: null, stageIndex: 1 });
        }
      } catch (err) {
        console.error('Polling error:', err);
      }
    }, 1000);
  };

  const loadProject = async (projectId: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/project/${projectId}`);
      const data: ProjectData = await res.json();
      setProject(data);
      setCuts(data.analysis.cuts || []);
      setDuration(data.transcript.duration || 0);
      setCurrentTime(0);
    } catch (err: any) {
      alert(`Failed to load project: ${err.message}`);
    }
  };

  const handleToggleCut = (segmentIndex: number) => {
    if (!project) return;
    const seg = project.transcript.segments[segmentIndex];
    const existingCutIdx = cuts.findIndex(
      (c) => seg.start >= c.start - 0.1 && seg.end <= c.end + 0.5
    );

    let updatedCuts: CutProposal[];
    if (existingCutIdx >= 0) {
      // Restore segment
      updatedCuts = cuts.filter((_, idx) => idx !== existingCutIdx);
    } else {
      // Cut segment
      updatedCuts = [
        ...cuts,
        {
          start: seg.start,
          end: seg.end,
          reason: 'manual_cut',
          explanation: 'User manual override',
          text: seg.text,
          confidence: 1.0,
          action: 'cut',
        },
      ];
    }

    setCuts(updatedCuts);

    // Sync overrides with backend
    fetch(`${API_BASE}/api/cuts/update`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        project_id: project.id,
        cuts: updatedCuts.map((c) => ({ ...c, action: 'cut' })),
      }),
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.analysis && data.edit_plan) {
          setProject((prev: ProjectData | null) => (prev ? { ...prev, analysis: data.analysis, edit_plan: data.edit_plan } : null));
          setCuts(data.analysis.cuts || []);
        } else if (data.edit_plan) {
          setProject((prev: ProjectData | null) => (prev ? { ...prev, edit_plan: data.edit_plan } : null));
        }
      })
      .catch(console.error);
  };

  const handleExport = async () => {
    if (!project) return;
    setIsRendering(true);
    setProcessingState({
      isOpen: true,
      title: 'Rendering Clean Video',
      message: 'Running FFmpeg MPEG-TS concat demuxer for gapless stitching...',
    });

    const formData = new FormData();
    formData.append('project_id', project.id);

    try {
      const res = await fetch(`${API_BASE}/api/render`, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        throw new Error('Render request failed');
      }

      const data = await res.json();
      setProcessingState({ isOpen: false, title: '', message: '' });
      setIsRendering(false);

      window.open(data.rendered_url, '_blank');
    } catch (err: any) {
      alert(`Rendering error: ${err.message}`);
      setProcessingState({ isOpen: false, title: '', message: '' });
      setIsRendering(false);
    }
  };

  const cutDuration = cuts.reduce((sum, c) => sum + (c.end - c.start), 0);

  // If on landing page and no active project
  if (currentView === 'landing' && !project) {
    return (
      <>
        <LandingPage
          onLaunchStudio={() => setCurrentView('studio')}
          onOpenSettings={() => setIsSettingsOpen(true)}
          onFileUpload={handleFileUpload}
        />
        {isSettingsOpen && (
          <SettingsModal
            settings={settings}
            onSave={handleSaveSettings}
            onClose={() => setIsSettingsOpen(false)}
          />
        )}
        {processingState.isOpen && (
          <ProcessingModal
            title={processingState.title}
            message={processingState.message}
            progress={processingState.progress}
            stageIndex={processingState.stageIndex}
          />
        )}
      </>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <Header
        onHomeClick={() => setCurrentView('landing')}
        hasProject={!!project}
        isRendering={isRendering}
        provider={settings.provider}
        projectName={project?.video_filename}
        onNewProject={() => {
          setProject(null);
          setCurrentView('studio');
        }}
        onOpenSettings={() => setIsSettingsOpen(true)}
        onOpenEditPlan={() => setIsEditPlanOpen(true)}
        onExport={handleExport}
      />

      {!project ? (
        <UploadHero onFileUpload={handleFileUpload} />
      ) : (
        <main className="main-layout">
          {/* Left Column: Video Player, Multi-Track Timeline, & Stats */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            <div className="glass-panel" style={{ padding: '1.5rem' }}>
              <VideoPlayer
                src={project.video_url}
                currentTime={currentTime}
                duration={duration}
                autoSkipCuts={autoSkipCuts}
                cuts={cuts}
                onTimeUpdate={setCurrentTime}
                onDurationChange={setDuration}
                onToggleAutoSkip={() => setAutoSkipCuts(!autoSkipCuts)}
              />

              <div style={{ marginTop: '1.25rem' }}>
                <Timeline
                  duration={duration}
                  currentTime={currentTime}
                  keeps={project.analysis.keeps || []}
                  cuts={cuts}
                  silences={project.transcript.silences || []}
                  onSeek={setCurrentTime}
                />
              </div>

              <div style={{ marginTop: '1rem' }}>
                <StatsBar
                  totalDuration={duration}
                  cutDuration={cutDuration}
                  cutsCount={cuts.length}
                />
              </div>
            </div>
          </div>

          {/* Right Column: Transcript & Cut Decisions */}
          <div style={{ height: 'calc(100vh - 110px)' }}>
            <TranscriptList
              segments={project.transcript.segments}
              cuts={cuts}
              currentTime={currentTime}
              onSeek={setCurrentTime}
              onToggleCut={handleToggleCut}
            />
          </div>
        </main>
      )}

      {/* Edit Plan Modal */}
      {project && (
        <EditPlanViewer
          isOpen={isEditPlanOpen}
          onClose={() => setIsEditPlanOpen(false)}
          project={project}
        />
      )}

      {/* Settings Modal */}
      {isSettingsOpen && (
        <SettingsModal
          settings={settings}
          onSave={handleSaveSettings}
          onClose={() => setIsSettingsOpen(false)}
        />
      )}

      {/* Processing Stepper Modal */}
      {processingState.isOpen && (
        <ProcessingModal
          title={processingState.title}
          message={processingState.message}
          progress={processingState.progress}
          stageIndex={processingState.stageIndex}
        />
      )}
    </div>
  );
}

export default App;
