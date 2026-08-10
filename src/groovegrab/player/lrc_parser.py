"""
Synced .lrc Timestamped Lyric Parser
"""

import re
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel


class LrcLine(BaseModel):
    timestamp_sec: float
    end_sec: Optional[float] = None
    text: str


class LrcParser:
    """Parses .lrc synced lyric files into timed sequence models."""

    TIMESTAMP_REGEX = re.compile(r'\[(\d{2}):(\d{2})(?:\.(\d{2,3}))?\]')

    def parse_file(self, file_path: Path) -> List[LrcLine]:
        if not file_path.exists():
            return []
        
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            return self.parse_text(content)
        except Exception:
            return []

    def parse_text(self, text: str) -> List[LrcLine]:
        raw_lines = text.splitlines()
        parsed: List[LrcLine] = []

        for line in raw_lines:
            line_str = line.strip()
            if not line_str:
                continue

            matches = list(self.TIMESTAMP_REGEX.finditer(line_str))
            if not matches:
                continue

            clean_text = self.TIMESTAMP_REGEX.sub('', line_str).strip()
            if not clean_text:
                continue

            for match in matches:
                minutes = int(match.group(1))
                seconds = int(match.group(2))
                frac_str = match.group(3) or "0"
                
                # Normalize fraction of a second (centiseconds or milliseconds)
                if len(frac_str) == 2:
                    frac = int(frac_str) / 100.0
                elif len(frac_str) == 3:
                    frac = int(frac_str) / 1000.0
                else:
                    frac = 0.0

                total_seconds = minutes * 60 + seconds + frac
                parsed.append(LrcLine(timestamp_sec=total_seconds, text=clean_text))

        # Sort by timestamp
        parsed.sort(key=lambda x: x.timestamp_sec)

        # Compute end_sec for each line
        for i in range(len(parsed)):
            if i + 1 < len(parsed):
                parsed[i].end_sec = parsed[i + 1].timestamp_sec
            else:
                parsed[i].end_sec = parsed[i].timestamp_sec + 5.0

        return parsed
