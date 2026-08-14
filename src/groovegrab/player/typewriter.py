"""
Ultra-Fast Word-by-Word Typewriter Karaoke Lyric Animator
Types characters ultra-fast per word with zero pre-rendered dimmed text
"""

from typing import Tuple
from groovegrab.player.lrc_parser import LrcLine


class TypewriterAnimator:
    """Calculates ultra-fast character typing cadence without pre-rendering future text."""

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
        
        progress = min(1.0, elapsed / duration)
        
        # Word-by-word ultra-fast typewriter (2.8x speed burst per word)
        words = text.split(" ")
        num_words = len(words)
        
        if num_words <= 1:
            char_count = int(min(1.0, progress * 2.8) * len(text))
        else:
            word_idx = int(progress * num_words)
            word_idx = max(0, min(num_words - 1, word_idx))
            
            word_progress = (progress * num_words) - word_idx
            
            chars_completed = sum(len(w) + 1 for w in words[:word_idx])
            active_word = words[word_idx]
            
            # Ultra-fast character typing burst (2.8x speed)
            active_chars = int(min(1.0, word_progress * 2.8) * len(active_word))
            char_count = chars_completed + active_chars

        char_count = min(len(text), max(1, char_count))
        typed_part = text[:char_count]

        return f"[{active_color}]{typed_part}[/{active_color}]"
