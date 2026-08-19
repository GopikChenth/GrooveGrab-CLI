"""
Live MPRIS Synced Lyrics Terminal Player Component
Clean 2-line couplet lyrics display (Line 1 -> Line 2 -> CLR) with full-height bottom CAVA visualizer for Spotify.
"""

import time
from typing import List, Optional

from rich.console import Console
from rich.live import Live
from rich.text import Text

from groovegrab.engines.mpris_engine import MprisEngine, MprisTrackInfo
from groovegrab.engines.lyric_fetcher import LyricFetcher
from groovegrab.player.lrc_parser import LrcParser, LrcLine
from groovegrab.player.typewriter import TypewriterAnimator
from groovegrab.player.keyboard import NonBlockingKeyboard
from groovegrab.player.themes import get_theme, next_theme_name, Theme
from groovegrab.player.visualizer import AudioSpectrumVisualizer, VisualizerMode, next_visualizer_mode

console = Console()


class MprisLiveLyricsPlayer:
    """Live terminal synchronized lyrics displayer with 2-line couplet lyrics and bottom CAVA visualizer."""

    def __init__(
        self,
        player_name: Optional[str] = None,
        theme_name: str = "cava",
        initial_mode: VisualizerMode = VisualizerMode.BARS
    ):
        self.engine = MprisEngine()
        self.fetcher = LyricFetcher()
        self.parser = LrcParser()
        self.typewriter = TypewriterAnimator()
        self.visualizer = AudioSpectrumVisualizer(num_bars=48)
        
        self.target_player = player_name
        self.theme_name = theme_name.lower()
        self.mode = initial_mode

        self.current_track: Optional[MprisTrackInfo] = None
        self.current_lyrics: List[LrcLine] = []
        self.last_track_signature: str = ""

    def start(self):
        """Starts the live MPRIS synchronized lyric tracking loop."""
        players = self.engine.list_active_players()
        if not players:
            console.print("[bold yellow][Warning] No active media players found on D-Bus.[/bold yellow]")
            console.print("[dim]Please start Spotify or another media player and play a song.[/dim]\n")

        with NonBlockingKeyboard() as kbd:
            with console.screen():
                with Live(self._build_screen(0.0), console=console, refresh_per_second=30, screen=True) as live:
                    last_poll_time = 0.0

                    while True:
                        now = time.monotonic()
                        
                        # Poll D-Bus every 300ms for track metadata & state
                        if now - last_poll_time > 0.30:
                            self._poll_mpris()
                            last_poll_time = now

                        # Compute exact interpolated position
                        if self.current_track:
                            current_pos = self.engine.get_interpolated_position(self.current_track)
                        else:
                            current_pos = 0.0

                        live.update(self._build_screen(current_pos))

                        # Handle keyboard interactions
                        key = kbd.read_key()
                        if key:
                            if key.lower() == 'q' or key == 'ESC':
                                break
                            elif key == 'SPACE':
                                self.engine.play_pause(self.current_track.player_name if self.current_track else None)
                                self._poll_mpris()
                            elif key.lower() in ('n', 'right'):
                                self.engine.next_track(self.current_track.player_name if self.current_track else None)
                                self._poll_mpris()
                            elif key.lower() in ('p', 'left'):
                                self.engine.previous_track(self.current_track.player_name if self.current_track else None)
                                self._poll_mpris()
                            elif key.lower() == 't':
                                self.theme_name = next_theme_name(self.theme_name)
                            elif key.lower() == 'v':
                                self.mode = next_visualizer_mode(self.mode)

                        time.sleep(0.025)

        console.print("[bold green][Lyrics tracker stopped][/bold green]")

    def _poll_mpris(self):
        track_info = self.engine.get_track_info(self.target_player)
        if not track_info:
            self.current_track = None
            return

        self.current_track = track_info
        sig = f"{track_info.artist}_{track_info.title}_{track_info.track_id}"

        # Detect track change
        if sig != self.last_track_signature and (track_info.title or track_info.artist):
            self.last_track_signature = sig
            self._load_lyrics_for_track(track_info)

    def _load_lyrics_for_track(self, track_info: MprisTrackInfo):
        synced_text, _ = self.fetcher.fetch_lyrics_by_metadata(
            title=track_info.title,
            artist=track_info.artist,
            album=track_info.album,
            duration=track_info.duration_sec
        )
        if synced_text:
            self.current_lyrics = self.parser.parse_text(synced_text)
        else:
            self.current_lyrics = []

    def _build_screen(self, current_pos: float) -> Text:
        theme = get_theme(self.theme_name)
        term_width = max(30, console.size.width or 80)
        term_height = max(10, console.size.height or 24)

        if not self.current_track or (not self.current_track.title and not self.current_track.artist):
            content = f"\n  [{theme.header}]> SPOTIFY LIVE LYRICS TRACKER[/{theme.header}]\n\n  [dim]Waiting for Spotify / MPRIS playback on D-Bus...[/dim]\n  [dim]Play any song in Spotify to start live lyric sync.[/dim]\n"
            text_obj = Text.from_markup(content)
            text_obj.no_wrap = True
            return text_obj

        # 1. Top Header
        header_str = self._build_header(current_pos, term_width, theme)
        header_lines = [l for l in header_str.split("\n") if l]

        # 2. Exactly 2 Lines of Synced Couplet Lyrics
        lyrics_str = self._render_lyrics_2lines(current_pos, theme)
        lyrics_lines = lyrics_str.split("\n") if lyrics_str else []

        # 3. Full-Height Bottom CAVA Spectrum Visualizer
        reserved_lines = len(header_lines) + len(lyrics_lines)
        viz_height = max(3, term_height - reserved_lines - 1)
        viz_width = term_width

        is_playing = self.current_track.status.lower() == "playing"
        viz_output = self.visualizer.render(
            current_time_sec=current_pos,
            width=viz_width,
            height=viz_height,
            mode=self.mode,
            theme_name=self.theme_name,
            is_playing=is_playing,
            mirror=False
        )

        body_parts = [header_str]
        if lyrics_str:
            body_parts.append(lyrics_str)
        body_parts.append(viz_output)

        full_content = "\n".join(body_parts)
        text_obj = Text.from_markup(full_content)
        text_obj.no_wrap = True
        return text_obj

    def _build_header(self, current_pos: float, width: int, theme: Theme) -> str:
        track = self.current_track
        is_playing = track.status.lower() == "playing"
        status_badge = f"[{theme.header}]PLAYING[/{theme.header}]" if is_playing else f"[{theme.header}]PAUSED[/{theme.header}]"

        total_dur = track.duration_sec or 180.0
        curr_min, curr_sec = int(current_pos) // 60, int(current_pos) % 60
        tot_min, tot_sec = int(total_dur) // 60, int(total_dur) % 60
        time_str = f"{curr_min:02d}:{curr_sec:02d} / {tot_min:02d}:{tot_sec:02d}"

        title = track.title or "Unknown Title"
        artist = track.artist or "Unknown Artist"
        player_label = f"[{track.player_name.upper()}]" if track.player_name else "[SPOTIFY]"

        progress_ratio = max(0.0, min(1.0, current_pos / max(1.0, float(total_dur))))
        bar_len = max(6, min(width - len(title) - len(artist) - 45, 18))
        filled_len = int(progress_ratio * bar_len)
        progress_bar = f"[{theme.header}]{'━' * filled_len}●[/{theme.header}][dim {theme.header}]{'─' * max(0, bar_len - filled_len - 1)}[/dim {theme.header}]"

        return f" [{theme.header}]> {player_label} {title} - {artist}[/{theme.header}]  {status_badge}  [{theme.header}]{time_str}[/{theme.header}] {progress_bar}"

    def _render_lyrics_2lines(self, current_pos: float, theme: Theme) -> str:
        """
        Renders exactly 2 lines in couplets (Pairs) with clear on transition:
        - Couplet 1: Line 1 types -> Line 2 types below it while Line 1 stays -> CLR!
        - Couplet 2: Line 3 types -> Line 4 types below it while Line 3 stays -> CLR!
        - Zero dull preview text anywhere.
        """
        if not self.current_lyrics:
            return " \n "

        # 1. Before first lyric: Both rows blank (no dull text)
        if current_pos < self.current_lyrics[0].timestamp_sec:
            return " \n "

        # 2. Find active line index
        active_idx = 0
        for idx, line in enumerate(self.current_lyrics):
            if current_pos >= line.timestamp_sec:
                active_idx = idx

        # Couplet pair base index (0, 2, 4, 6, ...)
        pair_start = (active_idx // 2) * 2
        line_top = self.current_lyrics[pair_start]
        line_bottom = self.current_lyrics[pair_start + 1] if pair_start + 1 < len(self.current_lyrics) else None

        if active_idx == pair_start:
            # First line of couplet is active and typing; second row is blank
            rendered_top = self.typewriter.render_active_line(
                line_top,
                current_pos,
                active_color=f"{theme.header}"
            )
            line1 = f" [{theme.header}]>[/{theme.header}] {rendered_top}[{theme.header}]█[/{theme.header}]"
            line2 = " "
        else:
            # First line of couplet completed; second line is active and typing below it
            line1 = f"   [{theme.header}]{line_top.text}[/{theme.header}]"
            if line_bottom:
                rendered_bottom = self.typewriter.render_active_line(
                    line_bottom,
                    current_pos,
                    active_color=f"{theme.header}"
                )
                line2 = f" [{theme.header}]>[/{theme.header}] {rendered_bottom}[{theme.header}]█[/{theme.header}]"
            else:
                line2 = " "

        return f"{line1}\n{line2}"
