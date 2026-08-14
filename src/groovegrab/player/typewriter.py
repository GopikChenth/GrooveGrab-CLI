"""
Exact 1:1 LRC Timestamped Lyric Character Animator
Follows exact start and end timestamps marked in the .lrc file for natural vocal synchronization
"""

from typing import Tuple
from groovegrab.player.lrc_parser import LrcLine


class TypewriterAnimator:
    """Calculates character typing cadence following exact LRC timestamps."""

    def render_active_line(
        self,
        line: LrcLine,
        current_time_sec: float,
        active_color: str = "bold bright_cyan"
    ) -> str:
        text = line.text
        if not text:
            return ""

        start = line.timestamp_sec
        end = line.end_sec or (start + 4.0)
        duration = max(0.5, end - start)

        elapsed = current_time_sec - start
        if elapsed <= 0:
            return ""
        
        # Follow exact 1:1 LRC line duration timing marked in the file
        progress = min(1.0, max(0.0, elapsed / duration))
        
        words = text.split(" ")
        num_words = len(words)
        
        if num_words <= 1:
            char_count = int(progress * len(text))
        else:
            word_idx = int(progress * num_words)
            word_idx = max(0, min(num_words - 1, word_idx))
            
            word_progress = (progress * num_words) - word_idx
            
            chars_completed = sum(len(w) + 1 for w in words[:word_idx])
            active_word = words[word_idx]
            
            active_chars = int(min(1.0, word_progress * 1.3) * len(active_word))
            char_count = chars_completed + active_chars

        char_count = min(len(text), max(1, char_count))
        typed_part = text[:char_count]

        return f"[{active_color}]{typed_part}[/{active_color}]"
