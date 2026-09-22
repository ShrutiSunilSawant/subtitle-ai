"""
app/models/schemas.py — Pydantic Request/Response Schemas
===========================================================
Defines the data shapes for API requests and responses.
FastAPI uses these for automatic validation and documentation.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


# -------------------------------------------------------
# Enumerations
# -------------------------------------------------------

class ProcessingStatus(str, Enum):
    """Tracks where a video is in the processing pipeline."""
    PENDING    = "pending"
    UPLOADING  = "uploading"
    PROCESSING = "processing"
    DONE       = "done"
    FAILED     = "failed"


class WhisperModelSize(str, Enum):
    """Available Whisper model sizes (larger = more accurate, slower)."""
    TINY   = "tiny"
    BASE   = "base"
    SMALL  = "small"
    MEDIUM = "medium"
    LARGE  = "large"


# -------------------------------------------------------
# Request Schemas
# -------------------------------------------------------

class ProcessRequest(BaseModel):
    """
    Options the user can pass when requesting video processing.
    All fields have sensible defaults.
    """
    job_id: str                             = Field(..., description="Job ID from the upload step")
    whisper_model: WhisperModelSize         = Field(WhisperModelSize.BASE, description="Whisper model size")
    language: Optional[str]                 = Field(None, description="Force a language (e.g. 'en', 'fr'). Auto-detect if None.")
    silence_threshold_db: float             = Field(-40.0, description="dB below which audio is considered silent")
    min_silence_duration_sec: float         = Field(1.5, description="Minimum seconds of silence to generate an explainer")
    burn_subtitles: bool                    = Field(True, description="Whether to burn subtitles into the video")


# -------------------------------------------------------
# Response Schemas
# -------------------------------------------------------

class UploadResponse(BaseModel):
    """Returned immediately after a successful upload."""
    job_id: str
    filename: str
    file_size_bytes: int
    message: str


class StatusResponse(BaseModel):
    """Current state of a processing job."""
    job_id: str
    status: ProcessingStatus
    progress_percent: int                   = Field(0, ge=0, le=100)
    current_step: str                       = ""
    error_message: Optional[str]            = None


class SubtitleEntry(BaseModel):
    """A single subtitle entry (one line in the SRT file)."""
    index: int
    start_time: float                       # seconds
    end_time: float                         # seconds
    text: str
    is_explainer: bool                      = False  # True = BLIP-generated, False = Whisper


class ResultResponse(BaseModel):
    """Full result once processing is complete."""
    job_id: str
    status: ProcessingStatus
    video_url: Optional[str]               = None   # URL to download processed video
    srt_url: Optional[str]                 = None   # URL to download .srt file
    transcript_url: Optional[str]          = None   # URL to download plain text transcript
    subtitle_entries: list[SubtitleEntry]  = []
    duration_seconds: float                = 0.0
    language_detected: Optional[str]       = None
    processing_time_seconds: float         = 0.0
