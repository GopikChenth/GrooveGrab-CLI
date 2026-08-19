"""
Config Subcommand Handler (`groovegrab config` & `groovegrab setup`)
"""

from typing import Optional
import typer
import questionary
from rich.console import Console
from rich.table import Table

from groovegrab.core.config import ConfigManager, GrooveGrabConfig
from groovegrab.core.models import AudioFormat, AudioBitrate
from groovegrab.ui.banner import print_success, print_info

console = Console()
app = typer.Typer(help="Manage user configuration settings")


def run_interactive_wizard(cfg: GrooveGrabConfig) -> GrooveGrabConfig:
    console.print("\n[bold cyan]GrooveGrab Interactive Setup Wizard[/bold cyan]\n")

    # 1. Download Directory
    new_dir = questionary.text(
        "1. Download Directory:",
        default=cfg.download_dir
    ).ask()
    if new_dir:
        cfg.download_dir = new_dir

    # 2. Audio Format Choice Menu
    fmt_choice = questionary.select(
        "2. Select Audio Format:",
        choices=[
            "mp3 - Standard MP3 (ID3 Tagged)",
            "flac - Lossless Studio Audio",
            "m4a - AAC Audio",
            "opus - High-Efficiency Opus",
            "wav - Uncompressed Wave",
        ]
    ).ask()
    if fmt_choice:
        cfg.audio_format = AudioFormat(fmt_choice.split(" ")[0])

    # 3. Audio Bitrate Choice Menu
    bitrate_choice = questionary.select(
        "3. Select Audio Bitrate / Quality:",
        choices=[
            "320k - Maximum Quality",
            "256k - High Quality",
            "192k - Standard Quality",
            "128k - Compact Size",
        ]
    ).ask()
    if bitrate_choice:
        cfg.audio_bitrate = AudioBitrate(bitrate_choice.split(" ")[0])

    # 4. Lyrics Toggle Menu
    fetch_lyrics_choice = questionary.select(
        "4. Fetch Synced Lyrics (.lrc)?",
        choices=[
            "Yes - Fetch synced .lrc lyrics files",
            "No - Skip lyrics",
        ]
    ).ask()
    cfg.fetch_lyrics = bool(fetch_lyrics_choice and fetch_lyrics_choice.startswith("Yes"))

    # 5. Cover Artwork Toggle Menu
    embed_cover_choice = questionary.select(
        "5. Embed HD Album Cover Artwork?",
        choices=[
            "Yes - Embed HD cover art in files",
            "No - Skip embedding cover artwork",
        ]
    ).ask()
    cfg.embed_cover = bool(embed_cover_choice and embed_cover_choice.startswith("Yes"))

    # 6. Default Visualizer & Lyrics Theme
    theme_choice = questionary.select(
        "6. Select Default Player Visualizer Theme:",
        choices=[
            "cava - Classic Cyan/Blue (Default)",
            "cyberpunk - Neon Pink & Bright Cyan",
            "matrix - Hacker Terminal Green",
            "fire - Amber Orange & Crimson Red",
            "sunset - Coral Magenta & Gold Yellow",
            "ocean - Deep Blue & Aqua",
            "aurora - Emerald Green & Violet",
            "synthwave - Retro Purple & Hot Pink",
            "monochrome - Minimalist Clean White",
        ]
    ).ask()
    if theme_choice:
        cfg.player_theme = theme_choice.split(" ")[0].lower()

    # 7. Concurrent Downloads Menu
    conc_choice = questionary.select(
        "7. Select Concurrent Downloads Limit:",
        choices=[
            "3 - Recommended Default",
            "1 - Sequential (Single track at a time)",
            "5 - Fast Parallel",
            "8 - Maximum Speed",
        ]
    ).ask()
    if conc_choice:
        cfg.concurrent_downloads = int(conc_choice.split(" ")[0])

    return cfg


@app.callback(invoke_without_command=True)
def config_command(
    set_dir: Optional[str] = typer.Option(None, "--dir", help="Set default download directory"),
    set_format: Optional[AudioFormat] = typer.Option(None, "--format", "-f", help="Set default audio format (mp3, flac, m4a, opus, wav)"),
    set_bitrate: Optional[AudioBitrate] = typer.Option(None, "--bitrate", "-b", help="Set default audio bitrate (320k, 256k, 192k)"),
    set_theme: Optional[str] = typer.Option(None, "--theme", "-t", help="Set default player theme (cava, cyberpunk, matrix, fire, sunset, ocean, aurora, synthwave, monochrome)"),
    concurrent: Optional[int] = typer.Option(
        None, "--concurrent", "-c", min=1, max=16, help="Set concurrent download limit"
    ),
    lyrics: Optional[bool] = typer.Option(None, "--lyrics/--no-lyrics", help="Enable or disable fetching synced lyrics (.lrc)"),
    cover: Optional[bool] = typer.Option(None, "--cover/--no-cover", help="Enable or disable embedding cover artwork"),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="Run interactive configuration setup wizard"),
):
    """View or update user configuration settings."""
    config_mgr = ConfigManager()
    cfg = config_mgr.get()

    if interactive:
        cfg = run_interactive_wizard(cfg)
        config_mgr.save_config(cfg)
        print_success("Saved new configuration!")

    updated = False
    if set_dir:
        cfg.download_dir = set_dir
        updated = True
    if set_format:
        cfg.audio_format = set_format
        updated = True
    if set_bitrate:
        cfg.audio_bitrate = set_bitrate
        updated = True
    if set_theme:
        cfg.player_theme = set_theme.lower().strip()
        updated = True
    if concurrent:
        cfg.concurrent_downloads = concurrent
        updated = True
    if lyrics is not None:
        cfg.fetch_lyrics = lyrics
        updated = True
    if cover is not None:
        cfg.embed_cover = cover
        updated = True

    if updated:
        config_mgr.save_config(cfg)
        print_success("Configuration updated successfully.")

    if not interactive:
        table = Table(title="Current GrooveGrab Configuration", header_style="bold magenta")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Download Directory", cfg.download_dir)
        table.add_row("Audio Format", cfg.audio_format.value)
        table.add_row("Audio Bitrate", cfg.audio_bitrate.value)
        table.add_row("Player Theme", cfg.player_theme)
        table.add_row("Fetch Lyrics (.lrc)", str(cfg.fetch_lyrics))
        table.add_row("Embed Cover Art", str(cfg.embed_cover))
        table.add_row("Concurrent Downloads", str(cfg.concurrent_downloads))

        console.print(table)
        print_info("Run [bold cyan]groovegrab setup[/bold cyan] to change settings interactively.\n")
