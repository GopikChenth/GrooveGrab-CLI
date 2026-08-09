"""
Queue & History Subcommand Handler (`groovegrab queue`)
"""

import typer
from rich.console import Console
from rich.table import Table

from groovegrab.queue.storage import TaskStorage

console = Console()
app = typer.Typer(help="View download queue history")


@app.callback(invoke_without_command=True)
def queue_command(
    limit: int = typer.Option(20, "--limit", "-n", min=1, max=500, help="Number of history items to show")
):
    """View recent download history and task status."""
    storage = TaskStorage()
    tasks = storage.list_tasks(limit=limit)

    if not tasks:
        console.print("[yellow]No download history found.[/yellow]")
        return

    table = Table(title="📜 Download History & Queue", show_header=True, header_style="bold magenta")
    table.add_column("Status", style="cyan")
    table.add_column("Track", style="bold white")
    table.add_column("Artist", style="green")
    table.add_column("Provider", style="blue")
    table.add_column("Output Path", style="dim white")

    for task in tasks:
        status_color = "green" if task.status == "completed" else ("red" if task.status == "failed" else "yellow")
        table.add_row(
            f"[{status_color}]{task.status.upper()}[/{status_color}]",
            task.track.title,
            task.track.artist,
            task.track.provider_name,
            task.output_path or task.error_message or "-"
        )

    console.print(table)
