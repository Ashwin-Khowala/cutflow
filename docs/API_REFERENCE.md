# CutFlow REST API Reference

The CutFlow backend server runs on `http://127.0.0.1:8000` (by default) and provides the following endpoints:

---

## 1. Endpoints

### `POST /api/upload`
Uploads a raw video file.
- **Request:** `multipart/form-data` with field `file`
- **Response:**
```json
{
  "status": "success",
  "video_filename": "a1b2c3d4_recording.mp4",
  "video_url": "/media/uploads/a1b2c3d4_recording.mp4",
  "original_name": "recording.mp4"
}
```

---

### `POST /api/process`
Initiates asynchronous audio extraction, Moonshine transcription, silence detection, and Gemini analysis.
- **Request:** `application/json`
```json
{
  "video_filename": "a1b2c3d4_recording.mp4",
  "api_key": "optional_gemini_key",
  "silence_threshold": "-35dB",
  "silence_min_duration": 0.8,
  "max_silence": 1.5
}
```
- **Response:**
```json
{
  "project_id": "9f8e7d6c",
  "status": "pending"
}
```

---

### `GET /api/status/{project_id}`
Polls the processing status of a project.
- **Status values:** `pending`, `transcribing`, `analyzing`, `ready`, `failed`
- **Response:**
```json
{
  "id": "9f8e7d6c",
  "status": "ready",
  "message": "Analysis ready for review.",
  "result": { "transcript": {...}, "analysis": {...} },
  "error": null
}
```

---

### `GET /api/project/{project_id}`
Fetches the full project object including transcript, proposed cuts, and keep regions.

---

### `POST /api/cuts/update`
Saves manual user overrides (e.g. user toggled a cut or restored a segment in the UI).
- **Request:**
```json
{
  "project_id": "9f8e7d6c",
  "cuts": [
    {
      "start": 0.0,
      "end": 2.5,
      "reason": "false_start",
      "action": "cut",
      "text": "Speaker stumbled",
      "explanation": "Manual override",
      "confidence": 1.0
    }
  ]
}
```

---

### `POST /api/render`
Triggers FFmpeg to slice the keep regions and produce the final clean output.
- **Request:** `multipart/form-data` with field `project_id`
- **Response:**
```json
{
  "status": "success",
  "rendered_url": "/media/projects/9f8e7d6c/9f8e7d6c_cut.mp4",
  "output_path": "cutflow_data/projects/9f8e7d6c/9f8e7d6c_cut.mp4",
  "saved_seconds": 12.4
}
```
