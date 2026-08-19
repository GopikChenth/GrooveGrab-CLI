"""
Unit Tests for MPRIS2 D-Bus Media Player Engine and Live Lyrics Fetcher
"""

import time
from groovegrab.engines.mpris_engine import MprisEngine, MprisTrackInfo
from groovegrab.engines.lyric_fetcher import LyricFetcher


def test_mpris_track_info_model():
    info = MprisTrackInfo(
        title="Blinding Lights",
        artist="The Weeknd",
        album="After Hours",
        duration_sec=200.0,
        position_sec=45.0,
        status="Playing",
        player_name="spotify",
        track_id="spotify:track:0VjIjW4GlUZAMYd2vXMi3b"
    )

    assert info.display_name() == "The Weeknd - Blinding Lights"
    assert info.duration_sec == 200.0
    assert info.status == "Playing"


def test_mpris_engine_interpolation():
    engine = MprisEngine()
    info = MprisTrackInfo(
        title="Song",
        artist="Artist",
        duration_sec=300.0,
        position_sec=10.0,
        status="Playing",
        poll_timestamp=time.monotonic() - 2.5
    )

    interp_pos = engine.get_interpolated_position(info)
    assert 12.4 <= interp_pos <= 12.6

    # When paused, interpolation stays constant
    info.status = "Paused"
    paused_pos = engine.get_interpolated_position(info)
    assert paused_pos == 10.0


def test_mpris_player_discovery():
    engine = MprisEngine()
    players = engine.list_active_players()
    assert isinstance(players, list)


def test_lyric_fetcher_metadata_query():
    fetcher = LyricFetcher()
    synced, _ = fetcher.fetch_lyrics_by_metadata(
        title="Starboy",
        artist="The Weeknd",
        duration=230.0
    )
    # If network is available or cached, it returns synced lrc string with timestamps
    if synced:
        assert "[" in synced and "]" in synced
