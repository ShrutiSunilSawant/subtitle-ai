"""
main.py — FastAPI Application Entry Point
==========================================
This is the root of the backend application.
It wires together all routers, CORS settings, and startup events.
"""

import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import upload, process, status, download
from app.core.config import settings
from app.core.model_cache import ModelCache

# Configure logging to show INFO-level messages in the console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


# -------------------------------------------------------
# Lifespan: runs on startup and shutdown
# -------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager.
    - On startup: pre-load AI models into memory cache
    - On shutdown: clean up resources
    """
    logger.info("🚀 Starting AI Subtitle Explainer API...")

    # Ensure required directories exist
    for directory in [settings.UPLOAD_DIR, settings.OUTPUT_DIR, settings.TEMP_DIR]:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"📁 Directory ready: {directory}")

    # Pre-load ML models to avoid cold-start delays on first request
    logger.info("🤖 Pre-loading AI models (Whisper + BLIP)...")
    await ModelCache.initialize()
    logger.info("✅ Models loaded and cached successfully.")

    yield  # Application runs here

    # Shutdown cleanup
    logger.info("🛑 Shutting down — clearing model cache...")
    ModelCache.clear()


# -------------------------------------------------------
# FastAPI Application
# -------------------------------------------------------
app = FastAPI(
    title="AI Subtitle & Scene Explainer API",
    description="Automatic subtitles + contextual silent-scene explainers using Whisper & BLIP",
    version="1.0.0",
    lifespan=lifespan,
)


# -------------------------------------------------------
# CORS — allow the React frontend to call this API
# -------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------------------------------------
# Static file serving for processed outputs
# -------------------------------------------------------
# StaticFiles is mounted at import time (before the lifespan startup hook
# below has a chance to run), so the directory must already exist here.
os.makedirs(settings.OUTPUT_DIR, exist_ok=True)
app.mount("/outputs", StaticFiles(directory=settings.OUTPUT_DIR), name="outputs")


# -------------------------------------------------------
# API Routers
# -------------------------------------------------------
app.include_router(upload.router,   prefix="/api/v1", tags=["Upload"])
app.include_router(process.router,  prefix="/api/v1", tags=["Processing"])
app.include_router(status.router,   prefix="/api/v1", tags=["Status"])
app.include_router(download.router, prefix="/api/v1", tags=["Download"])


# -------------------------------------------------------
# Health Check
# -------------------------------------------------------
@app.get("/health", tags=["Health"])
async def health_check():
    """Simple health check endpoint for monitoring."""
    return {"status": "ok", "service": "AI Subtitle Explainer"}


# -------------------------------------------------------
# Run directly with: python main.py
# -------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
