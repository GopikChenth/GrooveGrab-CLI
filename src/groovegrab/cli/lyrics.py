"""
Lyrics Subcommand Handler (`groovegrab lyrics` / `groovegrab sync` / `groovegrab spotify`)
"""

from typing import Optional
import typer
from rich.console import Console

from groovegrab.player.mpris_player import MprisLiveLyricsPlayer

console = Console()
app = typer.Typer(help="Live real-time synced lyrics tracker for Spotify and MPRIS players")


@app.callback(invoke_without_command=True)
def lyrics_command(
    player: Optional[str] = typer.Option(
        None, "--player", "-p", help="Target media player (e.g. spotify, vlc, firefox, mpv)"
    ),
    theme: str = typer.Option(
        "cava", "--theme", "-t", help="UI Color Theme (cava, cyberpunk, matrix, fire, sunset, ocean, aurora, synthwave, monochrome)"
    ),
):
    """
    Connect to Spotify or any active Linux media player over MPRIS D-Bus to display live synced lyrics in real time.
    """
    mpris_player = MprisLiveLyricsPlayer(
        player_name=player,
        theme_name=theme
    )
    mpris_player.start()
