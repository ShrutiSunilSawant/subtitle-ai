"""
model_cache.py — Caches BLIP model only.
faster-whisper manages its own model caching internally.
"""

import logging
import torch

logger = logging.getLogger(__name__)


class ModelCache:
    _whisper_model   = None   # kept for openai-whisper fallback
    _blip_processor  = None
    _blip_model      = None
    _initialized     = False

    @classmethod
    async def initialize(cls):
        if cls._initialized:
            return
        cls._load_whisper_fallback()
        cls._load_blip()
        cls._initialized = True

    @classmethod
    def _load_whisper_fallback(cls):
        """Only load openai-whisper as fallback if faster-whisper is missing."""
        try:
            import faster_whisper
            logger.info("✅ faster-whisper available — skipping openai-whisper preload.")
        except ImportError:
            try:
                import whisper
                from app.core.config import settings
                logger.info(f"Loading openai-whisper fallback: {settings.WHISPER_MODEL_SIZE}")
                cls._whisper_model = whisper.load_model(settings.WHISPER_MODEL_SIZE)
                logger.info("✅ openai-whisper loaded.")
            except Exception as e:
                logger.error(f"❌ openai-whisper load failed: {e}")

    @classmethod
    def _load_blip(cls):
        from app.core.config import settings
        model_name = settings.BLIP_MODEL_NAME
        logger.info(f"Loading BLIP: {model_name}")
        try:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            from transformers import BlipProcessor, BlipForConditionalGeneration
            cls._blip_processor = BlipProcessor.from_pretrained(model_name)
            cls._blip_model = BlipForConditionalGeneration.from_pretrained(
                model_name, torch_dtype=torch.float32
            ).to(device).eval()
            logger.info(f"✅ BLIP loaded on {device}.")
        except Exception as e:
            logger.error(f"❌ BLIP load failed: {e}")

    @classmethod
    def get_whisper(cls):
        return cls._whisper_model

    @classmethod
    def get_blip(cls):
        return cls._blip_processor, cls._blip_model

    @classmethod
    def clear(cls):
        cls._whisper_model  = None
        cls._blip_processor = None
        cls._blip_model     = None
        cls._initialized    = False
