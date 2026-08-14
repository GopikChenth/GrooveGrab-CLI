"""
Unit Tests for Synced LRC Parser, Typewriter Animator, and LyricSyncStore
"""

from groovegrab.player.lrc_parser import LrcParser, LrcLine
from groovegrab.player.typewriter import TypewriterAnimator
from groovegrab.player.lyric_sync_store import LyricSyncStore


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

    # Before start timestamp -> empty string (no dull text preview!)
    rendered_before = animator.render_active_line(line, 5.0)
    assert rendered_before == ""

    # Halfway -> partial typewriter text
    rendered_mid = animator.render_active_line(line, 12.5)
    assert "Hello" in rendered_mid


def test_lyric_sync_store():
    store = LyricSyncStore()
    store.save_offset("Loser", "Tame Impala", 1.5)
    
    saved_offset = store.get_offset("Loser", "Tame Impala")
    assert saved_offset == 1.5
