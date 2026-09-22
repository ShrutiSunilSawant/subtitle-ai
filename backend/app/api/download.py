"""
app/api/download.py — File Download Endpoints
==============================================
Serves processed output files for download:
- Processed video (MP4 with burned subtitles)
- SRT subtitle file
- Plain text transcript
"""

import os
import logging
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from app.models.job_store import get_job
from app.models.schemas import ProcessingStatus

router = APIRouter()
logger = logging.getLogger(__name__)


def _get_completed_job(job_id: str):
    """Helper: retrieve a job and verify it's done."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found.",
        )
    if job.status != ProcessingStatus.DONE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job is not complete yet. Current status: {job.status}",
        )
    return job


@router.get(
    "/download/{job_id}/video",
    summary="Download the processed video with burned subtitles",
)
async def download_video(job_id: str):
    """Download the MP4 video with subtitles burned in."""
    job = _get_completed_job(job_id)

    if not job.output_video_path or not os.path.exists(job.output_video_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Processed video file not found.",
        )

    return FileResponse(
        path=job.output_video_path,
        media_type="video/mp4",
        filename=f"subtitled_{job.filename}",
    )


@router.get(
    "/download/{job_id}/srt",
    summary="Download the SRT subtitle file",
)
async def download_srt(job_id: str):
    """Download the .srt subtitle file containing speech + scene explainers."""
    job = _get_completed_job(job_id)

    if not job.output_srt_path or not os.path.exists(job.output_srt_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SRT file not found.",
        )

    return FileResponse(
        path=job.output_srt_path,
        media_type="application/x-subrip",
        filename=f"{os.path.splitext(job.filename)[0]}.srt",
    )


@router.get(
    "/download/{job_id}/transcript",
    summary="Download the plain text transcript",
)
async def download_transcript(job_id: str):
    """Download a plain text transcript (speech only, no timestamps)."""
    job = _get_completed_job(job_id)

    if not job.output_transcript_path or not os.path.exists(job.output_transcript_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transcript file not found.",
        )

    return FileResponse(
        path=job.output_transcript_path,
        media_type="text/plain",
        filename=f"{os.path.splitext(job.filename)[0]}_transcript.txt",
    )
