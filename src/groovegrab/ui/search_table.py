"""
Interactive Search Results Table Component
"""

from typing import List
from rich.console import Console
from rich.table import Table
import typer

from groovegrab.core.models import TrackInfo

console = Console()


def display_search_results(tracks: List[TrackInfo]) -> List[TrackInfo]:
    if not tracks:
        console.print("[yellow]No tracks found matching query.[/yellow]")
        return []

    table = Table(title="🔍 Search Results", show_header=True, header_style="bold magenta")
    table.add_column("#", style="cyan", width=4)
    table.add_column("Title", style="bold white")
    table.add_column("Artist", style="green")
    table.add_column("Album", style="dim white")
    table.add_column("Duration", style="yellow")
    table.add_column("Provider", style="blue")

    for idx, track in enumerate(tracks, 1):
        dur_str = f"{track.duration // 60}:{track.duration % 60:02d}" if track.duration else "--:--"
        table.add_row(
            str(idx),
            track.title,
            track.artist,
            track.album or "-",
            dur_str,
            track.provider_name
        )

    console.print(table)
    console.print("\n[bold cyan]Tip:[/bold cyan] Enter track numbers separated by commas (e.g. `1,3,5`), `all`, or `0` to cancel.")
    
    selection = typer.prompt("Select tracks to download")
    selection = selection.strip()

    if selection == "0" or not selection:
        return []

    if selection.lower() == "all":
        return tracks

    selected_tracks = []
    for part in selection.split(","):
        part = part.strip()
        if part.isdigit():
            idx = int(part)
            if 1 <= idx <= len(tracks):
                selected_tracks.append(tracks[idx - 1])

    return selected_tracks
