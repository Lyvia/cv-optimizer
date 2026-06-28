"""
CV Optimizer AI — Main Application
Streamlit app: CV (+ optional job description) → ATS-optimized CV, cover letter, analysis
"""

import html
import io
import logging
import re
import zipfile

import streamlit as st

from src.parsers import parse_document
from src.llm_client import LLMClient
from src.prompts import PromptBuilder
from src.exporters import DOCXExporter
from src.pdf_exporter import PDFExporter
from src.anonymizer import anonymize
from src.utils import strip_fences
from src.differ import compute_diff, rebuild_text
from src import styles, guide_content
from src.styles import StyleConfig
from src.preview import render_preview_html
from src.i18n import t as i18n_t

logger = logging.getLogger(__name__)

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
PDF_MIME = "application/pdf"

# ─── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="CV Optimizer AI",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    /* ── Base ── */
    .block-container { padding-top: 1.5rem; }
    h1 { color: #1a3a5c; }
    h2 { color: #2e6da4; border-bottom: 1px solid #d0e4f7; padding-bottom: 4px; }
    .stTabs [data-baseweb="tab"] { font-size: 0.95rem; font-weight: 600; }
    .result-box {
        background: #f0f7ff;
        border-left: 4px solid #2e6da4;
        padding: 1rem;
        border-radius: 4px;
        margin-bottom: 1rem;
    }

    /* ── Mobile (≤ 768px) ── */
    @media (max-width: 768px) {
        /* Stack all columns vertically */
        [data-testid="column"] {
            width: 100% !important;
            flex: 1 1 100% !important;
            min-width: 100% !important;
        }
        /* Larger tap targets for buttons */
        .stButton > button {
            width: 100%;
            min-height: 3rem;
            font-size: 1rem;
        }
        /* Full-width download buttons */
        .stDownloadButton > button {
            width: 100%;
            min-height: 2.75rem;
        }
        /* Reduce heading size on small screens */
        h1 { font-size: 1.5rem !important; }
        h2 { font-size: 1.1rem !important; }
        /* Avoid padding waste */
        .block-container {
            padding-left: 0.75rem !important;
            padding-right: 0.75rem !important;
        }
        /* Tab labels wrap instead of truncate */
        .stTabs [data-baseweb="tab"] {
            font-size: 0.8rem;
            padding: 0.4rem 0.5rem;
        }
        /* Text areas fill width */
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
        "ai_calls_used": 0,
        "style_config": styles.DEFAULT_STYLE,
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
            _render_text_block(chunk.old_lines, bg="", fg="#31333F")
            continue

        status = _diff_status(chunk.chunk_id)

        if status == "accepted":
            _render_text_block(chunk.new_lines, bg="", fg="#31333F")
            continue
        if status == "ignored":
            _render_text_block(chunk.old_lines, bg="", fg="#31333F")
            continue

        any_pending = True
        if chunk.type == "removed":
            _render_text_block(chunk.old_lines, bg="#fde8e8", fg="#842029", strike=True)
        elif chunk.type == "added":
            _render_text_block(chunk.new_lines, bg="#e6f4ea", fg="#1e7e34")
        elif chunk.type == "replaced":
            _render_text_block(chunk.old_lines, bg="#fde8e8", fg="#842029", strike=True)
            _render_text_block(chunk.new_lines, bg="#e6f4ea", fg="#1e7e34")

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


@st.fragment
def _render_cv_subtab(style: StyleConfig):
    """CV sub-tab: content + downloads + changes log + refine-with-diff.
    A fragment so accept/ignore/refine only redraw this block, not the
    whole page (preserves scroll position elsewhere)."""
    if st.session_state.show_accept_warning_once:
        st.warning(tr("diff_irreversible_warning"))
        st.session_state.show_accept_warning_once = False

    exporter = DOCXExporter()
    pdf_exporter = PDFExporter()

    st.subheader(tr("results_cv_heading"))

    if st.session_state.cv_pending_diff:
        if st.session_state.cv_pending_change_note:
            st.caption(st.session_state.cv_pending_change_note)
        _render_diff_view(st.session_state.cv_pending_diff, doc_key="cv")
    else:
        st.markdown(render_preview_html(st.session_state.current_cv, style), unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        try:
            cv_docx = exporter.cv_to_docx(st.session_state.current_cv, style=style)
            st.download_button(tr("dl_cv_docx"), data=cv_docx, file_name="Optimized_CV.docx", mime=DOCX_MIME, key="dl_cv_docx_btn")
        except Exception as e:
            st.warning(tr("export_unavailable").format(error=e))
    with col2:
        try:
            cv_pdf = pdf_exporter.cv_to_pdf(st.session_state.current_cv, style=style)
            st.download_button(tr("dl_cv_pdf"), data=cv_pdf, file_name="Optimized_CV.pdf", mime=PDF_MIME, key="dl_cv_pdf_btn")
        except Exception as e:
            st.warning(tr("export_unavailable").format(error=e))

    st.divider()
    st.subheader(tr("results_changes_heading"))
    st.markdown(
        f'<div class="result-box">{st.session_state.changes}</div>',
        unsafe_allow_html=True,
    )

    st.divider()
    cv_expanded = st.session_state.cv_diff_round > 0
    with st.expander(tr("refine_cv_expander_title"), expanded=cv_expanded):
        st.caption(tr("refine_chat_examples"))

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


@st.fragment
def _render_cl_subtab(style: StyleConfig):
    """Cover letter sub-tab: content + downloads + changes log + refine-with-diff.
    Same line-by-line diff mechanism as the CV sub-tab (CVO-3 — previously
    the cover letter only supported a full replace, inconsistent with the
    CV's per-change Accept/Ignore)."""
    if st.session_state.show_accept_warning_once:
        st.warning(tr("diff_irreversible_warning"))
        st.session_state.show_accept_warning_once = False

    exporter = DOCXExporter()
    pdf_exporter = PDFExporter()

    st.subheader(tr("results_letter_heading"))

    if st.session_state.cl_pending_diff:
        if st.session_state.cl_pending_change_note:
            st.caption(st.session_state.cl_pending_change_note)
        _render_diff_view(st.session_state.cl_pending_diff, doc_key="cl")
    else:
        st.markdown(render_preview_html(st.session_state.current_cl, style), unsafe_allow_html=True)

    col5, col6 = st.columns(2)
    with col5:
        try:
            cl_docx = exporter.cover_letter_to_docx(st.session_state.current_cl, style=style)
            st.download_button(tr("dl_letter_docx"), data=cl_docx, file_name="Cover_Letter.docx", mime=DOCX_MIME, key="dl_letter_docx_btn")
        except Exception as e:
            st.warning(tr("export_unavailable").format(error=e))
    with col6:
        try:
            cl_pdf = pdf_exporter.cover_letter_to_pdf(st.session_state.current_cl, style=style)
            st.download_button(tr("dl_letter_pdf"), data=cl_pdf, file_name="Cover_Letter.pdf", mime=PDF_MIME, key="dl_letter_pdf_btn")
        except Exception as e:
            st.warning(tr("export_unavailable").format(error=e))

    st.divider()
    cl_expanded = st.session_state.cl_diff_round > 0
    with st.expander(tr("refine_letter_expander_title"), expanded=cl_expanded):
        st.caption(tr("refine_chat_examples"))

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


# ─── Main layout ──────────────────────────────────────────────────────────────

st.title("📄 CV Optimizer AI")

# ── Interface language — first selectable control on the page ────────────────
ui_lang_choice = st.radio(
    "Interface language",
    ["🇬🇧 English", "🇫🇷 Français"],
    horizontal=True,
    key="ui_lang_radio",
)
st.session_state.ui_lang = "fr" if "Français" in ui_lang_choice else "en"

st.markdown(f"*{tr('app_tagline')}*")

# ── Output language — controls the generated document language, not the UI ──
st.subheader(tr("output_lang_subheader"))
st.caption(tr("output_lang_caption"))
output_language = st.selectbox(
    "Output language",
    ["English", "Français", "Español", "Deutsch", "Italiano"],
    label_visibility="collapsed",
)
st.session_state.language = output_language

# ── Disclaimer — always visible, regardless of the active tab ─────────────────
st.warning(tr("disclaimer_banner"))

if not _api_key:
    st.error(tr("no_api_key_error"))

tab_guide, tab_input, tab_analysis, tab_results = st.tabs([
    tr("tab_guide"),
    tr("tab_input"),
    tr("tab_analysis"),
    tr("tab_results"),
])


# ─── TAB : How to Use ─────────────────────────────────────────────────────────

with tab_guide:
    if st.session_state.ui_lang == "en":
        st.markdown(guide_content.GUIDE_EN)
    else:
        st.markdown(guide_content.GUIDE_FR)


# ─── TAB : Input ──────────────────────────────────────────────────────────────

with tab_input:
    st.subheader(tr("input_cv_subheader"))
    cv_file = st.file_uploader(
        tr("input_cv_upload_label"),
        type=["pdf", "docx", "txt"],
        key="cv_upload",
    )
    cv_text_paste = st.text_area(
        tr("input_cv_paste_label"),
        height=180,
        placeholder=tr("input_cv_placeholder"),
    )

    st.divider()

    st.subheader(tr("input_job_subheader"))
    st.caption(tr("input_job_caption"))
    job_file = st.file_uploader(
        tr("input_job_upload_label"),
        type=["pdf", "docx", "txt"],
        key="job_upload",
    )
    job_text_paste = st.text_area(
        tr("input_job_paste_label"),
        height=180,
        placeholder=tr("input_job_placeholder"),
    )

    st.divider()

    # ── Privacy option ────────────────────────────────────────────────────────
    anonymize_data = st.toggle(
        tr("input_anonymize_toggle"),
        value=True,
        help=tr("input_anonymize_help"),
    )
    debug_mode = st.toggle(
        tr("input_debug_toggle"),
        value=False,
        help=tr("input_debug_help"),
    )

    st.divider()
    generate_btn = st.button(
        tr("input_generate_btn"),
        type="primary",
        use_container_width=True,
        disabled=_quota_exhausted(),
    )
    quota_caption = st.empty()
    quota_caption.caption(_quota_caption_text())
    if _quota_exhausted():
        st.error(tr("quota_exhausted_error").format(max=MAX_AI_CALLS_PER_SESSION))

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

        # Reset refine/diff state on a fresh generation
        st.session_state.cv_pending_diff = None
        st.session_state.cv_pending_change_note = None
        st.session_state.cv_diff_round = 0
        st.session_state.cl_pending_diff = None
        st.session_state.cl_pending_change_note = None
        st.session_state.cl_diff_round = 0

        prompt_builder = PromptBuilder(language=output_language)
        st.session_state.ai_calls_used += 1
        quota_caption.caption(_quota_caption_text())

        # ── Generate
        progress = st.progress(0, text=tr("progress_starting"))

        try:
            progress.progress(10, text=tr("progress_analyzing"))
            st.session_state.analysis = strip_fences(llm.generate(
                system="You are an HR expert and ATS specialist with 15 years of experience.",
                user=prompt_builder.analysis(cv_for_llm, job_content),
                max_tokens=4000,
            ))

            progress.progress(45, text=tr("progress_optimizing"))
            raw_opt = strip_fences(llm.generate(
                system="You are an expert CV writer and ATS specialist.",
                user=prompt_builder.optimize_cv(cv_for_llm, job_content),
                max_tokens=8000,
            ))
            st.session_state.optimized_cv, st.session_state.changes = _split_cv_and_changes(raw_opt)

            progress.progress(80, text=tr("progress_writing_letter"))
            st.session_state.cover_letter = strip_fences(llm.generate(
                system="You are an expert at writing compelling cover letters.",
                user=prompt_builder.cover_letter(cv_for_llm, job_content),
                max_tokens=3000,
            ))

            st.session_state.current_cv = st.session_state.optimized_cv
            st.session_state.current_cl = st.session_state.cover_letter

            progress.progress(100, text=tr("progress_done"))
            st.session_state.generated = True
            st.success(tr("generation_success"))

        except Exception as e:
            progress.empty()
            st.error(tr("generation_error").format(error=e))
            st.info(tr("generation_error_hint"))


# ─── TAB : Analysis ───────────────────────────────────────────────────────────

with tab_analysis:
    if st.session_state.analysis:
        st.markdown(st.session_state.analysis)
    else:
        st.info(tr("analysis_empty_hint"))


# ─── TAB : Results ────────────────────────────────────────────────────────────

with tab_results:
    if not st.session_state.optimized_cv:
        st.info(tr("results_empty_hint"))
    else:
        # ── Visual style controls + live preview ──────────────────────────────
        st.subheader(tr("results_style_subheader"))
        st.caption(tr("results_style_caption"))

        mode = st.radio(
            tr("style_mode_label"),
            [tr("style_mode_template"), tr("style_mode_advanced")],
            horizontal=True,
            key="style_mode",
        )

        if mode == tr("style_mode_template"):
            template_names = list(styles.TEMPLATES.keys())
            chosen_name = st.radio(
                tr("style_template_label"),
                template_names,
                horizontal=True,
                key="template_choice",
            )
            style = styles.TEMPLATES[chosen_name]
        else:
            base = st.session_state.style_config
            col1, col2, col3 = st.columns(3)
            with col1:
                text_color = st.color_picker(tr("style_color_text_label"), value=base.text_color)
            with col2:
                heading_color = st.color_picker(tr("style_color_heading_label"), value=base.heading_color)
            with col3:
                font_index = styles.FONT_CHOICES.index(base.font) if base.font in styles.FONT_CHOICES else 0
                font = st.selectbox(tr("style_font_label"), styles.FONT_CHOICES, index=font_index)
            style = StyleConfig(
                name="Custom",
                text_color=text_color,
                heading_color=heading_color,
                accent_color=heading_color,
                font=font,
                heading_uppercase=base.heading_uppercase,
                heading_border=base.heading_border,
            )

        st.session_state.style_config = style
        st.caption(tr("results_style_live_note"))

        st.divider()

        cv_subtab, cl_subtab = st.tabs([tr("results_subtab_cv"), tr("results_subtab_letter")])

        with cv_subtab:
            _render_cv_subtab(style)

        with cl_subtab:
            _render_cl_subtab(style)

        # ── Bundle download (both current documents, DOCX + PDF) ───────────────
        exporter = DOCXExporter()
        pdf_exporter = PDFExporter()
        st.divider()
        try:
            zip_cv_docx = exporter.cv_to_docx(st.session_state.current_cv, style=style)
            zip_cv_pdf = pdf_exporter.cv_to_pdf(st.session_state.current_cv, style=style)
            zip_cl_docx = exporter.cover_letter_to_docx(st.session_state.current_cl, style=style)
            zip_cl_pdf = pdf_exporter.cover_letter_to_pdf(st.session_state.current_cl, style=style)
            zip_bytes = _build_zip(zip_cv_docx, zip_cv_pdf, zip_cl_docx, zip_cl_pdf)
            st.download_button(
                tr("dl_all_zip"),
                data=zip_bytes,
                file_name="complete_application.zip",
                mime="application/zip",
                key="dl_all_zip_btn",
            )
        except Exception as e:
            st.warning(tr("export_unavailable").format(error=e))
