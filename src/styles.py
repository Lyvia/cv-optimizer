"""
styles.py — Visual style definitions for CV and cover letter exports.
Drives both the DOCX export (exporters.py) and the free, local HTML
live preview (preview.py). No AI call is involved in resolving or
previewing a style — it is pure local configuration.
"""

from dataclasses import dataclass


@dataclass
class StyleConfig:
    """A resolved visual style: one accent set + one font."""
    name: str
    text_color: str       # main body text, hex e.g. "#1A1A1A"
    heading_color: str    # section headings, hex
    accent_color: str     # border/underline accents, hex
    font: str             # must be one of FONT_CHOICES
    heading_uppercase: bool = True   # ## H2 section headings rendered in ALL CAPS
    heading_border: bool = True      # ## H2 section headings get a bottom border


# Max 4 fonts, all standard Word/Office fonts (safe for DOCX rendering).
FONT_CHOICES = ["Calibri", "Arial", "Georgia", "Garamond"]

# 3 starter templates. "Classic Blue" matches the app's original default look.
TEMPLATES: dict[str, StyleConfig] = {
    "Classic Blue": StyleConfig(
        name="Classic Blue",
        text_color="#1A1A1A",
        heading_color="#1A3A5C",
        accent_color="#2E6DA4",
        font="Calibri",
    ),
    "Modern Minimal": StyleConfig(
        name="Modern Minimal",
        text_color="#222222",
        heading_color="#000000",
        accent_color="#666666",
        font="Arial",
        heading_border=False,
    ),
    "Elegant Burgundy": StyleConfig(
        name="Elegant Burgundy",
        text_color="#2E2E2E",
        heading_color="#7A1F2B",
        accent_color="#B5495B",
        font="Georgia",
        heading_uppercase=False,
    ),
}

DEFAULT_STYLE = TEMPLATES["Classic Blue"]
