/**
 * CutFlow API Client — Standardized REST client for all frontend API calls.
 */

import type { ProjectData, ProjectSummary, CutProposal, EditPlan } from '../types';

export const API_BASE = import.meta.env.VITE_API_URL || '';

/**
 * Upload a raw video file with progress tracking
 */
export function uploadVideo(
  file: File,
  onProgress?: (percent: number) => void
): Promise<{ video_filename: string; video_url: string; original_name: string }> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${API_BASE}/api/upload`);

    if (onProgress) {
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) {
          const percent = Math.round((e.loaded / e.total) * 100);
          onProgress(percent);
        }
      };
    }

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText));
        } catch {
          reject(new Error('Invalid JSON in upload response'));
        }
      } else {
        reject(new Error(`Upload failed with status ${xhr.status}`));
      }
    };

    xhr.onerror = () => reject(new Error('Network error during video upload'));

    const formData = new FormData();
    formData.append('file', file);
    xhr.send(formData);
  });
}

/**
 * Start asynchronous transcription and analysis into a new project
 */
export async function createProject(params: {
  video_filename: string;
  api_key?: string | null;
  groq_api_key?: string | null;
  provider: string;
  model?: string;
  silence_threshold?: string;
  max_silence?: number;
}): Promise<{ project_id: string; status: string }> {
  const res = await fetch(`${API_BASE}/api/projects`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`Project creation failed: ${errorText || res.statusText}`);
  }
  return res.json();
}

/**
 * List all saved projects with summary metadata
 */
export async function getProjects(): Promise<ProjectSummary[]> {
  const res = await fetch(`${API_BASE}/api/projects`);
  if (!res.ok) {
    throw new Error(`Failed to fetch projects: ${res.statusText}`);
  }
  return res.json();
}

/**
 * Get full project details (manifest, transcript, analysis, edit plan)
 */
export async function getProject(projectId: string): Promise<ProjectData> {
  const res = await fetch(`${API_BASE}/api/projects/${projectId}`);
  if (!res.ok) {
    throw new Error(`Failed to load project ${projectId}: ${res.statusText}`);
  }
  return res.json();
}

/**
 * Update project mutable metadata (such as name)
 */
export async function patchProject(projectId: string, patch: { name?: string }): Promise<any> {
  const res = await fetch(`${API_BASE}/api/projects/${projectId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(patch),
  });
  if (!res.ok) {
    throw new Error(`Failed to update project: ${res.statusText}`);
  }
  return res.json();
}

/**
 * Delete a project and its artifacts
 */
export async function deleteProject(projectId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/api/projects/${projectId}`, {
    method: 'DELETE',
  });
  if (!res.ok) {
    throw new Error(`Failed to delete project: ${res.statusText}`);
  }
  return res.json();
}

/**
 * Check the progress/status of a project's background processing job
 */
export async function getProjectStatus(projectId: string): Promise<{
  id: string;
  status: string;
  progress?: number;
  stage_index?: number;
  message?: string;
  error?: string | null;
}> {
  const res = await fetch(`${API_BASE}/api/projects/${projectId}/status`);
  if (!res.ok) {
    throw new Error(`Failed to check project status: ${res.statusText}`);
  }
  return res.json();
}

/**
 * Retrieve raw transcript data
 */
export async function getProjectTranscript(projectId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/api/projects/${projectId}/transcript`);
  if (!res.ok) throw new Error(`Failed to load transcript: ${res.statusText}`);
  return res.json();
}

/**
 * Retrieve AI cuts analysis
 */
export async function getProjectAnalysis(projectId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/api/projects/${projectId}/analysis`);
  if (!res.ok) throw new Error(`Failed to load analysis: ${res.statusText}`);
  return res.json();
}

/**
 * Retrieve universal Edit Plan IR JSON
 */
export async function getProjectEditPlan(projectId: string): Promise<EditPlan> {
  const res = await fetch(`${API_BASE}/api/projects/${projectId}/edit-plan`);
  if (!res.ok) throw new Error(`Failed to load edit plan: ${res.statusText}`);
  return res.json();
}

/**
 * Update manual cut proposals and synchronize Edit Plan
 */
export async function updateProjectCuts(
  projectId: string,
  cuts: CutProposal[]
): Promise<{ status: string; analysis: any; edit_plan: any }> {
  const res = await fetch(`${API_BASE}/api/projects/${projectId}/cuts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      cuts: cuts.map((c) => ({ ...c, action: 'cut' })),
    }),
  });
  if (!res.ok) {
    throw new Error(`Failed to sync cuts: ${res.statusText}`);
  }
  return res.json();
}

/**
 * Apply approved cuts with ffmpeg and render final clean video
 */
export async function renderProjectVideo(projectId: string): Promise<{
  status: string;
  rendered_url: string;
  output_path: string;
  saved_seconds: number;
}> {
  const res = await fetch(`${API_BASE}/api/projects/${projectId}/render`, {
    method: 'POST',
  });
  if (!res.ok) {
    throw new Error(`Render failed: ${res.statusText}`);
  }
  return res.json();
}

/**
 * Get direct download URL for CMX 3600 EDL export
 */
export function getExportEdlUrl(projectId: string): string {
  return `${API_BASE}/api/projects/${projectId}/export/edl`;
}

/**
 * Get direct download URL for Edit Plan JSON export
 */
export function getExportJsonUrl(projectId: string): string {
  return `${API_BASE}/api/projects/${projectId}/export/json`;
}

/**
 * Send an editorial message or query to the LangGraph AI Editing Agent
 */
export async function sendAgentMessage(
  projectId: string,
  message: string,
  options?: { provider?: string; model?: string; apiKey?: string }
): Promise<{
  response: string;
  action_taken: string;
  updated_cuts?: CutProposal[];
  edit_plan?: EditPlan;
}> {
  const res = await fetch(`${API_BASE}/api/projects/${projectId}/agent/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      provider: options?.provider || 'groq',
      model: options?.model,
      api_key: options?.apiKey,
    }),
  });
  if (!res.ok) {
    throw new Error(`Agent interaction failed: ${res.statusText}`);
  }
  return res.json();
}

/**
 * Inspect persistent agent memory and editorial decisions for this project
 */
export async function getAgentMemory(projectId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/api/projects/${projectId}/agent/memory`);
  if (!res.ok) throw new Error(`Failed to load memory: ${res.statusText}`);
  return res.json();
}

/**
 * Storage management: get usage stats
 */
export async function getStorageInfo(): Promise<{
  upload_mb: number;
  projects_mb: number;
  total_mb: number;
  upload_count: number;
  project_count: number;
}> {
  const res = await fetch(`${API_BASE}/api/storage/info`);
  if (!res.ok) throw new Error('Failed to load storage info');
  return res.json();
}

/**
 * Storage management: purge stale uploads
 */
export async function cleanupStorage(keepRecent: number = 1): Promise<{
  status: string;
  stats: { total_mb: number; upload_count: number };
}> {
  const res = await fetch(`${API_BASE}/api/storage/cleanup?keep_recent=${keepRecent}`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Storage cleanup failed');
  return res.json();
}
