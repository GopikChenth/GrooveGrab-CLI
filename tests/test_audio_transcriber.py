"""
Unit Tests for AudioTranscriber AI Word-Level Forced Alignment Engine
"""

from pathlib import Path
from groovegrab.engines.audio_transcriber import AudioTranscriber
from groovegrab.player.lrc_parser import LrcLine, WordTiming
from groovegrab.player.typewriter import TypewriterAnimator


def test_audio_transcriber_initialization():
    transcriber = AudioTranscriber()
    assert transcriber._is_initialized is False
    assert transcriber.cache_dir.exists()


def test_word_level_typewriter_reveal():
    animator = TypewriterAnimator()
    line = LrcLine(
        timestamp_sec=10.0,
        end_sec=14.0,
        text="I had to tell ya",
        words=[
            WordTiming(word="I", start_sec=10.0, end_sec=10.4),
            WordTiming(word="had", start_sec=10.5, end_sec=10.9),
            WordTiming(word="to", start_sec=11.0, end_sec=11.3),
            WordTiming(word="tell", start_sec=11.4, end_sec=11.9),
            WordTiming(word="ya", start_sec=12.0, end_sec=12.5),
        ]
    )

    # Before start -> empty string
    assert animator.render_active_line(line, 9.5) == ""

    # At 10.6s -> "I had"
    rendered = animator.render_active_line(line, 10.6)
    assert "I" in rendered

    # At 11.2s -> "I had to"
    rendered_mid = animator.render_active_line(line, 11.2)
    assert "had" in rendered_mid

    # At 13.0s -> all words fully rendered
    rendered_full = animator.render_active_line(line, 13.0)
    assert "I had to tell ya" in rendered_full
