"""
TimingChain - High-Precision Audio Waveform & Lyric Timing Engine
Direct audio clock synchronization aligning playback position with acoustic timestamps.
"""

from typing import List, Optional, Tuple
import numpy as np

from groovegrab.player.lrc_parser import LrcLine


class TimingChain:
    """Core TimingChain synchronization engine aligning audio playback to lyric timestamps."""

    def __init__(self):
        self.leading_silence_sec: float = 0.0
        self.audio_duration_sec: float = 0.0

    def inspect_audio(self, pcm_data: Optional[np.ndarray], sample_rate: int = 22050) -> float:
        """
        Inspects PCM audio samples to measure audio duration.
        """
        if pcm_data is None or len(pcm_data) == 0:
            self.leading_silence_sec = 0.0
            self.audio_duration_sec = 0.0
            return 0.0

        self.audio_duration_sec = float(len(pcm_data)) / float(sample_rate)
        return self.audio_duration_sec

    def find_active_line(
        self,
        lyrics: List[LrcLine],
        current_audio_time: float
    ) -> Tuple[Optional[int], Optional[LrcLine]]:
        """
        Finds the current active lyric line based on direct audio playback time.
        Returns (index, line) or (None, None) if before the first lyric line.
        """
        if not lyrics:
            return None, None

        # If before first lyric timestamp
        if current_audio_time < lyrics[0].timestamp_sec:
            return None, None

        active_idx = 0
        for idx, line in enumerate(lyrics):
            if current_audio_time >= line.timestamp_sec:
                active_idx = idx

        return active_idx, lyrics[active_idx]
