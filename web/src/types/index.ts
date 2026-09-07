export interface Word {
  text: string;
  start: number;
  end: number;
}

export interface Segment {
  text: string;
  start: number;
  end: number;
  words?: Word[];
}

export interface SilenceRegion {
  start: number;
  end: number;
  duration: number;
}

export interface Transcript {
  duration: number;
  audio_path: string;
  segments: Segment[];
  silences: SilenceRegion[];
}

export interface CutProposal {
  start: number;
  end: number;
  duration?: number;
  reason: 'false_start' | 'repeated_take' | 'filler_words' | 'long_silence' | 'stumble' | 'manual_cut' | string;
  explanation: string;
  text: string;
  confidence: number;
  action?: 'cut' | 'keep';
}

export interface KeepRegion {
  start: number;
  end: number;
  duration?: number;
  text: string;
}

export interface SelectedClip {
  id: string;
  type: 'keep' | 'cut';
  start: number;
  end: number;
  duration: number;
  text: string;
  reason?: string;
  explanation?: string;
  originalIndex?: number;
}

export interface Analysis {
  summary: string;
  total_duration: number;
  kept_duration: number;
  cut_duration: number;
  savings_percent: number;
  cuts: CutProposal[];
  keeps: KeepRegion[];
}

export interface TimelineEntry {
  id: string;
  start: number;
  end: number;
  duration: number;
  type: 'a_roll' | 'b_roll' | 'silence' | 'cut';
  action: 'keep' | 'cut' | 'replace';
  text?: string;
  reason?: string;
  confidence?: number;
  effects?: Record<string, any>;
  words?: Word[];
}

export interface EditPlan {
  version: string;
  project_id: string;
  source_video: string;
  source_duration: number;
  stats: {
    original_duration: number;
    clean_duration: number;
    time_saved: number;
    savings_percent: number;
    cuts_count: number;
    keeps_count: number;
  };
  timeline: TimelineEntry[];
  metadata: Record<string, any>;
}

export interface ProjectSummary {
  id: string;
  name: string;
  video_filename: string;
  video_url: string;
  created_at: string;
  updated_at: string;
  status: string;
  duration: number;
  cuts_count: number;
  keeps_count: number;
  time_saved: number;
  savings_percent: number;
  rendered: boolean;
  rendered_url?: string | null;
  provider?: string;
  model?: string;
}

export interface ProjectData {
  id: string;
  name?: string;
  video_filename: string;
  video_url: string;
  rendered_url?: string | null;
  metadata?: ProjectSummary;
  transcript: Transcript;
  analysis: Analysis;
  edit_plan?: EditPlan | null;
}

export interface Settings {
  provider: 'groq' | 'gemini';
  model: string;
  groqApiKey: string;
  geminiApiKey: string;
  silenceThreshold: string;
  maxSilence: number;
}
