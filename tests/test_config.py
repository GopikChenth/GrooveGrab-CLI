"""
Unit Tests for GrooveGrab Config Manager
"""

from pathlib import Path
from groovegrab.core.config import ConfigManager, GrooveGrabConfig
from groovegrab.core.models import AudioFormat, AudioBitrate


def test_config_load_save(tmp_path: Path):
    config_file = tmp_path / "config.json"
    mgr = ConfigManager(config_path=config_file)

    cfg = mgr.get()
    assert cfg.audio_format == AudioFormat.MP3
    assert cfg.audio_bitrate == AudioBitrate.CBR_320

    cfg.audio_format = AudioFormat.FLAC
    cfg.concurrent_downloads = 5
    mgr.save_config(cfg)

    new_mgr = ConfigManager(config_path=config_file)
    loaded_cfg = new_mgr.get()
    assert loaded_cfg.audio_format == AudioFormat.FLAC
    assert loaded_cfg.concurrent_downloads == 5


def test_config_recovers_from_invalid_json(tmp_path: Path):
    config_file = tmp_path / "config.json"
    config_file.write_text("{invalid", encoding="utf-8")

    cfg = ConfigManager(config_path=config_file).get()

    assert cfg.audio_format == AudioFormat.MP3
    assert cfg.concurrent_downloads == 3
