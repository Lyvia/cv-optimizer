"""
CV Optimizer AI — Main Application
Streamlit app: CV + job description → ATS-optimized CV, cover letter, analysis
"""

import io
import zipfile
import streamlit as st

from src.parsers import parse_document
from src.llm_client import LLMClient, PROVIDERS
from src.prompts import PromptBuilder
from src.exporters import DOCXExporter
from src.anonymizer import anonymize

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


# ─── Session state init ────────────────────────────────────────────────────────

def _init_state():
    defaults = {
        "analysis": None,
        "optimized_cv": None,
        "changes": None,
        "cover_letter": None,
        "generated": False,
        "messages": [],
        "llm": None,
        "language": "Français",
        "cv_content": None,
        "job_content": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


_init_state()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _split_cv_and_changes(text: str) -> tuple[str, str]:
    """Split LLM output into (optimized_cv, changes_explanation)."""
    marker = "---CHANGES---"
    if marker in text:
        parts = text.split(marker, 1)
        return parts[0].strip(), parts[1].strip()
    # Fallback: try heading-based split
    for heading in ["## Modifications apportées", "## Changes Made", "## Cambios realizados"]:
        if heading in text:
            parts = text.split(heading, 1)
            return parts[0].strip(), heading + parts[1].strip()
    return text.strip(), "_L'explication des changements n'a pas pu être extraite séparément._"


def _build_zip(cv_bytes: bytes, cl_bytes: bytes) -> bytes:
    """Package CV + cover letter into a single ZIP."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("CV_optimise.docx", cv_bytes)
        zf.writestr("Lettre_de_motivation.docx", cl_bytes)
    buf.seek(0)
    return buf.getvalue()


# ─── Sidebar ──────────────────────────────────────────────────────────────────

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
    load_dotenv()  # Charge le fichier .env si présent (usage local)

    # Try each provider in order of preference (free first)
    candidates = [
        ("GOOGLE_API_KEY",    "Google (Gemini)",    "gemini-1.5-flash"),
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


# ─── Main layout ──────────────────────────────────────────────────────────────

st.title("📄 CV Optimizer AI")
st.markdown("*CV + fiche de poste → CV ATS-optimisé, lettre de motivation, analyse détaillée.*")

if not _api_key:
    st.error(
        "⚠️ Aucune clé API configurée. "
        "Ajoute `GOOGLE_API_KEY`, `GROQ_API_KEY` ou `ANTHROPIC_API_KEY` "
        "dans les secrets Streamlit (Settings → Secrets) ou dans un fichier `.env`."
    )

tab_input, tab_analysis, tab_output, tab_refine = st.tabs([
    "📤 Entrée",
    "🔍 Analyse du CV",
    "✨ Sortie optimisée",
    "💬 Affiner avec l'IA",
])


# ─── TAB 1 : Input ────────────────────────────────────────────────────────────

with tab_input:
    st.subheader("Votre CV")
    cv_file = st.file_uploader(
        "Uploader votre CV",
        type=["pdf", "docx", "txt"],
        key="cv_upload",
    )
    cv_text_paste = st.text_area(
        "Ou coller votre CV ici",
        height=180,
        placeholder="Jean Dupont\njean@email.com | LinkedIn\n\nEXPÉRIENCE\n...",
    )

    st.divider()

    st.subheader("Fiche de poste")
    job_file = st.file_uploader(
        "Uploader la fiche (optionnel)",
        type=["pdf", "docx", "txt"],
        key="job_upload",
    )
    job_text_paste = st.text_area(
        "Ou coller la fiche de poste ici",
        height=180,
        placeholder="Titre du poste : ...\nMissions : ...\nProfil recherché : ...",
    )

    st.divider()

    # ── Langue de sortie (prominent, always visible) ──────────────────────────
    st.subheader("🌐 Langue du CV et de la lettre produits")
    st.caption("Peu importe la langue du CV en entrée, les documents générés seront dans cette langue.")
    output_language = st.selectbox(
        "Langue de sortie",
        ["Français", "English", "Español", "Deutsch", "Italiano"],
        label_visibility="collapsed",
    )
    st.session_state.language = output_language

    # ── Privacy option ────────────────────────────────────────────────────────
    st.divider()
    anonymize_data = st.toggle(
        "🔒 Anonymiser mes données personnelles avant envoi à l'IA",
        value=True,
        help=(
            "Remplace nom, email, téléphone, LinkedIn, adresse par des placeholders "
            "avant d'envoyer à l'API. Le résultat contiendra ces placeholders — "
            "complète-les avant d'envoyer ta candidature."
        ),
    )
    debug_mode = st.toggle(
        "🐛 Mode debug — afficher le texte envoyé à l'IA",
        value=False,
        help="Affiche le contenu exact transmis à l'API, après anonymisation. Utile pour vérifier ce qui part.",
    )

    st.divider()
    generate_btn = st.button("🚀 Générer", type="primary", use_container_width=True)

    if generate_btn:
        # ── Validation
        errors = []
        if not api_key:
            errors.append("Clé API non configurée. Contacte l'administrateur de l'app.")

        cv_content = ""
        if cv_file:
            try:
                cv_content = parse_document(cv_file)
            except Exception as e:
                errors.append(f"Erreur lecture CV : {e}")
        elif cv_text_paste.strip():
            cv_content = cv_text_paste.strip()
        else:
            errors.append("CV manquant (fichier ou texte collé).")

        job_content = ""
        if job_file:
            try:
                job_content = parse_document(job_file)
            except Exception as e:
                errors.append(f"Erreur lecture fiche de poste : {e}")
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
                with st.expander(f"🔒 {len(anon_result.summary)} élément(s) anonymisé(s) — clique pour voir"):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.markdown("**Remplacé par**")
                        for placeholder in anon_result.replacements:
                            st.code(placeholder, language=None)
                    with col_b:
                        st.markdown("**Valeur originale**")
                        for original in anon_result.replacements.values():
                            st.code(original, language=None)
                    st.caption(
                        "Ces placeholders apparaîtront dans les documents générés. "
                        "Remplace-les par tes vraies informations avant envoi."
                    )
            else:
                st.info("🔒 Aucune donnée personnelle détectée automatiquement.")

        # ── Debug mode ────────────────────────────────────────────────────────
        if debug_mode:
            with st.expander("🐛 Debug — texte exact envoyé à l'IA", expanded=True):
                st.markdown("**CV (après anonymisation) :**")
                st.text_area("CV envoyé", value=cv_for_llm, height=200, disabled=True, key="debug_cv")
                st.markdown("**Fiche de poste :**")
                st.text_area("Job envoyé", value=job_content, height=150, disabled=True, key="debug_job")
                st.caption(f"Provider : {_provider} | Modèle : {_model}")

        # ── Init LLM
        try:
            llm = LLMClient(provider=_provider, api_key=_api_key, model=_model)
        except Exception as e:
            st.error(f"Initialisation LLM échouée : {e}")
            st.stop()

        st.session_state.llm = llm
        st.session_state.cv_content = cv_content
        st.session_state.job_content = job_content
        st.session_state.messages = []  # Reset chat on new generation

        prompt_builder = PromptBuilder(language=output_language)

        # ── Generate
        progress = st.progress(0, text="Démarrage...")

        try:
            progress.progress(10, text="Analyse du CV en cours...")
            st.session_state.analysis = llm.generate(
                system="Tu es un expert RH et spécialiste ATS avec 15 ans d'expérience.",
                user=prompt_builder.analysis(cv_for_llm, job_content),
                max_tokens=3000,
            )

            progress.progress(45, text="Optimisation ATS du CV...")
            raw_opt = llm.generate(
                system="Tu es un expert rédacteur de CV et spécialiste ATS.",
                user=prompt_builder.optimize_cv(cv_for_llm, job_content),
                max_tokens=4000,
            )
            st.session_state.optimized_cv, st.session_state.changes = _split_cv_and_changes(raw_opt)

            progress.progress(80, text="Rédaction de la lettre de motivation...")
            st.session_state.cover_letter = llm.generate(
                system="Tu es expert en rédaction de lettres de motivation percutantes.",
                user=prompt_builder.cover_letter(cv_for_llm, job_content),
                max_tokens=2000,
            )

            progress.progress(100, text="Terminé !")
            st.session_state.generated = True
            st.success("✅ Génération complète ! Consulte les onglets **Analyse** et **Sortie optimisée**.")

        except Exception as e:
            progress.empty()
            st.error(f"Erreur lors de la génération : {e}")
            st.info("Vérifie ta clé API et ta connexion internet.")


# ─── TAB 2 : Analysis ─────────────────────────────────────────────────────────

with tab_analysis:
    if st.session_state.analysis:
        st.markdown(st.session_state.analysis)
    else:
        st.info("Lance la génération dans l'onglet **Entrée** pour voir l'analyse.")


# ─── TAB 3 : Output ───────────────────────────────────────────────────────────

with tab_output:
    if st.session_state.optimized_cv:
        exporter = DOCXExporter()

        # ── CV optimisé
        st.subheader("✨ CV optimisé (ATS)")
        st.markdown(st.session_state.optimized_cv)

        try:
            cv_bytes = exporter.cv_to_docx(st.session_state.optimized_cv)
            st.download_button(
                "📥 Télécharger le CV (.docx)",
                data=cv_bytes,
                file_name="CV_optimise.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        except Exception as e:
            st.warning(f"Export DOCX indisponible : {e}")

        st.divider()

        # ── Changements
        st.subheader("🔄 Modifications & explications")
        st.markdown(
            f'<div class="result-box">{st.session_state.changes}</div>',
            unsafe_allow_html=True,
        )

        st.divider()

        # ── Cover letter
        st.subheader("📝 Lettre de motivation")
        st.markdown(st.session_state.cover_letter)

        try:
            cl_bytes = exporter.cover_letter_to_docx(st.session_state.cover_letter)
            col_dl1, col_dl2 = st.columns(2)
            with col_dl1:
                st.download_button(
                    "📥 Télécharger la lettre (.docx)",
                    data=cl_bytes,
                    file_name="Lettre_de_motivation.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            with col_dl2:
                zip_bytes = _build_zip(cv_bytes, cl_bytes)
                st.download_button(
                    "📦 Tout télécharger (.zip)",
                    data=zip_bytes,
                    file_name="candidature_complete.zip",
                    mime="application/zip",
                )
        except Exception as e:
            st.warning(f"Export DOCX indisponible : {e}")

    else:
        st.info("Lance la génération dans l'onglet **Entrée** pour voir les résultats.")


# ─── TAB 4 : AI Refinement chat ───────────────────────────────────────────────

with tab_refine:
    st.subheader("💬 Affiner avec l'IA")
    st.markdown(
        "Donne des instructions précises pour modifier le CV ou la lettre. "
        "Exemples : *\"Rends le ton plus formel\"*, *\"Ajoute des mots-clés liés au management\"*, "
        "*\"Raccourcis la lettre de 20%\"*."
    )

    if not st.session_state.generated:
        st.info("Lance d'abord la génération dans l'onglet **Entrée**.")
    else:
        # Display chat history
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if user_instruction := st.chat_input("Ton instruction..."):
            st.session_state.messages.append({"role": "user", "content": user_instruction})
            with st.chat_message("user"):
                st.markdown(user_instruction)

            with st.chat_message("assistant"):
                with st.spinner("Traitement..."):
                    context = (
                        f"CV optimisé actuel :\n{st.session_state.optimized_cv}\n\n"
                        f"Lettre de motivation actuelle :\n{st.session_state.cover_letter}"
                    )
                    pb = PromptBuilder(language=st.session_state.language)
                    try:
                        response = st.session_state.llm.generate(
                            system="Tu es un expert rédacteur CV. Applique les instructions de l'utilisateur avec précision.",
                            user=pb.refine(context, user_instruction),
                            max_tokens=3000,
                        )
                        st.markdown(response)
                        st.session_state.messages.append({"role": "assistant", "content": response})

                        # Offer download of refined version
                        exporter = DOCXExporter()
                        try:
                            refined_bytes = exporter.cv_to_docx(response)
                            st.download_button(
                                "📥 Télécharger cette version (.docx)",
                                data=refined_bytes,
                                file_name="CV_affine.docx",
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                key=f"dl_refined_{len(st.session_state.messages)}",
                            )
                        except Exception:
                            pass

                    except Exception as e:
                        error_msg = f"Erreur : {e}"
                        st.error(error_msg)
                        st.session_state.messages.append({"role": "assistant", "content": error_msg})
