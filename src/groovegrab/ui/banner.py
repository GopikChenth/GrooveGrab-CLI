"""
ASCII Banner and Console Formatting Utilities
"""

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()

BANNER_TEXT = r"""
  ____                 _                 _ 
 |  _ \ __ _ _   _ | | ___   __ _  __| |
 | |_) / _` | | | || |/ _ \ / _` |/ _` |
 |  __/ (_| | |_| || | (_) | (_| | (_| |
 |_|   \__,_|\__, ||_|\___/ \__,_|\__,_|
             |___/                      
"""


def print_banner():
    panel = Panel(
        Text(BANNER_TEXT, style="bold cyan"),
        subtitle="[bold yellow]v0.1.0 • High-Performance Modular Media Downloader[/bold yellow]",
        border_style="bright_blue",
        expand=False
    )
    console.print(panel)


def print_error(msg: str):
    console.print(f"[bold red]❌ Error:[/bold red] {msg}")


def print_success(msg: str):
    console.print(f"[bold green]✨ Success:[/bold green] {msg}")


def print_info(msg: str):
    console.print(f"[bold blue]ℹ️  Info:[/bold blue] {msg}")
