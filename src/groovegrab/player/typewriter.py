"""
Natural Vocal Cadence Lyric Typewriter Animator
Paces character and word reveal to match the singing tempo and time duration of each line.
"""

from groovegrab.player.lrc_parser import LrcLine


class TypewriterAnimator:
    """Calculates character reveal matching singing tempo and line duration."""

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

        # Available time gap until next line
        line_gap = (line.end_sec - start) if line.end_sec else 4.0
        words = text.split()
        num_words = max(1, len(words))

        # Singing duration is proportional to words and line interval (~80% of gap)
        singing_duration = max(0.8, min(line_gap * 0.82, max(1.2, num_words * 0.40)))

        if elapsed >= singing_duration:
            # Line completed: show 100% of line
            return f"[{active_color}]{text}[/{active_color}]"

        # Paced character reveal across singing duration
        progress = min(1.0, max(0.0, elapsed / singing_duration))
        char_count = max(1, min(len(text), int(progress * len(text))))

        typed_part = text[:char_count]
        return f"[{active_color}]{typed_part}[/{active_color}]"
