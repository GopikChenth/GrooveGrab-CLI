# 🎵 GrooveGrab CLI (`groovegrab`)

> A modular, high-performance CLI download tool for songs, audio, and videos.

## Features

- 🎵 **Multi-Provider Audio Extraction**: Download songs from YouTube Music, Spotify (metadata matching), JioSaavn, SoundCloud, and direct media URLs.
- 📁 **Automatic Playlist Subfolders**: Downloads playlists & albums directly into dedicated folders named after the playlist title.
- ⏭️ **Instant Skip Existing Songs**: Automatically detects already downloaded files and skips re-downloading them.
- 🎨 **Automatic HD Tagging**: Embeds high-resolution album cover art, title, artist, album, track numbers, release year, and genres via Mutagen.
- 📝 **Synced Lyrics**: Automatically fetches and saves synced `.lrc` lyrics from LRCLIB API.
- 🎛️ **Audio Transcoding**: Convert audio to high-quality `MP3` (320kbps), `FLAC`, `M4A`, or `OPUS` using FFmpeg.
- 🔍 **Interactive Song Search**: Search songs directly from your terminal and choose tracks interactively before downloading.
- 🎯 **Interactive Setup Wizard**: Run `groovegrab setup` for arrow-key selectable CLI config menus.
- 📊 **Rich Terminal UI**: Live multi-bar progress displays, ASCII banners, and queue tracking.

## Quick Start

```bash
# Install in editable mode
pip install -e .

# Run interactive setup wizard
groovegrab setup

# Download a song, playlist, or album
groovegrab dl "https://open.spotify.com/playlist/..."

# Search songs interactively
groovegrab search "Blinding Lights - The Weeknd"

# View download queue history
groovegrab queue

# Configure settings
groovegrab config
```
