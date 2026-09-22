# 🎬 AI-Powered Automatic Subtitle & Silent Scene Explainer

> A multimodal AI media-processing pipeline that generates subtitles from speech (Whisper) and contextual scene descriptions for silent video segments (BLIP) — merged into a single, accessible subtitle file and burned into the video.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Running the App](#running-the-app)
- [API Endpoints](#api-endpoints)
- [Processing Pipeline](#processing-pipeline)
- [Configuration](#configuration)
- [Docker Setup](#docker-setup)

---

## Overview

SubtitleAI takes any video file and:

1. **Transcribes speech** using OpenAI Whisper (99+ languages)
2. **Detects silent segments** using Librosa audio analysis
3. **Extracts key frames** from silent scenes using OpenCV
4. **Generates scene descriptions** using Salesforce BLIP vision AI
5. **Merges** speech subtitles + scene explainers into one SRT file
6. **Burns subtitles** into the video with FFmpeg
7. **Delivers** processed video, SRT file, and plain text transcript

### Use Cases
- Accessibility for deaf / hard-of-hearing viewers
- Movie and OTT content subtitling
- Documentary and short film post-production
- Educational video content

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        User (Browser)                       │
│            React + Tailwind CSS Frontend (Port 5173)        │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP / REST API
┌──────────────────────▼──────────────────────────────────────┐
│                 FastAPI Backend (Port 8000)                  │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────┐  │
│  │  /upload │  │ /process │  │ /status  │  │ /download │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └─────┬─────┘  │
│       │              │              │               │        │
│  ┌────▼──────────────▼──────────────────────────────▼────┐  │
│  │              Processing Service (Background)           │  │
│  │                                                       │  │
│  │  ┌─────────────┐    ┌─────────────────────────────┐  │  │
│  │  │   Whisper   │    │    Silence Detector         │  │  │
│  │  │Transcription│    │    (Librosa / FFmpeg)        │  │  │
│  │  └──────┬──────┘    └──────────────┬──────────────┘  │  │
│  │         │                          │                  │  │
│  │         │            ┌─────────────▼──────────────┐  │  │
│  │         │            │    Frame Extractor          │  │  │
│  │         │            │    (OpenCV)                 │  │  │
│  │         │            └─────────────┬──────────────┘  │  │
│  │         │                          │                  │  │
│  │         │            ┌─────────────▼──────────────┐  │  │
│  │         │            │    BLIP Explainer           │  │  │
│  │         │            │    (HuggingFace)             │  │  │
│  │         │            └─────────────┬──────────────┘  │  │
│  │         │                          │                  │  │
│  │  ┌──────▼──────────────────────────▼──────────────┐  │  │
│  │  │              Subtitle Merger                   │  │  │
│  │  │         (Speech + Explainers → SRT)            │  │  │
│  │  └──────────────────────────────┬─────────────────┘  │  │
│  │                                  │                    │  │
│  │  ┌───────────────────────────────▼──────────────┐    │  │
│  │  │          Video Renderer (FFmpeg)              │    │  │
│  │  │      (Burn subtitles into MP4 output)         │    │  │
│  │  └───────────────────────────────────────────────┘    │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 18, Tailwind CSS, Vite, React Router, Axios, react-dropzone |
| **Backend** | Python 3.11, FastAPI, Uvicorn, Pydantic |
| **Speech AI** | OpenAI Whisper |
| **Vision AI** | Salesforce BLIP (HuggingFace Transformers) |
| **Video** | FFmpeg, OpenCV, MoviePy |
| **Audio** | Librosa, PyDub |
| **Infra** | Docker, Docker Compose |

---

## Project Structure

```
subtitle-ai/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── upload.py          # POST /upload — file upload endpoint
│   │   │   ├── process.py         # POST /process — start pipeline
│   │   │   ├── status.py          # GET /status/{id} — progress polling
│   │   │   └── download.py        # GET /download/{id}/* — file downloads
│   │   │
│   │   ├── core/
│   │   │   ├── config.py          # Pydantic Settings (loads .env)
│   │   │   └── model_cache.py     # Singleton model cache (Whisper + BLIP)
│   │   │
│   │   ├── models/
│   │   │   ├── schemas.py         # Pydantic request/response schemas
│   │   │   └── job_store.py       # In-memory job state tracker
│   │   │
│   │   ├── transcription/
│   │   │   └── transcription_service.py  # Whisper wrapper
│   │   │
│   │   ├── video_processing/
│   │   │   ├── silence_detector.py       # Librosa silence detection
│   │   │   ├── frame_extractor.py        # OpenCV frame extraction
│   │   │   └── video_renderer.py         # FFmpeg subtitle burning
│   │   │
│   │   ├── explainers/
│   │   │   └── blip_explainer.py         # BLIP scene captioning
│   │   │
│   │   ├── subtitle_generation/
│   │   │   └── subtitle_merger.py        # Merge + write SRT/TXT
│   │   │
│   │   ├── services/
│   │   │   └── processing_service.py     # Full pipeline orchestrator
│   │   │
│   │   ├── utils/
│   │   │   └── file_utils.py             # File helpers
│   │   │
│   │   └── main.py                # FastAPI app entry point
│   │
│   ├── uploads/                   # Uploaded video files
│   ├── outputs/                   # Processed outputs (video, srt, txt)
│   ├── temp/                      # Temporary working files
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── HomePage.jsx       # Landing page with features
│   │   │   ├── UploadPage.jsx     # Drag-and-drop upload
│   │   │   ├── ProcessingPage.jsx # Live progress view
│   │   │   └── ResultsPage.jsx    # Downloads + subtitle preview
│   │   │
│   │   ├── components/
│   │   │   └── Navbar.jsx
│   │   │
│   │   ├── utils/
│   │   │   └── api.js             # Axios API client
│   │   │
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   │
│   ├── public/
│   ├── index.html
│   ├── package.json
│   ├── tailwind.config.js
│   ├── vite.config.js
│   └── Dockerfile
│
├── docker-compose.yml
├── .gitignore
└── README.md
```

---

## Prerequisites

### System Requirements

- Python 3.10+
- Node.js 18+
- **FFmpeg** (required)
- ~3 GB disk space (for AI models)

### Install FFmpeg

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu / Debian:**
```bash
sudo apt update && sudo apt install -y ffmpeg
```

**Windows:**
1. Download from https://ffmpeg.org/download.html
2. Extract and add the `bin/` folder to your system PATH
3. Verify: `ffmpeg -version`

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/subtitle-ai.git
cd subtitle-ai
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment config
cp .env .env.local              # Edit as needed
```

> **Note:** First run will download Whisper (~140MB) and BLIP (~1GB) model weights from the internet. Subsequent runs use the cached models.

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install
```

---

## Running the App

### Start Backend

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`  
Interactive docs: `http://localhost:8000/docs`

### Start Frontend

```bash
cd frontend
npm run dev
```

The app will be available at `http://localhost:5173`

---

## API Endpoints

### Upload Video
```
POST /api/v1/upload
Content-Type: multipart/form-data

Body: file (video file)

Response: { job_id, filename, file_size_bytes, message }
```

### Start Processing
```
POST /api/v1/process
Content-Type: application/json

Body: {
  "job_id": "a3f9c12e4b7d",
  "language": "en",                    // null for auto-detect
  "silence_threshold_db": -40,
  "min_silence_duration_sec": 1.5,
  "burn_subtitles": true
}

Response: { job_id, status, progress_percent, current_step }
```

### Check Status
```
GET /api/v1/status/{job_id}

Response: {
  "job_id": "a3f9c12e4b7d",
  "status": "processing",              // pending|processing|done|failed
  "progress_percent": 60,
  "current_step": "Generating scene explainers with BLIP AI..."
}
```

### Get Result
```
GET /api/v1/result/{job_id}

Response: {
  "job_id": "...",
  "status": "done",
  "video_url": "/outputs/.../output.mp4",
  "srt_url": "/outputs/.../subtitles.srt",
  "transcript_url": "/outputs/.../transcript.txt",
  "subtitle_entries": [...],
  "language_detected": "en",
  "processing_time_seconds": 47.2
}
```

### Download Files
```
GET /api/v1/download/{job_id}/video       → MP4 with burned subtitles
GET /api/v1/download/{job_id}/srt         → .srt subtitle file
GET /api/v1/download/{job_id}/transcript  → .txt plain transcript
```

---

## Processing Pipeline

| Step | Tool | Description |
|------|------|-------------|
| 1. Upload | FastAPI | Streams file to disk, creates job |
| 2. Transcribe | Whisper | Speech → timestamped text segments |
| 3. Detect Silence | Librosa | Find quiet segments ≥ 1.5s |
| 4. Extract Frames | OpenCV | Best (sharpest) frame per segment |
| 5. Caption Frames | BLIP | Generate scene description per frame |
| 6. Merge | subtitle_merger | Sort speech + explainers into SRT |
| 7. Render | FFmpeg | Burn subtitles into video |
| 8. Deliver | FastAPI | Serve download links |

---

## Configuration

Edit `backend/.env`:

```env
WHISPER_MODEL_SIZE=base          # tiny|base|small|medium|large
BLIP_MODEL_NAME=Salesforce/blip-image-captioning-base
SILENCE_THRESHOLD_DB=-40         # dB below which audio is "silent"
MIN_SILENCE_DURATION_SEC=1.5     # Ignore silences shorter than this
MAX_UPLOAD_SIZE_MB=500
```

**Whisper Model Size Guide:**

| Model | VRAM | Speed | Accuracy |
|-------|------|-------|----------|
| tiny  | 1 GB | Fastest | Good |
| base  | 1 GB | Fast | Better ✓ |
| small | 2 GB | Medium | Good |
| medium | 5 GB | Slow | Great |
| large | 10 GB | Slowest | Best |

---

## Docker Setup

```bash
# Build and start all services
docker-compose up --build

# Run in background
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f backend
```

Access: `http://localhost:5173`

---

