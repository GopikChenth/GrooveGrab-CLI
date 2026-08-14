"""
Persistent Lyric Sync Offset Store
Saves and loads song-specific lyric sync offsets to ~/.config/groovegrab/lyric_offsets.json
"""

import json
from pathlib import Path
from platformdirs import user_config_dir


class LyricSyncStore:
    """Manages persistent song-specific lyric sync offsets."""

    def __init__(self):
        try:
            base_dir = Path(user_config_dir("groovegrab"))
            base_dir.mkdir(parents=True, exist_ok=True)
            self.store_file = base_dir / "lyric_offsets.json"
        except Exception:
            self.store_file = Path("./.groovegrab_config/lyric_offsets.json")
        
        self.offsets = self._load()

    def _make_key(self, title: str, artist: str) -> str:
        clean_title = (title or "").strip().lower()
        clean_artist = (artist or "").strip().lower()
        return f"{clean_artist} - {clean_title}"

    def _load(self) -> dict:
        if self.store_file.exists():
            try:
                with open(self.store_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def get_offset(self, title: str, artist: str) -> float:
        key = self._make_key(title, artist)
        return float(self.offsets.get(key, 0.0))

    def save_offset(self, title: str, artist: str, offset_sec: float):
        key = self._make_key(title, artist)
        self.offsets[key] = round(float(offset_sec), 2)
        try:
            self.store_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.store_file, "w", encoding="utf-8") as f:
                json.dump(self.offsets, f, indent=2)
        except Exception:
            pass
