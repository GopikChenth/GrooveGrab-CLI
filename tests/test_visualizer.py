"""
Unit Tests for CAVA Audio Spectrum Visualizer & Themes
"""

import numpy as np
from groovegrab.player.visualizer import AudioSpectrumVisualizer, VisualizerMode, SpectrumDataEngine, next_visualizer_mode
from groovegrab.player.themes import get_theme, next_theme_name, Theme


def test_theme_gradient():
    theme = get_theme("cava")
    assert theme.name == "cava"
    
    # Test gradient row mapping
    bottom_color = theme.get_row_color(0, 10)
    top_color = theme.get_row_color(9, 10)
    assert bottom_color == theme.bar_colors[0]
    assert top_color == theme.bar_colors[-1]

    # Test cyclic next theme
    nxt = next_theme_name("cava")
    assert nxt == "cyberpunk"


def test_visualizer_modes_cycle():
    mode = VisualizerMode.BARS
    next_mode = next_visualizer_mode(mode)
    assert next_mode == VisualizerMode.BRAILLE

    next_mode2 = next_visualizer_mode(next_mode)
    assert next_mode2 == VisualizerMode.WAVE


def test_spectrum_physics_decay():
    engine = SpectrumDataEngine(num_bars=16)
    
    # Active playback updates heights
    heights = engine.update(10.0, num_bars=16, is_playing=True)
    assert len(heights) == 16
    assert np.all(heights >= 0.0)
    assert np.all(heights <= 1.0)

    # When stopped/paused, heights decay
    decayed = engine.update(10.0, num_bars=16, is_playing=False)
    assert np.all(decayed <= heights + 1e-5)


def test_visualizer_render_modes():
    viz = AudioSpectrumVisualizer(num_bars=32)
    
    for mode in [VisualizerMode.BARS, VisualizerMode.BRAILLE, VisualizerMode.WAVE, VisualizerMode.MIRROR, VisualizerMode.PARTICLES]:
        rendered = viz.render(
            current_time_sec=5.0,
            width=60,
            height=10,
            mode=mode,
            theme_name="cyberpunk",
            is_playing=True
        )
        assert rendered is not None
        assert len(rendered) > 0
        assert "\n" in rendered
