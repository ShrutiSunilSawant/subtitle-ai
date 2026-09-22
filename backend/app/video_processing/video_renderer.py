"""
video_renderer.py — Netflix-style subtitle rendering.
Clean white text, black outline, proper size and position.
"""

import os
import logging
import subprocess

logger = logging.getLogger(__name__)

# Netflix/OTT standard subtitle style
STYLE = (
    "FontName=Arial,"
    "FontSize=18,"
    "PrimaryColour=&H00FFFFFF,"   # White
    "OutlineColour=&H00000000,"   # Black outline
    "BackColour=&H64000000,"      # Subtle dark background
    "Bold=0,"
    "Outline=2,"
    "Shadow=0,"
    "Alignment=2,"                # Bottom center
    "MarginV=30,"
    "MarginL=60,"
    "MarginR=60,"
    "WrapStyle=0"
)


class VideoRenderer:

    def burn_subtitles(self, input_path: str, srt_path: str, output_path: str) -> str:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        escaped = srt_path.replace("\\", "/").replace(":", "\\:")
        vf      = f"subtitles='{escaped}':force_style='{STYLE}'"

        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-vf", vf,
            "-c:v", "libx264", "-crf", "20", "-preset", "fast",
            "-c:a", "copy",
            "-movflags", "+faststart",
            output_path,
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg failed: {result.stderr.decode(errors='replace')[-400:]}")
        logger.info(f"Video rendered: {output_path}")
        return output_path

    def copy_without_subtitles(self, input_path: str, output_path: str) -> str:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        cmd = ["ffmpeg", "-y", "-i", input_path, "-c", "copy", "-movflags", "+faststart", output_path]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg copy failed: {result.stderr.decode()[-300:]}")
        return output_path
