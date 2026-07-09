"""
CV Optimizer AI — Main Application
Streamlit app: CV (+ optional job description) → ATS-optimized CV, cover letter, analysis
"""

import html
import io
import logging
import re
import zipfile

import pdfplumber
import streamlit as st

from src.parsers import parse_document
from src.llm_client import LLMClient
from src.prompts import PromptBuilder
from src.exporters import DOCXExporter
from src.pdf_exporter import PDFExporter
from src.anonymizer import anonymize
from src.utils import strip_fences
from src.differ import compute_diff, rebuild_text
from src import styles
from src.styles import StyleConfig
from src.analysis_parser import parse_analysis
from src.preview import render_preview_html
from src.i18n import t as i18n_t

logger = logging.getLogger(__name__)

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
PDF_MIME = "application/pdf"

# ─── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="CV Optimizer AI",
    page_icon="📄",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(styles.inject_atlas_theme(), unsafe_allow_html=True)

st.markdown("""
<style>
    .result-box {
        background: var(--atlas-accent-soft, #F4FAF7);
        border-left: 4px solid var(--atlas-accent, #1E6F57);
        padding: 1rem;
        border-radius: 4px;
        margin-bottom: 1rem;
    }

    /* ── Mobile (≤ 768px) ── */
    @media (max-width: 768px) {
        [data-testid="column"] {
            width: 100% !important;
            flex: 1 1 100% !important;
            min-width: 100% !important;
        }
        .stButton > button {
            width: 100%;
            min-height: 3rem;
            font-size: 1rem;
        }
        .stDownloadButton > button {
            width: 100%;
            min-height: 2.75rem;
        }
        .block-container {
            padding-left: 1.1rem !important;
            padding-right: 1.1rem !important;
        }
        .stTextArea textarea { font-size: 0.9rem; }
    }
</style>
""", unsafe_allow_html=True)


# ─── AI usage quota (per browser session) ──────────────────────────────────────

MAX_AI_CALLS_PER_SESSION = 10


def _remaining_calls() -> int:
    return max(0, MAX_AI_CALLS_PER_SESSION - st.session_state.ai_calls_used)


def _quota_exhausted() -> bool:
    return st.session_state.ai_calls_used >= MAX_AI_CALLS_PER_SESSION


# ─── Session state init ────────────────────────────────────────────────────────

def _init_state():
    defaults = {
        "wizard_step": 1,
        "generation_notices": [],
        "analysis": None,
        "optimized_cv": None,
        "changes": None,
        "cover_letter": None,
        "generated": False,
        "llm": None,
        "language": "English",
        "ui_lang": "en",
        "cv_content": None,
        "job_content": None,
        "cv_for_llm": None,
        "target_pages": None,
        "ai_calls_used": 0,
        "style_config": styles.DEFAULT_STYLE,
        "template_choice": styles.DEFAULT_STYLE.name,
        "style_custom_enabled": False,
        "current_cv": None,
        "current_cl": None,
        "cv_pending_diff": None,
        "cv_pending_change_note": None,
        "cv_diff_round": 0,
        "cl_pending_diff": None,
        "cl_pending_change_note": None,
        "cl_diff_round": 0,
        "accept_warning_shown": False,
        "show_accept_warning_once": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


_init_state()


def tr(key: str) -> str:
    return i18n_t(key, st.session_state.ui_lang)


# ─── Helpers ──────────────────────────────────────────────────────────────────

_LITERAL_CHANGES_SEPARATORS = ("---CHANGES---", "--- CHANGES ---")
_CHANGES_HEADING_RE = re.compile(
    r"^#{1,3}\s*(change|modification|modif|änder|cambio|modific)",
    re.IGNORECASE | re.MULTILINE,
)


def _split_cv_and_changes(text: str) -> tuple[str, str]:
    """Split LLM output into (optimized_cv, changes_explanation)."""
    for sep in _LITERAL_CHANGES_SEPARATORS:
        if sep in text:
            parts = text.split(sep, 1)
            return parts[0].strip(), parts[1].strip()

    match = _CHANGES_HEADING_RE.search(text)
    if match:
        return text[: match.start()].strip(), text[match.start():].strip()

    logger.warning(
        "Could not find a changes separator in the LLM output; "
        "returning the full text as the CV with no changes summary."
    )
    return text.strip(), ""


def _build_zip(cv_docx: bytes, cv_pdf: bytes, cl_docx: bytes, cl_pdf: bytes) -> bytes:
    """Package CV + cover letter, both DOCX and PDF, into a single ZIP."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("Optimized_CV.docx", cv_docx)
        zf.writestr("Optimized_CV.pdf", cv_pdf)
        zf.writestr("Cover_Letter.docx", cl_docx)
        zf.writestr("Cover_Letter.pdf", cl_pdf)
    buf.seek(0)
    return buf.getvalue()


def _diff_status(chunk_id: str) -> str:
    return st.session_state.get(f"diff_{chunk_id}", "pending")


def _set_diff_status(chunk_id: str, status: str):
    st.session_state[f"diff_{chunk_id}"] = status


def _collect_diff_statuses(chunks) -> dict[str, str]:
    return {c.chunk_id: _diff_status(c.chunk_id) for c in chunks}


def _maybe_show_accept_warning():
    """
    Queue the one-time irreversibility warning instead of rendering it
    directly: this is called right before st.rerun(), which would discard
    anything rendered in the same pass before the rerun lands.
    """
    if not st.session_state.accept_warning_shown:
        st.session_state.show_accept_warning_once = True
        st.session_state.accept_warning_shown = True


def _render_text_block(lines: list[str], bg: str, fg: str, strike: bool = False):
    text = html.escape("\n".join(lines))
    if not text.strip():
        return
    decoration = "text-decoration: line-through;" if strike else ""
    background = f"background:{bg};" if bg else ""
    st.markdown(
        f"<div style='{background} color:{fg}; padding:6px 10px; border-radius:4px; "
        f"{decoration} white-space:pre-wrap; margin:2px 0; font-family:monospace; "
        f"font-size:0.85rem;'>{text}</div>",
        unsafe_allow_html=True,
    )


def _render_diff_view(chunks, doc_key: str):
    """
    Render a document (CV or cover letter, per CVO-3 — both use this same
    line-by-line mechanism) as ONE continuous document: unchanged lines
    stay plain (context, per CVO-5 — no separate stripped-down diff list),
    chunks still awaiting a decision are color-highlighted with inline
    Accept/Ignore, and chunks already resolved blend back into plain text
    reflecting that decision. This view *replaces* the static styled
    preview while a diff is pending (there is only ever one view on
    screen, never both at once). Once nothing is left pending, the diff
    is cleared and the static styled view returns. Runs inside a
    fragment, so every accept/ignore only re-renders this fragment, not
    the whole page.

    doc_key: "cv" or "cl" — selects which session-state-backed document
    (current_cv/current_cl, {doc_key}_pending_diff, etc.) this round acts on.
    """
    current_attr = "current_cv" if doc_key == "cv" else "current_cl"
    pending_diff_attr = f"{doc_key}_pending_diff"
    pending_note_attr = f"{doc_key}_pending_change_note"
    diff_round_attr = f"{doc_key}_diff_round"

    actionable = [c for c in chunks if c.type != "equal"]
    if not actionable:
        st.info(tr("diff_no_changes"))
        return

    any_pending = False
    for chunk in chunks:
        if chunk.type == "equal":
            _render_text_block(chunk.old_lines, bg="", fg="#3A3833")
            continue

        status = _diff_status(chunk.chunk_id)

        if status == "accepted":
            _render_text_block(chunk.new_lines, bg="", fg="#3A3833")
            continue
        if status == "ignored":
            _render_text_block(chunk.old_lines, bg="", fg="#3A3833")
            continue

        any_pending = True
        if chunk.type == "removed":
            _render_text_block(chunk.old_lines, bg="#FBEEEA", fg="#A8412A", strike=True)
        elif chunk.type == "added":
            _render_text_block(chunk.new_lines, bg="#E9F4EE", fg="#1E6F57")
        elif chunk.type == "replaced":
            _render_text_block(chunk.old_lines, bg="#FBEEEA", fg="#A8412A", strike=True)
            _render_text_block(chunk.new_lines, bg="#E9F4EE", fg="#1E6F57")

        if chunk.type != "removed":
            bcol1, bcol2 = st.columns(2)
            with bcol1:
                if st.button(tr("diff_accept_btn"), key=f"accept_{chunk.chunk_id}", use_container_width=True):
                    _maybe_show_accept_warning()
                    _set_diff_status(chunk.chunk_id, "accepted")
                    st.session_state[current_attr] = rebuild_text(chunks, _collect_diff_statuses(chunks))
                    st.rerun(scope="fragment")
            with bcol2:
                if st.button(tr("diff_ignore_btn"), key=f"ignore_{chunk.chunk_id}", use_container_width=True):
                    _set_diff_status(chunk.chunk_id, "ignored")
                    st.session_state[current_attr] = rebuild_text(chunks, _collect_diff_statuses(chunks))
                    st.rerun(scope="fragment")

    if not any_pending:
        # Last chunk just got resolved — clear and immediately switch back
        # to the styled static view instead of leaving this plain-text
        # rendering on screen as the final state.
        st.session_state[pending_diff_attr] = None
        st.session_state[pending_note_attr] = None
        st.rerun(scope="fragment")
        return

    st.divider()
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button(tr("diff_accept_all_btn"), key=f"accept_all_{doc_key}_{st.session_state[diff_round_attr]}", use_container_width=True):
            _maybe_show_accept_warning()
            for c in chunks:
                _set_diff_status(c.chunk_id, "accepted")
            st.session_state[current_attr] = rebuild_text(chunks, _collect_diff_statuses(chunks))
            st.session_state[pending_diff_attr] = None
            st.session_state[pending_note_attr] = None
            st.rerun(scope="fragment")
    with col_b:
        if st.button(tr("diff_ignore_all_btn"), key=f"ignore_all_{doc_key}_{st.session_state[diff_round_attr]}", use_container_width=True):
            for c in chunks:
                _set_diff_status(c.chunk_id, "ignored")
            st.session_state[current_attr] = rebuild_text(chunks, _collect_diff_statuses(chunks))
            st.session_state[pending_diff_attr] = None
            st.session_state[pending_note_attr] = None
            st.rerun(scope="fragment")


def _render_downloads_row(row_label: str, docx_bytes_fn, pdf_bytes_fn, docx_name: str, pdf_name: str, key_prefix: str):
    """One 'label + .docx + .pdf' row, matching the Atlas downloads layout."""
    col_label, col_docx, col_pdf = st.columns([1, 2, 2])
    with col_label:
        st.markdown(
            f"<div style='font-size:13px;font-weight:600;color:var(--atlas-text);padding-top:10px'>"
            f"{html.escape(row_label)}</div>",
            unsafe_allow_html=True,
        )
    with col_docx:
        try:
            st.download_button(
                ".docx", data=docx_bytes_fn(), file_name=docx_name, mime=DOCX_MIME,
                key=f"{key_prefix}_docx_btn", use_container_width=True,
            )
        except Exception as e:
            st.warning(tr("export_unavailable").format(error=e))
    with col_pdf:
        try:
            st.download_button(
                ".pdf", data=pdf_bytes_fn(), file_name=pdf_name, mime=PDF_MIME,
                key=f"{key_prefix}_pdf_btn", use_container_width=True,
            )
        except Exception as e:
            st.warning(tr("export_unavailable").format(error=e))


def _render_cv_subtab(style: StyleConfig):
    """CV sub-tab: content + downloads + changes log + refine-with-diff.
    Called from the @st.fragment-decorated _render_results_section(), so
    accept/ignore/refine only redraw that block, not the whole page
    (preserves scroll position elsewhere) -- and, since the cover letter
    sub-tab and the bundled ZIP download live in that same fragment, they
    automatically stay in sync with the latest accepted CV too (CVO-9)."""
    if st.session_state.show_accept_warning_once:
        st.warning(tr("diff_irreversible_warning"))
        st.session_state.show_accept_warning_once = False

    exporter = DOCXExporter()
    pdf_exporter = PDFExporter()

    if st.session_state.cv_pending_diff:
        if st.session_state.cv_pending_change_note:
            st.caption(st.session_state.cv_pending_change_note)
        _render_diff_view(st.session_state.cv_pending_diff, doc_key="cv")
    else:
        st.markdown(render_preview_html(st.session_state.current_cv, style), unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    _render_downloads_row(
        tr("dl_cv_row_label"),
        lambda: exporter.cv_to_docx(st.session_state.current_cv, style=style),
        lambda: pdf_exporter.cv_to_pdf(st.session_state.current_cv, style=style),
        "Optimized_CV.docx", "Optimized_CV.pdf", "dl_cv",
    )

    with st.expander(tr("results_changes_heading"), expanded=False):
        st.markdown(
            f'<div class="result-box">{st.session_state.changes}</div>',
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
    with st.container(key="atlas_refine_cv"):
        with st.expander(tr("refine_cv_expander_title"), expanded=True):
            st.caption(f"{tr('refine_chat_examples')} · {tr('refine_ai_note')}")

            quota_exhausted = _quota_exhausted()
            st.caption(_quota_caption_text())
            if quota_exhausted:
                st.error(tr("quota_exhausted_error").format(max=MAX_AI_CALLS_PER_SESSION))

            placeholder = tr("refine_quota_placeholder") if quota_exhausted else tr("refine_chat_placeholder")
            if cv_instruction := st.chat_input(placeholder, disabled=quota_exhausted, key="cv_chat_input"):
                with st.spinner(tr("refine_processing")):
                    pb = PromptBuilder(language=st.session_state.language)
                    st.session_state.ai_calls_used += 1
                    success = False
                    try:
                        raw_response = st.session_state.llm.generate(
                            system="You are an expert CV writer. Apply the user's instructions precisely.",
                            user=pb.refine(st.session_state.current_cv, cv_instruction),
                            max_tokens=8000,
                        )
                        document, change_note = _split_cv_and_changes(strip_fences(raw_response))
                        st.session_state.cv_diff_round += 1
                        st.session_state.cv_pending_diff = compute_diff(
                            st.session_state.current_cv,
                            document,
                            round_id=f"cv_{st.session_state.cv_diff_round}",
                        )
                        st.session_state.cv_pending_change_note = change_note
                        success = True
                    except Exception as e:
                        st.error(tr("refine_error").format(error=e))
                if success:
                    st.rerun(scope="fragment")


def _render_cl_subtab(style: StyleConfig):
    """Cover letter sub-tab: content + downloads + changes log + refine-with-diff.
    Called from _render_results_section() -- see _render_cv_subtab()'s
    docstring. Same line-by-line diff mechanism as the CV sub-tab (CVO-3 —
    previously the cover letter only supported a full replace, inconsistent with the
    CV's per-change Accept/Ignore)."""
    if st.session_state.show_accept_warning_once:
        st.warning(tr("diff_irreversible_warning"))
        st.session_state.show_accept_warning_once = False

    exporter = DOCXExporter()
    pdf_exporter = PDFExporter()

    if st.session_state.cl_pending_diff:
        if st.session_state.cl_pending_change_note:
            st.caption(st.session_state.cl_pending_change_note)
        _render_diff_view(st.session_state.cl_pending_diff, doc_key="cl")
    else:
        st.markdown(render_preview_html(st.session_state.current_cl, style), unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    _render_downloads_row(
        tr("dl_letter_row_label"),
        lambda: exporter.cover_letter_to_docx(st.session_state.current_cl, style=style),
        lambda: pdf_exporter.cover_letter_to_pdf(st.session_state.current_cl, style=style),
        "Cover_Letter.docx", "Cover_Letter.pdf", "dl_letter",
    )

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
    with st.container(key="atlas_refine_cl"):
        with st.expander(tr("refine_letter_expander_title"), expanded=True):
            st.caption(f"{tr('refine_chat_examples')} · {tr('refine_ai_note')}")

            quota_exhausted = _quota_exhausted()
            st.caption(_quota_caption_text())
            if quota_exhausted:
                st.error(tr("quota_exhausted_error").format(max=MAX_AI_CALLS_PER_SESSION))

            placeholder = tr("refine_quota_placeholder") if quota_exhausted else tr("refine_chat_placeholder")
            if cl_instruction := st.chat_input(placeholder, disabled=quota_exhausted, key="cl_chat_input"):
                with st.spinner(tr("refine_processing")):
                    pb = PromptBuilder(language=st.session_state.language)
                    st.session_state.ai_calls_used += 1
                    success = False
                    try:
                        raw_response = st.session_state.llm.generate(
                            system="You are an expert at writing compelling cover letters. Apply the user's instructions precisely.",
                            user=pb.refine(st.session_state.current_cl, cl_instruction),
                            max_tokens=3000,
                        )
                        document, change_note = _split_cv_and_changes(strip_fences(raw_response))
                        st.session_state.cl_diff_round += 1
                        st.session_state.cl_pending_diff = compute_diff(
                            st.session_state.current_cl,
                            document,
                            round_id=f"cl_{st.session_state.cl_diff_round}",
                        )
                        st.session_state.cl_pending_change_note = change_note
                        success = True
                    except Exception as e:
                        st.error(tr("refine_error").format(error=e))
                if success:
                    st.rerun(scope="fragment")


def _render_zip_download(style: StyleConfig):
    """
    Bundle download (both current documents, DOCX + PDF), always rebuilt
    from the latest current_cv/current_cl. Called from
    _render_results_section() -- being in that same fragment is what
    keeps this transparently up to date after an accept/ignore (CVO-9):
    no separate "prepare" step needed, since this whole block reruns
    together whenever either document's diff is acted on.
    """
    exporter = DOCXExporter()
    pdf_exporter = PDFExporter()
    try:
        zip_cv_docx = exporter.cv_to_docx(st.session_state.current_cv, style=style)
        zip_cv_pdf = pdf_exporter.cv_to_pdf(st.session_state.current_cv, style=style)
        zip_cl_docx = exporter.cover_letter_to_docx(st.session_state.current_cl, style=style)
        zip_cl_pdf = pdf_exporter.cover_letter_to_pdf(st.session_state.current_cl, style=style)
        zip_bytes = _build_zip(zip_cv_docx, zip_cv_pdf, zip_cl_docx, zip_cl_pdf)
        with st.container(key="atlas_zip_download"):
            st.download_button(
                tr("dl_all_zip"),
                data=zip_bytes,
                file_name="complete_application.zip",
                mime="application/zip",
                key="dl_all_zip_btn",
                use_container_width=True,
            )
    except Exception as e:
        st.warning(tr("export_unavailable").format(error=e))


def _render_style_swatches():
    """The 3 template color swatches + 'Style: {name}' label, placed next
    to the CV/Letter tabs (see _render_results_section()). Clicking a
    swatch switches the template and turns off custom colors, then does a
    full rerun -- style is resolved before this fragment runs (see
    _resolve_style()), so the new template takes effect immediately."""
    template_names = list(styles.TEMPLATES.keys())
    current = st.session_state.template_choice
    is_custom = st.session_state.style_custom_enabled

    css_rules = []
    for name in template_names:
        key = f"swatch_{name.replace(' ', '_')}"
        color = styles.TEMPLATES[name].accent_color
        active = (name == current) and not is_custom
        outline = "outline:2px solid var(--atlas-accent);" if active else "outline:2px solid transparent;"
        css_rules.append(
            f".st-key-{key} button {{background:{color} !important;width:22px !important;"
            f"height:22px !important;min-width:22px !important;padding:0 !important;"
            f"border-radius:6px !important;border:none !important;{outline}outline-offset:2px;"
            f"color:transparent !important;box-shadow:none !important;}}"
        )
    st.markdown(f"<style>{''.join(css_rules)}</style>", unsafe_allow_html=True)

    with st.container(key="atlas_swatches"):
        st.markdown(
            f"<div style='font-size:11.5px;color:var(--atlas-faint);text-align:right;"
            f"margin-bottom:6px'>{html.escape(tr('results_style_label').format(name=st.session_state.style_config.name))}</div>",
            unsafe_allow_html=True,
        )
        cols = st.columns(len(template_names))
        for name, col in zip(template_names, cols):
            key = f"swatch_{name.replace(' ', '_')}"
            with col:
                if st.button("‌", key=key, help=name):
                    st.session_state.template_choice = name
                    st.session_state.style_custom_enabled = False
                    st.rerun()


@st.fragment
def _render_results_section(style: StyleConfig):
    """
    CV sub-tab + cover letter sub-tab + bundled ZIP download, all in one
    fragment. Combining them (rather than one fragment per sub-tab) is
    what makes the ZIP transparently reflect the latest accepted state
    of *both* documents (CVO-9): st.rerun(scope="fragment") reruns
    whichever @st.fragment function is currently executing, so an
    accept/ignore inside either sub-tab now reruns this whole block --
    recomputing the other (unchanged) sub-tab and the ZIP is cheap (no
    LLM call, just markdown/DOCX/PDF rendering) and invisible to the
    user, while the rest of the page (Input/Analysis tabs, sidebar)
    still never reruns, preserving scroll position there (CVO-5).

    The template swatches live in this same row (see _render_style_swatches())
    to match the Atlas layout, but a swatch click does a *full* st.rerun()
    (not fragment-scoped) since it needs _resolve_style() outside this
    fragment to pick up the new template on the next run.
    """
    col_tabs, col_style = st.columns([1.6, 1])
    with col_tabs:
        with st.container(key="atlas_doc_tabs"):
            cv_subtab, cl_subtab = st.tabs([tr("results_subtab_cv"), tr("results_subtab_letter")])
    with col_style:
        _render_style_swatches()

    with cv_subtab:
        _render_cv_subtab(style)

    with cl_subtab:
        _render_cl_subtab(style)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    _render_zip_download(style)


# ─── LLM config — loaded from Streamlit secrets or .env (not exposed to users) ─

def _load_config() -> tuple[str, str, str]:
    """
    Load provider / api_key / model from Streamlit secrets or environment variables.
    Priority: st.secrets > environment variables.

    To configure locally: set variables in .env
    To configure on Streamlit Cloud: Settings → Secrets
    """
    import os
    from dotenv import load_dotenv
    load_dotenv()  # Load the .env file if present (local usage)

    # Try each provider in order of preference (free first)
    candidates = [
        ("GOOGLE_API_KEY",    "Google (Gemini)",    "gemini-2.5-flash"),
        ("GROQ_API_KEY",      "Groq (Llama)",       "llama-3.3-70b-versatile"),
        ("ANTHROPIC_API_KEY", "Anthropic (Claude)", "claude-3-5-haiku-20241022"),
    ]

    for env_var, provider, model in candidates:
        # Check Streamlit secrets first
        try:
            key = st.secrets.get(env_var, "")
        except Exception:
            key = ""
        # Fall back to environment variable
        if not key:
            key = os.environ.get(env_var, "")
        if key:
            return provider, key, model

    return "", "", ""


_provider, _api_key, _model = _load_config()


def _quota_caption_text() -> str:
    base = tr("quota_remaining_caption").format(remaining=_remaining_calls(), max=MAX_AI_CALLS_PER_SESSION)
    return f"{base} · {_model}"


# ─── Atlas shell — top bar + stepper (common to all 3 steps) ─────────────────

def _render_top_bar():
    with st.container(key="atlas_topbar"):
        col_logo, col_lang, col_credits = st.columns([3, 1.3, 1.7])
        with col_logo:
            st.markdown(
                "<div style='display:flex;align-items:center;gap:10px'>"
                "<div style='width:30px;height:30px;border-radius:8px;background:var(--atlas-accent);"
                "display:flex;align-items:center;justify-content:center;color:#fff;"
                "font-family:Newsreader,serif;font-size:18px;font-weight:600'>C</div>"
                "<span class='atlas-serif' style='font-size:19px;font-weight:600;letter-spacing:-.01em'>"
                "CV&nbsp;Optimizer</span></div>",
                unsafe_allow_html=True,
            )
        with col_lang:
            ui_lang_choice = st.selectbox(
                "Interface language",
                ["🇬🇧 EN", "🇫🇷 FR"],
                label_visibility="collapsed",
                key="ui_lang_select",
            )
            st.session_state.ui_lang = "fr" if "FR" in ui_lang_choice else "en"
        with col_credits:
            st.markdown(
                "<div style='text-align:right;padding-top:5px'>"
                f"<span style='background:var(--atlas-accent-tint);color:var(--atlas-accent);"
                "border-radius:7px;padding:5px 11px;font-size:12px;font-weight:600;white-space:nowrap'>"
                f"{tr('credits_pill').format(remaining=_remaining_calls())}</span></div>",
                unsafe_allow_html=True,
            )
    if not _api_key:
        st.error(tr("no_api_key_error"))


def _render_stepper(current_step: int):
    labels = {1: tr("stepper_step1"), 2: tr("stepper_step2"), 3: tr("stepper_step3")}
    state_css = []
    for num in (1, 2, 3):
        if num < current_step:
            rule = "background:var(--atlas-accent-tint);color:var(--atlas-accent);"
        elif num == current_step:
            rule = "background:var(--atlas-accent);color:#fff;"
        else:
            rule = "background:transparent;color:var(--atlas-vvfaint);border:1.5px solid var(--atlas-border-strong);"
        state_css.append(f".st-key-step_btn_{num} button {{ {rule} font-weight:600; }}")
    st.markdown(f"<style>{''.join(state_css)}</style>", unsafe_allow_html=True)

    with st.container(key="atlas_stepper"):
        c1, cline1, c2, cline2, c3 = st.columns([2.3, 0.35, 2, 0.35, 2.3])
        with c1:
            if st.button(("✓ " if current_step > 1 else "1 ") + labels[1], key="step_btn_1", use_container_width=True):
                st.session_state.wizard_step = 1
                st.rerun()
        with cline1:
            color = "var(--atlas-accent)" if current_step > 1 else "var(--atlas-border-med)"
            op = "opacity:.45;" if current_step > 1 else ""
            st.markdown(f"<div style='height:1.5px;background:{color};{op}margin-top:15px'></div>", unsafe_allow_html=True)
        with c2:
            if st.button(("✓ " if current_step > 2 else "2 ") + labels[2], key="step_btn_2", use_container_width=True):
                st.session_state.wizard_step = 2
                st.rerun()
        with cline2:
            color = "var(--atlas-accent)" if current_step > 2 else "var(--atlas-border-med)"
            op = "opacity:.45;" if current_step > 2 else ""
            st.markdown(f"<div style='height:1.5px;background:{color};{op}margin-top:15px'></div>", unsafe_allow_html=True)
        with c3:
            if st.button("3 " + labels[3], key="step_btn_3", use_container_width=True):
                st.session_state.wizard_step = 3
                st.rerun()


# ─── Step 1 — Import ───────────────────────────────────────────────────────────

def _render_step1():
    st.markdown(
        f"<h1 class='atlas-serif' style='margin:0 0 6px;font-size:34px;font-weight:500;"
        f"letter-spacing:-.015em;line-height:1.1'>{tr('step1_title')}</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<p style='margin:0 0 26px;font-size:15px;line-height:1.5;color:var(--atlas-muted);"
        f"max-width:560px'>{tr('step1_subtitle')}</p>",
        unsafe_allow_html=True,
    )

    col_cv, col_job = st.columns(2)
    with col_cv:
        with st.container(key="atlas_cv_zone"):
            st.markdown(
                "<div style='width:42px;height:42px;border-radius:11px;background:var(--atlas-accent-tint);"
                "margin-bottom:8px;display:flex;align-items:center;justify-content:center;"
                "color:var(--atlas-accent);font-size:20px'>↑</div>"
                f"<div style='font-size:15px;font-weight:600;margin-bottom:6px'>{tr('step1_cv_zone_title')}</div>",
                unsafe_allow_html=True,
            )
            cv_file = st.file_uploader(
                tr("input_cv_upload_label"), type=["pdf", "docx", "txt"],
                key="cv_upload", label_visibility="collapsed",
            )
            with st.expander(tr("step1_paste_instead")):
                cv_text_paste = st.text_area(
                    tr("input_cv_paste_label"), height=150,
                    placeholder=tr("input_cv_placeholder"), label_visibility="collapsed",
                )
    with col_job:
        with st.container(key="atlas_job_zone"):
            st.markdown(
                "<div style='width:42px;height:42px;border-radius:11px;background:var(--atlas-surface-soft);"
                "margin-bottom:8px;display:flex;align-items:center;justify-content:center;"
                "color:var(--atlas-faint);font-size:20px'>+</div>"
                f"<div style='font-size:15px;font-weight:600;margin-bottom:2px'>{tr('step1_job_zone_title')}</div>"
                f"<div style='font-size:12.5px;color:var(--atlas-faint);margin-bottom:6px'>"
                f"{tr('step1_job_zone_subtitle')} · {tr('input_job_caption')}</div>",
                unsafe_allow_html=True,
            )
            job_file = st.file_uploader(
                tr("input_job_upload_label"), type=["pdf", "docx", "txt"],
                key="job_upload", label_visibility="collapsed",
            )
            with st.expander(tr("step1_paste_instead")):
                job_text_paste = st.text_area(
                    tr("input_job_paste_label"), height=150,
                    placeholder=tr("input_job_placeholder"), label_visibility="collapsed",
                )

    with st.container(key="atlas_settings"):
        col_a, col_b = st.columns([1.4, 1])
        with col_a:
            anonymize_data = st.toggle(
                f"{tr('step1_anonymize_label')} · :green[{tr('recommended_badge')}]",
                value=True,
                help=tr("input_anonymize_help"),
                key="anonymize_toggle",
            )
        with col_b:
            output_language = st.selectbox(
                tr("step1_output_lang_label"),
                ["English", "Français", "Español", "Deutsch", "Italiano"],
                help=tr("output_lang_caption"),
                key="output_language_select",
            )
    st.session_state.language = output_language

    with st.expander(tr("step1_advanced_label"), expanded=False):
        debug_mode = st.toggle(
            tr("input_debug_toggle"), value=False, help=tr("input_debug_help"), key="debug_mode_toggle",
        )
        target_length_choice = st.radio(
            tr("target_length_label"),
            [tr("target_length_original"), tr("target_length_1page"), tr("target_length_2page")],
            horizontal=True,
            key="target_length_choice",
        )
        st.caption(tr("target_length_caption"))

    with st.container(key="atlas_cta"):
        generate_btn = st.button(
            tr("step1_cta"),
            type="primary",
            use_container_width=True,
            disabled=_quota_exhausted(),
            key="generate_btn",
        )
    quota_caption = st.empty()
    quota_caption.caption(_quota_caption_text())
    if _quota_exhausted():
        st.error(tr("quota_exhausted_error").format(max=MAX_AI_CALLS_PER_SESSION))

    st.markdown(
        f"<p style='margin:8px 0 0;font-size:11.5px;line-height:1.45;color:var(--atlas-vfaint);"
        f"text-align:center'>{tr('step1_disclaimer')}</p>",
        unsafe_allow_html=True,
    )

    if generate_btn:
        # ── Validation
        errors = []
        if not _api_key:
            errors.append(tr("input_error_no_api_key"))

        cv_content = ""
        if cv_file:
            try:
                cv_content = parse_document(cv_file)
            except Exception as e:
                errors.append(tr("input_error_cv_read").format(error=e))
        elif cv_text_paste.strip():
            cv_content = cv_text_paste.strip()
        else:
            errors.append(tr("input_error_cv_missing"))

        job_content = ""
        if job_file:
            try:
                job_content = parse_document(job_file)
            except Exception as e:
                errors.append(tr("input_error_job_read").format(error=e))
        elif job_text_paste.strip():
            job_content = job_text_paste.strip()
        # No error if empty — job description is optional

        if errors:
            for err in errors:
                st.error(err)
            st.stop()

        # ── Anonymize PII before sending to LLM ──────────────────────────────
        cv_for_llm = cv_content
        if anonymize_data:
            anon_result = anonymize(cv_content)
            cv_for_llm = anon_result.anonymized_text
            if anon_result.summary:
                with st.expander(tr("input_anon_expander_title").format(count=len(anon_result.summary))):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.markdown(tr("input_anon_replaced_with"))
                        for placeholder in anon_result.replacements:
                            st.code(placeholder, language=None)
                    with col_b:
                        st.markdown(tr("input_anon_original_value"))
                        for original in anon_result.replacements.values():
                            st.code(original, language=None)
                    st.caption(tr("input_anon_caption"))
            else:
                st.info(tr("input_anon_none_detected"))

        # ── Debug mode ────────────────────────────────────────────────────────
        if debug_mode:
            with st.expander(tr("input_debug_expander_title"), expanded=True):
                st.markdown(tr("input_debug_cv_label"))
                st.text_area("CV sent", value=cv_for_llm, height=200, disabled=True, key="debug_cv")
                st.markdown(tr("input_debug_job_label"))
                st.text_area("Job sent", value=job_content, height=150, disabled=True, key="debug_job")
                st.caption(tr("input_debug_provider_model").format(provider=_provider, model=_model))

        # ── Init LLM
        try:
            llm = LLMClient(provider=_provider, api_key=_api_key, model=_model)
        except Exception as e:
            st.error(tr("input_llm_init_failed").format(error=e))
            st.stop()

        st.session_state.llm = llm
        st.session_state.cv_content = cv_content
        st.session_state.job_content = job_content
        # Persisted for Step 2's CTA, which runs the CV + cover-letter calls
        # (see _render_step2()) -- that screen has no file/job inputs of its
        # own, so it reuses exactly what was sent to the LLM here.
        st.session_state.cv_for_llm = cv_for_llm

        if target_length_choice == tr("target_length_1page"):
            st.session_state.target_pages = 1
        elif target_length_choice == tr("target_length_2page"):
            st.session_state.target_pages = 2
        else:
            st.session_state.target_pages = None

        # Reset refine/diff state and any previous results on a fresh analysis
        st.session_state.optimized_cv = None
        st.session_state.changes = None
        st.session_state.cover_letter = None
        st.session_state.current_cv = None
        st.session_state.current_cl = None
        st.session_state.generated = False
        st.session_state.cv_pending_diff = None
        st.session_state.cv_pending_change_note = None
        st.session_state.cv_diff_round = 0
        st.session_state.cl_pending_diff = None
        st.session_state.cl_pending_change_note = None
        st.session_state.cl_diff_round = 0

        prompt_builder = PromptBuilder(language=output_language)
        st.session_state.ai_calls_used += 1
        quota_caption.caption(_quota_caption_text())

        # ── Generate — analysis only. CV + cover letter are generated from
        # Step 2's CTA once the user has seen the score (see _render_step2()).
        progress = st.progress(0, text=tr("progress_analyzing"))

        try:
            st.session_state.analysis = strip_fences(llm.generate(
                system="You are an HR expert and ATS specialist with 15 years of experience.",
                user=prompt_builder.analysis(cv_for_llm, job_content),
                max_tokens=4000,
            ))
            progress.progress(100, text=tr("progress_done"))

            # Renders on Step 2, not here -- see _render_step2()'s flush of
            # generation_notices (the "flash message across a rerun"
            # pattern, same idea as show_accept_warning_once above): the
            # st.rerun() right below would otherwise discard this message
            # before anyone sees it.
            st.session_state.generation_notices.append(("success", tr("analysis_ready_notice")))
            st.session_state.wizard_step = 2
            st.rerun()

        except Exception as e:
            progress.empty()
            st.error(tr("generation_error").format(error=e))
            st.info(tr("generation_error_hint"))


# ─── Step 2 — Analyse ──────────────────────────────────────────────────────────

_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")


def _inline_md(text: str) -> str:
    """Escape, then re-enable **bold** -- the analysis prompt's gap/action
    items sometimes use it (e.g. "**Missing keywords**: ..."); without this
    the literal asterisks would show up in the plain-text bullet list."""
    return _BOLD_RE.sub(r"<strong>\1</strong>", html.escape(text))


def _score_headline(score: int) -> str:
    if score >= 85:
        return tr("score_headline_excellent")
    if score >= 70:
        return tr("score_headline_good")
    if score >= 50:
        return tr("score_headline_partial")
    return tr("score_headline_weak")


def _render_score_hero(parsed):
    has_job = bool((st.session_state.job_content or "").strip())
    subline = tr("score_subline_with_job") if has_job else tr("score_subline_no_job")

    ats_count = len(parsed.ats_issues)
    if ats_count > 0:
        pill2_text = tr("ats_status_issues").format(count=ats_count)
        pill2_bg, pill2_fg = "var(--atlas-alert-tint)", "var(--atlas-alert)"
    else:
        pill2_text = tr("ats_status_no_issues")
        pill2_bg, pill2_fg = "var(--atlas-accent-tint)", "var(--atlas-accent)"

    col_ring, col_text = st.columns([1, 2.4])
    with col_ring:
        st.markdown(styles.score_ring_html(parsed.score, tr("score_label")), unsafe_allow_html=True)
    with col_text:
        st.markdown(
            f"<div class='atlas-serif' style='font-size:26px;font-weight:500;"
            f"letter-spacing:-.01em;margin-bottom:5px'>{html.escape(_score_headline(parsed.score))}</div>"
            f"<p style='margin:0 0 12px;font-size:14px;line-height:1.45;color:var(--atlas-muted)'>"
            f"{html.escape(subline)}</p>"
            "<div style='display:flex;gap:8px;flex-wrap:wrap'>"
            "<span style='font-size:11.5px;font-weight:600;background:var(--atlas-accent-tint);"
            f"color:var(--atlas-accent);border-radius:20px;padding:5px 12px'>{html.escape(tr('ats_status_readable'))}</span>"
            f"<span style='font-size:11.5px;font-weight:600;background:{pill2_bg};"
            f"color:{pill2_fg};border-radius:20px;padding:5px 12px'>{html.escape(pill2_text)}</span>"
            "</div>",
            unsafe_allow_html=True,
        )
    st.markdown(
        "<div style='border-bottom:1px solid var(--atlas-border);margin:22px 0 24px'></div>",
        unsafe_allow_html=True,
    )

    def _bullet_list(items: list[str]) -> str:
        return "".join(f"<div>· {_inline_md(i)}</div>" for i in items) or "—"

    col_strengths, col_gaps = st.columns(2)
    with col_strengths:
        st.markdown(
            "<div style=\"font:600 10.5px 'Public Sans';letter-spacing:.14em;text-transform:uppercase;"
            f"color:var(--atlas-accent);margin-bottom:13px\">{html.escape(tr('strengths_heading'))}</div>"
            "<div style='font-size:13.5px;line-height:1.5;color:var(--atlas-text);"
            f"display:flex;flex-direction:column;gap:10px'>{_bullet_list(parsed.strengths)}</div>",
            unsafe_allow_html=True,
        )
    with col_gaps:
        st.markdown(
            "<div style=\"font:600 10.5px 'Public Sans';letter-spacing:.14em;text-transform:uppercase;"
            f"color:var(--atlas-alert);margin-bottom:13px\">{html.escape(tr('gaps_heading'))}</div>"
            "<div style='font-size:13.5px;line-height:1.5;color:var(--atlas-text);"
            f"display:flex;flex-direction:column;gap:10px'>{_bullet_list(parsed.gaps)}</div>",
            unsafe_allow_html=True,
        )

    if parsed.top_actions:
        st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
        with st.container(key="atlas_actions_panel"):
            st.markdown(
                "<div style=\"font:600 10.5px 'Public Sans';letter-spacing:.14em;text-transform:uppercase;"
                f"color:var(--atlas-muted);margin-bottom:15px\">{html.escape(tr('actions_heading'))}</div>",
                unsafe_allow_html=True,
            )
            rows = [
                "<div style='display:flex;gap:11px'>"
                "<span style='flex:none;width:21px;height:21px;border-radius:50%;background:var(--atlas-accent);"
                "color:#fff;font-size:11px;font-weight:700;display:flex;align-items:center;"
                f"justify-content:center'>{i}</span> {_inline_md(action)}</div>"
                for i, action in enumerate(parsed.top_actions[:5], start=1)
            ]
            st.markdown(
                "<div style='display:flex;flex-direction:column;gap:12px;font-size:13.5px;"
                f"line-height:1.4;color:var(--atlas-text)'>{''.join(rows)}</div>",
                unsafe_allow_html=True,
            )


def _run_cv_and_letter_generation():
    """Step 2's CTA: generate the optimized CV + cover letter from the CV
    text and settings captured back in Step 1. No extra quota charge here
    -- the whole analyze-then-generate flow still costs 1 AI-generations
    unit total, same as the old single-click flow, just split across two
    user actions to match the guided narrative (charged once, at Step 1's
    analysis click)."""
    llm = st.session_state.llm
    prompt_builder = PromptBuilder(language=st.session_state.language)
    cv_for_llm = st.session_state.cv_for_llm
    job_content = st.session_state.job_content or ""
    target_pages = st.session_state.target_pages

    progress = st.progress(0, text=tr("progress_optimizing"))
    try:
        raw_opt = strip_fences(llm.generate(
            system="You are an expert CV writer and ATS specialist.",
            user=prompt_builder.optimize_cv(cv_for_llm, job_content, target_pages=target_pages),
            max_tokens=8000,
        ))
        st.session_state.optimized_cv, st.session_state.changes = _split_cv_and_changes(raw_opt)

        progress.progress(60, text=tr("progress_writing_letter"))
        st.session_state.cover_letter = strip_fences(llm.generate(
            system="You are an expert at writing compelling cover letters.",
            user=prompt_builder.cover_letter(cv_for_llm, job_content),
            max_tokens=3000,
        ))

        st.session_state.current_cv = st.session_state.optimized_cv
        st.session_state.current_cl = st.session_state.cover_letter

        progress.progress(100, text=tr("progress_done"))
        st.session_state.generated = True
        st.session_state.generation_notices.append(("success", tr("generation_success")))

        # Same best-effort overflow check as before (see the old single-stage
        # flow this was split from) -- now runs here since this is where the
        # CV is actually produced.
        if target_pages is not None:
            try:
                check_pdf = PDFExporter().cv_to_pdf(
                    st.session_state.current_cv, style=st.session_state.style_config
                )
                with pdfplumber.open(io.BytesIO(check_pdf)) as pdf:
                    actual_pages = len(pdf.pages)
                if actual_pages > target_pages:
                    st.session_state.generation_notices.append((
                        "warning",
                        tr("target_length_overflow_warning").format(
                            actual=actual_pages, target=target_pages
                        ),
                    ))
            except Exception:
                pass

        st.session_state.wizard_step = 3
        st.rerun()

    except Exception as e:
        progress.empty()
        st.error(tr("generation_error").format(error=e))
        st.info(tr("generation_error_hint"))


def _render_step2():
    if st.session_state.generation_notices:
        for level, msg in st.session_state.generation_notices:
            getattr(st, level)(msg)
        st.session_state.generation_notices = []

    if not st.session_state.analysis:
        st.info(tr("analysis_empty_hint"))
        if st.button(tr("wizard_back"), key="step2_back_empty"):
            st.session_state.wizard_step = 1
            st.rerun()
        return

    parsed = parse_analysis(st.session_state.analysis)

    if parsed.score is None:
        # The analysis text didn't match the expected section shape --
        # degrade to the raw markdown rather than showing a broken/empty
        # hero (see src/analysis_parser.py's docstring).
        st.markdown(
            f"<h2 class='atlas-serif' style='margin:0 0 18px;font-size:26px;font-weight:500'>"
            f"{tr('stepper_step2')}</h2>",
            unsafe_allow_html=True,
        )
        st.markdown(st.session_state.analysis)
    else:
        _render_score_hero(parsed)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    already_generated = bool(st.session_state.optimized_cv)
    col_back, col_next = st.columns(2)
    with col_back:
        if st.button(tr("wizard_back"), use_container_width=True, key="step2_back"):
            st.session_state.wizard_step = 1
            st.rerun()
    with col_next:
        next_disabled = (not already_generated) and _quota_exhausted()
        next_clicked = st.button(
            tr("wizard_view_results") if already_generated else tr("step2_cta"),
            type="primary", use_container_width=True,
            key="step2_next", disabled=next_disabled,
        )
    if not already_generated and _quota_exhausted():
        st.error(tr("quota_exhausted_error").format(max=MAX_AI_CALLS_PER_SESSION))

    if next_clicked:
        if already_generated:
            st.session_state.wizard_step = 3
            st.rerun()
        else:
            _run_cv_and_letter_generation()


# ─── Step 3 — Résultats ────────────────────────────────────────────────────────

def _resolve_style() -> StyleConfig:
    """Read-only: resolves the active StyleConfig from already-persisted
    widget state (template_choice / style_custom_enabled / custom_*)
    without creating any widgets itself. Needed *before*
    _render_results_section()'s fragment runs (its swatch row lives
    inside that fragment); the actual customize controls are rendered
    afterwards by _render_style_customize_expander(), using the same
    keys -- Streamlit persists a keyed widget's value in session_state
    across runs even before the widget is re-created in a later run, so
    this read-first pattern is safe."""
    template_names = list(styles.TEMPLATES.keys())
    if st.session_state.template_choice not in template_names:
        st.session_state.template_choice = template_names[0]

    if st.session_state.style_custom_enabled:
        base = st.session_state.style_config
        text_color = st.session_state.get("custom_text_color", base.text_color)
        heading_color = st.session_state.get("custom_heading_color", base.heading_color)
        font = st.session_state.get("custom_font", base.font)
        style = StyleConfig(
            name="Custom",
            text_color=text_color,
            heading_color=heading_color,
            accent_color=heading_color,
            font=font,
            heading_uppercase=True,
            heading_border=True,
        )
    else:
        style = styles.TEMPLATES[st.session_state.template_choice]

    st.session_state.style_config = style
    return style


def _render_style_customize_expander():
    base = st.session_state.style_config
    with st.expander(tr("style_customize_expander"), expanded=False):
        st.toggle(tr("style_customize_toggle"), key="style_custom_enabled")
        if st.session_state.style_custom_enabled:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.color_picker(tr("style_color_text_label"), value=base.text_color, key="custom_text_color")
            with col2:
                st.color_picker(tr("style_color_heading_label"), value=base.heading_color, key="custom_heading_color")
            with col3:
                font_index = styles.FONT_CHOICES.index(base.font) if base.font in styles.FONT_CHOICES else 0
                st.selectbox(tr("style_font_label"), styles.FONT_CHOICES, index=font_index, key="custom_font")


def _render_step3():
    if st.session_state.generation_notices:
        for level, msg in st.session_state.generation_notices:
            getattr(st, level)(msg)
        st.session_state.generation_notices = []

    if not st.session_state.optimized_cv:
        st.info(tr("results_empty_hint"))
        if st.button(tr("wizard_back"), key="step3_back"):
            st.session_state.wizard_step = 1
            st.rerun()
        return

    style = _resolve_style()
    _render_results_section(style)

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    _render_style_customize_expander()


# ─── Main layout ──────────────────────────────────────────────────────────────

_render_top_bar()
_render_stepper(st.session_state.wizard_step)

if st.session_state.wizard_step == 1:
    _render_step1()
elif st.session_state.wizard_step == 2:
    _render_step2()
else:
    _render_step3()
