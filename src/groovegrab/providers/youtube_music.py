"""
YouTube & YouTube Music Provider Plugin
Smart studio audio matching to avoid music video dialogue skits & ensure exact Spotify / LRCLIB sync.
"""

import re
from typing import List, Union
import yt_dlp

from groovegrab.providers.base import BaseProvider
from groovegrab.core.models import TrackInfo, PlaylistInfo, MediaType
from groovegrab.core.exceptions import ProviderError

YOUTUBE_URL_REGEX = re.compile(
    r'^(https?://)?(www\.|music\.)?(youtube\.com|youtu\.be)/(watch\?v=|playlist\?list=|v/|embed/|shorts/)?'
)


class YouTubeProvider(BaseProvider):
    @property
    def name(self) -> str:
        return "YouTube / YT Music"

    def can_handle(self, query_or_url: str) -> bool:
        if YOUTUBE_URL_REGEX.match(query_or_url):
            return True
        return False

    def resolve(self, query_or_url: str) -> Union[TrackInfo, PlaylistInfo]:
        is_url = query_or_url.startswith("http")
        target = query_or_url if is_url else f"ytsearch5:{query_or_url} Audio"

        ydl_opts = {
            'extract_flat': 'in_playlist',
            'skip_download': True,
            'quiet': True,
            'no_warnings': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(target, download=False)
            except Exception as e:
                raise ProviderError(f"Failed to extract info from YouTube: {e}")

        if not info:
            raise ProviderError("No metadata returned from YouTube.")

        # Handle Search wrapper or Playlist
        if 'entries' in info:
            entries = [e for e in info['entries'] if e]
            if not entries:
                raise ProviderError("No tracks found for search query.")
            
            if not is_url:
                best_entry = self._select_best_studio_track(entries, query_or_url)
                return self._parse_track_info(best_entry)

            tracks: List[TrackInfo] = []
            for entry in entries:
                tracks.append(self._parse_track_info(entry))
            
            return PlaylistInfo(
                title=info.get('title', 'YouTube Playlist'),
                description=info.get('description'),
                author=info.get('uploader') or info.get('channel'),
                tracks=tracks,
                cover_url=self._get_thumbnail(info),
                provider_name=self.name
            )

        # Single Track
        return self._parse_track_info(info)

    def _select_best_studio_track(self, entries: List[dict], query: str) -> dict:
        """
        Ranks search candidates to prioritize clean studio audio / Topic tracks over music videos with dialogue skits.
        """
        scored = []
        for e in entries:
            title = (e.get('title') or '').lower()
            channel = (e.get('uploader') or e.get('channel') or '').lower()
            score = 100

            # Priority 1: Official Topic channels (official studio album release)
            if '- topic' in channel:
                score += 80

            # Priority 2: Official Audio / Audio releases
            if 'official audio' in title or 'audio' in title:
                score += 30
            if 'lyrics' in title:
                score += 20

            # Penalty: Music videos often have non-musical skits, dialogue, or extended openings
            if 'official video' in title or 'music video' in title or 'short film' in title or 'film' in title:
                score -= 50

            scored.append((score, e))

        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1]

    def search(self, query: str, limit: int = 10) -> List[TrackInfo]:
        search_query = f"ytsearch{limit}:{query}"
        ydl_opts = {
            'extract_flat': True,
            'skip_download': True,
            'quiet': True,
            'no_warnings': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(search_query, download=False)
            except Exception as e:
                raise ProviderError(f"Search failed: {e}")

        if not info or 'entries' not in info:
            return []

        results = []
        for entry in info['entries']:
            if entry:
                results.append(self._parse_track_info(entry))
        return results

    def _parse_track_info(self, info: dict) -> TrackInfo:
        title = info.get('title', 'Unknown Title')
        artist = info.get('artist') or info.get('uploader') or info.get('channel') or 'Unknown Artist'
        
        # Strip Topic suffix from channel name
        if artist.endswith(' - Topic'):
            artist = artist[:-8].strip()

        # Format artist and title if title contains "Artist - Title"
        if '-' in title and not info.get('artist'):
            parts = title.split('-', 1)
            artist = parts[0].strip()
            title = parts[1].strip()

        webpage_url = info.get('webpage_url') or info.get('url')
        if webpage_url and not webpage_url.startswith('http'):
            webpage_url = f"https://www.youtube.com/watch?v={webpage_url}"

        return TrackInfo(
            title=title,
            artist=artist,
            album=info.get('album'),
            release_year=info.get('release_year') or self._parse_year(info.get('upload_date')),
            duration=info.get('duration'),
            cover_url=self._get_thumbnail(info),
            stream_url=webpage_url,
            webpage_url=webpage_url,
            provider_name=self.name,
            media_type=MediaType.AUDIO,
            raw_metadata=info
        )

    def _get_thumbnail(self, info: dict) -> str:
        thumbnails = info.get('thumbnails', [])
        if thumbnails:
            return thumbnails[-1].get('url', '')
        return info.get('thumbnail', '')

    def _parse_year(self, upload_date: str) -> Union[int, None]:
        if upload_date and len(upload_date) >= 4:
            try:
                return int(upload_date[:4])
            except ValueError:
                pass
        return None
