"""
Full-Featured CAVA-Style Audio Spectrum Visualizer Engine
Supports multi-row vertical equalizer bars, braille curves, oscilloscope waveform,
symmetric mirror, particles, gravity peak physics, and gradient rendering.
"""

import math
import random
from enum import Enum
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np

from groovegrab.player.themes import Theme, get_theme


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
    """Computes real or synthesized logarithmic frequency bands with physics."""

    def __init__(self, num_bars: int = 32):
        self.num_bars = num_bars
        self.heights = np.zeros(num_bars, dtype=np.float32)
        self.peak_heights = np.zeros(num_bars, dtype=np.float32)
        self.peak_hold_timers = np.zeros(num_bars, dtype=np.float32)
        self.velocities = np.zeros(num_bars, dtype=np.float32)
        
        # Audio buffer for real PCM data if available
        self.pcm_data: Optional[np.ndarray] = None
        self.sample_rate: int = 44100
        self.audio_loaded: bool = False

    def load_audio_file(self, file_path: Path):
        """Optionally load audio samples for real FFT calculation."""
        try:
            import soundfile as sf
            data, sr = sf.read(str(file_path), dtype='float32')
            if len(data.shape) > 1:
                # Convert stereo to mono
                data = data.mean(axis=1)
            self.pcm_data = data
            self.sample_rate = sr
            self.audio_loaded = True
        except Exception:
            self.audio_loaded = False
            self.pcm_data = None

    def update(self, current_time_sec: float, num_bars: int, is_playing: bool = True, dt: float = 0.033) -> np.ndarray:
        """Compute frequency bar heights normalized between 0.0 and 1.0."""
        if num_bars != self.num_bars:
            self.num_bars = num_bars
            self.heights = np.zeros(num_bars, dtype=np.float32)
            self.peak_heights = np.zeros(num_bars, dtype=np.float32)
            self.peak_hold_timers = np.zeros(num_bars, dtype=np.float32)
            self.velocities = np.zeros(num_bars, dtype=np.float32)

        if not is_playing:
            # Decay to zero smoothly
            self.heights *= 0.85
            self.peak_heights *= 0.90
            return np.clip(self.heights, 0.0, 1.0)

        # Real FFT if audio loaded, otherwise procedural physics
        if self.audio_loaded and self.pcm_data is not None:
            raw_spectrum = self._compute_real_fft(current_time_sec, num_bars)
        else:
            raw_spectrum = self._compute_procedural_spectrum(current_time_sec, num_bars)

        # Apply CAVA physics: Rising speed, falloff gravity, peak hold
        for i in range(num_bars):
            target = raw_spectrum[i]
            if target > self.heights[i]:
                # Quick rise
                self.heights[i] = self.heights[i] * 0.3 + target * 0.7
            else:
                # Gravitational fall
                self.heights[i] = max(0.0, self.heights[i] - 0.065)

            # Peak tracking
            if self.heights[i] >= self.peak_heights[i]:
                self.peak_heights[i] = self.heights[i]
                self.peak_hold_timers[i] = 0.18 # Hold for ~180ms
            else:
                if self.peak_hold_timers[i] > 0:
                    self.peak_hold_timers[i] -= dt
                else:
                    self.peak_heights[i] = max(0.0, self.peak_heights[i] - 0.04)

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

        # Hanning window
        windowed = chunk * np.hanning(len(chunk))
        fft_vals = np.abs(np.fft.rfft(windowed))

        # Logarithmic frequency binning
        bands = np.zeros(num_bars, dtype=np.float32)
        fft_len = len(fft_vals)
        
        # Frequency range: ~40Hz to ~16000Hz
        min_freq = 40.0
        max_freq = min(16000.0, self.sample_rate / 2.0)
        log_min = math.log10(min_freq)
        log_max = math.log10(max_freq)

        for i in range(num_bars):
            f_start = 10 ** (log_min + (log_max - log_min) * (i / num_bars))
            f_end = 10 ** (log_min + (log_max - log_min) * ((i + 1) / num_bars))
            
            bin_start = max(0, min(fft_len - 1, int(f_start * window_size / self.sample_rate)))
            bin_end = max(bin_start + 1, min(fft_len, int(f_end * window_size / self.sample_rate)))
            
            val = float(np.mean(fft_vals[bin_start:bin_end])) if bin_end > bin_start else 0.0
            
            # Equal loudness boost for high frequencies
            boost = 1.0 + (i / max(1, num_bars)) * 1.6
            norm_val = math.log1p(val * 4.0) * 0.25 * boost
            bands[i] = min(1.0, max(0.05, norm_val))

        return bands

    def _compute_procedural_spectrum(self, t: float, num_bars: int) -> np.ndarray:
        """High-fidelity multi-frequency rhythmic simulation with dynamic beats."""
        spectrum = np.zeros(num_bars, dtype=np.float32)
        
        # 128 BPM beat clock
        beat_phase = (t * (128.0 / 60.0)) % 1.0
        kick_pulse = math.exp(-beat_phase * 6.0) # Bass kick punch
        snare_pulse = math.exp(-((beat_phase + 0.5) % 1.0) * 8.0) # Snare hit

        for i in range(num_bars):
            ratio = i / max(1, num_bars - 1)
            
            # Frequency weights
            bass_weight = math.exp(-ratio * 3.5)
            mid_weight = math.sin(ratio * math.pi) ** 1.5
            treble_weight = ratio ** 1.3
            
            # Multi-layer harmonic sine rhythms
            wave1 = math.sin(t * 8.0 + i * 0.45) * 0.35
            wave2 = math.cos(t * 14.5 - i * 0.25) * 0.25
            wave3 = math.sin(t * 26.0 + i * 0.8) * 0.20
            
            # Shimmer noise for hi-hats / treble
            shimmer = (random.random() * 0.20) if ratio > 0.6 else (random.random() * 0.08)

            energy = (
                bass_weight * (0.35 + kick_pulse * 0.60) +
                mid_weight * (0.25 + wave1 + wave2 + snare_pulse * 0.35) +
                treble_weight * (0.20 + wave3 + shimmer)
            )

            spectrum[i] = max(0.04, min(0.98, energy))

        return spectrum


class AudioSpectrumVisualizer:
    """Full-Terminal Multi-Row CAVA Audio Spectrum Visualizer."""

    BAR_SUBBLOCKS = [" ", " ", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
    PEAK_CHARS = ["▔", "━", "•", "▀"]
    
    # 2x4 Braille pattern matrix
    BRAILLE_MAP = [
        [" ", "⠂", "⠒", "⠲", "⠶", "⠶", "⣶", "⣿"],
        [" ", "⠁", "⠉", "⠋", "⠛", "⠟", "⠿", "⣿"],
    ]

    def __init__(self, num_bars: int = 40):
        self.num_bars = num_bars
        self.engine = SpectrumDataEngine(num_bars)
        self.particles: List[Tuple[float, float, float, str]] = []  # (x, y, speed, char)
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
        """Render the full multi-row visualizer string formatted for Rich."""
        theme = get_theme(theme_name)
        height = max(4, height)
        width = max(20, width)
        self.mirror_mode = mirror

        # Calculate number of bars based on terminal width and bar spacing
        bar_width = 2 if width >= 50 else 1
        num_bars = max(8, min(width // (bar_width + 1), 64))

        heights = self.engine.update(current_time_sec, num_bars, is_playing=is_playing)
        peaks = self.engine.peak_heights

        if mode == VisualizerMode.BARS:
            return self._render_bars_grid(heights, peaks, width, height, theme, bar_width)
        elif mode == VisualizerMode.BRAILLE:
            return self._render_braille_grid(heights, width, height, theme)
        elif mode == VisualizerMode.WAVE:
            return self._render_waveform_grid(current_time_sec, width, height, theme, is_playing)
        elif mode == VisualizerMode.MIRROR:
            return self._render_mirror_grid(heights, peaks, width, height, theme, bar_width)
        elif mode == VisualizerMode.PARTICLES:
            return self._render_particles_grid(heights, width, height, theme, is_playing)
        else:
            return self._render_bars_grid(heights, peaks, width, height, theme, bar_width)

    def _render_bars_grid(
        self,
        heights: np.ndarray,
        peaks: np.ndarray,
        width: int,
        height: int,
        theme: Theme,
        bar_width: int
    ) -> str:
        """Classic CAVA Multi-Row Vertical Equalizer Bars with Falling Peak Caps."""
        num_bars = len(heights)
        grid_lines = []

        # Render each row from top (height - 1) to bottom (0)
        for row in range(height - 1, -1, -1):
            row_color = theme.get_row_color(row, height)
            row_chars = []

            for i in range(num_bars):
                val = heights[i] * height
                peak_val = peaks[i] * height

                bar_char = " "
                # Full block or partial block
                if val >= row + 1:
                    bar_char = "█"
                elif val > row:
                    fraction = val - row
                    sub_idx = int(fraction * 8)
                    sub_idx = max(0, min(8, sub_idx))
                    bar_char = self.BAR_SUBBLOCKS[sub_idx]
                elif int(peak_val) == row:
                    # Floating peak cap
                    bar_char = "▔"

                is_peak = (bar_char == "▔")
                char_style = theme.peak_color if is_peak else row_color

                # Repeat bar width
                cell = bar_char * bar_width
                row_chars.append(f"[{char_style}]{cell}[/{char_style}]")

            # Join bars with gap space
            line_str = " ".join(row_chars)
            # Center line in terminal width
            grid_lines.append(f"  {line_str}")

        # Add frequency indicator footer
        freq_footer = self._build_frequency_labels(num_bars, bar_width, theme)
        grid_lines.append(freq_footer)

        return "\n".join(grid_lines)

    def _render_mirror_grid(
        self,
        heights: np.ndarray,
        peaks: np.ndarray,
        width: int,
        height: int,
        theme: Theme,
        bar_width: int
    ) -> str:
        """Symmetric Mirror Visualizer (Center-Outward Equalizer)."""
        # Create symmetric mirrored heights: [reversed(right), left]
        half_n = len(heights) // 2
        left_side = heights[:half_n]
        mirrored_heights = np.concatenate([left_side[::-1], left_side])
        
        left_peaks = peaks[:half_n]
        mirrored_peaks = np.concatenate([left_peaks[::-1], left_peaks])

        return self._render_bars_grid(mirrored_heights, mirrored_peaks, width, height, theme, bar_width)

    def _render_braille_grid(
        self,
        heights: np.ndarray,
        width: int,
        height: int,
        theme: Theme
    ) -> str:
        """Ultra-High-Resolution 2x4 Braille Dot Matrix Spectrum."""
        total_cols = min(width - 4, len(heights) * 2)
        grid_lines = []

        # Interpolate heights for smooth curve
        x_orig = np.linspace(0, 1, len(heights))
        x_dense = np.linspace(0, 1, total_cols)
        dense_heights = np.interp(x_dense, x_orig, heights)

        # Braille dots mapping (4 vertical dots per row cell)
        for row in range(height - 1, -1, -1):
            row_color = theme.get_row_color(row, height)
            row_chars = []

            for col in range(0, total_cols, 2):
                h1 = dense_heights[col] * height * 4
                h2 = dense_heights[col + 1] * height * 4 if col + 1 < total_cols else h1

                # Calculate dot bits for this 2x4 Braille cell at this row
                # Dot numbering:
                # [col 0]: 1, 2, 3, 7
                # [col 1]: 4, 5, 6, 8
                dots = 0
                row_base = row * 4

                for d in range(4):
                    dot_y = row_base + d
                    if h1 > dot_y:
                        # left dots (1, 2, 3, 7) -> bits 0, 1, 2, 6
                        bit = 6 if d == 3 else d
                        dots |= (1 << bit)
                    if h2 > dot_y:
                        # right dots (4, 5, 6, 8) -> bits 3, 4, 5, 7
                        bit = 7 if d == 3 else (d + 3)
                        dots |= (1 << bit)

                braille_char = chr(0x2800 + dots) if dots > 0 else " "
                row_chars.append(f"[{row_color}]{braille_char}[/{row_color}]")

            grid_lines.append(f"  {''.join(row_chars)}")

        freq_footer = self._build_frequency_labels(total_cols // 2, 1, theme)
        grid_lines.append(freq_footer)
        return "\n".join(grid_lines)

    def _render_waveform_grid(
        self,
        t: float,
        width: int,
        height: int,
        theme: Theme,
        is_playing: bool
    ) -> str:
        """Oscilloscope Waveform Visualizer."""
        total_cols = max(20, width - 6)
        mid_row = height // 2
        grid = [[" " for _ in range(total_cols)] for _ in range(height)]

        for x in range(total_cols):
            x_ratio = x / total_cols
            if is_playing:
                # Waveform superposition
                wave = (
                    math.sin(t * 14.0 + x_ratio * 12.0) * 0.45 +
                    math.sin(t * 28.0 - x_ratio * 20.0) * 0.25 +
                    math.cos(t * 7.0 + x_ratio * 6.0) * 0.20
                )
            else:
                wave = 0.0

            y_pos = int(mid_row + wave * (mid_row - 1))
            y_pos = max(0, min(height - 1, y_pos))
            grid[y_pos][x] = "━" if y_pos == mid_row else "●"

        grid_lines = []
        for r in range(height - 1, -1, -1):
            row_color = theme.get_row_color(r, height)
            line_content = "".join(grid[r])
            grid_lines.append(f"  [{row_color}]{line_content}[/{row_color}]")

        return "\n".join(grid_lines)

    def _render_particles_grid(
        self,
        heights: np.ndarray,
        width: int,
        height: int,
        theme: Theme,
        is_playing: bool
    ) -> str:
        """Bouncing Sparks and Falling Audio Particles."""
        total_cols = min(width - 4, len(heights) * 2)
        grid = [[" " for _ in range(total_cols)] for _ in range(height)]
        
        particle_chars = ["✦", "★", "·", "•", "✶", "▲"]

        # Spawn particles based on high energy bars
        if is_playing and random.random() < 0.7:
            high_indices = np.where(heights > 0.4)[0]
            if len(high_indices) > 0:
                spawn_bar = random.choice(high_indices)
                px = min(total_cols - 1, int((spawn_bar / len(heights)) * total_cols))
                py = min(height - 1, int(heights[spawn_bar] * height))
                p_char = random.choice(particle_chars)
                self.particles.append((float(px), float(py), random.uniform(0.3, 0.9), p_char))

        # Update and decay particles
        new_particles = []
        for px, py, speed, pchar in self.particles:
            new_y = py - speed
            ix, iy = int(px), int(new_y)
            if 0 <= ix < total_cols and 0 <= iy < height:
                grid[iy][ix] = pchar
                new_particles.append((px, new_y, speed + 0.05, pchar))

        self.particles = new_particles[:40]

        # Draw base mini bars at bottom
        for c in range(total_cols):
            bar_idx = int((c / total_cols) * len(heights))
            val = heights[bar_idx] * 2.0
            if val > 0.5:
                sub_idx = min(8, max(1, int(val * 4)))
                grid[0][c] = self.BAR_SUBBLOCKS[sub_idx]

        grid_lines = []
        for r in range(height - 1, -1, -1):
            row_color = theme.get_row_color(r, height)
            line_str = "".join(grid[r])
            grid_lines.append(f"  [{row_color}]{line_str}[/{row_color}]")

        return "\n".join(grid_lines)

    def _build_frequency_labels(self, num_bars: int, bar_width: int, theme: Theme) -> str:
        """Bottom frequency axis tags like CAVA: 60Hz ── 250Hz ── 1kHz ── 4kHz ── 16kHz."""
        tag_str = f"[{theme.dim_lyric}]  [ 60Hz ──── 250Hz ──── 1kHz ──── 4kHz ──── 16kHz ][/{theme.dim_lyric}]"
        return tag_str
