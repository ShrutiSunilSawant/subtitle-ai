"""
app/utils/file_utils.py — File System Utilities
=================================================
Helper functions for file validation, path management,
and cleanup of temporary files after processing.
"""

import os
import uuid
import logging
import shutil

logger = logging.getLogger(__name__)

# Supported video extensions
SUPPORTED_EXTENSIONS = {"mp4", "mov", "mkv", "avi", "webm"}


def generate_job_id() -> str:
    """Generate a short unique job identifier."""
    return uuid.uuid4().hex[:12]  # e.g. "a3f9c12e4b7d"


def validate_video_extension(filename: str) -> bool:
    """
    Check if the filename has a supported video extension.

    Args:
        filename: Original filename from the upload.

    Returns:
        True if valid, False otherwise.
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in SUPPORTED_EXTENSIONS


def safe_filename(filename: str) -> str:
    """
    Sanitize a filename by removing unsafe characters.
    Keeps the original extension.
    """
    import re
    basename = os.path.splitext(filename)[0]
    ext = os.path.splitext(filename)[1]
    # Replace anything not alphanumeric, dash, underscore, or dot
    safe = re.sub(r"[^\w\-_.]", "_", basename)
    return safe + ext


def get_file_size_mb(path: str) -> float:
    """Return file size in megabytes."""
    return os.path.getsize(path) / (1024 * 1024)


def clean_temp_files(file_paths: list[str]):
    """
    Delete a list of temporary files.
    Ignores missing files gracefully.
    """
    for path in file_paths:
        try:
            if os.path.exists(path):
                os.remove(path)
                logger.debug(f"Cleaned up temp file: {path}")
        except Exception as e:
            logger.warning(f"Could not delete temp file {path}: {e}")


def clean_temp_dir(directory: str):
    """
    Remove an entire temporary directory.
    Used to clean up frame extraction directories after processing.
    """
    try:
        if os.path.exists(directory):
            shutil.rmtree(directory)
            logger.debug(f"Cleaned up temp dir: {directory}")
    except Exception as e:
        logger.warning(f"Could not delete temp dir {directory}: {e}")


def ensure_dirs(*dirs: str):
    """Create directories if they don't already exist."""
    for d in dirs:
        os.makedirs(d, exist_ok=True)
