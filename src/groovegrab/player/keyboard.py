"""
Cross-Platform Non-Blocking Keyboard Input Reader
Supports Windows (msvcrt) and Unix (termios/tty/select)
Safe handling for mouse scroll escape sequences without accidental TUI exit
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
                return None

            if ch == '\r' or ch == '\n':
                return "ENTER"
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

            # Non-blocking escape sequence payload reader
            seq = ""
            while True:
                rlist2, _, _ = select.select([sys.stdin], [], [], 0.02)
                if not rlist2:
                    break
                seq += sys.stdin.read(1)
                if len(seq) >= 16:
                    break

            if not seq:
                # Standalone ESC key press (Safely drop so it doesn't trigger quit)
                return None

            # Standard Arrow Keys
            if seq == "[A":
                return "UP"
            elif seq == "[B":
                return "DOWN"
            elif seq == "[C":
                return "RIGHT"
            elif seq == "[D":
                return "LEFT"

            # Mouse wheel scroll sequences (SGR mode & normal tracking)
            # Mouse scroll up: <64;, Ma, [5~, [A
            if "<64;" in seq or "Ma" in seq or "[5~" in seq or "<0;" in seq:
                return "UP"
            # Mouse scroll down: <65;, Mb, [6~, [B
            elif "<65;" in seq or "Mb" in seq or "[6~" in seq or "<1;" in seq:
                return "DOWN"

            # Safely ignore all unhandled mouse/terminal escape sequences without quitting
            return None
        except Exception:
            return None
