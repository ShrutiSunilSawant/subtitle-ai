"""
app/services/processing_service.py — Full Processing Pipeline
"""

import os
import logging
import asyncio
from typing import Optional

from app.models.job_store import Job, get_job
from app.models.schemas import ProcessingStatus
from app.transcription.transcription_service import TranscriptionService
from app.video_processing.silence_detector import SilenceDetector
from app.video_processing.frame_extractor import FrameExtractor
from app.video_processing.video_renderer import VideoRenderer
from app.explainers.blip_explainer import BLIPExplainer
from app.subtitle_generation.subtitle_merger import SubtitleMerger
from app.core.config import settings
from app.utils.file_utils import clean_temp_files

logger = logging.getLogger(__name__)


class ProcessingService:

    def __init__(self):
        self.transcription = TranscriptionService()
        self.silence_detector = SilenceDetector(
            silence_threshold_db=settings.SILENCE_THRESHOLD_DB,
            min_silence_duration_sec=3.0,
            max_silence_duration_sec=settings.MAX_SILENCE_DURATION_SEC,
        )
        self.frame_extractor = FrameExtractor()
        self.blip_explainer = BLIPExplainer()
        self.subtitle_merger = SubtitleMerger()
        self.video_renderer = VideoRenderer()

    async def process(
        self,
        job_id: str,
        language: Optional[str] = None,
        silence_threshold_db: float = -40.0,
        min_silence_duration_sec: float = 1.5,
        burn_subtitles: bool = True,
    ):
        job = get_job(job_id)
        if not job:
            logger.error(f"Job {job_id} not found.")
            return

        self.silence_detector.silence_threshold_db = silence_threshold_db
        self.silence_detector.min_silence_duration_sec = min_silence_duration_sec

        # Pre-create all temp directories
        temp_job_dir = os.path.join(settings.TEMP_DIR, job_id)
        temp_frames_dir = os.path.join(temp_job_dir, "frames")
        os.makedirs(temp_job_dir, exist_ok=True)
        os.makedirs(temp_frames_dir, exist_ok=True)

        temp_files: list[str] = []

        try:
            job.status = ProcessingStatus.PROCESSING

            # STEP 1: Transcribe with Whisper
            job.update_progress(10, "Transcribing audio with Whisper...")
            logger.info(f"[{job_id}] Step 1: Transcription")

            transcription = await asyncio.to_thread(
                self.transcription.transcribe,
                job.file_path,
                language,
            )

            job.language_detected = transcription.language
            job.duration_seconds = transcription.duration_seconds

            # STEP 2: Detect silent segments
            # First try audio energy method, fall back to transcript gap method
            job.update_progress(30, "Detecting silent segments...")
            logger.info(f"[{job_id}] Step 2: Silence Detection")

            try:
                silent_segments = await asyncio.to_thread(
                    self.silence_detector.detect,
                    job.file_path,
                    temp_job_dir,
                )
            except Exception as e:
                logger.warning(f"Audio-based silence detection failed: {e}. Falling back to transcript gaps.")
                silent_segments = []

            # If audio method found nothing, use transcript gaps
            if not silent_segments:
                logger.info("No audio-silent segments found — using speech gaps from transcript instead.")
                silent_segments = self.silence_detector.detect_from_transcript(
                    transcription.segments,
                    transcription.duration_seconds,
                )

            logger.info(f"[{job_id}] Found {len(silent_segments)} segment(s) for BLIP captioning")

            # STEP 3: Extract frames
            job.update_progress(45, "Extracting frames from silent scenes...")
            logger.info(f"[{job_id}] Step 3: Frame Extraction")

            frames = await asyncio.to_thread(
                self.frame_extractor.extract_frames,
                job.file_path,
                silent_segments,
                temp_frames_dir,
            )
            temp_files.extend([f.frame_path for f in frames])

            # STEP 4: BLIP captioning
            job.update_progress(60, "Generating scene explainers with BLIP AI...")
            logger.info(f"[{job_id}] Step 4: BLIP Captioning ({len(frames)} frames)")

            explainers = await asyncio.to_thread(
                self.blip_explainer.generate_explainers,
                frames,
            )

            # STEP 5: Merge subtitles
            job.update_progress(75, "Merging subtitles and scene explainers...")
            logger.info(f"[{job_id}] Step 5: Subtitle Merging")

            merged_entries = self.subtitle_merger.merge(
                transcription.segments,
                explainers,
            )

            output_base = os.path.join(settings.OUTPUT_DIR, job_id)
            os.makedirs(output_base, exist_ok=True)

            srt_path = os.path.join(output_base, "subtitles.srt")
            transcript_path = os.path.join(output_base, "transcript.txt")

            self.subtitle_merger.write_srt(merged_entries, srt_path)
            self.subtitle_merger.write_transcript(merged_entries, transcript_path)

            job.output_srt_path = srt_path
            job.output_transcript_path = transcript_path
            job.subtitle_entries = self.subtitle_merger.to_schema_entries(merged_entries)

            # STEP 6: Render video
            output_video_path = os.path.join(output_base, "output.mp4")

            if burn_subtitles and merged_entries:
                job.update_progress(85, "Burning subtitles into video...")
                logger.info(f"[{job_id}] Step 6: Video Rendering")

                await asyncio.to_thread(
                    self.video_renderer.burn_subtitles,
                    job.file_path,
                    srt_path,
                    output_video_path,
                )
            else:
                job.update_progress(85, "Copying video...")
                await asyncio.to_thread(
                    self.video_renderer.copy_without_subtitles,
                    job.file_path,
                    output_video_path,
                )

            job.output_video_path = output_video_path
            job.mark_done()
            logger.info(f"[{job_id}] ✅ Done in {job.processing_time_seconds:.1f}s")

        except Exception as e:
            logger.exception(f"[{job_id}] ❌ Failed: {e}")
            job.mark_failed(str(e))

        finally:
            clean_temp_files(temp_files)
