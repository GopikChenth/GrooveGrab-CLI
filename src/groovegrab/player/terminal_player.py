"""
Full-Screen CAVA-Style Live TUI Terminal Player UI Component
"""

import time
import shutil
from pathlib import Path
from typing import List, Optional

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.align import Align

from groovegrab.core.models import TrackInfo
from groovegrab.player.audio_driver import AudioDriver
from groovegrab.player.keyboard import NonBlockingKeyboard
from groovegrab.player.lrc_parser import LrcParser, LrcLine
from groovegrab.player.typewriter import TypewriterAnimator
from groovegrab.player.visualizer import AudioSpectrumVisualizer, VisualizerMode, next_visualizer_mode
from groovegrab.player.themes import get_theme, next_theme_name, Theme

console = Console()


class TerminalPlayer:
    """Full-Screen CAVA-Style TUI Audio Player with Real-Time Spectrum Visualizer & Synced Lyrics."""

    def __init__(
        self,
        audio_path: Path,
        track_info: TrackInfo,
        lrc_path: Optional[Path] = None,
        theme_name: str = "cava",
        initial_mode: VisualizerMode = VisualizerMode.BARS,
    ):
        self.audio_path = audio_path
        self.track_info = track_info
        self.lrc_path = lrc_path or audio_path.with_suffix(".lrc")
        
        self.theme_name = theme_name.lower()
        self.mode = initial_mode
        self.show_lyrics = True
        self.mirror_mode = False

        self.driver = AudioDriver()
        self.lrc_parser = LrcParser()
        self.typewriter = TypewriterAnimator()
        self.visualizer = AudioSpectrumVisualizer(num_bars=48)
        
        # Load audio for real FFT if supported
        self.visualizer.load_audio_file(self.audio_path)
        
        self.lyrics: List[LrcLine] = self.lrc_parser.parse_file(self.lrc_path) if self.lrc_path.exists() else []

    def start(self):
        if not self.driver.load_and_play(self.audio_path):
            console.print(f"[bold red]❌ Error: Failed to load audio file {self.audio_path}[/bold red]")
            return

        with NonBlockingKeyboard() as kbd:
            with console.screen():
                with Live(self._build_screen(0.0), console=console, refresh_per_second=30, screen=True) as live:
                    while self.driver.is_busy():
                        current_time = self.driver.get_position_sec()
                        live.update(self._build_screen(current_time))

                        key = kbd.read_key()
                        if key:
                            if key.lower() == 'q':
                                break
                            elif key == 'SPACE':
                                self.driver.toggle_pause()
                            elif key in ('LEFT', 'h', '['):
                                self.driver.seek_relative(-5.0)
                            elif key in ('RIGHT', 'l_seek', ']'):
                                self.driver.seek_relative(5.0)
                            elif key in ('UP', 'k', '+', '='):
                                self.driver.change_volume(0.05)
                            elif key in ('DOWN', 'j', '-'):
                                self.driver.change_volume(-0.05)
                            elif key.lower() == 'm':
                                self.driver.toggle_mute()
                            elif key.lower() == 'v':
                                self.mode = next_visualizer_mode(self.mode)
                            elif key.lower() == 't':
                                self.theme_name = next_theme_name(self.theme_name)
                            elif key.lower() == 'l':
                                self.show_lyrics = not self.show_lyrics
                            elif key.lower() == 's':
                                self.mirror_mode = not self.mirror_mode

                        time.sleep(0.025)

        self.driver.stop()
        console.print(f"[bold green]✔ Playback finished:[/bold green] [white]{self.track_info.display_name()}[/white]")

    def _build_screen(self, current_time: float) -> Panel:
        theme = get_theme(self.theme_name)
        term_width = console.size.width or 80
        term_height = console.size.height or 24

        # 1. Header Information & Progress
        header_text = self._build_header(current_time, term_width, theme)

        # 2. Visualizer Height Allocation
        # Reserve lines for header (4 lines), footer (2 lines), lyrics (5 lines if shown)
        reserved_lines = 8 if self.show_lyrics else 5
        viz_height = max(5, min(term_height - reserved_lines, 20))
        viz_width = max(30, term_width - 8)

        # 3. Render Visualizer
        viz_output = self.visualizer.render(
            current_time_sec=current_time,
            width=viz_width,
            height=viz_height,
            mode=self.mode,
            theme_name=self.theme_name,
            is_playing=not self.driver.is_paused,
            mirror=self.mirror_mode
        )

        # 4. Render Synced Karaoke Lyrics (if active)
        lyrics_output = self._render_lyrics(current_time, theme) if self.show_lyrics else ""

        # 5. Footer Hotkey Controls
        footer_text = self._build_footer(theme)

        # Assemble full layout
        body_parts = [header_text, "\n", viz_output]
        if self.show_lyrics and lyrics_output:
            body_parts.extend(["\n", lyrics_output])
        body_parts.extend(["\n", footer_text])

        full_content = "\n".join(body_parts)

        return Panel(
            Text.from_markup(full_content),
            title=f"[{theme.header}] 🎵 GROOVEGRAB CAVA PLAYER [/{theme.header}]",
            subtitle=f"[dim]Theme: [bold]{theme.display_name}[/bold] | Mode: [bold]{self.mode.value.upper()}[/bold][/dim]",
            border_style=theme.border,
            expand=True,
            padding=(1, 2)
        )

    def _build_header(self, current_time: float, width: int, theme: Theme) -> str:
        status_badge = "[bold red]⏸ PAUSED[/bold red]" if self.driver.is_paused else "[bold green]▶ PLAYING[/bold green]"
        
        # Volume meter
        vol_pct = int(self.driver.volume * 100)
        if self.driver.is_muted:
            vol_str = "[bold red]🔇 MUTED[/bold red]"
        else:
            vol_bars = int(self.driver.volume * 8)
            vol_meter = "█" * vol_bars + "░" * (8 - vol_bars)
            vol_str = f"Vol: {vol_pct}% [{theme.accent}]{vol_meter}[/{theme.accent}]"

        # Duration & Progress Bar
        total_dur = self.track_info.duration or 180
        curr_min, curr_sec = int(current_time) // 60, int(current_time) % 60
        tot_min, tot_sec = int(total_dur) // 60, int(total_dur) % 60
        time_str = f"{curr_min:02d}:{curr_sec:02d} / {tot_min:02d}:{tot_sec:02d}"

        # Visual progress slider
        progress_ratio = max(0.0, min(1.0, current_time / max(1.0, float(total_dur))))
        bar_len = max(10, min(width - 45, 40))
        filled_len = int(progress_ratio * bar_len)
        progress_bar = f"[{theme.accent}]{'━' * filled_len}●[/{theme.accent}][dim white]{'─' * max(0, bar_len - filled_len - 1)}[/dim white]"

        # Metadata line
        track_line = f" [bold white]{self.track_info.title}[/bold white]  [dim]by[/dim]  [{theme.header}]{self.track_info.artist}[/{theme.header}]"
        status_line = f"  {status_badge}   {vol_str}   [bold white]{time_str}[/bold white]  {progress_bar}"

        return f"{track_line}\n{status_line}"

    def _render_lyrics(self, current_time: float, theme: Theme) -> str:
        if not self.lyrics:
            return f"  [{theme.dim_lyric}]♪ (No synced lyrics available) ♪[/{theme.dim_lyric}]"

        active_idx = 0
        for idx, line in enumerate(self.lyrics):
            if current_time >= line.timestamp_sec:
                active_idx = idx

        # Render active line with 1 line context above and 1 line below
        lines_output = []
        
        # Previous line
        if active_idx > 0:
            lines_output.append(f"    [{theme.dim_lyric}]{self.lyrics[active_idx - 1].text}[/{theme.dim_lyric}]")
        else:
            lines_output.append(" ")

        # Active line with typewriter animation
        active_line = self.lyrics[active_idx]
        rendered_active = self.typewriter.render_active_line(
            active_line,
            current_time,
            active_color=theme.active_lyric,
            dim_color=theme.dim_lyric
        )
        lines_output.append(f"  [bold yellow]❯[/bold yellow]  {rendered_active}")

        # Next line
        if active_idx + 1 < len(self.lyrics):
            lines_output.append(f"    [{theme.dim_lyric}]{self.lyrics[active_idx + 1].text}[/{theme.dim_lyric}]")
        else:
            lines_output.append(" ")

        return "\n".join(lines_output)

    def _build_footer(self, theme: Theme) -> str:
        lyrics_status = "ON" if self.show_lyrics else "OFF"
        stereo_status = "MIRROR" if self.mirror_mode else "NORMAL"
        return (
            f"[dim white]Controls: "
            f"[[bold]Space[/bold]] Pause | "
            f"[[bold]←/→[/bold]] Seek 5s | "
            f"[[bold]↑/↓[/bold]] Vol | "
            f"[[bold]M[/bold]] Mute | "
            f"[[bold]V[/bold]] Mode: [{theme.accent}]{self.mode.value}[/{theme.accent}] | "
            f"[[bold]T[/bold]] Theme: [{theme.accent}]{theme.name}[/{theme.accent}] | "
            f"[[bold]L[/bold]] Lyrics: {lyrics_status} | "
            f"[[bold]S[/bold]] {stereo_status} | "
            f"[[bold]Q[/bold]] Quit[/dim white]"
        )
