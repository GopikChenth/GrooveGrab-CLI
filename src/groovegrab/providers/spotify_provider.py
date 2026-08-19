"""
Spotify Metadata & Playlist Resolver Plugin
Robust extraction of track, album, and playlist metadata via Spotify embed entity.
"""

import re
import json
from typing import List, Union
import httpx

from groovegrab.providers.base import BaseProvider
from groovegrab.core.models import TrackInfo, PlaylistInfo, MediaType
from groovegrab.core.exceptions import ProviderError

SPOTIFY_URL_REGEX = re.compile(
    r'^(https?://)?open\.spotify\.com/(user/[^/]+/playlist/|playlist/|album/|track/)([a-zA-Z0-9]+)'
)


class SpotifyProvider(BaseProvider):
    @property
    def name(self) -> str:
        return "Spotify"

    def can_handle(self, query_or_url: str) -> bool:
        return bool(SPOTIFY_URL_REGEX.match(query_or_url))

    def resolve(self, query_or_url: str) -> Union[TrackInfo, PlaylistInfo]:
        match = SPOTIFY_URL_REGEX.match(query_or_url)
        if not match:
            raise ProviderError("Invalid Spotify URL")

        raw_type = match.group(2)
        spotify_id = match.group(3)

        if "playlist" in raw_type:
            media_kind = "playlist"
        elif "album" in raw_type:
            media_kind = "album"
        else:
            media_kind = "track"

        embed_url = f"https://open.spotify.com/embed/{media_kind}/{spotify_id}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }

        try:
            resp = httpx.get(embed_url, headers=headers, timeout=12.0, follow_redirects=True)
            if resp.status_code == 200:
                script_tags = re.findall(r"<script[^>]*>(.*?)</script>", resp.text, re.DOTALL)
                for content in script_tags:
                    if "props" in content and "entity" in content:
                        try:
                            parsed_json = json.loads(content)
                            entity = parsed_json.get("props", {}).get("pageProps", {}).get("state", {}).get("data", {}).get("entity", {})
                            if entity:
                                return self._parse_entity(entity, media_kind, query_or_url)
                        except Exception:
                            continue
        except Exception as e:
            raise ProviderError(f"Failed to fetch Spotify metadata: {e}")

        # Oembed fallback
        return self._oembed_fallback(query_or_url)

    def _parse_entity(self, entity: dict, media_kind: str, original_url: str) -> Union[TrackInfo, PlaylistInfo]:
        title = entity.get("name") or entity.get("title") or "Spotify Content"
        
        # Extract artists
        artists_list = entity.get("artists", [])
        if artists_list:
            artists_str = ", ".join(a.get("name") for a in artists_list if a.get("name"))
        else:
            artists_str = entity.get("subtitle") or entity.get("author") or "Spotify"

        cover_url = self._extract_cover(entity)

        # Single track
        if media_kind == "track":
            dur_ms = entity.get("duration", 0)
            dur_sec = int(dur_ms // 1000) if dur_ms else None
            release_date = entity.get("releaseDate", {}).get("isoString", "")
            release_year = int(release_date[:4]) if len(release_date) >= 4 and release_date[:4].isdigit() else None

            return TrackInfo(
                title=title,
                artist=artists_str,
                album=entity.get("album", {}).get("name") if isinstance(entity.get("album"), dict) else None,
                release_year=release_year,
                duration=dur_sec,
                cover_url=cover_url,
                stream_url=None,  # Forces yt-dlp to search for exact studio audio
                webpage_url=original_url,
                provider_name=self.name,
                media_type=MediaType.AUDIO,
                raw_metadata=entity
            )

        # Album / Playlist
        track_list_raw = entity.get("trackList", [])
        tracks: List[TrackInfo] = []

        for idx, t in enumerate(track_list_raw, 1):
            t_title = t.get("title", "Unknown Track")
            t_artists = t.get("artists", [])
            if t_artists:
                t_artist_str = ", ".join(a.get("name") for a in t_artists if a.get("name"))
            else:
                t_artist_str = t.get("subtitle") or artists_str
            
            dur_ms = t.get("duration", 0)
            dur_sec = int(dur_ms // 1000) if dur_ms else None

            tracks.append(TrackInfo(
                title=t_title,
                artist=t_artist_str,
                album=title if media_kind == "album" else None,
                track_number=idx,
                duration=dur_sec,
                cover_url=cover_url,
                stream_url=None,
                webpage_url=original_url,
                provider_name=self.name,
                media_type=MediaType.AUDIO
            ))

        if media_kind in ["playlist", "album"] or len(tracks) > 1:
            return PlaylistInfo(
                title=title,
                author=artists_str,
                tracks=tracks,
                cover_url=cover_url,
                provider_name=self.name
            )

        if tracks:
            return tracks[0]

        return self._oembed_fallback(original_url)

    def _extract_cover(self, entity: dict) -> str:
        visual = entity.get("visualIdentity", {})
        images = visual.get("image", []) or entity.get("images", [])
        if images:
            return images[-1].get("url", "") or images[0].get("url", "")
        cover = entity.get("coverArt", {})
        sources = cover.get("sources", [])
        if sources:
            return sources[-1].get("url", "") or sources[0].get("url", "")
        return ""

    def _oembed_fallback(self, query_or_url: str) -> TrackInfo:
        try:
            resp = httpx.get("https://open.spotify.com/oembed", params={"url": query_or_url}, timeout=10.0)
            if resp.status_code == 200:
                data = resp.json()
                title = data.get("title", "Unknown Title")
                author = data.get("author_name", "Unknown Artist")
                thumbnail = data.get("thumbnail_url")
                return TrackInfo(
                    title=title,
                    artist=author,
                    cover_url=thumbnail,
                    stream_url=None,
                    webpage_url=query_or_url,
                    provider_name=self.name,
                    media_type=MediaType.AUDIO
                )
        except Exception:
            pass
        raise ProviderError("Could not resolve Spotify URL metadata. Please verify the URL.")

    def search(self, query: str, limit: int = 10) -> List[TrackInfo]:
        return []
