"""
Live Progress Dashboard Component
"""

from typing import Dict, List
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TransferSpeedColumn,
    TimeRemainingColumn,
    TaskID
)
from rich.console import Console

from groovegrab.core.models import DownloadTask, DownloadStatus

console = Console()


class PlaylistProgressDashboard:
    """Manages dynamic progress bars for overall playlist and active track downloads."""

    def __init__(self, total_tracks: int):
        self.total_tracks = total_tracks
        self.task_map: Dict[str, TaskID] = {}
        
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("{task.description}"),
            BarColumn(bar_width=30),
            TaskProgressColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
            console=console,
            transient=False,
            refresh_per_second=10
        )
        self.progress.start()
        self.overall_id = self.progress.add_task(
            "[bold yellow]Overall Progress[/bold yellow]", total=total_tracks
        )

    def update_task(self, task: DownloadTask):
        task_id = task.id
        title_str = f"[cyan]{task.track.artist}[/cyan] - [bold white]{task.track.title}[/bold white]"

        # Handle skipped tracks
        if task.status == DownloadStatus.SKIPPED:
            if task_id in self.task_map:
                self.progress.remove_task(self.task_map[task_id])
                del self.task_map[task_id]
            self.progress.advance(self.overall_id, 1)
            console.print(f"[bold yellow]  ⏭  Skipped (Already exists):[/bold yellow] {title_str}")
            return

        # Handle completed tracks
        if task.status == DownloadStatus.COMPLETED:
            if task_id in self.task_map:
                self.progress.remove_task(self.task_map[task_id])
                del self.task_map[task_id]
            self.progress.advance(self.overall_id, 1)
            console.print(f"[bold green]  ✔ Downloaded:[/bold green] {title_str}")
            return

        # Handle failed tracks
        if task.status == DownloadStatus.FAILED:
            if task_id in self.task_map:
                self.progress.remove_task(self.task_map[task_id])
                del self.task_map[task_id]
            self.progress.advance(self.overall_id, 1)
            err_msg = task.error_message or "Unknown error"
            console.print(f"[bold red]  ❌ Failed:[/bold red] {title_str} [dim]({err_msg})[/dim]")
            return

        # Handle active tracks
        if task_id not in self.task_map:
            desc = f"[bold cyan]Downloading[/bold cyan] {title_str}"
            self.task_map[task_id] = self.progress.add_task(desc, total=100)

        t_id = self.task_map[task_id]
        
        if task.status == DownloadStatus.TAGGING:
            self.progress.update(t_id, description=f"[bold magenta]Tagging ID3[/bold magenta] {title_str}", completed=95)
        elif task.status == DownloadStatus.CONVERTING:
            self.progress.update(t_id, description=f"[bold blue]Converting Audio[/bold blue] {title_str}", completed=85)
        else:
            self.progress.update(t_id, completed=task.progress)

    def close(self):
        self.progress.stop()


def print_tasks_summary(tasks: List[DownloadTask]):
    completed = sum(1 for t in tasks if t.status == DownloadStatus.COMPLETED)
    skipped = sum(1 for t in tasks if t.status == DownloadStatus.SKIPPED)
    failed = sum(1 for t in tasks if t.status == DownloadStatus.FAILED)
    
    console.print()
    console.print(f"[bold green]✨ Download finished: {completed} downloaded, {skipped} skipped (already exist), {failed} failed.[/bold green]")
    if failed > 0:
        console.print(f"[bold red]⚠️ {failed} track(s) failed during download. Re-run command to retry failed tracks.[/bold red]")
