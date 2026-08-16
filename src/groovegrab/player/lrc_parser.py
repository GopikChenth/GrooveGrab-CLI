"""
Synced .lrc Timestamped Lyric Parser
Robust parsing supporting [mm:ss.xx], [mm:ss.xxx], [offset:+/-ms], and word-level timing models.
"""

import re
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field


class WordTiming(BaseModel):
    word: str
    start_sec: float
    end_sec: float


class LrcLine(BaseModel):
    timestamp_sec: float
    end_sec: Optional[float] = None
    text: str
    words: List[WordTiming] = Field(default_factory=list)


class LrcParser:
    """Parses .lrc synced lyric files into cleanly sorted, timestamped sequence models."""

    TIMESTAMP_REGEX = re.compile(r'\[(\d{1,2}):(\d{2})(?:\.(\d{2,3}))?\]')
    OFFSET_REGEX = re.compile(r'\[offset:\s*([+-]?\d+)\s*\]', re.IGNORECASE)
    METADATA_TAG_REGEX = re.compile(r'\[[a-zA-Z]{1,8}:.*?\]')

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
        global_offset_sec = 0.0

        # Check for [offset:+/-ms] tag
        for line in raw_lines:
            match = self.OFFSET_REGEX.search(line)
            if match:
                try:
                    global_offset_sec = float(match.group(1)) / 1000.0
                except ValueError:
                    pass

        for line in raw_lines:
            line_str = line.strip()
            if not line_str:
                continue

            matches = list(self.TIMESTAMP_REGEX.finditer(line_str))
            if not matches:
                continue

            # Strip timestamps and any metadata tags from lyric text
            clean_text = self.TIMESTAMP_REGEX.sub('', line_str)
            clean_text = self.METADATA_TAG_REGEX.sub('', clean_text).strip()
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

                total_seconds = max(0.0, minutes * 60.0 + seconds + frac + global_offset_sec)
                parsed.append(LrcLine(timestamp_sec=total_seconds, text=clean_text))

        # Sort strictly by timestamp
        parsed.sort(key=lambda x: x.timestamp_sec)

        # Remove duplicate consecutive lines at exact same timestamp
        unique_parsed: List[LrcLine] = []
        for line in parsed:
            if not unique_parsed or abs(line.timestamp_sec - unique_parsed[-1].timestamp_sec) > 0.05 or line.text != unique_parsed[-1].text:
                unique_parsed.append(line)

        # Compute end_sec for each line
        for i in range(len(unique_parsed)):
            if i + 1 < len(unique_parsed):
                unique_parsed[i].end_sec = unique_parsed[i + 1].timestamp_sec
            else:
                unique_parsed[i].end_sec = unique_parsed[i].timestamp_sec + 5.0

        return unique_parsed
