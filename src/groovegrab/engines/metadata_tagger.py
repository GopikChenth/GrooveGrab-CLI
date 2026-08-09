"""
Mutagen Audio Metadata & Cover Art Tagger
"""

from pathlib import Path
from typing import Optional
import httpx

import mutagen
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TRCK, APIC, USLT
from mutagen.flac import FLAC, Picture
from mutagen.mp4 import MP4, MP4Cover

from groovegrab.core.models import TrackInfo
from groovegrab.core.exceptions import MetadataError


class MetadataTagger:
    """Embeds ID3, Vorbis, or MP4 metadata and artwork into audio files."""

    def tag_file(self, file_path: Path, track: TrackInfo, lyrics: Optional[str] = None) -> None:
        if not file_path.exists():
            raise MetadataError(f"File for tagging does not exist: {file_path}")

        cover_data = self._fetch_cover(track.cover_url)
        ext = file_path.suffix.lower()

        try:
            if ext == ".mp3":
                self._tag_mp3(file_path, track, cover_data, lyrics)
            elif ext == ".flac":
                self._tag_flac(file_path, track, cover_data, lyrics)
            elif ext in [".m4a", ".mp4"]:
                self._tag_m4a(file_path, track, cover_data, lyrics)
            else:
                # Generic fallback using mutagen.File
                audio = mutagen.File(file_path, easy=True)
                if audio is not None:
                    audio["title"] = track.title
                    audio["artist"] = track.artist
                    if track.album:
                        audio["album"] = track.album
                    audio.save()
        except Exception as e:
            raise MetadataError(f"Failed to tag file {file_path.name}: {e}")

    def _fetch_cover(self, cover_url: Optional[str]) -> Optional[bytes]:
        if not cover_url:
            return None
        try:
            resp = httpx.get(cover_url, timeout=10.0, follow_redirects=True)
            if resp.status_code == 200 and len(resp.content) > 0:
                return resp.content
        except Exception:
            pass
        return None

    def _tag_mp3(self, file_path: Path, track: TrackInfo, cover_bytes: Optional[bytes], lyrics: Optional[str]):
        try:
            tags = ID3(file_path)
        except Exception:
            tags = ID3()

        tags.add(TIT2(encoding=3, text=track.title))
        tags.add(TPE1(encoding=3, text=track.artist))
        
        if track.album:
            tags.add(TALB(encoding=3, text=track.album))
        if track.release_year:
            tags.add(TDRC(encoding=3, text=str(track.release_year)))
        if track.track_number:
            tags.add(TRCK(encoding=3, text=str(track.track_number)))
        
        if cover_bytes:
            tags.add(APIC(
                encoding=3,
                mime="image/jpeg",
                type=3,
                desc="Cover",
                data=cover_bytes
            ))
            
        if lyrics:
            tags.add(USLT(encoding=3, lang="eng", desc="Lyrics", text=lyrics))

        tags.save(file_path)

    def _tag_flac(self, file_path: Path, track: TrackInfo, cover_bytes: Optional[bytes], lyrics: Optional[str]):
        audio = FLAC(file_path)
        audio["title"] = track.title
        audio["artist"] = track.artist
        if track.album:
            audio["album"] = track.album
        if track.release_year:
            audio["date"] = str(track.release_year)
        if track.track_number:
            audio["tracknumber"] = str(track.track_number)
        if lyrics:
            audio["lyrics"] = lyrics

        if cover_bytes:
            image = Picture()
            image.type = 3
            image.mime = "image/jpeg"
            image.desc = "Cover"
            image.data = cover_bytes
            audio.clear_pictures()
            audio.add_picture(image)

        audio.save()

    def _tag_m4a(self, file_path: Path, track: TrackInfo, cover_bytes: Optional[bytes], lyrics: Optional[str]):
        audio = MP4(file_path)
        audio["\xa9nam"] = track.title
        audio["\xa9ART"] = track.artist
        if track.album:
            audio["\xa9alb"] = track.album
        if track.release_year:
            audio["\xa9day"] = str(track.release_year)
        if lyrics:
            audio["\xa9lyr"] = lyrics

        if cover_bytes:
            audio["covr"] = [MP4Cover(cover_bytes, imageformat=MP4Cover.FORMAT_JPEG)]

        audio.save()
