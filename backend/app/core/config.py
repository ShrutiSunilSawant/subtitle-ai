"""
app/core/config.py — Centralized Application Settings
"""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # --- Server ---
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True

    # --- File Storage ---
    UPLOAD_DIR: str = "uploads"
    OUTPUT_DIR: str = "outputs"
    TEMP_DIR: str = "temp"
    MAX_UPLOAD_SIZE_MB: int = 500

    # --- Whisper ---
    WHISPER_MODEL_SIZE: str = "small"

    # --- BLIP ---
    BLIP_MODEL_NAME: str = "Salesforce/blip-image-captioning-base"

    # --- Silence Detection ---
    SILENCE_THRESHOLD_DB: float = -35.0
    MIN_SILENCE_DURATION_SEC: float = 5.0
    MAX_SILENCE_DURATION_SEC: float = 60.0

    # --- Processing ---
    MAX_VIDEO_DURATION_SEC: int = 3600
    ALLOWED_EXTENSIONS: str = "mp4,mov,mkv,avi,webm"

    # --- CORS ---
    FRONTEND_URL: str = "http://localhost:5173"

    # --- HuggingFace token for pyannote speaker diarization ---
    HF_TOKEN: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def allowed_extensions_list(self) -> list[str]:
        return [ext.strip() for ext in self.ALLOWED_EXTENSIONS.split(",")]


settings = Settings()
