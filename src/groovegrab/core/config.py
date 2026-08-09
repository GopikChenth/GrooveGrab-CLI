"""
GrooveGrab Configuration Manager
"""

import json
import os
import tempfile
from pathlib import Path
from typing import Optional
from platformdirs import user_config_dir, user_downloads_dir
from pydantic import BaseModel, Field
from groovegrab.core.models import AudioFormat, AudioBitrate


class GrooveGrabConfig(BaseModel):
    download_dir: str = str(Path(user_downloads_dir()) / "GrooveGrab")
    audio_format: AudioFormat = AudioFormat.MP3
    audio_bitrate: AudioBitrate = AudioBitrate.CBR_320
    embed_cover: bool = True
    fetch_lyrics: bool = True
    output_template: str = "{artist}/{album}/{track_number} - {title}.{ext}"
    concurrent_downloads: int = Field(default=3, ge=1, le=16)
    spotify_client_id: Optional[str] = None
    spotify_client_secret: Optional[str] = None


class ConfigManager:
    """Manages reading and writing user configuration file with fallback to local path."""
    
    def __init__(self, config_path: Optional[Path] = None):
        if config_path:
            self.config_file = config_path
        else:
            try:
                base_dir = Path(user_config_dir("groovegrab"))
                base_dir.mkdir(parents=True, exist_ok=True)
                self.config_file = base_dir / "config.json"
            except Exception:
                base_dir = Path("./.groovegrab_config")
                base_dir.mkdir(parents=True, exist_ok=True)
                self.config_file = base_dir / "config.json"
        
        self.config = self.load_config()

    def load_config(self) -> GrooveGrabConfig:
        if self.config_file.exists():
            try:
                with self.config_file.open("r", encoding="utf-8") as config_file:
                    data = json.load(config_file)
                return GrooveGrabConfig(**data)
            except (json.JSONDecodeError, OSError, ValueError):
                return GrooveGrabConfig()
        return GrooveGrabConfig()

    def save_config(self, new_config: GrooveGrabConfig) -> None:
        self.config = new_config
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        # Replacing a fully-written temporary file prevents a partial config when
        # the process is interrupted during a write.
        fd, temp_name = tempfile.mkstemp(
            prefix=f".{self.config_file.name}.", dir=self.config_file.parent, text=True
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as config_file:
                json.dump(new_config.model_dump(mode="json"), config_file, indent=2)
                config_file.write("\n")
                config_file.flush()
                os.fsync(config_file.fileno())
            os.replace(temp_name, self.config_file)
        except OSError:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass
            raise

    def get(self) -> GrooveGrabConfig:
        return self.config
