"""
Rich Full-Screen Live TUI Terminal Player UI Component
"""

import sys
import select
import termios
import tty
import time
from pathlib import Path
from typing import List, Optional, Dict

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from groovegrab.core.models import TrackInfo
from groovegrab.player.audio_driver import AudioDriver
from groovegrab.player.lrc_parser import LrcParser, LrcLine
from groovegrab.player.typewriter import TypewriterAnimator
from groovegrab.player.visualizer import AudioSpectrumVisualizer

console = Console()

THEMES: Dict[str, Dict[str, str]] = {
    "groove": {
        "header": "bold cyan",
        "border": "cyan",
        "active_lyric": "bold bright_yellow",
        "dim_lyric": "dim white",
        "viz": "bold magenta",
        "bar": "yellow",
    },
    "cyberpunk": {
        "header": "bold bright_magenta",
        "border": "magenta",
        "active_lyric": "bold bright_cyan",
        "dim_lyric": "dim magenta",
        "viz": "bold bright_cyan",
        "bar": "cyan",
    },
    "crimson": {
        "header": "bold bright_red",
        "border": "red",
        "active_lyric": "bold bright_white",
        "dim_lyric": "dim red",
        "viz": "bold red",
        "bar": "red",
    },
    "matrix": {
        "header": "bold green",
        "border": "green",
        "active_lyric": "bold bright_green",
        "dim_lyric": "dim green",
        "viz": "bold green",
        "bar": "bright_green",
    },
}


class NonBlockingInput:
    """Helper for reading single keypresses non-blockingly on Linux/macOS."""
    
    def __init__(self):
        self.fd = sys.stdin.fileno()
        self.old_settings = None

    def __enter__(self):
        try:
            self.old_settings = termios.tcgetattr(self.fd)
            tty.setcbreak(self.fd)
        except Exception:
            pass
        return self

    def __exit__(self, type, value, traceback):
        if self.old_settings:
            try:
                termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old_settings)
            except Exception:
                pass


class TerminalPlayer:
    """Full-Screen TUI Audio Player with Synced Lyrics & Visualizer."""

    def __init__(
        self,
        audio_path: Path,
        track_info: TrackInfo,
        lrc_path: Optional[Path] = None,
        theme_name: str = "groove"
    ):
        self.audio_path = audio_path
        self.track_info = track_info
        self.lrc_path = lrc_path or audio_path.with_suffix(".lrc")
        
        self.theme = THEMES.get(theme_name.lower(), THEMES["groove"])
        self.driver = AudioDriver()
        self.lrc_parser = LrcParser()
        self.typewriter = TypewriterAnimator()
        self.visualizer = AudioSpectrumVisualizer(num_bars=44)
        
        self.lyrics: List[LrcLine] = self.lrc_parser.parse_file(self.lrc_path) if self.lrc_path.exists() else []

    def start(self):
        if not self.driver.load_and_play(self.audio_path):
            console.print(f"[bold red]❌ Error: Failed to load audio file {self.audio_path}[/bold red]")
            return

        with NonBlockingInput():
            with console.screen():
                with Live(self._build_panel(0.0), console=console, refresh_per_second=20, screen=True) as live:
                    while self.driver.is_busy():
                        current_time = self.driver.get_position_sec()
                        live.update(self._build_panel(current_time))

                        key = self._read_key()
                        if key:
                            if key.lower() == 'q':
                                break
                            elif key == ' ':
                                self.driver.toggle_pause()
                            elif key == 'LEFT':
                                self.driver.seek_relative(-5.0)
                            elif key == 'RIGHT':
                                self.driver.seek_relative(5.0)
                            elif key == 'UP':
                                self.driver.change_volume(0.05)
                            elif key == 'DOWN':
                                self.driver.change_volume(-0.05)

                        time.sleep(0.03)

        self.driver.stop()
        console.print(f"[bold green]✔ Playback finished:[/bold green] [white]{self.track_info.display_name()}[/white]")

    def _read_key(self) -> Optional[str]:
        try:
            rlist, _, _ = select.select([sys.stdin], [], [], 0.005)
            if not rlist:
                return None
            
            ch = sys.stdin.read(1)
            if ch != '\x1b':
                return ch

            # Non-blocking read of escape sequence payload
            seq = ""
            while True:
                rlist2, _, _ = select.select([sys.stdin], [], [], 0.005)
                if not rlist2:
                    break
                seq += sys.stdin.read(1)
                if len(seq) >= 16:
                    break

            if not seq:
                # Standalone ESC key press
                return "ESC"

            # Parse arrow keys and mouse wheel sequences
            if seq == "[A":
                return "UP"
            elif seq == "[B":
                return "DOWN"
            elif seq == "[C":
                return "RIGHT"
            elif seq == "[D":
                return "LEFT"
            elif "<64;" in seq or "Ma" in seq or "[5~" in seq:
                # Mouse Scroll Up / Page Up -> Increase volume
                return "UP"
            elif "<65;" in seq or "Mb" in seq or "[6~" in seq:
                # Mouse Scroll Down / Page Down -> Decrease volume
                return "DOWN"

            # Safely ignore all unhandled mouse/terminal sequences without quitting!
            return None
        except Exception:
            return None

    def _build_panel(self, current_time: float) -> Panel:
        status_icon = "⏸ PAUSED" if self.driver.is_paused else "▶ PLAYING"
        total_dur = self.track_info.duration or 180
        curr_min, curr_sec = int(current_time) // 60, int(current_time) % 60
        tot_min, tot_sec = int(total_dur) // 60, int(total_dur) % 60

        # Header Info
        header_str = f"[{self.theme['header']}]🎵 GROOVEGRAB TUI PLAYER[/{self.theme['header']}]   [{status_icon}]   Vol: {int(self.driver.volume * 100)}%"
        track_str = f"[bold white]{self.track_info.title}[/bold white] - [cyan]{self.track_info.artist}[/cyan]"
        time_str = f"[{self.theme['bar']}][▶ {curr_min:02d}:{curr_sec:02d} / {tot_min:02d}:{tot_sec:02d}][/{self.theme['bar']}]"
        
        # Audio Spectrum Visualizer
        viz_bars = self.visualizer.render_bars(current_time, is_playing=not self.driver.is_paused, color_style=self.theme["viz"])

        # Synced Karaoke Lyrics Lines
        lyrics_markup = self._render_lyrics_markup(current_time)

        controls_str = "[dim white]Controls: [bold]Space[/bold] Pause/Play | [bold]←/→[/bold] Seek 5s | [bold]↑/↓ or Scroll[/bold] Volume | [bold]Q[/bold] Quit[/dim white]"

        body_content = f"{header_str}\n{track_str}   {time_str}\n\n{viz_bars}\n\n{lyrics_markup}\n\n{controls_str}"

        return Panel(
            Text.from_markup(body_content),
            title="[bold yellow]GrooveGrab Audio TUI[/bold yellow]",
            subtitle="[bold dim]Press Q to Quit TUI[/bold dim]",
            border_style=self.theme["border"],
            expand=True,
            padding=(2, 4)
        )

    def _render_lyrics_markup(self, current_time: float) -> str:
        if not self.lyrics:
            return "[dim white]♪ No synced lyrics available for this track ♪[/dim white]"

        active_idx = 0
        for idx, line in enumerate(self.lyrics):
            if current_time >= line.timestamp_sec:
                active_idx = idx

        # Render 3 lines above, 1 active line with typewriter, 3 lines below
        start_idx = max(0, active_idx - 3)
        end_idx = min(len(self.lyrics), active_idx + 4)

        lines_output = []
        for idx in range(start_idx, end_idx):
            line = self.lyrics[idx]
            if idx == active_idx:
                rendered = self.typewriter.render_active_line(
                    line,
                    current_time,
                    active_color=self.theme["active_lyric"],
                    dim_color=self.theme["dim_lyric"]
                )
                lines_output.append(f" ❯  {rendered}")
            else:
                lines_output.append(f"    [{self.theme['dim_lyric']}]{line.text}[/{self.theme['dim_lyric']}]")

        return "\n".join(lines_output)
