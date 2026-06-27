"""
pdf_exporter.py — Convert LLM markdown output to downloadable PDF files.
Uses fpdf2. Mirrors the markdown subset and StyleConfig handled by
exporters.py (DOCX), so both export formats look consistent.
"""

import re

from fpdf import FPDF

from .styles import StyleConfig, DEFAULT_STYLE

# fpdf2 only ships core fonts (Helvetica, Times, Courier) — map our
# Word-oriented font choices to the closest built-in equivalent.
_FONT_MAP = {
    "Calibri": "Helvetica",
    "Arial": "Helvetica",
    "Georgia": "Times",
    "Garamond": "Times",
}

_LINE_H = 0.22  # inches, body text line height
_INLINE_PATTERN = re.compile(r"(\*{3}.+?\*{3}|\*{2}.+?\*{2}|\*.+?\*)")

# fpdf2's core fonts (Helvetica/Times) only support latin-1. LLM output
# commonly contains "smart" Unicode punctuation outside that range —
# map the common ones to plain equivalents instead of crashing the export.
_UNICODE_REPLACEMENTS = {
    "‘": "'", "’": "'",
    "“": '"', "”": '"',
    "–": "-", "—": "-",
    "…": "...",
    "•": "-",
    " ": " ",
}


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _latin1_safe(text: str) -> str:
    """Map common smart punctuation to ASCII, then drop anything else
    the core fonts can't render (replaced with '?') rather than crashing."""
    for src, dst in _UNICODE_REPLACEMENTS.items():
        text = text.replace(src, dst)
    return text.encode("latin-1", errors="replace").decode("latin-1")


class PDFExporter:
    """
    Convert markdown-formatted text (as returned by the LLM) to PDF.
    Same margins and styling rules as DOCXExporter, for consistency
    between the two export formats.
    """

    # ── Public ────────────────────────────────────────────────────────────────

    def cv_to_pdf(self, markdown_text: str, style: StyleConfig = DEFAULT_STYLE) -> bytes:
        """Convert an optimized CV (markdown) to a PDF byte string."""
        pdf = self._new_pdf(style, top=0.8, bottom=0.8, left=1.0, right=1.0)
        self._render_markdown(pdf, markdown_text, style)
        return bytes(pdf.output())

    def cover_letter_to_pdf(self, markdown_text: str, style: StyleConfig = DEFAULT_STYLE) -> bytes:
        """Convert a cover letter (markdown) to a PDF byte string."""
        pdf = self._new_pdf(style, top=1.0, bottom=1.0, left=1.2, right=1.2)
        self._render_markdown(pdf, markdown_text, style)
        return bytes(pdf.output())

    # ── Setup ──────────────────────────────────────────────────────────────────

    def _new_pdf(self, style: StyleConfig, top: float, bottom: float, left: float, right: float) -> FPDF:
        pdf = FPDF(unit="in", format="A4")
        pdf.set_margins(left, top, right)
        pdf.set_auto_page_break(auto=True, margin=bottom)
        pdf.add_page()
        pdf.set_font(_FONT_MAP.get(style.font, "Helvetica"), size=11)
        return pdf

    # ── Markdown rendering ───────────────────────────────────────────────────────

    def _render_markdown(self, pdf: FPDF, text: str, style: StyleConfig):
        font = _FONT_MAP.get(style.font, "Helvetica")
        text_rgb = _hex_to_rgb(style.text_color)
        heading_rgb = _hex_to_rgb(style.heading_color)
        accent_rgb = _hex_to_rgb(style.accent_color)

        for line in _latin1_safe(text).split("\n"):
            stripped = line.rstrip()

            if not stripped:
                pdf.ln(_LINE_H * 0.6)
                continue

            if stripped.startswith("# ") and not stripped.startswith("## "):
                content = stripped[2:].strip()
                pdf.set_font(font, "B", 18)
                pdf.set_text_color(*heading_rgb)
                pdf.cell(0, _LINE_H * 1.3, text=content, align="C", new_x="LMARGIN", new_y="NEXT")
                pdf.ln(_LINE_H * 0.3)
                continue

            if stripped.startswith("## ") and not stripped.startswith("### "):
                content = stripped[3:].strip()
                if style.heading_uppercase:
                    content = content.upper()
                pdf.set_font(font, "B", 12)
                pdf.set_text_color(*heading_rgb)
                pdf.cell(0, _LINE_H * 1.1, text=content, new_x="LMARGIN", new_y="NEXT")
                if style.heading_border:
                    pdf.set_draw_color(*accent_rgb)
                    y = pdf.get_y()
                    pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
                pdf.ln(_LINE_H * 0.3)
                continue

            if stripped.startswith("### "):
                content = stripped[4:].strip()
                pdf.set_font(font, "B", 11)
                pdf.set_text_color(*heading_rgb)
                pdf.cell(0, _LINE_H, text=content, new_x="LMARGIN", new_y="NEXT")
                continue

            if re.match(r"^-{3,}$", stripped) or re.match(r"^\*{3,}$", stripped):
                pdf.set_draw_color(*accent_rgb)
                y = pdf.get_y() + _LINE_H * 0.3
                pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
                pdf.ln(_LINE_H * 0.6)
                continue

            if re.match(r"^[-*]\s", stripped):
                content = stripped[2:].strip()
                self._write_inline(pdf, f"-  {content}", font, text_rgb)
                continue

            if re.match(r"^\d+\.\s", stripped):
                content = re.sub(r"^\d+\.\s", "", stripped).strip()
                self._write_inline(pdf, content, font, text_rgb)
                continue

            self._write_inline(pdf, stripped, font, text_rgb)

    # ── Inline formatting ─────────────────────────────────────────────────────

    def _write_inline(self, pdf: FPDF, text: str, font: str, text_rgb: tuple[int, int, int]):
        """
        Parse **bold**, *italic*, and ***bold-italic*** inline markers
        and write each run on the same line via successive write() calls,
        then advance to the next line.
        """
        pdf.set_text_color(*text_rgb)
        parts = _INLINE_PATTERN.split(text)

        for part in parts:
            if not part:
                continue
            if part.startswith("***") and part.endswith("***"):
                pdf.set_font(font, "BI", 11)
                pdf.write(_LINE_H, part[3:-3])
            elif part.startswith("**") and part.endswith("**"):
                pdf.set_font(font, "B", 11)
                pdf.write(_LINE_H, part[2:-2])
            elif part.startswith("*") and part.endswith("*") and len(part) > 2:
                pdf.set_font(font, "I", 11)
                pdf.write(_LINE_H, part[1:-1])
            else:
                pdf.set_font(font, "", 11)
                pdf.write(_LINE_H, part)

        pdf.ln(_LINE_H)
