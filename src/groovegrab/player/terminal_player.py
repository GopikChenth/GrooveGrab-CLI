"""
Full-Screen CAVA-Style Live TUI Terminal Player UI Component
Clean, borderless, minimal aesthetic matching native CAVA visualizer
"""

import time
from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.live import Live
from rich.text import Text

from groovegrab.core.models import TrackInfo
from groovegrab.player.audio_driver import AudioDriver
from groovegrab.player.keyboard import NonBlockingKeyboard
from groovegrab.player.lrc_parser import LrcParser, LrcLine
from groovegrab.player.typewriter import TypewriterAnimator
from groovegrab.player.visualizer import AudioSpectrumVisualizer, VisualizerMode, next_visualizer_mode
from groovegrab.player.themes import get_theme, next_theme_name, Theme

console = Console()


class TerminalPlayer:
    """Clean Borderless CAVA-Style TUI Audio Player with Real-Time Spectrum Visualizer & Synced Lyrics."""

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
                            elif key in ('RIGHT', 'l', ']'):
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

    def _build_screen(self, current_time: float) -> Text:
        theme = get_theme(self.theme_name)
        term_width = console.size.width or 80
        term_height = console.size.height or 24

        # 1. Minimal Header (Track Title, Time & Volume)
        header_text = self._build_header(current_time, term_width, theme)

        # 2. Maximize Visualizer Height
        has_lyrics = self.show_lyrics and bool(self.lyrics)
        reserved_lines = 4 if has_lyrics else 2
        viz_height = max(4, term_height - reserved_lines)
        viz_width = max(20, term_width)

        # 3. Render Borderless CAVA Spectrum Visualizer
        viz_output = self.visualizer.render(
            current_time_sec=current_time,
            width=viz_width,
            height=viz_height,
            mode=self.mode,
            theme_name=self.theme_name,
            is_playing=not self.driver.is_paused,
            mirror=self.mirror_mode
        )

        # 4. Render Synced Karaoke Lyrics Line (if present)
        lyrics_output = self._render_lyrics(current_time, theme) if has_lyrics else ""

        # Assemble clean, borderless layout (NO outer box panel, NO footer text explanation)
        body_parts = [header_text, viz_output]
        if lyrics_output:
            body_parts.append(lyrics_output)

        full_content = "\n".join(body_parts)
        return Text.from_markup(full_content)

    def _build_header(self, current_time: float, width: int, theme: Theme) -> str:
        status_badge = "[bold red]⏸ PAUSED[/bold red]" if self.driver.is_paused else "[bold green]▶ PLAYING[/bold green]"
        
        # Volume meter
        vol_pct = int(self.driver.volume * 100)
        if self.driver.is_muted:
            vol_str = "[bold red]🔇 MUTED[/bold red]"
        else:
            vol_bars = int(self.driver.volume * 6)
            vol_meter = "█" * vol_bars + "░" * (6 - vol_bars)
            vol_str = f"Vol: {vol_pct}% [{theme.accent}]{vol_meter}[/{theme.accent}]"

        # Duration & Progress
        total_dur = self.track_info.duration or 180
        curr_min, curr_sec = int(current_time) // 60, int(current_time) % 60
        tot_min, tot_sec = int(total_dur) // 60, int(total_dur) % 60
        time_str = f"{curr_min:02d}:{curr_sec:02d} / {tot_min:02d}:{tot_sec:02d}"

        # Visual progress bar slider
        progress_ratio = max(0.0, min(1.0, current_time / max(1.0, float(total_dur))))
        bar_len = max(8, min(width - 45, 30))
        filled_len = int(progress_ratio * bar_len)
        progress_bar = f"[{theme.accent}]{'━' * filled_len}●[/{theme.accent}][dim white]{'─' * max(0, bar_len - filled_len - 1)}[/dim white]"

        # Metadata line
        track_line = f"🎵 [bold white]{self.track_info.title}[/bold white] [dim]by[/dim] [{theme.header}]{self.track_info.artist}[/{theme.header}]  {status_badge}  {vol_str}  [bold white]{time_str}[/bold white] {progress_bar}"

        return track_line

    def _render_lyrics(self, current_time: float, theme: Theme) -> str:
        if not self.lyrics:
            return ""

        active_idx = 0
        for idx, line in enumerate(self.lyrics):
            if current_time >= line.timestamp_sec:
                active_idx = idx

        # Active line with typewriter animation
        active_line = self.lyrics[active_idx]
        rendered_active = self.typewriter.render_active_line(
            active_line,
            current_time,
            active_color=theme.active_lyric,
            dim_color=theme.dim_lyric
        )
        return f" ❯ {rendered_active}"
