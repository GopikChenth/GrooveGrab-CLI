"""
Universal Audio Playback Driver & Clock Controller
"""

import os
import time
import shutil
import signal
import subprocess
from pathlib import Path
from typing import Optional


class AudioDriver:
    """Universal audio driver with system fallback (ffplay/mpv/paplay/aplay/afplay) and precise clock tracking."""

    def __init__(self):
        self.proc: Optional[subprocess.Popen] = None
        self.is_loaded = False
        self.is_paused = False
        self.start_time_sec = 0.0
        self.pause_time_sec = 0.0
        self.accumulated_time_sec = 0.0
        self.volume = 0.8
        
        # Check system audio player player preference
        self.player_cmd = self._detect_system_player()

    def _detect_system_player(self) -> Optional[str]:
        for cmd in ["ffplay", "mpv", "paplay", "aplay", "afplay"]:
            if shutil.which(cmd):
                return cmd
        return None

    def load_and_play(self, file_path: Path) -> bool:
        if not file_path.exists():
            return False

        self.stop()
        self.is_loaded = True
        self.is_paused = False
        self.accumulated_time_sec = 0.0
        self.start_time_sec = time.time()

        if self.player_cmd == "ffplay":
            cmd = ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", "-volume", str(int(self.volume * 100)), str(file_path)]
        elif self.player_cmd == "mpv":
            cmd = ["mpv", "--no-video", f"--volume={int(self.volume * 100)}", str(file_path)]
        elif self.player_cmd in ["paplay", "aplay", "afplay"]:
            cmd = [self.player_cmd, str(file_path)]
        else:
            cmd = ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", str(file_path)]

        try:
            self.proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            # Clock-only playback mode if binary is unavailable
            return True

    def get_position_sec(self) -> float:
        if not self.is_loaded:
            return 0.0
        if self.is_paused:
            return self.accumulated_time_sec
        return self.accumulated_time_sec + (time.time() - self.start_time_sec)

    def toggle_pause(self):
        if not self.is_loaded:
            return
        if self.is_paused:
            # Resume
            if self.proc and self.proc.poll() is None:
                try:
                    os.kill(self.proc.pid, signal.SIGCONT)
                except Exception:
                    pass
            self.start_time_sec = time.time()
            self.is_paused = False
        else:
            # Pause
            self.accumulated_time_sec += (time.time() - self.start_time_sec)
            if self.proc and self.proc.poll() is None:
                try:
                    os.kill(self.proc.pid, signal.SIGSTOP)
                except Exception:
                    pass
            self.is_paused = True

    def seek_relative(self, delta_sec: float):
        if not self.is_loaded:
            return
        curr = self.get_position_sec()
        new_pos = max(0.0, curr + delta_sec)
        self.accumulated_time_sec = new_pos
        self.start_time_sec = time.time()

    def change_volume(self, delta: float):
        self.volume = max(0.0, min(1.0, self.volume + delta))

    def is_busy(self) -> bool:
        if not self.is_loaded:
            return False
        if self.proc and self.proc.poll() is not None and not self.is_paused:
            return False
        return True

    def stop(self):
        if self.proc:
            try:
                if self.proc.poll() is None:
                    self.proc.terminate()
                    self.proc.wait(timeout=0.5)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
            self.proc = None
        self.is_loaded = False
