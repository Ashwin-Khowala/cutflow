# CutFlow Edit Plan Specification (v1.0)

## Overview

The **CutFlow Edit Plan** is an open, provider-agnostic Intermediate Representation (IR) for automated and AI-assisted video editing. It captures temporal regions, editorial intent (keep, cut, replace), semantic reasoning, and audio/video effects in a clean JSON format.

By standardizing this format, CutFlow enables any transcription model or LLM agent to output structured video edits that can be:
1. Previewed client-side in real-time (without rendering).
2. Rendered locally via FFmpeg.
3. Exported to NLEs (DaVinci Resolve, Final Cut Pro, Premiere) via CMX 3600 EDL.
4. Rendered in cloud serverless pipelines (Vercel / Remotion).

---

## JSON Schema Structure

```typescript
interface EditPlan {
  version: "1.0";
  project_id: string;
  source_video: string;
  source_duration: number; // in seconds
  stats: {
    original_duration: number;
    clean_duration: number;
    time_saved: number;
    savings_percent: number;
    cuts_count: number;
    keeps_count: number;
  };
  timeline: TimelineEntry[];
  metadata: {
    generator: string;
    created_at: string; // ISO 8601
    provider: string;   // e.g. "groq" | "gemini"
    model: string;      // e.g. "openai/gpt-oss-120b"
  };
}

interface TimelineEntry {
  id: string;             // Unique identifier, e.g. "entry_001"
  start: number;          // Start timestamp in seconds
  end: number;            // End timestamp in seconds
  duration: number;       // Duration in seconds
  type: "a_roll" | "b_roll" | "silence" | "cut";
  action: "keep" | "cut" | "replace";
  text?: string;          // Spoken dialogue in this segment
  reason?: string;        // "false_start" | "repeated_take" | "filler_words" | "long_silence"
  confidence?: number;    // Model confidence [0.0 - 1.0]
  effects?: Record<string, any>; // Optional zoom, transitions, volume fades
  words?: WordTimestamp[];       // Optional fine-grained word timings
}

interface WordTimestamp {
  word: string;
  start: number;
  end: number;
  probability?: number;
}
```

---

## API Endpoints

- `GET /api/project/{project_id}/edit-plan`
  Returns the complete `EditPlan` JSON for a project.

- `GET /api/project/{project_id}/export/edl`
  Returns the CMX 3600 Edit Decision List for direct import into professional NLE timelines.
