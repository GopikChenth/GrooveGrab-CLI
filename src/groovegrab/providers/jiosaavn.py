"""
JioSaavn Audio Provider Plugin
"""

import re
from typing import List, Union
import httpx

from groovegrab.providers.base import BaseProvider
from groovegrab.core.models import TrackInfo, PlaylistInfo, MediaType
from groovegrab.core.exceptions import ProviderError

SAAVN_URL_REGEX = re.compile(r'^(https?://)?(www\.)?(jiosaavn\.com|saavn\.com)/(song|album|featured)/')


class JioSaavnProvider(BaseProvider):
    @property
    def name(self) -> str:
        return "JioSaavn"

    def can_handle(self, query_or_url: str) -> bool:
        return bool(SAAVN_URL_REGEX.match(query_or_url))

    def resolve(self, query_or_url: str) -> Union[TrackInfo, PlaylistInfo]:
        # Saavn API integration
        try:
            if "/album/" in query_or_url:
                api_url = f"https://saavn.dev/api/albums?link={query_or_url}"
            elif "/featured/" in query_or_url or "/playlist/" in query_or_url:
                api_url = f"https://saavn.dev/api/playlists?link={query_or_url}"
            else:
                api_url = f"https://saavn.dev/api/songs?link={query_or_url}"

            resp = httpx.get(api_url, timeout=10.0)
            if resp.status_code == 200:
                res = resp.json()
                if res.get("success") and res.get("data"):
                    data = res["data"]
                    if isinstance(data, dict) and "songs" in data and isinstance(data["songs"], list):
                        playlist_title = data.get("name") or data.get("title") or "JioSaavn Playlist"
                        tracks = [
                            self._parse_song_data(s, query_or_url)
                            for s in data["songs"]
                            if isinstance(s, dict)
                        ]
                        if tracks:
                            images = data.get("image", [])
                            cover_url = images[-1].get("url") if isinstance(images, list) and images else None
                            return PlaylistInfo(
                                title=playlist_title,
                                author=data.get("subtitle") or "JioSaavn",
                                tracks=tracks,
                                cover_url=cover_url,
                                provider_name=self.name
                            )
                    elif isinstance(data, list) and len(data) > 0:
                        return self._parse_song_data(data[0], query_or_url)
                    elif isinstance(data, dict):
                        return self._parse_song_data(data, query_or_url)
        except Exception as e:
            raise ProviderError(f"Saavn resolution failed: {e}")

        raise ProviderError("Failed to fetch song from JioSaavn")

    def _parse_song_data(self, song: dict, webpage_url: str) -> TrackInfo:
        download_urls = song.get("downloadUrl", [])
        high_quality_url = download_urls[-1].get("url") if isinstance(download_urls, list) and download_urls else None
        images = song.get("image", [])
        cover_url = images[-1].get("url") if isinstance(images, list) and images else None

        artists = song.get("primaryArtists")
        if isinstance(artists, list):
            artist_str = ", ".join([a.get("name", "") for a in artists if isinstance(a, dict)])
        else:
            artist_str = str(artists or "Unknown Artist")

        album_name = song.get("album", {}).get("name") if isinstance(song.get("album"), dict) else None

        return TrackInfo(
            title=song.get("name", "Unknown Title"),
            artist=artist_str or "Unknown Artist",
            album=album_name,
            release_year=int(song.get("year")) if song.get("year") else None,
            duration=int(song.get("duration")) if song.get("duration") else None,
            cover_url=cover_url,
            stream_url=high_quality_url,
            webpage_url=webpage_url,
            provider_name=self.name,
            media_type=MediaType.AUDIO
        )

    def search(self, query: str, limit: int = 10) -> List[TrackInfo]:
        try:
            api_url = f"https://saavn.dev/api/search/songs?query={query}&limit={limit}"
            resp = httpx.get(api_url, timeout=10.0)
            if resp.status_code == 200:
                res = resp.json()
                if res.get("success") and res.get("data", {}).get("results"):
                    results = []
                    for song in res["data"]["results"]:
                        images = song.get("image", [])
                        cover_url = images[-1].get("url") if images else None
                        results.append(TrackInfo(
                            title=song.get("name", "Unknown Title"),
                            artist=song.get("primaryArtists", "Unknown Artist"),
                            album=song.get("album", {}).get("name"),
                            duration=int(song.get("duration")) if song.get("duration") else None,
                            cover_url=cover_url,
                            webpage_url=song.get("url"),
                            provider_name=self.name,
                            media_type=MediaType.AUDIO
                        ))
                    return results
        except Exception:
            pass
        return []
