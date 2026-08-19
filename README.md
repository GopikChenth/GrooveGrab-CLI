<p align="center">
  <img src="assets/readme/hero.svg" alt="GrooveGrab CLI - Modular Music Downloader &amp; CAVA Audio Player" width="100%">
</p>

<p align="center">
  <a href="#quick-start"><img src="https://img.shields.io/badge/python-3.10+-38BDF8.svg?style=flat-square" alt="Python 3.10+"></a>
  <a href="#quick-start"><img src="https://img.shields.io/badge/audio%20engine-FFmpeg-10B981.svg?style=flat-square" alt="FFmpeg"></a>
  <a href="#key-features"><img src="https://img.shields.io/badge/lyrics-2--Line%20Couplet%20CLR-8B5CF6.svg?style=flat-square" alt="2-Line Couplet CLR"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square" alt="MIT License"></a>
</p>

---

## Overview

**GrooveGrab CLI** is a modular, high-performance music engine and terminal audio player built for power users, audiophiles, and command-line enthusiasts. It combines multi-threaded media downloading with an integrated CAVA spectrum visualizer, a distraction-free **2-line couplet (CLR) karaoke lyric teleprompter**, and real-time Spotify/MPRIS D-Bus tracking.

Whether downloading entire studio discographies with offline `.lrc` lyrics, tracking live Spotify lyrics from your terminal, or enjoying music with reactive audio spectrum bars, GrooveGrab delivers an instantaneous, clean, and distraction-free audio experience.

---

## Key Features

- ⚡ **Multi-Provider Ingestion**: Download songs and playlists from YouTube Music, Spotify (metadata matching), JioSaavn, SoundCloud, and direct media URLs.
- 🎛️ **Studio Audio Transcoding**: Convert audio streams into high-bitrate **320kbps MP3**, lossless **FLAC**, **M4A**, or **OPUS** powered by FFmpeg.
- 🎨 **Automatic HD Tagging**: Automatically embeds high-resolution album cover artwork, artist, album, track numbers, release year, and genres via Mutagen.
- 📝 **Offline Synced Lyrics (.lrc)**: Automatically downloads and saves synchronized `.lrc` lyrics alongside audio files for instant offline playback.
- 📜 **2-Line Couplet (CLR) Teleprompter**: Zero dull preview text or spoilers. Line 1 types ➔ Line 2 types below it ➔ Screen clears for the next couplet in sync with singing tempo.
- 📡 **Live Spotify &amp; MPRIS Lyrics**: Listens to active Spotify or Linux media playback over D-Bus (`MPRIS2`), tracking real-time position with continuous scrolling lyrics (`groovegrab lyrics`).
- 📊 **CAVA Spectrum Visualizer**: Full-terminal mathematical FFT audio visualizer featuring multiple modes (*Bars*, *Braille*, *Waveform*, *Mirror*, *Particles*) across 9 curated color themes.
- 📁 **Smart Playlist Subfolders**: Automatically categorizes playlists and albums into dedicated folders while skipping already-downloaded tracks.
- ⚙️ **Interactive Setup Wizard with Theme Picker**: Built-in interactive terminal wizard (`groovegrab setup`) to configure directories, formats, bitrates, and default visualizer themes.

---

## Architecture &amp; Processing Pipeline

<p align="center">
  <img src="assets/readme/architecture.svg" alt="GrooveGrab Processing Pipeline Diagram" width="100%">
</p>

---

## Quick Start

### 1. Prerequisites

Ensure you have **Python 3.10+** and **FFmpeg** installed on your system:

```bash
# Ubuntu / Debian
sudo apt update && sudo apt install -y ffmpeg

# Arch Linux
sudo pacman -S ffmpeg

# macOS (Homebrew)
brew install ffmpeg
```

### 2. Installation

Clone the repository and install GrooveGrab in editable mode:

```bash
git clone https://github.com/GopikChenth/GroveGrab-CLI.git
cd GroveGrab-CLI
pip install -e .
```

---

## Usage Guide

### 🎵 Play with CAVA Visualizer &amp; 2-Line Couplet Lyrics

Launch the full-screen terminal player with live audio spectrum and real-time 2-line couplet lyrics (auto-downloads if not cached locally):

```bash
# Play by song name or local file
groovegrab play "The Weeknd - Blinding Lights"

# Play an entire downloaded folder / playlist seamlessly
groovegrab play ~/Downloads/GrooveGrab

# Play local audio file with custom visualizer theme and mode
groovegrab play "path/to/song.mp3" --theme cyberpunk --mode braille
```

### 📡 Live Spotify &amp; MPRIS Synced Lyrics

Connect directly to your active Spotify (or any Linux MPRIS player) to stream live synchronized scrolling lyrics in your terminal:

```bash
# Live track Spotify lyrics in real time
groovegrab lyrics

# Or use the quick aliases
groovegrab spotify
groovegrab sync

# Target a specific player with custom theme
groovegrab lyrics --player spotify --theme cyberpunk
```

### 📥 Download Songs &amp; Playlists

Download individual tracks, entire albums, or full playlists with offline `.lrc` lyrics:

```bash
# Download from Spotify, YouTube Music, or direct link
groovegrab dl "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M"

# Download with custom format and bitrate
groovegrab dl "Tame Impala - Let It Happen" --format flac
```

### 🔍 Interactive Song Search

Search songs across providers and interactively select tracks to download:

```bash
groovegrab search "Daft Punk - Get Lucky"
```

### ⚙️ Interactive Configuration Wizard &amp; Theme Customization

Configure default download directories, audio formats, bitrates, lyrics fetching, and default player themes:

```bash
# Run interactive setup wizard with theme picker
groovegrab setup

# Or manage settings via CLI flags
groovegrab config --theme synthwave --dir ~/Music/GrooveGrab --format mp3 --bitrate 320k --concurrent 4
```

### 📜 Download Queue &amp; History

Inspect recent downloads and status logs:

```bash
groovegrab queue --limit 25
```

---

## 🎹 Terminal Player Hotkeys

During playback in `groovegrab play` or `groovegrab lyrics`, control audio and visualizer using interactive keyboard shortcuts:

| Key | Action |
| :--- | :--- |
| <kbd>Space</kbd> | **Play / Pause** toggle |
| <kbd>n</kbd> / <kbd>p</kbd> | **Next / Previous track in queue** |
| <kbd>←</kbd> / <kbd>→</kbd> *(or <kbd>h</kbd> / <kbd>l</kbd>)* | **Seek** 5 seconds backward / forward |
| <kbd>↑</kbd> / <kbd>↓</kbd> *(or <kbd>k</kbd> / <kbd>j</kbd>)* | **Volume** Up / Down (10% increments) |
| <kbd>m</kbd> | **Mute / Unmute** audio |
| <kbd>v</kbd> | **Cycle Visualizer Mode** (`bars` ➔ `braille` ➔ `wave` ➔ `mirror` ➔ `particles`) |
| <kbd>t</kbd> | **Cycle Theme** (`cava`, `cyberpunk`, `matrix`, `fire`, `sunset`, `ocean`, `aurora`, `synthwave`, `monochrome`) |
| <kbd>q</kbd> / <kbd>Esc</kbd> | **Quit Player** |

---

## 🎨 Visualizer Themes &amp; Modes

GrooveGrab features 9 high-contrast color themes and 5 visualization algorithms:

### Modes
- `bars` — Multi-row vertical equalizer with smooth IIR peak smoothing
- `braille` — High-density 8-dot Unicode braille curve rendering
- `wave` — Real-time continuous mathematical sine waveform oscilloscope
- `mirror` — Center-split dual stereo spectrum
- `particles` — Floating ambient frequency particles

### Themes
`cava` • `cyberpunk` • `matrix` • `fire` • `sunset` • `ocean` • `aurora` • `synthwave` • `monochrome`

---

## License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.
