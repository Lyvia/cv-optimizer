"""
preview.py — Free, local, zero-token HTML preview of a styled document.

Renders a small subset of markdown (the same subset exporters.py turns
into DOCX) as inline-styled HTML, so the user can simulate how a
template/color/font choice will look without ever calling the LLM.
"""

import html
import re

from .styles import StyleConfig, FONT_SIZE_BODY_PT, FONT_SIZE_SECTION_PT, FONT_SIZE_TITLE_PT

SAMPLE_CV_PREVIEW = """# John Doe
john.doe@email.com | linkedin.com/in/johndoe | Paris

## Professional Summary
Results-driven Project Manager with 6+ years of experience leading cross-functional teams.

## Professional Experience
**Project Manager** — Acme Corp (2021–2024)
- Led a team of 8 across 3 departments
- Increased on-time delivery rate by 27%

## Skills
Python, SQL, Agile, Stakeholder Management

## Education
**Master in Management** — Business School (2019)
"""

SAMPLE_LETTER_PREVIEW = """# Cover Letter

Dear Hiring Manager,

I am writing to apply for the **Project Manager** position at your company. \
With over six years of experience leading cross-functional teams, I am confident \
I can bring immediate value to your organization.

In my current role, I increased on-time delivery by 27% while managing a team of 8. \
I would welcome the opportunity to bring this same impact to your team.

Sincerely,
[CANDIDATE NAME]
"""


def render_preview_html(markdown_text: str, style: StyleConfig) -> str:
    """
    Convert a markdown string into a self-contained, inline-styled HTML
    "paper sheet" reflecting the given style. Pure string formatting —
    no network or AI call, safe to call on every widget interaction.

    Args:
        markdown_text: Markdown text (CV, cover letter, or sample snippet)
        style: Resolved StyleConfig (colors + font) to render with

    Returns:
        str: HTML fragment, ready for st.markdown(..., unsafe_allow_html=True)
    """
    body_html = _markdown_to_html(markdown_text, style)

    # Streamlit's markdown sanitizer strips `font-family` from inline
    # style="" attributes (color/size/border survive, font-family doesn't) —
    # a real <style> block is not filtered the same way, so the font has
    # to be set there instead of inline like the other properties below.
    return f"""
<style>
.cvopt-preview, .cvopt-preview * {{
    font-family: "{style.font}", sans-serif !important;
}}
</style>
<div class="cvopt-preview" style="
    background: #ffffff;
    color: {style.text_color};
    font-size: {FONT_SIZE_BODY_PT}pt;
    padding: 28px 32px;
    border: 1px solid #ddd;
    border-radius: 6px;
    box-shadow: 0 1px 6px rgba(0,0,0,0.08);
    line-height: 1.5;
">
{body_html}
</div>
"""


def _markdown_to_html(text: str, style: StyleConfig) -> str:
    lines = text.split("\n")
    out: list[str] = []
    in_list: str | None = None  # "ul" or "ol" while inside a list

    def close_list():
        nonlocal in_list
        if in_list:
            out.append(f"</{in_list}>")
            in_list = None

    for raw_line in lines:
        line = raw_line.rstrip()

        if not line:
            close_list()
            out.append("<div style='height: 0.6em;'></div>")
            continue

        if line.startswith("# ") and not line.startswith("## "):
            close_list()
            content = _inline(line[2:].strip())
            out.append(
                f"<h1 style='color:{style.heading_color}; text-align:center; "
                f"font-size:{FONT_SIZE_TITLE_PT}pt; margin-bottom:0.3em;'>{content}</h1>"
            )
            continue

        if line.startswith("## ") and not line.startswith("### "):
            close_list()
            content = _inline(line[3:].strip())
            text_transform = "uppercase" if style.heading_uppercase else "none"
            # Always declare border-bottom/padding-bottom explicitly (never omit
            # the property) — app.py has a page-wide `h2 { border-bottom: ...; }`
            # rule for the app's own headings, and an inline style only wins over
            # it for properties it actually declares. Omitting the property here
            # let that page-wide border leak into no-border styles (CVO-12).
            border = (
                f"border-bottom:1px solid {style.accent_color}; padding-bottom:2px; "
                if style.heading_border
                else "border-bottom:none; padding-bottom:0; "
            )
            out.append(
                f"<h2 style='color:{style.heading_color}; text-transform:{text_transform}; "
                f"font-size:{FONT_SIZE_SECTION_PT}pt; {border}margin-top:1em;'>{content}</h2>"
            )
            continue

        if line.startswith("### "):
            close_list()
            content = _inline(line[4:].strip())
            out.append(
                f"<h3 style='color:{style.heading_color}; "
                f"font-size:{FONT_SIZE_SECTION_PT}pt; "
                f"font-weight:bold; margin-top:0.8em;'>{content}</h3>"
            )
            continue

        if re.match(r"^-{3,}$", line) or re.match(r"^\*{3,}$", line):
            close_list()
            out.append(f"<hr style='border: none; border-top: 1px solid {style.accent_color};'>")
            continue

        if re.match(r"^[-*]\s", line):
            if in_list != "ul":
                close_list()
                out.append("<ul style='margin:0.2em 0;'>")
                in_list = "ul"
            content = _inline(line[2:].strip())
            out.append(f"<li>{content}</li>")
            continue

        if re.match(r"^\d+\.\s", line):
            if in_list != "ol":
                close_list()
                out.append("<ol style='margin:0.2em 0;'>")
                in_list = "ol"
            content = _inline(re.sub(r"^\d+\.\s", "", line).strip())
            out.append(f"<li>{content}</li>")
            continue

        close_list()
        out.append(f"<p style='margin:0.3em 0;'>{_inline(line)}</p>")

    close_list()
    return "\n".join(out)


def _inline(text: str) -> str:
    """Escape raw text, then apply **bold** / *italic* markdown markers."""
    escaped = html.escape(text)
    escaped = re.sub(r"\*\*\*(.+?)\*\*\*", r"<b><i>\1</i></b>", escaped)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped)
    escaped = re.sub(r"\*(.+?)\*", r"<i>\1</i>", escaped)
    return escaped
