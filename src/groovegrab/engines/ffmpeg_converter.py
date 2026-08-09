"""
FFmpeg Helper Engine
"""

import shutil
from typing import Tuple


class FfmpegHelper:
    @staticmethod
    def is_ffmpeg_installed() -> bool:
        return shutil.which("ffmpeg") is not None

    @staticmethod
    def get_ffmpeg_version() -> Tuple[bool, str]:
        ffmpeg_path = shutil.which("ffmpeg")
        if not ffmpeg_path:
            return False, "FFmpeg is not installed or not in PATH."
        return True, f"FFmpeg available at {ffmpeg_path}"
