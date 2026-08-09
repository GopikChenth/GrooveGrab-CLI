"""
SoundCloud Provider Plugin
"""

import re
from typing import List, Union
import yt_dlp

from groovegrab.providers.base import BaseProvider
from groovegrab.core.models import TrackInfo, PlaylistInfo, MediaType
from groovegrab.core.exceptions import ProviderError

SOUNDCLOUD_URL_REGEX = re.compile(r'^(https?://)?(www\.)?soundcloud\.com/')


class SoundCloudProvider(BaseProvider):
    @property
    def name(self) -> str:
        return "SoundCloud"

    def can_handle(self, query_or_url: str) -> bool:
        return bool(SOUNDCLOUD_URL_REGEX.match(query_or_url))

    def resolve(self, query_or_url: str) -> Union[TrackInfo, PlaylistInfo]:
        ydl_opts = {
            'extract_flat': 'in_playlist',
            'skip_download': True,
            'quiet': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(query_or_url, download=False)
            except Exception as e:
                raise ProviderError(f"SoundCloud extraction error: {e}")

        if not info:
            raise ProviderError("No metadata returned from SoundCloud")

        if 'entries' in info:
            tracks = []
            for entry in info['entries']:
                if entry:
                    tracks.append(self._parse_track(entry))
            return PlaylistInfo(
                title=info.get('title', 'SoundCloud Playlist'),
                author=info.get('uploader'),
                tracks=tracks,
                provider_name=self.name
            )

        return self._parse_track(info)

    def search(self, query: str, limit: int = 10) -> List[TrackInfo]:
        search_query = f"scsearch{limit}:{query}"
        ydl_opts = {'extract_flat': True, 'skip_download': True, 'quiet': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(search_query, download=False)
                if info and 'entries' in info:
                    return [self._parse_track(e) for e in info['entries'] if e]
            except Exception:
                pass
        return []

    def _parse_track(self, info: dict) -> TrackInfo:
        return TrackInfo(
            title=info.get('title', 'Unknown Title'),
            artist=info.get('uploader') or info.get('user', {}).get('username') or 'Unknown Artist',
            duration=info.get('duration'),
            cover_url=info.get('thumbnail'),
            webpage_url=info.get('webpage_url') or info.get('url'),
            provider_name=self.name,
            media_type=MediaType.AUDIO
        )
