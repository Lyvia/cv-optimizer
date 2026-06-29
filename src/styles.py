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


# ── Page layout (shared by exporters.py, pdf_exporter.py, and the one-page
# prompt budget in prompts.py — keep all three in sync with these values) ──
PAGE_WIDTH_IN = 8.27   # A4
PAGE_HEIGHT_IN = 11.69  # A4

CV_MARGINS_IN = {"top": 0.5, "bottom": 0.5, "left": 0.7, "right": 0.7}
LETTER_MARGINS_IN = {"top": 0.6, "bottom": 0.6, "left": 0.8, "right": 0.8}

FONT_SIZE_BODY_PT = 10
FONT_SIZE_SECTION_PT = 11
FONT_SIZE_TITLE_PT = 14

# Rough estimate of how many words fit on one A4 page at FONT_SIZE_BODY_PT
# with the CV margins above. Inherently approximate (depends on bullets,
# headings, and blank lines, which take less than a full line of text) --
# used only to give optimize_cv()'s explicit 1-page/2-page length budget a
# ballpark target, not as an exact layout calculation.
WORDS_PER_PAGE_ESTIMATE = 550
