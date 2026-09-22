"""
app/api/status.py — Job Status Endpoint
=========================================
Allows the frontend to poll processing progress.
"""

import logging
from fastapi import APIRouter, HTTPException, status

from app.models.job_store import get_job
from app.models.schemas import StatusResponse, ResultResponse, ProcessingStatus

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get(
    "/status/{job_id}",
    response_model=StatusResponse,
    summary="Check processing status",
)
async def get_status(job_id: str):
    """
    Poll the status of a processing job.

    Returns:
        - status: pending | processing | done | failed
        - progress_percent: 0–100
        - current_step: human-readable description of current step
    """
    job = get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found.",
        )

    return StatusResponse(
        job_id=job.job_id,
        status=job.status,
        progress_percent=job.progress_percent,
        current_step=job.current_step,
        error_message=job.error_message,
    )


@router.get(
    "/result/{job_id}",
    response_model=ResultResponse,
    summary="Get full processing results",
)
async def get_result(job_id: str):
    """
    Get the full results of a completed processing job.
    Only available when status == 'done'.
    """
    job = get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found.",
        )

    if job.status == ProcessingStatus.PROCESSING:
        raise HTTPException(
            status_code=status.HTTP_202_ACCEPTED,
            detail="Processing is still in progress.",
        )

    if job.status == ProcessingStatus.FAILED:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Processing failed: {job.error_message}",
        )

    if job.status != ProcessingStatus.DONE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Processing has not started yet.",
        )

    # Build download URLs
    base_url = f"/outputs/{job_id}"

    return ResultResponse(
        job_id=job.job_id,
        status=job.status,
        video_url=f"{base_url}/output.mp4" if job.output_video_path else None,
        srt_url=f"{base_url}/subtitles.srt" if job.output_srt_path else None,
        transcript_url=f"{base_url}/transcript.txt" if job.output_transcript_path else None,
        subtitle_entries=job.subtitle_entries,
        duration_seconds=job.duration_seconds,
        language_detected=job.language_detected,
        processing_time_seconds=job.processing_time_seconds,
    )
