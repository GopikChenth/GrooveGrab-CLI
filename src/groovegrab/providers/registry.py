"""
Provider Registry & Dispatcher Router
"""

from typing import List, Union, Optional
from groovegrab.providers.base import BaseProvider
from groovegrab.providers.youtube_music import YouTubeProvider
from groovegrab.providers.spotify_provider import SpotifyProvider
from groovegrab.providers.jiosaavn import JioSaavnProvider
from groovegrab.providers.soundcloud import SoundCloudProvider
from groovegrab.core.models import TrackInfo, PlaylistInfo
from groovegrab.core.exceptions import ProviderError


class ProviderRegistry:
    def __init__(self):
        self.providers: List[BaseProvider] = [
            YouTubeProvider(),
            SpotifyProvider(),
            JioSaavnProvider(),
            SoundCloudProvider(),
        ]
        self.default_provider = YouTubeProvider()

    def register_provider(self, provider: BaseProvider) -> None:
        self.providers.insert(0, provider)

    def find_provider(self, query_or_url: str) -> BaseProvider:
        for provider in self.providers:
            if provider.can_handle(query_or_url):
                return provider
        return self.default_provider

    def resolve(self, query_or_url: str) -> Union[TrackInfo, PlaylistInfo]:
        provider = self.find_provider(query_or_url)
        try:
            resolved = provider.resolve(query_or_url)
            return resolved
        except ProviderError:
            # Fallback to default YouTube provider search if URL resolution failed
            if not query_or_url.startswith("http"):
                return self.default_provider.resolve(query_or_url)
            raise

    def search_all(self, query: str, limit: int = 10) -> List[TrackInfo]:
        provider = self.find_provider(query)
        return provider.search(query, limit=limit)
