"""
transcription_service.py
========================
Professional subtitle generation using faster-whisper.
- Pitch-based speaker diarization (no pyannote needed)
- Word-level timestamps for perfect sync
- Punctuation-based line breaking
- Timing offset correction
"""

import os
import re
import logging
import subprocess
import numpy as np
from typing import Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

MAX_CHARS    = 40
MIN_DURATION = 0.8
# Slight delay correction — faster-whisper VAD can shift timestamps forward
TIMING_OFFSET = 0.0   # seconds to subtract from all timestamps (tune if needed)


@dataclass
class TranscriptionSegment:
    start:      float
    end:        float
    text:       str
    is_music:   bool = False
    speaker_id: str  = "S0"


@dataclass
class TranscriptionResult:
    segments:         list[TranscriptionSegment] = field(default_factory=list)
    full_text:        str   = ""
    language:         str   = "unknown"
    duration_seconds: float = 0.0


class TranscriptionService:

    def transcribe(self, file_path: str, language: Optional[str] = None) -> TranscriptionResult:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        for method in [self._faster_whisper, self._openai_whisper]:
            try:
                result = method(file_path, language)
                if result is not None:
                    # A result with zero segments is valid — it means the method
                    # ran successfully and found no speech (e.g. a silent video),
                    # not that the method itself failed.
                    return result
            except ImportError as e:
                logger.info(f"Skipping {method.__name__}: {e}")
            except Exception as e:
                logger.warning(f"{method.__name__} failed: {e}")

        raise RuntimeError("No transcription model available.")

    # ── faster-whisper ──────────────────────────────────────────────────

    def _faster_whisper(self, file_path: str, language: Optional[str]) -> TranscriptionResult:
        from faster_whisper import WhisperModel

        logger.info("Transcribing with faster-whisper small...")
        model = WhisperModel("small", device="cpu", compute_type="int8")

        opts = {
            "beam_size": 5,
            "word_timestamps": True,
            "vad_filter": True,
            "vad_parameters": {
                "min_silence_duration_ms": 300,
                "speech_pad_ms": 400,  # More padding to avoid early triggers   # Add padding around speech to avoid cutting words
            },
            "no_speech_threshold": 0.6,
            "condition_on_previous_text": False,
            "task": "transcribe",
            "temperature": 0.0,
            "prepend_punctuations": "\"'¿([{-",
            "append_punctuations": "\"'.。,，!！?？:：\")]}、",
        }
        if language:
            opts["language"] = language

        try:
            raw_segs, info = model.transcribe(file_path, **opts)
        except ValueError as e:
            # faster-whisper's language auto-detection can raise
            # "max() arg is an empty sequence" when VAD strips all audio
            # from a silent/non-speech file before any language probabilities
            # exist to choose from. That's a valid "no speech" outcome, not
            # a real failure.
            logger.info(f"No speech detected ({e}) — treating as a silent/non-speech video.")
            return TranscriptionResult(
                segments=[], full_text="", language="unknown",
                duration_seconds=self._probe_duration(file_path),
            )

        words = []
        for seg in raw_segs:
            is_music = self._is_music(seg.text)
            for w in (seg.words or []):
                word = w.word.strip()
                if not word:
                    continue
                # Apply timing offset correction
                start = max(0.0, round(w.start - TIMING_OFFSET, 3))
                end   = max(start + 0.05, round(w.end - TIMING_OFFSET, 3))
                words.append({
                    "word":     word,
                    "start":    start,
                    "end":      end,
                    "is_music": is_music,
                    "speaker":  "S0",
                })

        if not words:
            # No speech detected (e.g. a silent video) — this is a valid outcome,
            # not a failure. Let the pipeline fall back to scene-explainer-only
            # captions instead of aborting the whole job.
            logger.info("No speech detected — treating as a silent/non-speech video.")
            return TranscriptionResult(
                segments=[], full_text="", language=info.language,
                duration_seconds=info.duration,
            )

        # Speaker diarization
        wav_path = self._extract_wav(file_path)
        try:
            speaker_map = self._diarize_pitch(wav_path, words)
            for w in words:
                w["speaker"] = speaker_map.get(w["start"], "S0")
        except Exception as e:
            logger.warning(f"Diarization failed: {e}")
        finally:
            if os.path.exists(wav_path):
                os.remove(wav_path)

        segments = self._build_subtitles(words)
        segments = self._fix_common_mishearings(segments)
        segments = self._remove_isolated_short_segments(segments)
        logger.info(f"Done: {len(words)} words → {len(segments)} subtitles, lang={info.language}")

        return TranscriptionResult(
            segments=segments,
            full_text=" ".join(s.text for s in segments if not s.is_music),
            language=info.language,
            duration_seconds=segments[-1].end if segments else 0.0,
        )

    def _remove_isolated_short_segments(self, segments):
        """
        Remove short segments that are isolated by large gaps on both sides.
        These are typically Whisper hallucinations during music/silence.
        
        A segment is suspicious if:
        - It is 1-2 words
        - The gap BEFORE it is > 5 seconds (likely music playing)
        - The gap AFTER it is > 5 seconds (music continues)
        """
        if len(segments) < 3:
            return segments

        result = []
        for i, seg in enumerate(segments):
            words = seg.text.strip().split()
            is_short = len(words) <= 2 and not seg.is_music

            if not is_short:
                result.append(seg)
                continue

            gap_before = seg.start - segments[i-1].end if i > 0 else 0
            gap_after  = segments[i+1].start - seg.end if i < len(segments)-1 else 0

            # Isolated short segment surrounded by large gaps = likely hallucination
            if gap_before > 5.0 and gap_after > 5.0:
                logger.info(f"Removing likely hallucination: '{seg.text}' at {seg.start:.1f}s "
                           f"(gap_before={gap_before:.1f}s, gap_after={gap_after:.1f}s)")
                continue

            result.append(seg)

        return result

    def _fix_common_mishearings(self, segments):
        """
        Post-process corrections for common Whisper mishearings.
        Applied as word replacements on the final subtitle text.
        """
        import re
        corrections = [
            # Pattern, replacement (case-insensitive word boundary match)
            (r'\bHim\b (\d+)', r'Hymn \1'),      # "Him 17" → "Hymn 17"
            (r'\bhim (\d+)\b', r'Hymn \1'),
            (r"\bma 'am\b", "ma'am"),               # "ma 'am" → "ma'am"
            (r"\bma' am\b", "ma'am"),
        ]
        for seg in segments:
            text = seg.text
            for pattern, replacement in corrections:
                text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
            seg.text = text
        return segments

    # ── openai-whisper fallback ─────────────────────────────────────────

    def _openai_whisper(self, file_path: str, language: Optional[str]) -> TranscriptionResult:
        from app.core.model_cache import ModelCache
        model = ModelCache.get_whisper()
        if model is None:
            raise ImportError("openai-whisper not loaded")

        logger.info("Using openai-whisper fallback...")
        opts = {
            "verbose": False, "task": "transcribe",
            "temperature": 0.0, "no_speech_threshold": 0.6,
            "condition_on_previous_text": False,
        }
        if language:
            opts["language"] = language

        raw  = model.transcribe(file_path, **opts)
        segs = []

        for seg in raw.get("segments", []):
            text = seg.get("text", "").strip()
            if not text or seg.get("no_speech_prob", 0) > 0.6:
                continue
            start    = round(float(seg["start"]), 3)
            end      = round(float(seg["end"]),   3)
            dur      = end - start
            is_music = self._is_music(text)
            chunks   = self._split_at_punctuation(text)
            total    = sum(len(c) for c in chunks) or 1
            cursor   = start
            for i, chunk in enumerate(chunks):
                cend = end if i == len(chunks)-1 else round(
                    min(cursor + max(MIN_DURATION, dur * len(chunk) / total), end), 3)
                segs.append(TranscriptionSegment(start=cursor, end=cend, text=chunk, is_music=is_music))
                cursor = cend

        return TranscriptionResult(
            segs, " ".join(s.text for s in segs),
            raw.get("language", "unknown"), segs[-1].end if segs else 0.0,
        )

    def _probe_duration(self, file_path: str) -> float:
        """Get the media duration directly via ffprobe, independent of Whisper."""
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", file_path],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            return float(result.stdout.strip())
        except (ValueError, OSError):
            return 0.0

    # ── Speaker diarization ─────────────────────────────────────────────

    def _extract_wav(self, file_path: str) -> str:
        wav = file_path + "_spk.wav"
        subprocess.run([
            "ffmpeg", "-y", "-i", file_path,
            "-vn", "-ac", "1", "-ar", "16000",
            "-acodec", "pcm_s16le", wav
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return wav

    def _diarize_pitch(self, wav_path: str, words: list[dict]) -> dict:
        """
        Pitch-based speaker diarization using librosa.yin.
        Works with any NumPy version. Male ~85-165Hz, Female ~165-265Hz.

        Classifies by contiguous speech RUN (words with no pause > 0.35s
        between them), not by individual word. Per-word classification is
        too noisy: a single speaker's own sentence naturally rises and
        falls in pitch (intonation), which was enough to flip individual
        words across the median and mislabel one person's continuous
        sentence as multiple speakers. A run of uninterrupted speech is
        almost always one speaker, so it gets one pitch estimate and one
        consistent label.
        """
        try:
            import librosa

            y, sr = librosa.load(wav_path, sr=16000, mono=True)
            hop   = 512

            # yin is more robust than piptrack and numpy-version independent
            f0 = librosa.yin(y, fmin=60, fmax=400, hop_length=hop)

            def avg_pitch(s, e):
                sf = max(0, int(s * sr / hop))
                ef = min(len(f0), int(e * sr / hop))
                if sf >= ef:
                    return 0.0
                chunk   = f0[sf:ef]
                nonzero = chunk[chunk > 50]  # Filter out unvoiced frames
                return float(np.median(nonzero)) if len(nonzero) else 0.0

            # Group words into runs, splitting only at real pauses —
            # mirrors _diarize_pauses' own turn-taking threshold.
            PAUSE = 0.35
            runs: list[list[dict]] = []
            for w in words:
                if runs and w["start"] - runs[-1][-1]["end"] <= PAUSE:
                    runs[-1].append(w)
                else:
                    runs.append([w])

            run_pitches = [avg_pitch(run[0]["start"], run[-1]["end"]) for run in runs]
            nonzero = [p for p in run_pitches if p > 50]

            if len(nonzero) < 2 or len(set(nonzero)) < 2:
                logger.info("Not enough pitch variation — using pause diarization.")
                return self._diarize_pauses(words)

            median = float(np.median(nonzero))
            logger.info(f"Pitch diarization: median={median:.1f}Hz across {len(runs)} run(s)")

            spk_map = {}
            last_label = "S0"
            for run, p in zip(runs, run_pitches):
                # Unvoiced run (p < 50) — carry forward the previous speaker
                # rather than guessing, since there's no pitch signal to use.
                label = last_label if p < 50 else ("S1" if p > median else "S0")
                last_label = label
                for w in run:
                    spk_map[w["start"]] = label

            return spk_map

        except Exception as e:
            logger.warning(f"Pitch diarization failed: {e}")
            return self._diarize_pauses(words)

    def _diarize_pauses(self, words: list[dict]) -> dict:
        """Fallback: toggle speaker at pauses > 0.35s."""
        PAUSE = 0.35
        spk_map = {}
        cur     = 0
        for i, w in enumerate(words):
            if i > 0 and w["start"] - words[i-1]["end"] > PAUSE:
                cur = 1 - cur
            spk_map[w["start"]] = f"S{cur}"
        return spk_map

    # ── Subtitle builder ────────────────────────────────────────────────

    def _build_subtitles(self, words: list[dict]) -> list[TranscriptionSegment]:
        SENTENCE_END = set('.!?')
        CLAUSE_END   = set(',;:—')

        segments     = []
        line_text    = ""
        line_start   = None
        line_speaker = "S0"
        line_music   = False

        def flush(end_time):
            nonlocal line_text, line_start
            text = line_text.strip()
            if not text:
                return
            display = f"♪ {text}" if line_music else text
            segments.append(TranscriptionSegment(
                start=round(line_start, 3),
                end=round(end_time, 3),
                text=display,
                is_music=line_music,
                speaker_id=line_speaker,
            ))
            line_text  = ""
            line_start = None

        for i, w in enumerate(words):
            word     = w["word"]
            speaker  = w["speaker"]
            is_music = w["is_music"]
            is_last  = (i == len(words) - 1)

            # Speaker change → flush
            if line_start is not None and speaker != line_speaker and line_text:
                flush(words[i-1]["end"])
                line_speaker = speaker
                line_music   = is_music

            if line_start is None:
                line_start   = w["start"]
                line_speaker = speaker
                line_music   = is_music

            test     = (line_text + " " + word).strip()
            last_ch  = word.rstrip()[-1] if word.strip() else ""

            if len(test) > MAX_CHARS and line_text:
                flush(words[i-1]["end"])
                line_start   = w["start"]
                line_speaker = speaker
                line_music   = is_music
                test         = word

            line_text = test

            if (last_ch in SENTENCE_END or
               (last_ch in CLAUSE_END and len(line_text) >= 20) or
                is_last) and line_text.strip():
                flush(w["end"])

        return segments

    # ── Helpers ─────────────────────────────────────────────────────────

    def _is_music(self, text: str) -> bool:
        if any(m in text for m in ['♪', '♫', '🎵', '🎶']):
            return True
        return bool(re.match(r'^\s*[\(\[].*(?:music|song|singing|instrumental).*[\)\]]\s*$', text, re.I))

    def _split_at_punctuation(self, text: str) -> list[str]:
        parts  = re.split(r'(?<=[.!?,;:])\s+', text.strip())
        result = []
        for part in parts:
            part = part.strip()
            if not part:
                continue
            if len(part) <= MAX_CHARS:
                result.append(part)
            else:
                words, line = part.split(), ""
                for word in words:
                    test = (line + " " + word).strip()
                    if len(test) <= MAX_CHARS:
                        line = test
                    else:
                        if line: result.append(line)
                        line = word
                if line: result.append(line)
        return [r for r in result if r] or [text]
