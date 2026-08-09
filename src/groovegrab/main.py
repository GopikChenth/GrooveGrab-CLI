"""
GrooveGrab Main CLI Entrypoint
"""

import typer
from rich.console import Console

from groovegrab import __version__
from groovegrab.cli.download import download_command
from groovegrab.cli.search import search_command
from groovegrab.cli.queue import queue_command
from groovegrab.cli.config import config_command, setup_command

console = Console()

app = typer.Typer(
    name="groovegrab",
    help="🚀 GrooveGrab CLI - Modular High-Performance Song & Media Downloader",
    add_completion=False,
    no_args_is_help=True
)

app.command(name="get", help="Download songs, playlists, or albums")(download_command)
app.command(name="dl", help="Download songs, playlists, or albums (alias for get)")(download_command)
app.command(name="search", help="Search songs interactively")(search_command)
app.command(name="queue", help="View download queue history")(queue_command)
app.command(name="config", help="Manage configuration settings")(config_command)
app.command(name="setup", help="Run interactive auto-selection setup wizard")(setup_command)


@app.callback(invoke_without_command=True)
def main(
    version: bool = typer.Option(False, "--version", "-v", help="Show version information"),
):
    if version:
        console.print(f"[bold cyan]GrooveGrab CLI[/bold cyan] version [bold yellow]{__version__}[/bold yellow]")
        raise typer.Exit()


if __name__ == "__main__":
    app()
