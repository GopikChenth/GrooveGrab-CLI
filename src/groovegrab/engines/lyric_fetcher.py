"""
LRCLIB Synced Lyrics Fetcher Engine
Robust query cleaning & fallback search for accurate synced lyrics fetching
"""

import re
from pathlib import Path
from typing import Optional, Tuple
import httpx

from groovegrab.core.models import TrackInfo

LRCLIB_API_URL = "https://lrclib.net/api/get"
LRCLIB_SEARCH_URL = "https://lrclib.net/api/search"


def clean_track_title(title: str) -> str:
    """Removes video tags like (Official Video), [Audio], (Lyrics), etc."""
    if not title:
        return ""
    # Strip bracketed content
    clean = re.sub(r'[\(\[\{].*?[\)\]\}]', '', title).strip()
    # Strip common file/video noise words if still present
    clean = re.sub(r'\b(official|video|audio|lyric|lyrics|hd|4k|remix|version)\b', '', clean, flags=re.IGNORECASE).strip()
    return clean or title


class LyricFetcher:
    """Fetches synced and plain lyrics from LRCLIB API with smart title cleaning."""

    def fetch_lyrics(self, track: TrackInfo) -> Tuple[Optional[str], Optional[str]]:
        """
        Returns a tuple of (synced_lyrics_lrc, plain_lyrics).
        """
        raw_title = track.title
        clean_title = clean_track_title(raw_title)
        artist = track.artist

        # 1. Try exact get query with clean title
        synced, plain = self._query_get(clean_title, artist, track.album, track.duration)
        if synced:
            return synced, plain

        # 2. Try exact get query with raw title
        if clean_title != raw_title:
            synced, plain = self._query_get(raw_title, artist, track.album, track.duration)
            if synced:
                return synced, plain

        # 3. Fallback search query
        return self._query_search(clean_title or raw_title, artist)

    def _query_get(
        self,
        title: str,
        artist: str,
        album: Optional[str] = None,
        duration: Optional[float] = None
    ) -> Tuple[Optional[str], Optional[str]]:
        params = {
            "track_name": title,
            "artist_name": artist,
        }
        if album:
            params["album_name"] = album

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

    def _query_search(self, query: str, artist: str) -> Tuple[Optional[str], Optional[str]]:
        search_str = f"{query} {artist}".strip()
        try:
            resp = httpx.get(LRCLIB_SEARCH_URL, params={"q": search_str}, timeout=8.0)
            if resp.status_code == 200:
                results = resp.json()
                if isinstance(results, list):
                    for item in results:
                        synced = item.get("syncedLyrics")
                        if synced:
                            return synced, item.get("plainLyrics")
        except Exception:
            pass
        return None, None

    def save_lrc_file(self, audio_file_path: Path, synced_lyrics: str) -> Path:
        lrc_path = audio_file_path.with_suffix(".lrc")
        with open(lrc_path, "w", encoding="utf-8") as f:
            f.write(synced_lyrics)
        return lrc_path
