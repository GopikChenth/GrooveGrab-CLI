"""
LRCLIB Synced Lyrics Fetcher Engine
"""

from pathlib import Path
from typing import Optional, Tuple
import httpx

from groovegrab.core.models import TrackInfo

LRCLIB_API_URL = "https://lrclib.net/api/get"


class LyricFetcher:
    """Fetches synced and plain lyrics from LRCLIB API."""

    def fetch_lyrics(self, track: TrackInfo) -> Tuple[Optional[str], Optional[str]]:
        """
        Returns a tuple of (synced_lyrics_lrc, plain_lyrics).
        """
        params = {
            "track_name": track.title,
            "artist_name": track.artist,
        }
        if track.album:
            params["album_name"] = track.album
        if track.duration:
            params["duration"] = track.duration

        try:
            resp = httpx.get(LRCLIB_API_URL, params=params, timeout=8.0)
            if resp.status_code == 200:
                data = resp.json()
                synced = data.get("syncedLyrics")
                plain = data.get("plainLyrics")
                return synced, plain
        except Exception:
            pass
        return None, None

    def save_lrc_file(self, audio_file_path: Path, synced_lyrics: str) -> Path:
        lrc_path = audio_file_path.with_suffix(".lrc")
        with open(lrc_path, "w", encoding="utf-8") as f:
            f.write(synced_lyrics)
        return lrc_path
