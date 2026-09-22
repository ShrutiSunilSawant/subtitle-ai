"""
silence_detector.py
===================
Detects non-speech segments using WebRTC VAD.
Falls back to energy-based detection.
Also detects music/instrument segments for scene captioning.
"""

import os
import logging
import subprocess
from dataclasses import dataclass
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class SilentSegment:
    start: float
    end:   float
    is_music: bool = False

    @property
    def duration(self) -> float:
        return self.end - self.start


class SilenceDetector:

    def __init__(
        self,
        silence_threshold_db:    float = -35.0,
        min_silence_duration_sec: float = 3.0,   # lowered to 3s to catch guitar segments
        max_silence_duration_sec: float = 60.0,
    ):
        self.silence_threshold_db     = silence_threshold_db
        self.min_silence_duration_sec = min_silence_duration_sec
        self.max_silence_duration_sec = max_silence_duration_sec

    def detect(self, video_path: str, temp_dir: str) -> list[SilentSegment]:
        os.makedirs(temp_dir, exist_ok=True)
        audio_path = self._extract_audio(video_path, temp_dir)

        try:
            # Try VAD first (detects speech vs music/silence)
            segments = self._vad_detect(audio_path)
            if segments is not None:
                logger.info(f"VAD found {len(segments)} non-speech segment(s).")
                return segments

            # Fallback to energy
            logger.info("VAD unavailable — using energy detection.")
            return self._energy_detect(audio_path)
        finally:
            if os.path.exists(audio_path):
                os.remove(audio_path)

    def _extract_audio(self, video_path: str, temp_dir: str) -> str:
        output = os.path.join(temp_dir, "vad_audio.wav")
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-vn", "-ac", "1", "-ar", "16000",
            "-acodec", "pcm_s16le", output,
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg failed: {result.stderr.decode(errors='replace')}")
        return output

    def _vad_detect(self, audio_path: str):
        try:
            import webrtcvad
            import wave
        except ImportError:
            return None

        try:
            vad = webrtcvad.Vad(2)
            with wave.open(audio_path, 'rb') as wf:
                sr          = wf.getframerate()
                frame_ms    = 30
                frame_samps = int(sr * frame_ms / 1000)
                frame_bytes = frame_samps * 2
                frames = []
                while True:
                    raw = wf.readframes(frame_samps)
                    if len(raw) < frame_bytes:
                        break
                    frames.append(raw)

            is_speech = []
            for frame in frames:
                try:
                    is_speech.append(vad.is_speech(frame, sr))
                except Exception:
                    is_speech.append(False)

            # Smooth over ±8 frames
            smoothed = list(is_speech)
            window = 8
            for i in range(len(is_speech)):
                lo = max(0, i - window)
                hi = min(len(is_speech), i + window + 1)
                smoothed[i] = any(is_speech[lo:hi])

            frame_dur = frame_ms / 1000.0
            segments  = []
            in_nonspeech = False
            start = 0.0

            for i, speech in enumerate(smoothed):
                t = i * frame_dur
                if not speech and not in_nonspeech:
                    in_nonspeech = True
                    start = t
                elif speech and in_nonspeech:
                    in_nonspeech = False
                    dur = t - start
                    if self.min_silence_duration_sec <= dur <= self.max_silence_duration_sec:
                        segments.append(SilentSegment(start=start, end=t))

            if in_nonspeech:
                end = len(smoothed) * frame_dur
                dur = end - start
                if self.min_silence_duration_sec <= dur <= self.max_silence_duration_sec:
                    segments.append(SilentSegment(start=start, end=end))

            return segments
        except Exception as e:
            logger.error(f"VAD error: {e}")
            return None

    def _energy_detect(self, audio_path: str) -> list[SilentSegment]:
        import librosa
        y, sr        = librosa.load(audio_path, sr=None, mono=True)
        hop_length   = 256
        rms          = librosa.feature.rms(y=y, frame_length=512, hop_length=hop_length)[0]
        rms_db       = 20.0 * np.log10(rms + 1e-9)
        is_silent    = rms_db < self.silence_threshold_db
        frame_times  = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop_length)
        return self._group(is_silent, frame_times)

    def _group(self, is_silent, frame_times) -> list[SilentSegment]:
        segments = []
        in_sil   = False
        start    = 0.0
        for i, silent in enumerate(is_silent):
            t = float(frame_times[i])
            if silent and not in_sil:
                in_sil = True
                start  = t
            elif not silent and in_sil:
                in_sil = False
                dur    = t - start
                if self.min_silence_duration_sec <= dur <= self.max_silence_duration_sec:
                    segments.append(SilentSegment(start=start, end=t))
        if in_sil:
            dur = float(frame_times[-1]) - start
            if self.min_silence_duration_sec <= dur <= self.max_silence_duration_sec:
                segments.append(SilentSegment(start=start, end=float(frame_times[-1])))
        return segments

    def detect_from_transcript(self, segments, total_duration: float) -> list[SilentSegment]:
        """
        Fallback: find gaps between transcript segments.
        Used when VAD finds no silent segments (e.g. continuous speech with music).
        Any gap > min_silence_duration_sec between speech segments = scene caption opportunity.
        """
        from app.transcription.transcription_service import TranscriptionSegment

        logger.info("Finding gaps between transcript segments for scene captions...")
        silent = []

        # Add gap at the very start if speech doesn't begin immediately
        if segments and segments[0].start > self.min_silence_duration_sec:
            silent.append(SilentSegment(start=0.0, end=segments[0].start))

        # Find gaps between consecutive segments
        for i in range(len(segments) - 1):
            gap_start = segments[i].end
            gap_end   = segments[i + 1].start
            gap_dur   = gap_end - gap_start
            if self.min_silence_duration_sec <= gap_dur <= self.max_silence_duration_sec:
                silent.append(SilentSegment(start=gap_start, end=gap_end))

        # Gap at the end
        if segments and total_duration - segments[-1].end > self.min_silence_duration_sec:
            silent.append(SilentSegment(
                start=segments[-1].end,
                end=min(total_duration, segments[-1].end + self.max_silence_duration_sec)
            ))

        logger.info(f"Found {len(silent)} transcript-gap segment(s) for scene captioning.")
        return silent
