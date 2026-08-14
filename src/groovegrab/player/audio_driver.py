"""
Universal Cross-Platform Audio Playback Driver & Clock Controller
Supports Windows, Linux, and macOS with ffplay, mpv, or fallback players.
"""

import os
import sys
import time
import shutil
import signal
import subprocess
from pathlib import Path
from typing import Optional

IS_WINDOWS = os.name == "nt"


class AudioDriver:
    """Universal audio driver with robust cross-platform clock tracking and process management."""

    def __init__(self):
        self.proc: Optional[subprocess.Popen] = None
        self.is_loaded = False
        self.is_paused = False
        self.is_muted = False
        self.start_time_sec = 0.0
        self.accumulated_time_sec = 0.0
        self.volume = 0.8
        self.previous_volume = 0.8
        self.file_path: Optional[Path] = None
        
        self.player_cmd = self._detect_system_player()

    def _detect_system_player(self) -> Optional[str]:
        for cmd in ["ffplay", "mpv", "paplay", "aplay", "afplay"]:
            if shutil.which(cmd):
                return cmd
        return None

    def load_and_play(self, file_path: Path, start_offset: float = 0.0) -> bool:
        if not file_path.exists():
            return False

        self.stop()
        self.file_path = file_path
        self.is_loaded = True
        self.is_paused = False
        self.accumulated_time_sec = start_offset
        self.start_time_sec = time.time()

        vol_val = 0 if self.is_muted else int(self.volume * 100)

        if self.player_cmd == "ffplay":
            cmd = ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", "-volume", str(vol_val)]
            if start_offset > 0:
                cmd.extend(["-ss", f"{start_offset:.2f}"])
            cmd.append(str(file_path))
        elif self.player_cmd == "mpv":
            cmd = ["mpv", "--no-video", f"--volume={vol_val}"]
            if start_offset > 0:
                cmd.extend([f"--start={start_offset:.2f}"])
            cmd.append(str(file_path))
        elif self.player_cmd in ["paplay", "aplay", "afplay"]:
            cmd = [self.player_cmd, str(file_path)]
        else:
            cmd = ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", str(file_path)]

        try:
            self.proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if IS_WINDOWS else 0
            )
            return True
        except Exception:
            # Fallback to clock-only simulation
            return True

    def get_position_sec(self) -> float:
        if not self.is_loaded:
            return 0.0
        if self.is_paused:
            return self.accumulated_time_sec
        return self.accumulated_time_sec + (time.time() - self.start_time_sec)

    def toggle_pause(self):
        if not self.is_loaded or not self.file_path:
            return

        if self.is_paused:
            # Resume playback
            curr_pos = self.accumulated_time_sec
            if IS_WINDOWS:
                # Restart ffplay from current timestamp
                self._restart_at(curr_pos)
            else:
                if self.proc and self.proc.poll() is None:
                    try:
                        os.kill(self.proc.pid, signal.SIGCONT)
                    except Exception:
                        self._restart_at(curr_pos)
                else:
                    self._restart_at(curr_pos)
            self.start_time_sec = time.time()
            self.is_paused = False
        else:
            # Pause playback
            self.accumulated_time_sec += (time.time() - self.start_time_sec)
            self.is_paused = True
            if IS_WINDOWS:
                self._terminate_proc()
            else:
                if self.proc and self.proc.poll() is None:
                    try:
                        os.kill(self.proc.pid, signal.SIGSTOP)
                    except Exception:
                        self._terminate_proc()

    def seek_relative(self, delta_sec: float):
        if not self.is_loaded or not self.file_path:
            return
        curr = self.get_position_sec()
        new_pos = max(0.0, curr + delta_sec)
        self.accumulated_time_sec = new_pos
        self.start_time_sec = time.time()
        
        if not self.is_paused:
            self._restart_at(new_pos)

    def change_volume(self, delta: float):
        self.volume = max(0.0, min(1.0, self.volume + delta))
        if self.is_muted and delta > 0:
            self.is_muted = False

    def toggle_mute(self):
        if self.is_muted:
            self.is_muted = False
            self.volume = self.previous_volume or 0.8
        else:
            self.previous_volume = self.volume
            self.is_muted = True
            self.volume = 0.0

    def _restart_at(self, pos_sec: float):
        self._terminate_proc()
        if self.file_path:
            vol_val = 0 if self.is_muted else int(self.volume * 100)
            if self.player_cmd == "ffplay":
                cmd = ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", "-volume", str(vol_val), "-ss", f"{pos_sec:.2f}", str(self.file_path)]
            elif self.player_cmd == "mpv":
                cmd = ["mpv", "--no-video", f"--volume={vol_val}", f"--start={pos_sec:.2f}", str(self.file_path)]
            else:
                cmd = ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", "-ss", f"{pos_sec:.2f}", str(self.file_path)]

            try:
                self.proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if IS_WINDOWS else 0
                )
            except Exception:
                pass

    def _terminate_proc(self):
        if self.proc:
            try:
                if self.proc.poll() is None:
                    self.proc.terminate()
                    self.proc.wait(timeout=0.2)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
            self.proc = None

    def is_busy(self) -> bool:
        if not self.is_loaded:
            return False
        if self.proc and self.proc.poll() is not None and not self.is_paused:
            return False
        return True

    def stop(self):
        self._terminate_proc()
        self.is_loaded = False
        self.is_paused = False
