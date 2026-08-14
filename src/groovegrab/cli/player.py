"""
Player Subcommand Handler (`groovegrab play`)
"""

from pathlib import Path
from typing import Optional
import typer
from rich.console import Console

from groovegrab.core.config import ConfigManager
from groovegrab.core.models import TrackInfo, DownloadOptions
from groovegrab.providers.registry import ProviderRegistry
from groovegrab.queue.task_queue import TaskQueueManager
from groovegrab.engines.ytdlp_engine import YtDlpEngine
from groovegrab.player.terminal_player import TerminalPlayer
from groovegrab.player.visualizer import VisualizerMode
from groovegrab.ui.banner import print_info, print_error

console = Console()
app = typer.Typer(help="Play songs with real-time CAVA audio visualizer and synced lyrics")


@app.callback(invoke_without_command=True)
def play_command(
    target: str = typer.Argument(..., help="Song title, URL, or local file path to play"),
    theme: str = typer.Option("cava", "--theme", "-t", help="Player theme (cava, cyberpunk, matrix, fire, sunset, ocean, aurora, synthwave, monochrome)"),
    mode: str = typer.Option("bars", "--mode", "-m", help="Visualizer mode (bars, braille, wave, mirror, particles)"),
):
    """Play songs with real-time CAVA TUI audio spectrum visualizer & synced Karaoke lyrics."""
    config_mgr = ConfigManager()
    cfg = config_mgr.get()

    local_path = Path(target)
    
    # Parse initial visualizer mode
    try:
        viz_mode = VisualizerMode(mode.lower())
    except ValueError:
        viz_mode = VisualizerMode.BARS

    # 1. Direct local audio file
    if local_path.exists() and local_path.is_file():
        track_info = TrackInfo(
            title=local_path.stem.split(" - ")[-1] if " - " in local_path.stem else local_path.stem,
            artist=local_path.stem.split(" - ")[0] if " - " in local_path.stem else "Local Artist",
        )
        lrc_path = local_path.with_suffix(".lrc")
        player = TerminalPlayer(
            audio_path=local_path,
            track_info=track_info,
            lrc_path=lrc_path,
            theme_name=theme,
            initial_mode=viz_mode
        )
        player.start()
        return

    # 2. Check local download directory for matching song
    target_dir = Path(cfg.download_dir)
    downloader = YtDlpEngine()
    
    registry = ProviderRegistry()
    print_info(f"Resolving track: [bold cyan]{target}[/bold cyan]...")

    try:
        resolved = registry.resolve(target)
        if hasattr(resolved, "tracks"):
            track = resolved.tracks[0]
        else:
            track = resolved
    except Exception:
        track = TrackInfo(title=target, artist="Unknown Artist")

    options = DownloadOptions(
        output_dir=cfg.download_dir,
        audio_format=cfg.audio_format,
        audio_bitrate=cfg.audio_bitrate,
        embed_cover=cfg.embed_cover,
        fetch_lyrics=True
    )

    existing_file = downloader.find_existing_file(track, options)
    
    if not existing_file:
        print_info(f"Downloading track & synced lyrics on demand...")
        queue_mgr = TaskQueueManager()
        results = queue_mgr.process_tracks([track], options)
        if results and results[0].output_path:
            existing_file = Path(results[0].output_path)

    if not existing_file or not existing_file.exists():
        print_error(f"Could not find or download audio for '{target}'.")
        raise typer.Exit(1)

    lrc_path = existing_file.with_suffix(".lrc")
    player = TerminalPlayer(
        audio_path=existing_file,
        track_info=track,
        lrc_path=lrc_path,
        theme_name=theme,
        initial_mode=viz_mode
    )
    player.start()
