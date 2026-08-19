"""
Full-Screen CAVA-Style Live TUI Terminal Player UI Component
Seamless offline playlist queue & single-track playback with real-time 2-line lyrics & bottom CAVA visualizer.
"""

import time
from pathlib import Path
from typing import List, Tuple, Optional

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
from groovegrab.engines.lyric_fetcher import LyricFetcher
from groovegrab.player.timing_chain import TimingChain

console = Console()

PlaylistItem = Tuple[Path, TrackInfo, Optional[Path]]


class TerminalPlayer:
    """Seamless Offline CAVA Audio Player supporting continuous playlist queues, 2-line lyrics & FFT visualizer."""

    def __init__(
        self,
        audio_path: Optional[Path] = None,
        track_info: Optional[TrackInfo] = None,
        lrc_path: Optional[Path] = None,
        playlist: Optional[List[PlaylistItem]] = None,
        start_index: int = 0,
        theme_name: str = "cava",
        initial_mode: VisualizerMode = VisualizerMode.BARS,
    ):
        if playlist:
            self.playlist: List[PlaylistItem] = playlist
        elif audio_path and track_info:
            self.playlist = [(audio_path, track_info, lrc_path or audio_path.with_suffix(".lrc"))]
        else:
            self.playlist = []

        self.current_index = max(0, min(start_index, len(self.playlist) - 1)) if self.playlist else 0
        self.theme_name = theme_name.lower()
        self.mode = initial_mode
        self.show_lyrics = True
        self.mirror_mode = False

        self.driver = AudioDriver()
        self.lrc_parser = LrcParser()
        self.typewriter = TypewriterAnimator()
        self.visualizer = AudioSpectrumVisualizer(num_bars=48)
        self.timing_chain = TimingChain()

        self.audio_path: Optional[Path] = None
        self.track_info: Optional[TrackInfo] = None
        self.lrc_path: Optional[Path] = None
        self.lyrics: List[LrcLine] = []

        if self.playlist:
            self._load_track(self.current_index)

    def _load_track(self, index: int):
        if not self.playlist or index < 0 or index >= len(self.playlist):
            return

        self.current_index = index
        self.audio_path, self.track_info, self.lrc_path = self.playlist[index]
        self.visualizer.load_audio_file(self.audio_path)
        self.lyrics = self._resolve_and_load_lyrics()

    def _resolve_and_load_lyrics(self) -> List[LrcLine]:
        if not self.audio_path or not self.track_info:
            return []

        # 1. Check exact .lrc path next to audio file
        if self.lrc_path and self.lrc_path.exists():
            parsed = self.lrc_parser.parse_file(self.lrc_path)
            if parsed:
                return parsed

        # 2. Check parent directory for matching .lrc files
        if self.audio_path.parent.exists():
            stem_lower = self.audio_path.stem.lower()
            for lrc_candidate in self.audio_path.parent.glob("*.lrc"):
                if lrc_candidate.stem.lower() in stem_lower or stem_lower in lrc_candidate.stem.lower():
                    parsed = self.lrc_parser.parse_file(lrc_candidate)
                    if parsed:
                        self.lrc_path = lrc_candidate
                        return parsed

        # 3. Query and cache offline
        fetcher = LyricFetcher()
        synced_text, _ = fetcher.fetch_lyrics(self.track_info)
        if synced_text:
            parsed = self.lrc_parser.parse_text(synced_text)
            if parsed:
                try:
                    offline_lrc = self.audio_path.with_suffix(".lrc")
                    fetcher.save_lrc_file(offline_lrc, synced_text)
                except Exception:
                    pass
                return parsed

        return []

    def start(self):
        if not self.playlist:
            console.print("[bold red][Error] No audio tracks in playlist.[/bold red]")
            return

        with NonBlockingKeyboard() as kbd:
            with console.screen():
                with Live(self._build_screen(0.0), console=console, refresh_per_second=30, screen=True) as live:
                    while True:
                        if not self.audio_path or not self.driver.load_and_play(self.audio_path):
                            break

                        track_finished_naturally = False
                        while True:
                            # Check if current song finished naturally
                            if not self.driver.is_busy():
                                track_finished_naturally = True
                                break

                            current_time = self.driver.get_position_sec()
                            live.update(self._build_screen(current_time))

                            key = kbd.read_key()
                            if key:
                                if key.lower() == 'q' or key == 'ESC':
                                    self.driver.stop()
                                    return
                                elif key == 'SPACE':
                                    self.driver.toggle_pause()
                                elif key in ('LEFT', 'h'):
                                    self.driver.seek_relative(-5.0)
                                elif key in ('RIGHT', 'l'):
                                    self.driver.seek_relative(+5.0)
                                elif key in ('UP', 'k'):
                                    self.driver.change_volume(+0.1)
                                elif key in ('DOWN', 'j'):
                                    self.driver.change_volume(-0.1)
                                elif key.lower() == 'n':
                                    # Next track
                                    if self.current_index + 1 < len(self.playlist):
                                        self._load_track(self.current_index + 1)
                                        break
                                elif key.lower() == 'p':
                                    # Previous track
                                    if self.current_index > 0:
                                        self._load_track(self.current_index - 1)
                                        break
                                elif key.lower() == 'm':
                                    self.driver.toggle_mute()
                                elif key.lower() == 't':
                                    self.theme_name = next_theme_name(self.theme_name)
                                elif key.lower() == 'v':
                                    self.mode = next_visualizer_mode(self.mode)

                            time.sleep(0.025)

                        # Auto-advance to next track in playlist queue
                        if track_finished_naturally:
                            if self.current_index + 1 < len(self.playlist):
                                self._load_track(self.current_index + 1)
                            else:
                                break  # End of playlist

        self.driver.stop()
        if self.track_info:
            console.print(f"[bold green][Playback finished][/bold green] [white]{self.track_info.display_name()}[/white]")

    def _build_screen(self, current_time: float) -> Text:
        theme = get_theme(self.theme_name)
        term_width = max(30, console.size.width or 80)
        term_height = max(10, console.size.height or 24)

        if not self.track_info:
            return Text.from_markup("  [dim]No track loaded[/dim]")

        # 1. Top Status Header
        header_str = self._build_header(current_time, term_width, theme)
        header_lines = [l for l in header_str.split("\n") if l]

        # 2. Exactly 2 Lines of Synchronized Lyrics (Active + Upcoming Preview)
        has_lyrics = self.show_lyrics and bool(self.lyrics)
        lyrics_str = self._render_lyrics_2lines(current_time, theme) if has_lyrics else ""
        lyrics_lines = [l for l in lyrics_str.split("\n") if l] if lyrics_str else []

        # 3. Maximize CAVA Spectrum Visualizer Height for the Bottom Area
        reserved_lines = len(header_lines) + len(lyrics_lines)
        viz_height = max(3, term_height - reserved_lines - 1)
        viz_width = term_width

        # 4. Render Bottom CAVA Spectrum Visualizer
        viz_output = self.visualizer.render(
            current_time_sec=current_time,
            width=viz_width,
            height=viz_height,
            mode=self.mode,
            theme_name=self.theme_name,
            is_playing=not self.driver.is_paused,
            mirror=self.mirror_mode
        )

        body_parts = [header_str]
        if lyrics_str:
            body_parts.append(lyrics_str)
        body_parts.append(viz_output)

        full_content = "\n".join(body_parts)
        text_obj = Text.from_markup(full_content)
        text_obj.no_wrap = True
        return text_obj

    def _build_header(self, current_time: float, width: int, theme: Theme) -> str:
        status_badge = f"[{theme.header}]PLAYING[/{theme.header}]" if not self.driver.is_paused else f"[{theme.header}]PAUSED[/{theme.header}]"
        
        vol_pct = int(self.driver.volume * 100)
        vol_str = f"[{theme.header}]Vol: {vol_pct}%[/{theme.header}]" if not self.driver.is_muted else f"[{theme.header}]Vol: Muted[/{theme.header}]"

        total_dur = self.track_info.duration or 180
        curr_min, curr_sec = int(current_time) // 60, int(current_time) % 60
        tot_min, tot_sec = int(total_dur) // 60, int(total_dur) % 60
        time_str = f"{curr_min:02d}:{curr_sec:02d} / {tot_min:02d}:{tot_sec:02d}"

        title = self.track_info.title
        artist = self.track_info.artist

        queue_tag = f"[{self.current_index + 1}/{len(self.playlist)}] " if len(self.playlist) > 1 else ""

        progress_ratio = max(0.0, min(1.0, current_time / max(1.0, float(total_dur))))
        bar_len = max(6, min(width - len(title) - len(artist) - 45, 18))
        filled_len = int(progress_ratio * bar_len)
        progress_bar = f"[{theme.header}]{'━' * filled_len}●[/{theme.header}][dim {theme.header}]{'─' * max(0, bar_len - filled_len - 1)}[/dim {theme.header}]"

        return f" [{theme.header}]> {queue_tag}PLAYING TRACK - {title} - {artist}[/{theme.header}]  {status_badge}  [{theme.header}]{time_str}[/{theme.header}] {progress_bar}"

    def _render_lyrics_2lines(self, current_time: float, theme: Theme) -> str:
        if not self.lyrics:
            return ""

        # Check if before first lyric (Intro)
        if current_time < self.lyrics[0].timestamp_sec:
            first_preview = self.lyrics[0].text if self.lyrics else ""
            line1 = f" [{theme.header}]>[/{theme.header}] [{theme.header}]♪ (Instrumental Intro)[/{theme.header}][{theme.header}]█[/{theme.header}]"
            line2 = f" [dim {theme.header}]  {first_preview}[/dim {theme.header}]" if first_preview else " [dim]  ♪[/dim]"
            return f"{line1}\n{line2}"

        # Find active line
        idx, active_line = self.timing_chain.find_active_line(self.lyrics, current_time)

        if active_line is None or idx is None:
            return ""

        # Line 1: Active singing line with typewriter word reveal
        rendered_active = self.typewriter.render_active_line(
            active_line,
            current_time,
            active_color=f"{theme.header}"
        )
        if not rendered_active:
            line1 = f" [{theme.header}]>[/{theme.header}] [{theme.header}]{active_line.text}[/{theme.header}][{theme.header}]█[/{theme.header}]"
        else:
            line1 = f" [{theme.header}]>[/{theme.header}] {rendered_active}[{theme.header}]█[/{theme.header}]"

        # Line 2: Next upcoming preview line
        if idx + 1 < len(self.lyrics):
            next_line = self.lyrics[idx + 1]
            gap = next_line.timestamp_sec - active_line.timestamp_sec
            if not next_line.text.strip() or (gap >= 4.5 and current_pos_check(current_time, active_line.timestamp_sec)):
                line2 = f" [dim {theme.header}]  ♪[/dim {theme.header}]"
            else:
                line2 = f" [dim {theme.header}]  {next_line.text}[/dim {theme.header}]"
        else:
            line2 = f" [dim {theme.header}]  (Outro)[/dim {theme.header}]"

        return f"{line1}\n{line2}"


def current_pos_check(current_time: float, active_ts: float) -> bool:
    return current_time > active_ts + 3.0
