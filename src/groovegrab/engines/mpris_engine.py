"""
MPRIS2 D-Bus Media Player Listener Engine
Discovers active players (Spotify, VLC, browser, etc.) and tracks real-time playback position.
"""

import time
import subprocess
import shutil
import re
from typing import List, Optional
from pydantic import BaseModel, Field


class MprisTrackInfo(BaseModel):
    title: str = ""
    artist: str = ""
    album: str = ""
    duration_sec: float = 0.0
    position_sec: float = 0.0
    status: str = "Stopped"  # Playing, Paused, Stopped
    player_name: str = ""
    track_id: str = ""
    poll_timestamp: float = Field(default_factory=time.monotonic)

    def display_name(self) -> str:
        if self.artist and self.title:
            return f"{self.artist} - {self.title}"
        return self.title or self.artist or "Unknown Track"


class MprisEngine:
    """Discovers and communicates with MPRIS2 media players via D-Bus on Linux."""

    def __init__(self):
        self.has_gdbus = shutil.which("gdbus") is not None
        self.has_playerctl = shutil.which("playerctl") is not None
        self.has_qdbus = shutil.which("qdbus") is not None

    def list_active_players(self) -> List[str]:
        """
        Lists all active MPRIS media players on the current D-Bus session bus.
        Prioritizes Spotify if active.
        """
        players: List[str] = []

        if self.has_gdbus:
            cmd = [
                "gdbus", "call", "--session",
                "--dest", "org.freedesktop.DBus",
                "--object-path", "/org/freedesktop/DBus",
                "--method", "org.freedesktop.DBus.ListNames"
            ]
            try:
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=1.5)
                if res.stdout:
                    matches = re.findall(r"\x27(org\.mpris\.MediaPlayer2\.[^\x27]+)\x27", res.stdout)
                    players = matches
            except Exception:
                pass

        elif self.has_qdbus:
            try:
                res = subprocess.run(["qdbus"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=1.5)
                if res.stdout:
                    players = [line.strip() for line in res.stdout.splitlines() if line.strip().startswith("org.mpris.MediaPlayer2.")]
            except Exception:
                pass

        elif self.has_playerctl:
            try:
                res = subprocess.run(["playerctl", "-l"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=1.5)
                if res.stdout:
                    players = [f"org.mpris.MediaPlayer2.{p.strip()}" for p in res.stdout.splitlines() if p.strip()]
            except Exception:
                pass

        # Sort: Put Spotify at the very top of priority list
        def player_priority(name: str) -> int:
            name_lower = name.lower()
            if "spotify" in name_lower:
                return 0
            if "cava" in name_lower or "player" in name_lower:
                return 1
            if "vlc" in name_lower or "mpv" in name_lower:
                return 2
            return 3

        players.sort(key=player_priority)
        return players

    def get_track_info(self, player_dest: Optional[str] = None) -> Optional[MprisTrackInfo]:
        """
        Polls current metadata, playback status, and position from the targeted or active MPRIS player.
        """
        if not player_dest:
            players = self.list_active_players()
            if not players:
                return None
            player_dest = players[0]

        if self.has_gdbus:
            return self._query_gdbus(player_dest)
        elif self.has_playerctl:
            return self._query_playerctl(player_dest)
        elif self.has_qdbus:
            return self._query_qdbus(player_dest)

        return None

    def _query_gdbus(self, player_dest: str) -> Optional[MprisTrackInfo]:
        cmd = [
            "gdbus", "call", "--session",
            "--dest", player_dest,
            "--object-path", "/org/mpris/MediaPlayer2",
            "--method", "org.freedesktop.DBus.Properties.GetAll",
            "org.mpris.MediaPlayer2.Player"
        ]
        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=1.5)
            if not res.stdout or res.returncode != 0:
                return None
            out = res.stdout

            # Extract PlaybackStatus
            status_match = re.search(r"\x27PlaybackStatus\x27:\s*<\x27([^\x27]+)\x27>", out)
            status = status_match.group(1) if status_match else "Stopped"

            # Extract Position (microseconds -> seconds)
            pos_match = re.search(r"\x27Position\x27:\s*<int64\s*(\d+)>", out)
            position_sec = (int(pos_match.group(1)) / 1_000_000.0) if pos_match else 0.0

            # Extract Title
            title_match = re.search(r"\x27xesam:title\x27:\s*<\x27([^\x27]*)\x27>", out)
            title = title_match.group(1) if title_match else ""

            # Extract Album
            album_match = re.search(r"\x27xesam:album\x27:\s*<\x27([^\x27]*)\x27>", out)
            album = album_match.group(1) if album_match else ""

            # Extract Artist
            artist_list_match = re.search(r"\x27xesam:artist\x27:\s*<\[([^\]]*)\]>", out)
            if artist_list_match:
                artists = re.findall(r"\x27([^\x27]+)\x27", artist_list_match.group(1))
                artist = ", ".join(artists)
            else:
                artist_match = re.search(r"\x27xesam:artist\x27:\s*<\x27([^\x27]*)\x27>", out)
                artist = artist_match.group(1) if artist_match else ""

            # Extract Duration (microseconds -> seconds)
            len_match = re.search(r"\x27mpris:length\x27:\s*<int64\s*(\d+)>", out)
            duration_sec = (int(len_match.group(1)) / 1_000_000.0) if len_match else 0.0

            # Extract Track ID
            id_match = re.search(r"\x27mpris:trackid\x27:\s*<(?:objectpath\s*)?\x27?([^\x27>]+)\x27?>", out)
            track_id = id_match.group(1) if id_match else ""

            short_name = player_dest.replace("org.mpris.MediaPlayer2.", "")

            return MprisTrackInfo(
                title=title,
                artist=artist,
                album=album,
                duration_sec=duration_sec,
                position_sec=position_sec,
                status=status,
                player_name=short_name,
                track_id=track_id,
                poll_timestamp=time.monotonic()
            )
        except Exception:
            return None

    def _query_playerctl(self, player_dest: str) -> Optional[MprisTrackInfo]:
        player_name = player_dest.replace("org.mpris.MediaPlayer2.", "")
        try:
            fmt = "{{status}}||{{title}}||{{artist}}||{{album}}||{{position}}||{{mpris:length}}||{{mpris:trackid}}"
            cmd = ["playerctl", "-p", player_name, "metadata", "--format", fmt]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=1.5)
            if res.stdout and res.returncode == 0:
                parts = res.stdout.strip().split("||")
                if len(parts) >= 7:
                    status, title, artist, album, pos_str, len_str, track_id = parts[:7]
                    pos_sec = (float(pos_str) / 1_000_000.0) if pos_str.isdigit() else (float(pos_str) if pos_str else 0.0)
                    dur_sec = (float(len_str) / 1_000_000.0) if len_str.isdigit() else (float(len_str) if len_str else 0.0)
                    return MprisTrackInfo(
                        title=title,
                        artist=artist,
                        album=album,
                        duration_sec=dur_sec,
                        position_sec=pos_sec,
                        status=status,
                        player_name=player_name,
                        track_id=track_id,
                        poll_timestamp=time.monotonic()
                    )
        except Exception:
            pass
        return None

    def _query_qdbus(self, player_dest: str) -> Optional[MprisTrackInfo]:
        try:
            status_res = subprocess.run(["qdbus", player_dest, "/org/mpris/MediaPlayer2", "org.mpris.MediaPlayer2.Player.PlaybackStatus"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=1.0)
            pos_res = subprocess.run(["qdbus", player_dest, "/org/mpris/MediaPlayer2", "org.mpris.MediaPlayer2.Player.Position"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=1.0)
            status = status_res.stdout.strip() if status_res.stdout else "Stopped"
            pos_sec = (int(pos_res.stdout.strip()) / 1_000_000.0) if pos_res.stdout and pos_res.stdout.strip().isdigit() else 0.0

            return MprisTrackInfo(
                title="",
                artist="",
                status=status,
                position_sec=pos_sec,
                player_name=player_dest.replace("org.mpris.MediaPlayer2.", ""),
                poll_timestamp=time.monotonic()
            )
        except Exception:
            return None

    def get_interpolated_position(self, track_info: MprisTrackInfo) -> float:
        """
        Calculates high-precision monotonic playback position between D-Bus polling intervals.
        """
        if track_info.status.lower() == "playing":
            elapsed = time.monotonic() - track_info.poll_timestamp
            interpolated = track_info.position_sec + elapsed
            if track_info.duration_sec > 0:
                return min(track_info.duration_sec, interpolated)
            return max(0.0, interpolated)
        return track_info.position_sec

    def play_pause(self, player_dest: Optional[str] = None):
        dest = player_dest or (self.list_active_players() or ["org.mpris.MediaPlayer2.spotify"])[0]
        if self.has_gdbus:
            cmd = ["gdbus", "call", "--session", "--dest", dest, "--object-path", "/org/mpris/MediaPlayer2", "--method", "org.mpris.MediaPlayer2.Player.PlayPause"]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def next_track(self, player_dest: Optional[str] = None):
        dest = player_dest or (self.list_active_players() or ["org.mpris.MediaPlayer2.spotify"])[0]
        if self.has_gdbus:
            cmd = ["gdbus", "call", "--session", "--dest", dest, "--object-path", "/org/mpris/MediaPlayer2", "--method", "org.mpris.MediaPlayer2.Player.Next"]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def previous_track(self, player_dest: Optional[str] = None):
        dest = player_dest or (self.list_active_players() or ["org.mpris.MediaPlayer2.spotify"])[0]
        if self.has_gdbus:
            cmd = ["gdbus", "call", "--session", "--dest", dest, "--object-path", "/org/mpris/MediaPlayer2", "--method", "org.mpris.MediaPlayer2.Player.Previous"]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
