"""
yt-dlp Audio Downloader Engine
"""

import os
import re
import time
from pathlib import Path
from typing import Callable, Optional
import yt_dlp

from groovegrab.core.models import TrackInfo, DownloadOptions
from groovegrab.core.exceptions import ExtractionError


class YtDlpEngine:
    """Core download engine wrapping yt-dlp."""

    def find_existing_file(self, track: TrackInfo, options: DownloadOptions) -> Optional[Path]:
        target_dir = Path(options.output_dir)
        if not target_dir.exists():
            return None

        safe_artist = self._sanitize_filename(track.artist)
        safe_title = self._sanitize_filename(track.title)

        # 1. Exact match with extensions
        for ext in [options.audio_format.value, "mp3", "flac", "m4a", "opus", "wav"]:
            candidate = target_dir / f"{safe_artist} - {safe_title}.{ext}"
            if candidate.exists() and candidate.stat().st_size > 1024:
                return candidate

        # 2. Prefix match in target directory
        prefix = f"{safe_artist} - {safe_title}"
        for f in target_dir.iterdir():
            if f.is_file() and f.name.startswith(prefix) and f.stat().st_size > 1024:
                return f

        return None

    def download_track(
        self,
        track: TrackInfo,
        options: DownloadOptions,
        progress_hook: Optional[Callable[[dict], None]] = None
    ) -> Path:
        target_dir = Path(options.output_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        # Check existing file if overwrite is False
        if not options.overwrite:
            existing = self.find_existing_file(track, options)
            if existing:
                return existing

        url = track.stream_url
        web_url = track.webpage_url or ""
        
        # Spotify links require audio matching via YouTube search to bypass Spotify DRM
        if not url or "spotify.com" in (url or "") or "spotify.com" in web_url or not url.startswith("http"):
            search_query = f"{track.artist} - {track.title} audio"
        else:
            search_query = url

        safe_artist = self._sanitize_filename(track.artist)
        safe_title = self._sanitize_filename(track.title)

        output_template = os.path.join(
            options.output_dir,
            f"{safe_artist} - {safe_title}.%(ext)s"
        )

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': output_template,
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': False,
            'retries': 5,
            'fragment_retries': 5,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': options.audio_format.value,
                'preferredquality': options.audio_bitrate.value.replace('k', ''),
            }],
        }

        if progress_hook:
            ydl_opts['progress_hooks'] = [progress_hook]

        # Try download with fallback queries on 403 / connection errors
        queries_to_try = [
            search_query if search_query.startswith("http") else f"ytsearch1:{search_query}",
            f"ytsearch1:{track.title} {track.artist} official audio",
            f"ytsearch1:{track.title} {track.artist}"
        ]

        last_error = None
        for attempt_query in queries_to_try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    info = ydl.extract_info(attempt_query, download=True)
                    if info and 'entries' in info and len(info['entries']) > 0:
                        info = info['entries'][0]

                    if not info:
                        continue

                    filename = ydl.prepare_filename(info)
                    base, _ = os.path.splitext(filename)
                    expected_file = Path(f"{base}.{options.audio_format.value}")
                    
                    if expected_file.exists():
                        return expected_file
                    
                    # Check for alternative matches in output directory
                    for ext in [options.audio_format.value, "mp3", "m4a", "opus", "flac"]:
                        candidate = Path(f"{base}.{ext}")
                        if candidate.exists():
                            return candidate
                        
                    prefix = f"{safe_artist} - {safe_title}"
                    for f in target_dir.iterdir():
                        if f.name.startswith(prefix):
                            return f

                except Exception as e:
                    last_error = e
                    time.sleep(1.0)
                    continue

        raise ExtractionError(f"Extraction failed for {track.display_name()}: {last_error}")

    def _sanitize_filename(self, name: str) -> str:
        name = re.sub(r'[\\/*?:"<>|]', "", name)
        return name.strip()
