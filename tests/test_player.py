"""
Unit Tests for Synced LRC Parser, Typewriter Animator, LyricSyncStore, and TimingChain
"""

import numpy as np
from groovegrab.player.lrc_parser import LrcParser, LrcLine
from groovegrab.player.typewriter import TypewriterAnimator
from groovegrab.player.lyric_sync_store import LyricSyncStore
from groovegrab.player.timing_chain import TimingChain


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

    # Before start timestamp -> empty string
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


def test_timing_chain():
    tc = TimingChain()
    pcm = np.ones(22050, dtype=np.float32) * 0.5

    dur = tc.inspect_audio(pcm, sample_rate=22050)
    assert round(dur, 1) == 1.0

    lyrics = [
        LrcLine(timestamp_sec=5.0, text="First line"),
        LrcLine(timestamp_sec=10.0, text="Second line"),
    ]
    idx, active = tc.find_active_line(lyrics, 4.0)
    assert active is None

    idx, active = tc.find_active_line(lyrics, 5.6)
    assert idx == 0
    assert active.text == "First line"
