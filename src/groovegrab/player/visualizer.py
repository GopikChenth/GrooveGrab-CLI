"""
Audio Spectrum Equalizer Visualizer Component
"""

import math
import random
import numpy as np


class AudioSpectrumVisualizer:
    """Generates ASCII / Unicode frequency spectrum equalizer bars."""

    BAR_BLOCKS = [" ", " ", "▂", "▃", "▄", "▅", "▆", "▇", "█"]

    def __init__(self, num_bars: int = 32):
        self.num_bars = num_bars
        self.heights = np.zeros(num_bars)

    def render_bars(
        self,
        current_time_sec: float,
        is_playing: bool = True,
        color_style: str = "bold magenta"
    ) -> str:
        if not is_playing:
            flat_bars = [self.BAR_BLOCKS[1]] * self.num_bars
            return f"[{color_style}]{''.join(flat_bars)}[/{color_style}]"

        # Generate realistic frequency waveform dynamics using harmonic sines + noise
        t = current_time_sec
        bars_output = []

        for i in range(self.num_bars):
            # Frequency weight (bass heavier at left, treble lighter at right)
            freq_factor = 1.0 - (i / self.num_bars) * 0.4
            
            # Harmonic wave superposition
            wave = (
                math.sin(t * 12.0 + i * 0.4) * 0.4 +
                math.cos(t * 7.5 - i * 0.2) * 0.3 +
                math.sin(t * 22.0 + i * 0.8) * 0.3
            )
            
            # Amplitude envelope
            normalized = max(0.05, min(0.99, (wave + 1.0) / 2.0 * freq_factor))
            
            # Smooth interpolation with peak decay
            self.heights[i] = self.heights[i] * 0.65 + normalized * 0.35
            
            block_idx = int(self.heights[i] * (len(self.BAR_BLOCKS) - 1))
            block_idx = max(0, min(len(self.BAR_BLOCKS) - 1, block_idx))
            bars_output.append(self.BAR_BLOCKS[block_idx])

        return f"[{color_style}]{''.join(bars_output)}[/{color_style}]"
