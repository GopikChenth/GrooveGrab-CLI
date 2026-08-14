"""
Cross-Platform Non-Blocking Keyboard Input Reader
Supports Windows (msvcrt) and Unix (termios/tty/select)
"""

import sys
import os
from typing import Optional

IS_WINDOWS = os.name == "nt"

if IS_WINDOWS:
    import msvcrt
else:
    import select
    import termios
    import tty


class NonBlockingKeyboard:
    """Non-blocking single keypress reader context manager."""

    def __init__(self):
        self.old_settings = None
        self.fd = None

    def __enter__(self):
        if not IS_WINDOWS:
            try:
                self.fd = sys.stdin.fileno()
                self.old_settings = termios.tcgetattr(self.fd)
                tty.setcbreak(self.fd)
            except Exception:
                pass
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not IS_WINDOWS and self.old_settings and self.fd is not None:
            try:
                termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old_settings)
            except Exception:
                pass

    def read_key(self) -> Optional[str]:
        """Read a single key press without blocking. Returns normalized key name or None."""
        if IS_WINDOWS:
            return self._read_windows_key()
        else:
            return self._read_unix_key()

    def _read_windows_key(self) -> Optional[str]:
        try:
            if not msvcrt.kbhit():
                return None
            
            ch = msvcrt.getwch()
            # Special/extended keys prefix in Windows (0x00 or 0xe0)
            if ch in ('\x00', '\xe0'):
                if msvcrt.kbhit():
                    ch2 = msvcrt.getwch()
                    if ch2 == 'H':
                        return "UP"
                    elif ch2 == 'P':
                        return "DOWN"
                    elif ch2 == 'K':
                        return "LEFT"
                    elif ch2 == 'M':
                        return "RIGHT"
                    elif ch2 == 'S': # Delete
                        return "DEL"
                return None

            if ch == '\r' or ch == '\n':
                return "ENTER"
            elif ch == '\x1b':
                return "ESC"
            elif ch == ' ':
                return "SPACE"
            return ch
        except Exception:
            return None

    def _read_unix_key(self) -> Optional[str]:
        try:
            rlist, _, _ = select.select([sys.stdin], [], [], 0.002)
            if not rlist:
                return None

            ch = sys.stdin.read(1)
            if ch != '\x1b':
                if ch == ' ':
                    return "SPACE"
                elif ch in ('\r', '\n'):
                    return "ENTER"
                return ch

            # Non-blocking escape sequence check
            seq = ""
            while True:
                rlist2, _, _ = select.select([sys.stdin], [], [], 0.005)
                if not rlist2:
                    break
                seq += sys.stdin.read(1)
                if len(seq) >= 16:
                    break

            if not seq:
                return "ESC"

            # Parse arrow keys and scroll
            if seq == "[A":
                return "UP"
            elif seq == "[B":
                return "DOWN"
            elif seq == "[C":
                return "RIGHT"
            elif seq == "[D":
                return "LEFT"
            elif "<64;" in seq or "Ma" in seq or "[5~" in seq:
                return "UP"
            elif "<65;" in seq or "Mb" in seq or "[6~" in seq:
                return "DOWN"

            return None
        except Exception:
            return None
