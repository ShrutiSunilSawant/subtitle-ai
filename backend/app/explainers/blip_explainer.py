"""
blip_explainer.py
=================
Generates SHORT action-focused scene descriptions for non-speech segments.
Target output: [Guitar playing], [Music playing], [Footsteps approaching]

Uses BLIP for visual context, then maps to action-focused descriptions.
"""

import os
import re
import logging
from dataclasses import dataclass
from PIL import Image
from app.core.model_cache import ModelCache
from app.video_processing.frame_extractor import ExtractedFrame

logger = logging.getLogger(__name__)

# Action keyword mapping — if BLIP caption contains these, use short label
ACTION_MAP = [
    (["guitar", "playing guitar", "strumming", "acoustic", "electric guitar", "six string"], "Guitar playing"),
    (["piano", "playing piano", "keyboard", "keys"], "Piano playing"),
    (["violin", "fiddle"],                           "Violin playing"),
    (["drum", "drumming"],                           "Drums playing"),
    (["sing", "singing", "microphone"],              "Singing"),
    (["danc", "dancing"],                            "Dancing"),
    (["run", "running", "jogging"],                  "Running"),
    (["walk", "walking", "footstep"],                "Footsteps"),
    (["laugh", "laughing", "smile", "smiling"],      "Laughter"),
    (["cry", "crying", "tears"],                     "Crying"),
    (["kiss", "kissing", "embrace", "hugging"],      "Embracing"),
    (["fight", "fighting", "punch", "punching"],     "Fighting"),
    (["car", "driving", "vehicle", "road"],          "Car driving"),
    (["rain", "raining", "storm", "thunder"],        "Rain falling"),
    (["fire", "flame", "burning"],                   "Fire burning"),
    (["eat", "eating", "food", "dining", "table"],   "Dining"),
    (["phone", "calling", "talking on"],             "On the phone"),
    (["read", "reading", "book"],                    "Reading"),
    (["cook", "cooking", "kitchen"],                 "Cooking"),
    (["crowd", "audience", "cheering"],              "Crowd cheering"),
    (["church", "pray", "praying"],                  "Prayer"),
    (["music", "instrument", "band", "orchestra"],   "Music playing"),
]


@dataclass
class SceneExplainer:
    frame:      ExtractedFrame
    caption:    str
    start_time: float
    end_time:   float

    @property
    def formatted_caption(self) -> str:
        return f"[{self.caption}]"


class BLIPExplainer:

    def generate_explainers(self, frames: list[ExtractedFrame]) -> list[SceneExplainer]:
        if not frames:
            return []

        processor, model = ModelCache.get_blip()
        if processor is None or model is None:
            logger.error("BLIP model not loaded.")
            return []

        explainers = []
        prev = ""

        for frame in frames:
            raw_caption = self._get_raw_caption(frame.frame_path, processor, model)
            if not raw_caption:
                continue

            # Map to a short action label when it matches a known category,
            # otherwise fall back to a humanized version of BLIP's own caption
            # so every silent segment gets a description, not just the ones
            # that happen to match our curated list.
            caption = self._to_action_label(raw_caption) or self._humanize(raw_caption)

            # Skip duplicates
            if caption.lower() == prev.lower():
                logger.debug(f"Skipping duplicate: '{caption}'")
                continue

            prev = caption
            explainers.append(SceneExplainer(
                frame=frame,
                caption=caption,
                start_time=frame.segment.start,
                end_time=frame.segment.end,
            ))
            logger.info(f"[{frame.timestamp_sec:.1f}s] → [{caption}]")

        logger.info(f"Generated {len(explainers)} scene description(s).")
        return explainers

    def _get_raw_caption(self, frame_path: str, processor, model) -> str | None:
        """
        Get an unconditional BLIP caption for the frame.

        Deliberately does NOT prime the model with a leading prompt like
        "a person playing guitar" — conditional captioning models tend to
        echo/complete whatever prompt they're given, so a fixed instrument
        hint biases nearly every caption toward that instrument regardless
        of what's actually in the frame (verified: it captioned an unrelated
        test pattern as "person playing guitar").
        """
        import torch

        if not os.path.exists(frame_path):
            return None
        try:
            image  = Image.open(frame_path).convert("RGB")
            inputs = processor(image, return_tensors="pt")
            with torch.no_grad():
                out = model.generate(
                    **inputs,
                    max_new_tokens=30,
                    num_beams=4,
                    repetition_penalty=1.3,
                )
            return processor.decode(out[0], skip_special_tokens=True).strip().lower()
        except Exception as e:
            logger.error(f"BLIP error: {e}")
            return None

    def _humanize(self, caption: str) -> str:
        """
        Fallback for captions that don't match a curated ACTION_MAP category —
        turn BLIP's raw output into a short scene description instead of
        dropping the segment entirely.
        """
        text = caption.strip()
        if not text:
            return "Scene"
        for prefix in ("a photo of ", "an image of ", "a picture of "):
            if text.startswith(prefix):
                text = text[len(prefix):]
                break
        return text[0].upper() + text[1:] if text else "Scene"

    def _to_action_label(self, caption: str) -> str | None:
        """
        Map BLIP raw description to a short action label.
        Instruments take priority over setting (e.g. guitar over dining table).
        Skip generic people descriptions.
        """
        caption_lower = caption.lower()

        # Word-boundary matching, not plain substring — otherwise short
        # keywords false-positive inside unrelated words (e.g. "rain"
        # matching inside "rainbow", which mislabeled a TV-color-bars
        # scene as "Rain falling").
        for keywords, label in ACTION_MAP:
            if any(re.search(rf"\b{re.escape(kw)}\b", caption_lower) for kw in keywords):
                return label

        # No curated category matched — caller falls back to _humanize()
        logger.debug(f"No action category match for: '{caption}'")
        return None

