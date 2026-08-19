"""
LRCLIB & SyncedLyrics Synced Lyrics Fetcher Engine
Robust query cleaning, LRCLIB API integration, syncedlyrics fallback, and persistent local cache.
"""

import re
import hashlib
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
    clean = re.sub(r'[\(\[\{].*?[\)\]\}]', '', title).strip()
    clean = re.sub(r'\b(official|video|audio|lyric|lyrics|hd|4k|remix|version)\b', '', clean, flags=re.IGNORECASE).strip()
    return clean or title


class LyricFetcher:
    """Fetches synced and plain lyrics from LRCLIB & syncedlyrics with smart cleaning and disk cache."""

    def __init__(self):
        self.cache_dir = Path.home() / ".cache" / "groovegrab" / "lyrics"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, title: str, artist: str) -> Path:
        key = f"{artist.lower().strip()}_{title.lower().strip()}"
        h = hashlib.md5(key.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{h}.lrc"

    def fetch_lyrics(self, track: TrackInfo) -> Tuple[Optional[str], Optional[str]]:
        """Fetch lyrics for a TrackInfo model."""
        return self.fetch_lyrics_by_metadata(
            title=track.title,
            artist=track.artist,
            album=track.album,
            duration=track.duration
        )

    def fetch_lyrics_by_metadata(
        self,
        title: str,
        artist: str,
        album: Optional[str] = None,
        duration: Optional[float] = None
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Fetches synced lyrics using metadata from local cache, LRCLIB, or syncedlyrics fallback.
        """
        if not title:
            return None, None

        cache_path = self._get_cache_path(title, artist)
        if cache_path.exists():
            try:
                cached_text = cache_path.read_text(encoding="utf-8")
                if cached_text.strip():
                    return cached_text, None
            except Exception:
                pass

        raw_title = title
        clean_title = clean_track_title(raw_title)

        # 1. Query LRCLIB GET API with exact cleaned title
        synced, plain = self._query_lrclib_get(clean_title, artist, album, duration)
        if synced:
            self._save_cache(cache_path, synced)
            return synced, plain

        # 2. Query LRCLIB GET API with raw title if different
        if clean_title != raw_title:
            synced, plain = self._query_lrclib_get(raw_title, artist, album, duration)
            if synced:
                self._save_cache(cache_path, synced)
                return synced, plain

        # 3. Query LRCLIB Search endpoint
        synced, plain = self._query_lrclib_search(clean_title or raw_title, artist)
        if synced:
            self._save_cache(cache_path, synced)
            return synced, plain

        # 4. Fallback to syncedlyrics (Spotify original lyrics / Musixmatch / NetEase / Megalobiz)
        synced = self._query_syncedlyrics(clean_title or raw_title, artist)
        if synced:
            self._save_cache(cache_path, synced)
            return synced, None

        return None, None

    def _query_lrclib_get(
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
        if duration and duration > 0:
            params["duration"] = int(duration)

        try:
            resp = httpx.get(LRCLIB_API_URL, params=params, timeout=6.0)
            if resp.status_code == 200:
                data = resp.json()
                synced = data.get("syncedLyrics")
                plain = data.get("plainLyrics")
                if synced:
                    return synced, plain
        except Exception:
            pass
        return None, None

    def _query_lrclib_search(self, query: str, artist: str) -> Tuple[Optional[str], Optional[str]]:
        search_str = f"{query} {artist}".strip()
        try:
            resp = httpx.get(LRCLIB_SEARCH_URL, params={"q": search_str}, timeout=6.0)
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

    def _query_syncedlyrics(self, title: str, artist: str) -> Optional[str]:
        try:
            import syncedlyrics
            query = f"{title} {artist}".strip()
            lrc_text = syncedlyrics.search(query)
            if lrc_text and "[" in lrc_text:
                return lrc_text
        except Exception:
            pass
        return None

    def _save_cache(self, cache_path: Path, content: str):
        try:
            cache_path.write_text(content, encoding="utf-8")
        except Exception:
            pass

    def save_lrc_file(self, audio_file_path: Path, synced_lyrics: str) -> Path:
        lrc_path = audio_file_path.with_suffix(".lrc")
        with open(lrc_path, "w", encoding="utf-8") as f:
            f.write(synced_lyrics)
        return lrc_path
