"""
GrooveGrab Data Models
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class MediaType(str, Enum):
    AUDIO = "audio"
    VIDEO = "video"


class AudioFormat(str, Enum):
    MP3 = "mp3"
    FLAC = "flac"
    M4A = "m4a"
    OPUS = "opus"
    WAV = "wav"


class AudioBitrate(str, Enum):
    CBR_320 = "320k"
    CBR_256 = "256k"
    CBR_192 = "192k"
    CBR_128 = "128k"
    BEST = "best"


class DownloadStatus(str, Enum):
    PENDING = "pending"
    RESOLVING = "resolving"
    DOWNLOADING = "downloading"
    CONVERTING = "converting"
    TAGGING = "tagging"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


class TrackInfo(BaseModel):
    title: str
    artist: str = "Unknown Artist"
    album: Optional[str] = None
    album_artist: Optional[str] = None
    release_year: Optional[int] = None
    track_number: Optional[int] = None
    disc_number: Optional[int] = None
    genre: Optional[str] = None
    duration: Optional[int] = None  # in seconds
    cover_url: Optional[str] = None
    stream_url: Optional[str] = None
    webpage_url: Optional[str] = None
    provider_name: str = "generic"
    media_type: MediaType = MediaType.AUDIO
    raw_metadata: Dict[str, Any] = Field(default_factory=dict)

    def display_name(self) -> str:
        return f"{self.artist} - {self.title}"


class PlaylistInfo(BaseModel):
    title: str
    description: Optional[str] = None
    author: Optional[str] = None
    tracks: List[TrackInfo] = Field(default_factory=list)
    cover_url: Optional[str] = None
    provider_name: str = "generic"


class DownloadOptions(BaseModel):
    output_dir: str
    audio_format: AudioFormat = AudioFormat.MP3
    audio_bitrate: AudioBitrate = AudioBitrate.CBR_320
    embed_cover: bool = True
    fetch_lyrics: bool = True
    output_template: str = "{artist}/{album}/{track_number} - {title}.{ext}"
    concurrent_downloads: int = Field(default=3, ge=1, le=16)
    overwrite: bool = False


class DownloadTask(BaseModel):
    id: str
    track: TrackInfo
    options: DownloadOptions
    status: DownloadStatus = DownloadStatus.PENDING
    progress: float = 0.0
    speed: Optional[str] = None
    eta: Optional[str] = None
    output_path: Optional[str] = None
    error_message: Optional[str] = None
