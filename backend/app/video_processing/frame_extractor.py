"""
app/video_processing/frame_extractor.py — Key Frame Extraction
================================================================
For each silent segment, extracts one representative frame from
the middle of that segment. This frame will be fed to BLIP for
scene captioning.

Strategy:
- Seek to the midpoint of each silent segment
- Extract 3 candidate frames (start, mid, end)
- Use the sharpest (least blurry) one via Laplacian variance
"""

import os
import logging
from dataclasses import dataclass

import cv2
import numpy as np

from app.video_processing.silence_detector import SilentSegment

logger = logging.getLogger(__name__)


# -------------------------------------------------------
# Data Structure
# -------------------------------------------------------

@dataclass
class ExtractedFrame:
    """
    A video frame extracted for a silent segment.

    Attributes:
        segment       — the silent segment this frame represents
        frame_path    — file path to the saved frame image (PNG)
        timestamp_sec — exact timestamp of the frame in the video
    """
    segment: SilentSegment
    frame_path: str
    timestamp_sec: float


# -------------------------------------------------------
# Frame Extractor
# -------------------------------------------------------

class FrameExtractor:
    """
    Extracts the best representative frame from each silent segment.

    Uses OpenCV to seek video frames efficiently.
    """

    def extract_frames(
        self,
        video_path: str,
        silent_segments: list[SilentSegment],
        temp_dir: str,
    ) -> list[ExtractedFrame]:
        """
        Extract one best frame per silent segment.

        Args:
            video_path:       Path to the input video file.
            silent_segments:  List of SilentSegment objects.
            temp_dir:         Directory to save extracted frames.

        Returns:
            List of ExtractedFrame objects (one per segment).
        """
        if not silent_segments:
            logger.info("No silent segments — skipping frame extraction.")
            return []

        os.makedirs(temp_dir, exist_ok=True)

        # Open the video file with OpenCV
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"OpenCV could not open video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        logger.info(f"Video: {fps:.2f} fps, {total_frames} frames")

        extracted = []

        try:
            for idx, segment in enumerate(silent_segments):
                frame = self._extract_best_frame(cap, segment, fps, total_frames)

                if frame is None:
                    logger.warning(f"Could not extract frame for segment {segment}")
                    continue

                # Save the frame as a PNG image
                frame_filename = f"frame_segment_{idx:04d}.png"
                frame_path = os.path.join(temp_dir, frame_filename)
                cv2.imwrite(frame_path, frame)

                # Compute the actual timestamp (midpoint of segment)
                timestamp = (segment.start + segment.end) / 2.0

                extracted.append(ExtractedFrame(
                    segment=segment,
                    frame_path=frame_path,
                    timestamp_sec=timestamp,
                ))

                logger.debug(f"Saved frame: {frame_path} at {timestamp:.2f}s")
        finally:
            cap.release()

        logger.info(f"Extracted {len(extracted)} frame(s) from {len(silent_segments)} segment(s).")
        return extracted

    def _extract_best_frame(
        self,
        cap: cv2.VideoCapture,
        segment: SilentSegment,
        fps: float,
        total_frames: int,
    ):
        """
        Extract the sharpest frame from a set of candidate timestamps
        within the silent segment (start, mid, end).

        Why sharpness matters:
        Motion blur or transition frames can confuse BLIP.
        A sharp frame gives better captions.
        """
        # Candidate timestamps: start + 10%, midpoint, end - 10%
        duration = segment.end - segment.start
        candidates = [
            segment.start + duration * 0.1,
            segment.start + duration * 0.5,
            segment.start + duration * 0.9,
        ]

        best_frame = None
        best_sharpness = -1.0

        for timestamp in candidates:
            frame_index = int(timestamp * fps)
            frame_index = min(frame_index, total_frames - 1)  # Clamp to valid range

            # Seek to the exact frame
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            ret, frame = cap.read()

            if not ret or frame is None:
                continue

            # Compute sharpness using Laplacian variance
            # High variance = sharp edges = clear frame
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()

            if sharpness > best_sharpness:
                best_sharpness = sharpness
                best_frame = frame

        return best_frame
