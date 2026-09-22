"""
app/api/upload.py — Video Upload Endpoint
==========================================
Accepts multipart video file uploads, validates them,
saves to disk, and creates a job entry for processing.
"""

import os
import logging
import aiofiles

from fastapi import APIRouter, UploadFile, File, HTTPException, status

from app.core.config import settings
from app.models.job_store import create_job
from app.models.schemas import UploadResponse
from app.utils.file_utils import (
    generate_job_id,
    validate_video_extension,
    safe_filename,
    get_file_size_mb,
    ensure_dirs,
)

router = APIRouter()
logger = logging.getLogger(__name__)

# Chunk size for streaming file writes (4MB)
CHUNK_SIZE = 4 * 1024 * 1024


@router.post(
    "/upload",
    response_model=UploadResponse,
    summary="Upload a video file for processing",
    status_code=status.HTTP_201_CREATED,
)
async def upload_video(file: UploadFile = File(...)):
    """
    Upload a video file to begin the AI subtitle pipeline.

    - Validates file extension
    - Enforces file size limit
    - Saves file to uploads directory
    - Creates a job entry and returns a job_id

    Returns a job_id to use in subsequent /process and /status calls.
    """

    # --- Validate file extension ---
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided.",
        )

    if not validate_video_extension(file.filename):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Unsupported file format: '{file.filename}'. "
                f"Allowed formats: {', '.join(settings.allowed_extensions_list)}"
            ),
        )

    # --- Generate job ID and save path ---
    job_id = generate_job_id()
    clean_name = safe_filename(file.filename)
    upload_path = os.path.join(settings.UPLOAD_DIR, f"{job_id}_{clean_name}")

    ensure_dirs(settings.UPLOAD_DIR)

    # --- Stream file to disk in chunks ---
    total_bytes = 0
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    try:
        async with aiofiles.open(upload_path, "wb") as out_file:
            while chunk := await file.read(CHUNK_SIZE):
                total_bytes += len(chunk)

                if total_bytes > max_bytes:
                    # Clean up partial upload
                    os.remove(upload_path)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=(
                            f"File exceeds maximum allowed size of "
                            f"{settings.MAX_UPLOAD_SIZE_MB}MB."
                        ),
                    )

                await out_file.write(chunk)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"File upload failed: {e}")
        if os.path.exists(upload_path):
            os.remove(upload_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Upload failed due to a server error.",
        )

    # --- Create job entry in memory ---
    job = create_job(job_id=job_id, filename=file.filename, file_path=upload_path)

    logger.info(
        f"Upload complete: job_id={job_id}, "
        f"file={file.filename}, size={total_bytes / 1024:.1f}KB"
    )

    return UploadResponse(
        job_id=job_id,
        filename=file.filename,
        file_size_bytes=total_bytes,
        message="Upload successful. Use job_id to start processing.",
    )
