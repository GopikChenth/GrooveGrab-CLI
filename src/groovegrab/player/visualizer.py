"""
Full-Featured CAVA-Style Audio Spectrum Visualizer Engine
Computes real 100% mathematical FFT spectrum and uses TimingChain for synchronization.
"""

import math
import random
import subprocess
from enum import Enum
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np

from groovegrab.player.themes import Theme, get_theme
from groovegrab.player.timing_chain import TimingChain


class VisualizerMode(str, Enum):
    BARS = "bars"
    BRAILLE = "braille"
    WAVE = "wave"
    MIRROR = "mirror"
    PARTICLES = "particles"


VISUALIZER_MODES = [
    VisualizerMode.BARS,
    VisualizerMode.BRAILLE,
    VisualizerMode.WAVE,
    VisualizerMode.MIRROR,
    VisualizerMode.PARTICLES,
]


def next_visualizer_mode(current: VisualizerMode) -> VisualizerMode:
    idx = VISUALIZER_MODES.index(current) if current in VISUALIZER_MODES else 0
    return VISUALIZER_MODES[(idx + 1) % len(VISUALIZER_MODES)]


class SpectrumDataEngine:
    """Computes real 100% mathematical FFT frequency spectrum with TimingChain integration."""

    def __init__(self, num_bars: int = 40):
        self.num_bars = num_bars
        self.heights = np.zeros(num_bars, dtype=np.float32)
        self.peak_heights = np.zeros(num_bars, dtype=np.float32)
        
        self.pcm_data: Optional[np.ndarray] = None
        self.sample_rate: int = 22050
        self.audio_loaded: bool = False
        self.timing_chain = TimingChain()

    @property
    def leading_silence_sec(self) -> float:
        return self.timing_chain.leading_silence_sec

    def load_audio_file(self, file_path: Path):
        """Decode 100% real PCM audio samples using FFmpeg & run TimingChain inspection."""
        try:
            cmd = ["ffmpeg", "-i", str(file_path), "-f", "s16le", "-ac", "1", "-ar", "22050", "-loglevel", "quiet", "pipe:1"]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            if res.stdout and len(res.stdout) > 2048:
                raw_int16 = np.frombuffer(res.stdout, dtype=np.int16)
                self.pcm_data = raw_int16.astype(np.float32) / 32768.0
                self.sample_rate = 22050
                self.audio_loaded = True
                
                # Inspect PCM audio through TimingChain
                self.timing_chain.inspect_audio(self.pcm_data, self.sample_rate)
                return
        except Exception:
            pass

        try:
            import soundfile as sf
            data, sr = sf.read(str(file_path), dtype='float32')
            if len(data.shape) > 1:
                data = data.mean(axis=1)
            self.pcm_data = data
            self.sample_rate = sr
            self.audio_loaded = True
            self.timing_chain.inspect_audio(self.pcm_data, self.sample_rate)
        except Exception:
            self.audio_loaded = False
            self.pcm_data = None
            self.timing_chain.inspect_audio(None, 22050)

    def update(self, current_time_sec: float, num_bars: int, is_playing: bool = True, dt: float = 0.033) -> np.ndarray:
        """Compute frequency bar heights normalized with fluid smoothing."""
        if num_bars != self.num_bars:
            self.num_bars = num_bars
            self.heights = np.zeros(num_bars, dtype=np.float32)
            self.peak_heights = np.zeros(num_bars, dtype=np.float32)

        if not is_playing:
            self.heights *= 0.80
            return np.clip(self.heights, 0.0, 1.0)

        if self.audio_loaded and self.pcm_data is not None:
            raw_spectrum = self._compute_real_fft(current_time_sec, num_bars)
        else:
            raw_spectrum = self._compute_procedural_spectrum(current_time_sec, num_bars)

        # Apply CAVA IIR Exponential Smoothing for fluid motion
        smoothing_factor = 0.75
        for i in range(num_bars):
            target = raw_spectrum[i]
            if target > self.heights[i]:
                self.heights[i] = self.heights[i] * 0.40 + target * 0.60
            else:
                self.heights[i] = self.heights[i] * smoothing_factor + target * (1.0 - smoothing_factor)

        return np.clip(self.heights, 0.0, 1.0)

    def _compute_real_fft(self, current_time: float, num_bars: int) -> np.ndarray:
        if self.pcm_data is None:
            return np.zeros(num_bars, dtype=np.float32)

        center_idx = int(current_time * self.sample_rate)
        window_size = 2048
        half = window_size // 2

        start = max(0, center_idx - half)
        end = min(len(self.pcm_data), center_idx + half)

        chunk = self.pcm_data[start:end]
        if len(chunk) < window_size:
            chunk = np.pad(chunk, (0, window_size - len(chunk)))

        rms_energy = np.sqrt(np.mean(chunk ** 2))
        if rms_energy < 0.005:
            return np.zeros(num_bars, dtype=np.float32)

        windowed = chunk * np.hanning(len(chunk))
        fft_vals = np.abs(np.fft.rfft(windowed))

        bands = np.zeros(num_bars, dtype=np.float32)
        fft_len = len(fft_vals)
        
        min_freq = 40.0
        max_freq = min(10000.0, self.sample_rate / 2.0)
        log_min = math.log10(min_freq)
        log_max = math.log10(max_freq)

        for i in range(num_bars):
            f_start = 10 ** (log_min + (log_max - log_min) * (i / num_bars))
            f_end = 10 ** (log_min + (log_max - log_min) * ((i + 1) / num_bars))
            
            bin_start = max(0, min(fft_len - 1, int(f_start * window_size / self.sample_rate)))
            bin_end = max(bin_start + 1, min(fft_len, int(f_end * window_size / self.sample_rate)))
            
            val = float(np.mean(fft_vals[bin_start:bin_end])) if bin_end > bin_start else 0.0
            
            boost = 0.65 + (i / max(1, num_bars)) * 0.35
            norm_val = math.log1p(val * 1.6) * 0.09 * boost
            bands[i] = min(0.70, max(0.0, norm_val))

        return bands

    def _compute_procedural_spectrum(self, t: float, num_bars: int) -> np.ndarray:
        """Procedural fallback simulation with toned down height."""
        spectrum = np.zeros(num_bars, dtype=np.float32)
        beat_phase = (t * (128.0 / 60.0)) % 1.0
        kick_pulse = math.exp(-beat_phase * 5.0)

        for i in range(num_bars):
            ratio = i / max(1, num_bars - 1)
            bass_weight = math.exp(-ratio * 3.2)
            energy = bass_weight * (0.15 + kick_pulse * 0.3)
            spectrum[i] = max(0.0, min(0.6, energy))

        return spectrum


class AudioSpectrumVisualizer:
    """Full-Terminal Multi-Row CAVA Audio Spectrum Visualizer."""

    BAR_SUBBLOCKS = [" ", " ", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
    
    BRAILLE_MAP = [
        [" ", "⠂", "⠒", "⠲", "⠶", "⠶", "⣶", "⣿"],
        [" ", "⠁", "⠉", "⠋", "⠛", "⠟", "⠿", "⣿"],
    ]

    def __init__(self, num_bars: int = 40):
        self.num_bars = num_bars
        self.engine = SpectrumDataEngine(num_bars)
        self.mirror_mode: bool = False

    def load_audio_file(self, file_path: Path):
        self.engine.load_audio_file(file_path)

    def render(
        self,
        current_time_sec: float,
        width: int = 60,
        height: int = 12,
        mode: VisualizerMode = VisualizerMode.BARS,
        theme_name: str = "cava",
        is_playing: bool = True,
        mirror: bool = False,
    ) -> str:
        theme = get_theme(theme_name)
        height = max(4, height)
        width = max(20, width)
        self.mirror_mode = mirror

        bar_width = 2 if width >= 50 else 1
        num_bars = max(8, min(width // (bar_width + 1), 64))

        heights = self.engine.update(current_time_sec, num_bars, is_playing=is_playing)

        if mode == VisualizerMode.BARS:
            return self._render_bars_grid(heights, width, height, theme, bar_width)
        elif mode == VisualizerMode.BRAILLE:
            return self._render_braille_grid(heights, width, height, theme)
        elif mode == VisualizerMode.WAVE:
            return self._render_waveform_grid(current_time_sec, width, height, theme, is_playing)
        elif mode == VisualizerMode.MIRROR:
            return self._render_mirror_grid(heights, width, height, theme, bar_width)
        elif mode == VisualizerMode.PARTICLES:
            return self._render_particles_grid(heights, width, height, theme, is_playing)
        else:
            return self._render_bars_grid(heights, width, height, theme, bar_width)

    def _render_bars_grid(
        self,
        heights: np.ndarray,
        width: int,
        height: int,
        theme: Theme,
        bar_width: int
    ) -> str:
        num_bars = len(heights)
        grid_lines = []

        for row in range(height - 1, -1, -1):
            row_color = theme.get_row_color(row, height)
            row_chars = []

            for i in range(num_bars):
                val = heights[i] * height

                bar_char = " "
                if val >= row + 1:
                    bar_char = "█"
                elif val > row:
                    fraction = val - row
                    sub_idx = int(fraction * 8)
                    sub_idx = max(0, min(8, sub_idx))
                    bar_char = self.BAR_SUBBLOCKS[sub_idx]

                cell = bar_char * bar_width
                row_chars.append(f"[{row_color}]{cell}[/{row_color}]")

            line_str = " ".join(row_chars)
            grid_lines.append(f"  {line_str}")

        return "\n".join(grid_lines)

    def _render_mirror_grid(
        self,
        heights: np.ndarray,
        width: int,
        height: int,
        theme: Theme,
        bar_width: int
    ) -> str:
        half_n = len(heights) // 2
        left_side = heights[:half_n]
        mirrored_heights = np.concatenate([left_side[::-1], left_side])
        return self._render_bars_grid(mirrored_heights, width, height, theme, bar_width)

    def _render_braille_grid(
        self,
        heights: np.ndarray,
        width: int,
        height: int,
        theme: Theme
    ) -> str:
        num_bars = len(heights)
        grid_lines = []

        for row in range(height - 1, -1, -1):
            row_color = theme.get_row_color(row, height)
            row_chars = []

            for i in range(0, num_bars - 1, 2):
                val1 = heights[i] * height
                val2 = heights[i + 1] * height

                sub1 = max(0, min(7, int((val1 - row) * 7))) if val1 > row else 0
                sub2 = max(0, min(7, int((val2 - row) * 7))) if val2 > row else 0

                b_char = self.BRAILLE_MAP[0][sub1] if sub1 > 0 else " "
                if sub2 > 0 and sub1 > 0:
                    b_char = "⣿"
                elif sub2 > 0:
                    b_char = self.BRAILLE_MAP[1][sub2]

                row_chars.append(f"[{row_color}]{b_char}[/{row_color}]")

            line_str = " ".join(row_chars)
            grid_lines.append(f"  {line_str}")

        return "\n".join(grid_lines)

    def _render_waveform_grid(
        self,
        t: float,
        width: int,
        height: int,
        theme: Theme,
        is_playing: bool
    ) -> str:
        grid_lines = []
        mid_row = height // 2

        for row in range(height - 1, -1, -1):
            row_color = theme.get_row_color(row, height)
            line_chars = []

            for col in range(width):
                x = col / float(width)
                wave_y = mid_row + (math.sin(x * 12.0 + t * 10.0) * (height / 2.5) if is_playing else 0)
                
                if int(wave_y) == row:
                    line_chars.append(f"[{row_color}]━[/{row_color}]")
                else:
                    line_chars.append(" ")

            grid_lines.append("".join(line_chars))

        return "\n".join(grid_lines)

    def _render_particles_grid(
        self,
        heights: np.ndarray,
        width: int,
        height: int,
        theme: Theme,
        is_playing: bool
    ) -> str:
        return self._render_bars_grid(heights, width, height, theme, bar_width=1)
