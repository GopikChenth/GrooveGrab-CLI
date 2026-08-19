"""
Lyrics Subcommand Handler (`groovegrab lyrics` / `groovegrab sync` / `groovegrab spotify`)
"""

from typing import Optional
import typer
from rich.console import Console

from groovegrab.core.config import ConfigManager
from groovegrab.player.mpris_player import MprisLiveLyricsPlayer

console = Console()
app = typer.Typer(help="Live real-time synced lyrics tracker for Spotify and MPRIS players")


@app.callback(invoke_without_command=True)
def lyrics_command(
    player: Optional[str] = typer.Option(
        None, "--player", "-p", help="Target media player (e.g. spotify, vlc, firefox, mpv)"
    ),
    theme: Optional[str] = typer.Option(
        None, "--theme", "-t", help="UI Color Theme (cava, cyberpunk, matrix, fire, sunset, ocean, aurora, synthwave, monochrome)"
    ),
):
    """
    Connect to Spotify or any active Linux media player over MPRIS D-Bus to display live synced lyrics in real time.
    """
    config_mgr = ConfigManager()
    cfg = config_mgr.get()
    selected_theme = theme or cfg.player_theme

    mpris_player = MprisLiveLyricsPlayer(
        player_name=player,
        theme_name=selected_theme
    )
    mpris_player.start()
