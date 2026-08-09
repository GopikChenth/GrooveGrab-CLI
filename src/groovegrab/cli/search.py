"""
Search Subcommand Handler (`groovegrab search`)
"""

from typing import Optional
import typer
from rich.console import Console

from groovegrab.core.config import ConfigManager
from groovegrab.core.models import DownloadOptions
from groovegrab.providers.registry import ProviderRegistry
from groovegrab.ui.search_table import display_search_results
from groovegrab.ui.dashboard import print_tasks_summary
from groovegrab.queue.task_queue import TaskQueueManager
from groovegrab.ui.banner import print_info, print_error

console = Console()
app = typer.Typer(help="Search songs interactively")


@app.callback(invoke_without_command=True)
def search_command(
    query: str = typer.Argument(..., help="Search query string"),
    limit: int = typer.Option(10, "--limit", "-l", min=1, max=50, help="Number of search results to display"),
    output_dir: Optional[str] = typer.Option(None, "--output", "-o", help="Custom output directory"),
):
    """Search for songs interactively and choose tracks to download."""
    registry = ProviderRegistry()
    print_info(f"Searching for '[bold cyan]{query}[/bold cyan]'...")

    try:
        results = registry.search_all(query, limit=limit)
    except Exception as e:
        print_error(f"Search failed: {e}")
        raise typer.Exit(1)

    selected_tracks = display_search_results(results)

    if not selected_tracks:
        print_info("No tracks selected. Exiting.")
        return

    config_mgr = ConfigManager()
    cfg = config_mgr.get()

    options = DownloadOptions(
        output_dir=output_dir or cfg.download_dir,
        audio_format=cfg.audio_format,
        audio_bitrate=cfg.audio_bitrate,
        embed_cover=cfg.embed_cover,
        fetch_lyrics=cfg.fetch_lyrics,
        concurrent_downloads=cfg.concurrent_downloads
    )

    console.print(f"\n[bold yellow]Downloading {len(selected_tracks)} selected track(s)...[/bold yellow]\n")

    queue_mgr = TaskQueueManager()
    tasks = queue_mgr.process_tracks(selected_tracks, options)
    print_tasks_summary(tasks)
