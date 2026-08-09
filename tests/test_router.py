"""
Unit Tests for GrooveGrab Provider Registry and Router
"""

import pytest
from groovegrab.providers.registry import ProviderRegistry
from groovegrab.providers.youtube_music import YouTubeProvider
from groovegrab.providers.spotify_provider import SpotifyProvider
from groovegrab.providers.jiosaavn import JioSaavnProvider
from groovegrab.providers.soundcloud import SoundCloudProvider


def test_provider_matching():
    registry = ProviderRegistry()

    # YouTube URL
    provider = registry.find_provider("https://music.youtube.com/watch?v=dQw4w9WgXcQ")
    assert isinstance(provider, YouTubeProvider)

    # Spotify URL
    provider = registry.find_provider("https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT")
    assert isinstance(provider, SpotifyProvider)

    # JioSaavn URL
    provider = registry.find_provider("https://www.jiosaavn.com/song/kesariya/X1A-aBx5AGE")
    assert isinstance(provider, JioSaavnProvider)

    # SoundCloud URL
    provider = registry.find_provider("https://soundcloud.com/artist/track")
    assert isinstance(provider, SoundCloudProvider)

    # Generic Query -> Default YouTube Provider
    provider = registry.find_provider("Blinding Lights The Weeknd")
    assert isinstance(provider, YouTubeProvider)


def test_youtube_provider_does_not_disable_tls_verification():
    # TLS validation must remain enabled for provider and download requests.
    source = __import__("inspect").getsource(YouTubeProvider)
    assert "nocheckcertificate" not in source
