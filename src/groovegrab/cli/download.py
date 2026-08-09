"""
Download Subcommand Handler (`groovegrab get`)
"""

import re
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console

from groovegrab.core.config import ConfigManager
from groovegrab.core.models import DownloadOptions, AudioFormat, AudioBitrate, PlaylistInfo, TrackInfo
from groovegrab.providers.registry import ProviderRegistry
from groovegrab.queue.task_queue import TaskQueueManager
from groovegrab.engines.ffmpeg_converter import FfmpegHelper
from groovegrab.ui.dashboard import PlaylistProgressDashboard, print_tasks_summary
from groovegrab.ui.banner import print_info, print_error, print_success

console = Console()
app = typer.Typer(help="Download tracks, albums, or playlists")


def sanitize_filename(name: str) -> str:
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    return name.strip()


@app.callback(invoke_without_command=True)
def download_command(
    query_or_url: str = typer.Argument(..., help="URL or search query to download"),
    output_dir: Optional[str] = typer.Option(None, "--output", "-o", help="Custom output directory"),
    audio_format: Optional[AudioFormat] = typer.Option(None, "--format", "-f", help="Audio output format (mp3, flac, m4a, opus, wav)"),
    audio_bitrate: Optional[AudioBitrate] = typer.Option(None, "--bitrate", "-b", help="Audio bitrate quality (320k, 256k, 192k)"),
    no_cover: bool = typer.Option(False, "--no-cover", help="Disable embedding cover art"),
    no_lyrics: bool = typer.Option(False, "--no-lyrics", help="Disable fetching synced lyrics"),
):
    """Download songs, albums, or playlists from any supported provider URL or query."""
    config_mgr = ConfigManager()
    cfg = config_mgr.get()

    options = DownloadOptions(
        output_dir=output_dir or cfg.download_dir,
        audio_format=audio_format or cfg.audio_format,
        audio_bitrate=audio_bitrate or cfg.audio_bitrate,
        embed_cover=False if no_cover else cfg.embed_cover,
        fetch_lyrics=False if no_lyrics else cfg.fetch_lyrics,
        concurrent_downloads=cfg.concurrent_downloads
    )

    registry = ProviderRegistry()
    ffmpeg_available, ffmpeg_message = FfmpegHelper.get_ffmpeg_version()
    if not ffmpeg_available:
        print_error(f"FFmpeg is required for audio conversion. {ffmpeg_message}")
        raise typer.Exit(1)
    print_info(f"Resolving request: [bold cyan]{query_or_url}[/bold cyan]...")

    try:
        resolved = registry.resolve(query_or_url)
    except Exception as e:
        print_error(f"Failed to resolve request: {e}")
        raise typer.Exit(1)

    if isinstance(resolved, PlaylistInfo):
        tracks = resolved.tracks
        safe_folder = sanitize_filename(resolved.title) or "Playlist"
        options.output_dir = str(Path(options.output_dir) / safe_folder)
        Path(options.output_dir).mkdir(parents=True, exist_ok=True)
        print_info(f"Resolved Playlist: [bold yellow]{resolved.title}[/bold yellow] ({len(tracks)} tracks)")
        print_info(f"Playlist Folder: [bold magenta]{options.output_dir}[/bold magenta]")
    else:
        tracks = [resolved]
        print_info(f"Resolved Song: [bold green]{resolved.display_name()}[/bold green]")

    if not tracks:
        print_error("No tracks found to download.")
        raise typer.Exit(1)

    console.print(f"\n[bold yellow]Downloading {len(tracks)} track(s) to:[/bold yellow] [bold white]{options.output_dir}[/bold white]\n")

    dashboard = PlaylistProgressDashboard(total_tracks=len(tracks))
    queue_mgr = TaskQueueManager()

    try:
        tasks = queue_mgr.process_tracks(tracks, options, on_progress=dashboard.update_task)
    finally:
        dashboard.close()

    print_tasks_summary(tasks)
    if any(task.status.value == "failed" for task in tasks):
        raise typer.Exit(1)
