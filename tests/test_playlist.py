"""
Unit tests for Playlist Folder Creation and Tracks Download in GrooveGrab-CLI
"""

from pathlib import Path
from groovegrab.core.models import PlaylistInfo, TrackInfo, DownloadOptions, MediaType
from groovegrab.cli.download import sanitize_filename


def test_playlist_sanitization_and_directory(tmp_path):
    playlist_title = "My / Cool : Playlist ? <2026>"
    safe_folder = sanitize_filename(playlist_title) or "Playlist"
    assert safe_folder == "My  Cool  Playlist  2026"

    output_dir = tmp_path / safe_folder
    output_dir.mkdir(parents=True, exist_ok=True)

    assert output_dir.exists()
    assert output_dir.is_dir()


def test_playlist_info_structure():
    tracks = [
        TrackInfo(title="Song 1", artist="Artist 1", media_type=MediaType.AUDIO),
        TrackInfo(title="Song 2", artist="Artist 2", media_type=MediaType.AUDIO),
    ]
    playlist = PlaylistInfo(title="Top Hits", author="DJ", tracks=tracks, provider_name="TestProvider")

    assert playlist.title == "Top Hits"
    assert len(playlist.tracks) == 2
    assert playlist.tracks[0].title == "Song 1"
