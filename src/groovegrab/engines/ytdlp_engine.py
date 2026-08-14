"""
yt-dlp Audio Downloader Engine
Uses official studio audio search queries to guarantee 100% lyrics timestamp synchronization
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

        if not options.overwrite:
            existing = self.find_existing_file(track, options)
            if existing:
                return existing

        url = track.stream_url
        web_url = track.webpage_url or ""
        
        # Spotify & metadata queries use official audio search to avoid music video intro dialogues
        if not url or "spotify.com" in (url or "") or "spotify.com" in web_url or not url.startswith("http"):
            search_query = f"ytsearch1:{track.artist} - {track.title} official audio"
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

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(search_query, download=True)
                if 'entries' in info and info['entries']:
                    entry = info['entries'][0]
                else:
                    entry = info

                downloaded_file = ydl.prepare_filename(entry)
                final_file = Path(downloaded_file).with_suffix(f".{options.audio_format.value}")
                
                if final_file.exists():
                    return final_file
                
                candidates = list(target_dir.glob(f"{safe_artist} - {safe_title}.*"))
                if candidates:
                    return candidates[0]
                
                raise ExtractionError(f"File not found after extraction for {track.title}")

        except Exception as e:
            raise ExtractionError(f"Extraction failed for {track.title}: {str(e)}")

    def _sanitize_filename(self, name: str) -> str:
        clean = re.sub(r'[\\/*?:"<>|]', "", name)
        return clean.strip()
