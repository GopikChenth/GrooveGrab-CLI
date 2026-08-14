"""
Fast Word-by-Word Typewriter Karaoke Lyric Animator
Types characters rapidly per word with natural pause cadence on spaces
"""

from typing import Tuple
from groovegrab.player.lrc_parser import LrcLine


class TypewriterAnimator:
    """Calculates fast character typing and space pause cadence for active lyric lines."""

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
        
        # Word-by-word fast typewriter with pause on spaces
        words = text.split(" ")
        num_words = len(words)
        
        if num_words <= 1:
            char_count = int(min(1.0, progress * 1.6) * len(text))
        else:
            word_idx = int(progress * num_words)
            word_idx = max(0, min(num_words - 1, word_idx))
            
            # Progress within active word slot
            word_progress = (progress * num_words) - word_idx
            
            # Chars of completed words + fast burst for current active word
            chars_completed = sum(len(w) + 1 for w in words[:word_idx])
            active_word = words[word_idx]
            
            # Fast character typing burst (1.8x speed) then pause on space
            active_chars = int(min(1.0, word_progress * 1.8) * len(active_word))
            char_count = chars_completed + active_chars

        char_count = min(len(text), max(1, char_count))

        typed_part = text[:char_count]
        remaining_part = text[char_count:]

        return f"[{active_color}]{typed_part}[/{active_color}][{dim_color}]{remaining_part}[/{dim_color}]"
