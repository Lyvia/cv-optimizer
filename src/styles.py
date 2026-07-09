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

# 3 starter templates. Colors match the "Atlas" design handoff's template
# swatches exactly (heading_color == accent_color: the handoff uses a single
# accent per template for both headings and the contact-line border).
TEMPLATES: dict[str, StyleConfig] = {
    "Classic Blue": StyleConfig(
        name="Classic Blue",
        text_color="#1A1A1A",
        heading_color="#2B5C8A",
        accent_color="#2B5C8A",
        font="Calibri",
    ),
    "Modern Minimal": StyleConfig(
        name="Modern Minimal",
        text_color="#222222",
        heading_color="#1C1B18",
        accent_color="#1C1B18",
        font="Arial",
        heading_border=False,
    ),
    "Elegant Burgundy": StyleConfig(
        name="Elegant Burgundy",
        text_color="#2E2E2E",
        heading_color="#7A2B3A",
        accent_color="#7A2B3A",
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
# ballpark target, not as an exact layout calculation. Measured against the
# real PDFExporter: a CV built of generic bullets tips from 1 to 2 pages
# somewhere between 488 and 596 words. Set well below that floor (rather
# than at the average) for headroom against (a) LLMs overshooting a soft
# word-count instruction and (b) real CVs having more section-header
# overhead per word than the generic bullets used to measure this.
WORDS_PER_PAGE_ESTIMATE = 420


# ── "Atlas" app theme — custom CSS for the Streamlit UI shell itself ───────
# (separate from StyleConfig/TEMPLATES above, which style the exported
# CV/cover-letter documents, not the app's own chrome.)
#
# Streamlit doesn't let native widgets be nested inside HTML injected via
# st.markdown, so the app "card" from the design handoff is recreated by
# styling .block-container directly (it already wraps every widget on the
# page) rather than by opening an unclosed <div> before a series of widgets.
# Finer-grained pieces (top bar, stepper, drop zones, settings panel) are
# scoped with Streamlit's key=-derived `st-key-<key>` CSS class so this
# doesn't leak into unrelated widgets elsewhere on the page.
ATLAS_FONTS_HTML = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,400&family=Public+Sans:ital,wght@0,400;0,500;0,600;0,700;1,400&display=swap" rel="stylesheet">
"""

ATLAS_CSS = """
<style>
:root {
  --atlas-ink:#1C1B18;
  --atlas-text:#3A3833;
  --atlas-muted:#6B6862;
  --atlas-faint:#8B877E;
  --atlas-vfaint:#A29E95;
  --atlas-vvfaint:#B5B1A8;
  --atlas-accent:#1E6F57;
  --atlas-accent-hover:#1A6049;
  --atlas-accent-tint:#E8F1EC;
  --atlas-accent-soft:#F4FAF7;
  --atlas-alert:#C2532F;
  --atlas-alert-tint:#FBEFE9;
  --atlas-border:rgba(28,27,24,.10);
  --atlas-border-soft:rgba(28,27,24,.08);
  --atlas-border-med:rgba(28,27,24,.12);
  --atlas-border-strong:rgba(28,27,24,.18);
  --atlas-surface-soft:#F8F6F1;
  --atlas-page-bg:#EFEBE3;
}

html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
    background: var(--atlas-page-bg) !important;
}
[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stToolbar"] { right: 8px; }

body, .stMarkdown p, .stMarkdown li, .stMarkdown span, label, .stCaption {
    font-family: 'Public Sans', system-ui, sans-serif;
    color: var(--atlas-text);
}
.atlas-serif { font-family: 'Newsreader', serif; }

/* ── App card shell: .block-container IS the card ── */
.block-container {
    max-width: 940px !important;
    background: #FFFFFF;
    border: 1px solid var(--atlas-border);
    border-radius: 20px;
    box-shadow: 0 30px 70px -40px rgba(28,27,24,.5);
    padding: 34px 40px 40px !important;
    margin-top: 42px;
    margin-bottom: 64px;
}

/* ── Top bar — bleeds to the card's edges via negative margin ── */
.st-key-atlas_topbar {
    margin: -34px -40px 26px -40px;
    padding: 14px 28px;
    border-bottom: 1px solid var(--atlas-border-soft);
}
.st-key-atlas_topbar [data-testid="stSelectbox"] > div > div {
    border-radius: 7px !important;
    min-height: 32px !important;
    font-size: 12px !important;
}

/* ── Stepper ── */
.st-key-atlas_stepper { margin-bottom: 28px; }
.st-key-atlas_stepper .stButton > button {
    border-radius: 20px !important;
    font-size: 13px !important;
    padding: 6px 16px !important;
    box-shadow: none !important;
}

/* ── Drop zones (Step 1) ── */
.st-key-atlas_cv_zone {
    border: 1.5px dashed rgba(30,111,87,.45);
    background: var(--atlas-accent-soft);
    border-radius: 14px;
    padding: 18px 20px 10px;
}
.st-key-atlas_job_zone {
    border: 1.5px dashed var(--atlas-border-strong);
    background: #FBFAF7;
    border-radius: 14px;
    padding: 18px 20px 10px;
}
.st-key-atlas_cv_zone [data-testid="stFileUploaderDropzone"],
.st-key-atlas_job_zone [data-testid="stFileUploaderDropzone"] {
    background: transparent;
    border: none;
    padding: 4px 0;
}

/* ── Settings panel (Step 1) ── */
.st-key-atlas_settings {
    background: var(--atlas-surface-soft);
    border-radius: 12px;
    padding: 15px 18px 4px;
    margin-bottom: 14px;
}

/* ── Primary CTA ── */
.st-key-atlas_cta .stButton > button {
    padding: 16px !important;
    border-radius: 13px !important;
    font-size: 15px !important;
    font-weight: 600 !important;
}

/* ── Generic pill radius for secondary buttons ── */
.stButton > button {
    border-radius: 12px;
    font-weight: 600;
}

/* ── Step 2 — priority actions panel ── */
.st-key-atlas_actions_panel {
    background: var(--atlas-surface-soft);
    border-radius: 14px;
    padding: 22px 24px;
}

/* ── Step 3 — doc tabs (segmented, pill-active) ── */
.st-key-atlas_doc_tabs [data-baseweb="tab-list"] {
    background: #F1EFE8;
    border-radius: 11px;
    padding: 4px;
    gap: 4px;
}
.st-key-atlas_doc_tabs [data-baseweb="tab-list"] [data-baseweb="tab-highlight"],
.st-key-atlas_doc_tabs [data-baseweb="tab-border"] {
    display: none;
}
.st-key-atlas_doc_tabs button[data-baseweb="tab"] {
    border-radius: 8px;
    font-size: 13px;
    font-weight: 600;
    color: var(--atlas-faint);
    padding: 7px 16px;
}
.st-key-atlas_doc_tabs button[aria-selected="true"] {
    background: #fff;
    color: var(--atlas-ink);
    box-shadow: 0 1px 2px rgba(0,0,0,.06);
}

/* ── Step 3 — refine-with-AI panels (key= is on the expander itself) ── */
.st-key-atlas_refine_cv,
.st-key-atlas_refine_cl {
    background: var(--atlas-surface-soft);
    border-radius: 14px;
    border: none;
}

/* ── Step 3 — download buttons + bundled zip ── */
.stDownloadButton > button {
    border-radius: 12px;
}
.st-key-atlas_zip_download .stDownloadButton > button {
    width: 100%;
    background: var(--atlas-ink);
    color: #fff;
    border: none;
}
</style>
"""


def inject_atlas_theme() -> str:
    """Return the Atlas theme's font links + CSS as one HTML string, meant
    to be passed to st.markdown(..., unsafe_allow_html=True) once near the
    top of app.py."""
    return ATLAS_FONTS_HTML + ATLAS_CSS


def score_ring_html(score: int, score_label: str) -> str:
    """The Step 2 score-hero ring: a conic-gradient track filled to `score`
    percent, with the number centered on a white disc on top. Pure decor,
    no interactive children -- safe to render as one self-contained
    st.markdown(..., unsafe_allow_html=True) block."""
    pct = max(0, min(100, score))
    return f"""
<div style="width:128px;height:128px;border-radius:50%;flex:none;
    background:conic-gradient(var(--atlas-accent) 0 {pct}%, #E7E3DA {pct}% 100%);
    display:flex;align-items:center;justify-content:center">
  <div style="width:100px;height:100px;border-radius:50%;background:#fff;
      display:flex;flex-direction:column;align-items:center;justify-content:center">
    <span class="atlas-serif" style="font-size:40px;font-weight:600;line-height:1">{pct}</span>
    <span style="font-size:10px;letter-spacing:.12em;text-transform:uppercase;
        color:var(--atlas-faint);margin-top:3px">{score_label}</span>
  </div>
</div>
"""
