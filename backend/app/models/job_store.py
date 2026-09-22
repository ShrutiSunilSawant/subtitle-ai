"""
app/models/job_store.py — In-Memory Job State Tracker
=======================================================
Stores the state of each processing job.
In production, replace with Redis or a database.
"""

import time
from typing import Dict, Optional, Any
from app.models.schemas import ProcessingStatus


class Job:
    """Represents a single video processing job."""

    def __init__(self, job_id: str, filename: str, file_path: str):
        self.job_id: str = job_id
        self.filename: str = filename
        self.file_path: str = file_path                 # Path to the uploaded video
        self.status: ProcessingStatus = ProcessingStatus.PENDING
        self.progress_percent: int = 0
        self.current_step: str = "Waiting to start"
        self.error_message: Optional[str] = None
        self.created_at: float = time.time()
        self.completed_at: Optional[float] = None

        # Output paths (filled in during processing)
        self.output_video_path: Optional[str] = None
        self.output_srt_path: Optional[str] = None
        self.output_transcript_path: Optional[str] = None

        # Result metadata
        self.duration_seconds: float = 0.0
        self.language_detected: Optional[str] = None
        self.processing_time_seconds: float = 0.0
        self.subtitle_entries: list = []

    def update_progress(self, percent: int, step: str):
        """Convenience method to update progress and current step."""
        self.progress_percent = percent
        self.current_step = step

    def mark_done(self):
        self.status = ProcessingStatus.DONE
        self.progress_percent = 100
        self.current_step = "Complete"
        self.completed_at = time.time()
        self.processing_time_seconds = self.completed_at - self.created_at

    def mark_failed(self, error: str):
        self.status = ProcessingStatus.FAILED
        self.error_message = error
        self.current_step = "Failed"


# -------------------------------------------------------
# Global in-memory store: { job_id: Job }
# -------------------------------------------------------
_job_store: Dict[str, Job] = {}


def create_job(job_id: str, filename: str, file_path: str) -> Job:
    """Create and store a new job."""
    job = Job(job_id, filename, file_path)
    _job_store[job_id] = job
    return job


def get_job(job_id: str) -> Optional[Job]:
    """Retrieve a job by ID (returns None if not found)."""
    return _job_store.get(job_id)


def list_jobs() -> list[Job]:
    """Return all jobs (for debugging/admin use)."""
    return list(_job_store.values())
