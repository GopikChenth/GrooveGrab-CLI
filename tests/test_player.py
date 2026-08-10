"""
Unit Tests for Synced LRC Parser and Typewriter Animator
"""

from groovegrab.player.lrc_parser import LrcParser, LrcLine
from groovegrab.player.typewriter import TypewriterAnimator


def test_lrc_parsing():
    parser = LrcParser()
    sample_lrc = """
[00:12.34]I had to tell ya, it's now or never
[00:18.50]So much for waiting around
[01:05.10]Outro line
    """
    lines = parser.parse_text(sample_lrc)

    assert len(lines) == 3
    assert lines[0].timestamp_sec == 12.34
    assert lines[0].text == "I had to tell ya, it's now or never"
    assert lines[1].timestamp_sec == 18.50


def test_typewriter_animator():
    animator = TypewriterAnimator()
    line = LrcLine(timestamp_sec=10.0, end_sec=15.0, text="Hello World")

    # Before start timestamp -> dim
    rendered_before = animator.render_active_line(line, 5.0)
    assert "Hello World" in rendered_before

    # Halfway -> partial typewriter text
    rendered_mid = animator.render_active_line(line, 12.5)
    assert "Hello" in rendered_mid
