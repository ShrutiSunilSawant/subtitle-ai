"""
subtitle_merger.py — Merges speech + scene explainers into final SRT.
Post-processes to merge orphaned words and clamp long captions.
"""

import os
import logging
from dataclasses import dataclass
from app.transcription.transcription_service import TranscriptionSegment
from app.explainers.blip_explainer import SceneExplainer
from app.models.schemas import SubtitleEntry

logger = logging.getLogger(__name__)

MIN_WORDS_STANDALONE = 3    # Merge fragments under 3 words
MAX_EXPLAINER_SEC    = 5.0  # Scene captions show max 5 seconds
MAX_MERGE_GAP        = 0.35 # Max gap to merge adjacent orphan words


@dataclass
class MergedSubtitle:
    index:       int
    start:       float
    end:         float
    text:        str
    is_explainer: bool
    speaker_id:  str = "S0"


class SubtitleMerger:

    def merge(self, speech_segments, scene_explainers) -> list[MergedSubtitle]:
        all_entries = []

        for seg in speech_segments:
            text = seg.text.strip()
            if text:
                all_entries.append(MergedSubtitle(
                    index=0, start=seg.start, end=seg.end,
                    text=text, is_explainer=False,
                    speaker_id=getattr(seg, 'speaker_id', 'S0'),
                ))

        for exp in scene_explainers:
            caption = exp.formatted_caption.strip()
            if caption:
                # Clamp scene caption to max 5 seconds
                end = min(exp.end_time, exp.start_time + MAX_EXPLAINER_SEC)
                all_entries.append(MergedSubtitle(
                    index=0, start=exp.start_time, end=end,
                    text=caption, is_explainer=True,
                ))

        all_entries.sort(key=lambda e: e.start)
        all_entries = self._merge_orphans(all_entries)

        for i, e in enumerate(all_entries, 1):
            e.index = i

        logger.info(f"Total: {len(all_entries)} subtitle entries")
        return all_entries

    def _merge_orphans(self, entries: list[MergedSubtitle]) -> list[MergedSubtitle]:
        """
        Only merge truly isolated single words with their natural neighbor.
        Rules:
        - Only merge if gap < 0.15s (words cut by Whisper at segment boundary)
        - Never merge across speaker changes
        - Never merge two complete sentences
        - "Hey," before an explainer → merge with next speech after explainer
        - Orphan ending with punctuation → merge backward
        - Orphan not ending with punctuation → merge forward
        """
        if not entries:
            return entries

        result = []
        i = 0

        while i < len(entries):
            e = entries[i]

            if e.is_explainer:
                result.append(e)
                i += 1
                continue

            words    = e.text.strip().split()
            duration = e.end - e.start

            # Only consider truly single/double word orphans with very short duration
            is_orphan = len(words) <= 1 or (len(words) == 2 and duration < 0.3)

            if not is_orphan:
                result.append(e)
                i += 1
                continue

            ends_with_punct = e.text.strip()[-1] in '.!?,' if e.text.strip() else False

            # Find previous speech entry
            prev = next((r for r in reversed(result) if not r.is_explainer), None)
            # Find next speech entry (skip explainers between)
            next_e = None
            for j in range(i + 1, len(entries)):
                if not entries[j].is_explainer:
                    next_e = entries[j]
                    break

            gap_prev = (e.start - prev.end)   if prev   else 999
            gap_next = (next_e.start - e.end) if next_e else 999

            # Strict gap check — only merge if very close
            can_merge_prev = prev   and gap_prev < MAX_MERGE_GAP and prev.speaker_id == e.speaker_id
            can_merge_next = next_e and gap_next < MAX_MERGE_GAP and next_e.speaker_id == e.speaker_id

            if ends_with_punct and can_merge_prev:
                prev.text = prev.text.rstrip() + " " + e.text.strip()
                prev.end  = e.end
                i += 1
                continue
            elif not ends_with_punct and can_merge_next:
                next_e.text  = e.text.strip() + " " + next_e.text.lstrip()
                next_e.start = e.start
                i += 1
                continue
            else:
                result.append(e)
                i += 1

        return result

    def write_srt(self, entries, output_path) -> str:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            for e in entries:
                f.write(f"{e.index}\n")
                f.write(f"{self._fmt(e.start)} --> {self._fmt(e.end)}\n")
                f.write(f"{e.text}\n\n")
        logger.info(f"SRT written: {output_path} ({len(entries)} entries)")
        return output_path

    def write_transcript(self, entries, output_path, include_explainers=True) -> str:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            for e in entries:
                if not include_explainers and e.is_explainer:
                    continue
                f.write(e.text + "\n")
        return output_path

    def to_schema_entries(self, entries) -> list[SubtitleEntry]:
        return [
            SubtitleEntry(index=e.index, start_time=e.start, end_time=e.end,
                         text=e.text, is_explainer=e.is_explainer)
            for e in entries
        ]

    @staticmethod
    def _fmt(s: float) -> str:
        ms = int(s * 1000)
        h  = ms // 3600000; ms %= 3600000
        m  = ms // 60000;   ms %= 60000
        s  = ms // 1000;    ms %= 1000
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
