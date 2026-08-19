"""
Player Subcommand Handler (`groovegrab play`)
Seamlessly plays local/downloaded tracks, offline playlist folders, or live-tracks Spotify with 2-line lyrics & CAVA visualizer.
"""

from pathlib import Path
from typing import List, Tuple, Optional
import typer
from rich.console import Console

from groovegrab.core.config import ConfigManager
from groovegrab.core.models import TrackInfo, DownloadOptions
from groovegrab.providers.registry import ProviderRegistry
from groovegrab.queue.task_queue import TaskQueueManager
from groovegrab.engines.ytdlp_engine import YtDlpEngine
from groovegrab.engines.mpris_engine import MprisEngine
from groovegrab.player.terminal_player import TerminalPlayer, PlaylistItem
from groovegrab.player.mpris_player import MprisLiveLyricsPlayer
from groovegrab.player.visualizer import VisualizerMode
from groovegrab.ui.banner import print_info, print_error

console = Console()
app = typer.Typer(help="Play songs with real-time CAVA audio visualizer and synced lyrics")

AUDIO_EXTENSIONS = {".mp3", ".flac", ".m4a", ".opus", ".wav", ".ogg"}


def _build_playlist_from_files(files: List[Path]) -> List[PlaylistItem]:
    playlist: List[PlaylistItem] = []
    for f in sorted(files):
        if f.is_file() and f.suffix.lower() in AUDIO_EXTENSIONS:
            stem = f.stem
            if " - " in stem:
                artist, title = stem.split(" - ", 1)
            else:
                artist, title = "Local Artist", stem
            
            track_info = TrackInfo(title=title.strip(), artist=artist.strip())
            lrc_path = f.with_suffix(".lrc")
            playlist.append((f, track_info, lrc_path))
    return playlist


def _search_local_library(target: str, base_dir: Path) -> List[PlaylistItem]:
    if not base_dir.exists():
        return []

    clean_target = target.lower().strip()
    matches: List[Path] = []

    for f in base_dir.rglob("*"):
        if f.is_file() and f.suffix.lower() in AUDIO_EXTENSIONS:
            if clean_target in f.stem.lower():
                matches.append(f)

    return _build_playlist_from_files(matches)


@app.callback(invoke_without_command=True)
def play_command(
    target: Optional[str] = typer.Argument(None, help="Song title, URL, local folder/file, or omit to auto-play local tracks / Spotify"),
    theme: str = typer.Option("cava", "--theme", "-t", help="Player theme (cava, cyberpunk, matrix, fire, sunset, ocean, aurora, synthwave, monochrome)"),
    mode: str = typer.Option("bars", "--mode", "-m", help="Visualizer mode (bars, braille, wave, mirror, particles)"),
    spotify: bool = typer.Option(False, "--spotify", "-s", help="Attach to live Spotify / MPRIS playback"),
):
    """Play songs with real-time CAVA TUI audio spectrum visualizer & 2-line synced Karaoke lyrics."""
    config_mgr = ConfigManager()
    cfg = config_mgr.get()
    download_dir = Path(cfg.download_dir)

    try:
        viz_mode = VisualizerMode(mode.lower())
    except ValueError:
        viz_mode = VisualizerMode.BARS

    # 1. No target passed or --spotify flag
    if not target or spotify:
        mpris_engine = MprisEngine()
        players = mpris_engine.list_active_players()
        if spotify or (players and any("spotify" in p.lower() for p in players)):
            mpris_player = MprisLiveLyricsPlayer(
                player_name="spotify" if spotify else players[0],
                theme_name=theme,
                initial_mode=viz_mode
            )
            mpris_player.start()
            return
        
        # If no Spotify running, check if local library has downloaded songs
        local_files = [f for f in download_dir.rglob("*") if f.is_file() and f.suffix.lower() in AUDIO_EXTENSIONS]
        if local_files:
            playlist = _build_playlist_from_files(local_files)
            player = TerminalPlayer(
                playlist=playlist,
                start_index=0,
                theme_name=theme,
                initial_mode=viz_mode
            )
            player.start()
            return
        else:
            console.print("[bold cyan]GrooveGrab Audio Player[/bold cyan]")
            console.print("Usage: [bold green]groovegrab play \"Song Name\"[/bold green] or start Spotify.\n")
            target_input = typer.prompt("Enter song name, URL, or local path to play")
            if not target_input.strip():
                return
            target = target_input.strip()

    local_path = Path(target).expanduser().resolve()

    # 2. Target is a local directory / playlist folder
    if local_path.exists() and local_path.is_dir():
        files = [f for f in local_path.iterdir() if f.is_file() and f.suffix.lower() in AUDIO_EXTENSIONS]
        if not files:
            print_error(f"No audio files found in directory: {local_path}")
            raise typer.Exit(1)
        playlist = _build_playlist_from_files(files)
        player = TerminalPlayer(
            playlist=playlist,
            start_index=0,
            theme_name=theme,
            initial_mode=viz_mode
        )
        player.start()
        return

    # 3. Target is a direct local audio file
    if local_path.exists() and local_path.is_file() and local_path.suffix.lower() in AUDIO_EXTENSIONS:
        # Also queue neighbor songs in the same folder
        parent_files = [f for f in local_path.parent.iterdir() if f.is_file() and f.suffix.lower() in AUDIO_EXTENSIONS]
        playlist = _build_playlist_from_files(parent_files)
        start_idx = 0
        for idx, (p, _, _) in enumerate(playlist):
            if p == local_path:
                start_idx = idx
                break
        
        player = TerminalPlayer(
            playlist=playlist,
            start_index=start_idx,
            theme_name=theme,
            initial_mode=viz_mode
        )
        player.start()
        return

    # 4. Target is a song name: Check local downloaded library first (100% offline match)
    local_matches = _search_local_library(target, download_dir)
    if local_matches:
        player = TerminalPlayer(
            playlist=local_matches,
            start_index=0,
            theme_name=theme,
            initial_mode=viz_mode
        )
        player.start()
        return

    # 5. Online resolution & on-demand stream / download
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

    downloader = YtDlpEngine()
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
    playlist = [(existing_file, track, lrc_path)]
    player = TerminalPlayer(
        playlist=playlist,
        start_index=0,
        theme_name=theme,
        initial_mode=viz_mode
    )
    player.start()
