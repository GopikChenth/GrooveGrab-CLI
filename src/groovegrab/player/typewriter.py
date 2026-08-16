"""
AI Word-Level & Natural Singing Cadence Lyric Typewriter Animator
Supports exact millisecond word-by-word acoustic alignment (Meta MMS_FA) with natural cadence fallback.
"""

from typing import List
from groovegrab.player.lrc_parser import LrcLine, WordTiming


class TypewriterAnimator:
    """Calculates character/word reveal matching exact acoustic word timestamps."""

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
        elapsed = current_time_sec - start
        if elapsed <= 0:
            return ""

        # 1. AI Word-Level Sync (100% Exact Millisecond Acoustic Word Reveal)
        if line.words and len(line.words) > 0:
            rendered_words: List[str] = []
            for w in line.words:
                w_duration = min(0.6, max(0.15, w.end_sec - w.start_sec))
                w_finish = w.start_sec + w_duration

                if current_time_sec >= w_finish:
                    # Word has been fully sung
                    rendered_words.append(w.word)
                elif current_time_sec >= w.start_sec:
                    # Word is actively being vocalized right now (sub-word character reveal)
                    w_elapsed = current_time_sec - w.start_sec
                    w_progress = min(1.0, max(0.0, w_elapsed / w_duration))
                    chars_shown = max(1, int(w_progress * len(w.word)))
                    rendered_words.append(w.word[:chars_shown])
                    break
                else:
                    # Word has not been sung yet
                    break

            if rendered_words:
                typed_part = " ".join(rendered_words)
                return f"[{active_color}]{typed_part}[/{active_color}]"

        # 2. Natural Singing Cadence Fallback (~14 chars/sec)
        available_gap = max(0.5, (line.end_sec - start) if line.end_sec else 4.0)
        natural_vocal_time = len(text) / 14.0

        if natural_vocal_time >= available_gap:
            typing_duration = max(0.4, available_gap * 0.88)
        else:
            typing_duration = max(1.0, min(3.5, natural_vocal_time))

        progress = min(1.0, max(0.0, elapsed / max(0.3, typing_duration)))
        char_count = int(progress * len(text))
        char_count = max(1, min(len(text), char_count))

        typed_part = text[:char_count]
        return f"[{active_color}]{typed_part}[/{active_color}]"
