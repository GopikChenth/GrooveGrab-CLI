"""
Visualizer Themes and Color Gradient Engine
"""

from typing import Dict, List, Tuple


class Theme:
    """Color palette and gradient definition for TUI and Visualizer."""

    def __init__(
        self,
        name: str,
        display_name: str,
        header: str,
        border: str,
        active_lyric: str,
        dim_lyric: str,
        bar_colors: List[str],  # from bottom to top
        peak_color: str,
        accent: str,
        waveform_color: str,
    ):
        self.name = name
        self.display_name = display_name
        self.header = header
        self.border = border
        self.active_lyric = active_lyric
        self.dim_lyric = dim_lyric
        self.bar_colors = bar_colors
        self.peak_color = peak_color
        self.accent = accent
        self.waveform_color = waveform_color

    def get_row_color(self, row_idx: int, total_rows: int) -> str:
        """Get the gradient color for a given vertical row index (0 = bottom, total_rows-1 = top)."""
        if total_rows <= 1 or not self.bar_colors:
            return self.bar_colors[0] if self.bar_colors else "cyan"
        ratio = max(0.0, min(1.0, row_idx / max(1, total_rows - 1)))
        idx = int(ratio * (len(self.bar_colors) - 1))
        return self.bar_colors[idx]


THEMES: Dict[str, Theme] = {
    "cava": Theme(
        name="cava",
        display_name="CAVA Classic",
        header="bold bright_cyan",
        border="bright_cyan",
        active_lyric="bold bright_yellow",
        dim_lyric="dim white",
        bar_colors=["green", "bright_green", "yellow", "bright_yellow", "bright_red"],
        peak_color="bold bright_cyan",
        accent="bright_yellow",
        waveform_color="bold bright_green",
    ),
    "cyberpunk": Theme(
        name="cyberpunk",
        display_name="Cyberpunk Neon",
        header="bold bright_magenta",
        border="magenta",
        active_lyric="bold bright_cyan",
        dim_lyric="dim magenta",
        bar_colors=["blue", "magenta", "bright_magenta", "bright_cyan", "bright_white"],
        peak_color="bold bright_yellow",
        accent="bright_cyan",
        waveform_color="bold bright_cyan",
    ),
    "matrix": Theme(
        name="matrix",
        display_name="Matrix Code",
        header="bold green",
        border="green",
        active_lyric="bold bright_green",
        dim_lyric="dim green",
        bar_colors=["dark_green", "green", "bright_green", "bright_white"],
        peak_color="bold bright_white",
        accent="bright_green",
        waveform_color="bold bright_green",
    ),
    "fire": Theme(
        name="fire",
        display_name="Inferno Flame",
        header="bold bright_red",
        border="red",
        active_lyric="bold bright_yellow",
        dim_lyric="dim red",
        bar_colors=["red", "bright_red", "dark_orange", "bright_yellow", "bright_white"],
        peak_color="bold bright_yellow",
        accent="bright_red",
        waveform_color="bold bright_yellow",
    ),
    "sunset": Theme(
        name="sunset",
        display_name="Sunset Vibes",
        header="bold dark_orange",
        border="dark_orange",
        active_lyric="bold bright_magenta",
        dim_lyric="dim white",
        bar_colors=["purple", "magenta", "deep_pink3", "dark_orange", "bright_yellow"],
        peak_color="bold bright_white",
        accent="bright_magenta",
        waveform_color="bold magenta",
    ),
    "ocean": Theme(
        name="ocean",
        display_name="Deep Ocean",
        header="bold bright_blue",
        border="blue",
        active_lyric="bold bright_cyan",
        dim_lyric="dim cyan",
        bar_colors=["navy_blue", "blue", "dodger_blue1", "bright_cyan", "bright_white"],
        peak_color="bold bright_white",
        accent="bright_cyan",
        waveform_color="bold dodger_blue1",
    ),
    "aurora": Theme(
        name="aurora",
        display_name="Northern Lights",
        header="bold bright_green",
        border="spring_green3",
        active_lyric="bold bright_cyan",
        dim_lyric="dim green",
        bar_colors=["dark_green", "spring_green3", "medium_spring_green", "cyan", "violet"],
        peak_color="bold bright_magenta",
        accent="spring_green3",
        waveform_color="bold medium_spring_green",
    ),
    "synthwave": Theme(
        name="synthwave",
        display_name="Retro Synthwave",
        header="bold bright_magenta",
        border="purple",
        active_lyric="bold bright_yellow",
        dim_lyric="dim purple",
        bar_colors=["purple", "violet", "bright_magenta", "hot_pink", "bright_yellow"],
        peak_color="bold bright_cyan",
        accent="hot_pink",
        waveform_color="bold bright_magenta",
    ),
    "monochrome": Theme(
        name="monochrome",
        display_name="Monochrome Ice",
        header="bold white",
        border="bright_black",
        active_lyric="bold bright_white",
        dim_lyric="dim white",
        bar_colors=["grey37", "grey58", "grey78", "white", "bright_white"],
        peak_color="bold bright_white",
        accent="white",
        waveform_color="bold white",
    ),
}

# Alias "groove" to "cava"
THEMES["groove"] = THEMES["cava"]

THEME_ORDER = ["cava", "cyberpunk", "matrix", "fire", "sunset", "ocean", "aurora", "synthwave", "monochrome"]


def get_theme(name: str) -> Theme:
    """Get theme by name with fallback to cava."""
    clean_name = (name or "cava").strip().lower()
    return THEMES.get(clean_name, THEMES["cava"])


def next_theme_name(current_name: str) -> str:
    """Get the next theme in cyclic order."""
    curr = current_name.lower()
    if curr not in THEME_ORDER:
        return THEME_ORDER[0]
    idx = THEME_ORDER.index(curr)
    return THEME_ORDER[(idx + 1) % len(THEME_ORDER)]
