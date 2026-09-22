"""
app/api/process.py — Video Processing Endpoint
================================================
Starts the AI processing pipeline for an uploaded video.
Runs the pipeline as a FastAPI BackgroundTask so the API
returns immediately while processing continues in the background.
"""

import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks, status

from app.models.job_store import get_job
from app.models.schemas import ProcessRequest, StatusResponse, ProcessingStatus
from app.services.processing_service import ProcessingService

router = APIRouter()
logger = logging.getLogger(__name__)

# Single shared instance of the processing service
_processing_service = ProcessingService()


@router.post(
    "/process",
    response_model=StatusResponse,
    summary="Start processing an uploaded video",
)
async def start_processing(
    request: ProcessRequest,
    background_tasks: BackgroundTasks,
):
    """
    Kick off the full AI subtitle pipeline for a previously uploaded video.

    Steps run in the background:
    1. Whisper transcription
    2. Silence detection
    3. Frame extraction
    4. BLIP scene captioning
    5. Subtitle merging
    6. Video rendering

    Use /status/{job_id} to poll progress.
    """

    # --- Validate job exists ---
    job = get_job(request.job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{request.job_id}' not found. Did you upload a video first?",
        )

    # --- Prevent re-processing an already-running job ---
    if job.status == ProcessingStatus.PROCESSING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This job is already being processed.",
        )

    if job.status == ProcessingStatus.DONE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This job has already completed. Download the results.",
        )

    # --- Queue background processing ---
    background_tasks.add_task(
        _processing_service.process,
        job_id=request.job_id,
        language=request.language,
        silence_threshold_db=request.silence_threshold_db,
        min_silence_duration_sec=request.min_silence_duration_sec,
        burn_subtitles=request.burn_subtitles,
    )

    job.status = ProcessingStatus.PROCESSING
    job.update_progress(5, "Pipeline started...")

    logger.info(f"Processing started for job: {request.job_id}")

    return StatusResponse(
        job_id=job.job_id,
        status=job.status,
        progress_percent=job.progress_percent,
        current_step=job.current_step,
    )
