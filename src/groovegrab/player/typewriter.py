"""
Typewriter Karaoke Lyric Character Animator
"""

from typing import Tuple
from groovegrab.player.lrc_parser import LrcLine


class TypewriterAnimator:
    """Calculates character reveal count and styling for active lyric lines."""

    def render_active_line(
        self,
        line: LrcLine,
        current_time_sec: float,
        active_color: str = "bold bright_cyan",
        dim_color: str = "dim white"
    ) -> str:
        text = line.text
        if not text:
            return ""

        start = line.timestamp_sec
        end = line.end_sec or (start + 4.0)
        duration = max(0.5, end - start)

        elapsed = current_time_sec - start
        if elapsed <= 0:
            return f"[{dim_color}]{text}[/{dim_color}]"
        
        progress = min(1.0, elapsed / duration)
        char_count = int(progress * len(text))
        char_count = min(len(text), max(1, char_count))

        typed_part = text[:char_count]
        remaining_part = text[char_count:]

        return f"[{active_color}]{typed_part}[/{active_color}][{dim_color}]{remaining_part}[/{dim_color}]"
