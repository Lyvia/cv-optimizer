"""
i18n.py — Flat key -> string lookup driving the bilingual (EN/FR) UI.
Long-form help text lives separately in guide_content.py; this module
covers short UI strings (labels, buttons, messages).
"""

from typing import Literal

Lang = Literal["en", "fr"]

UI: dict[Lang, dict[str, str]] = {
    "en": {
        # ── Top of page ──────────────────────────────────────────────────
        "app_tagline": "CV + job description → ATS-optimized CV, cover letter, detailed analysis.",
        "output_lang_subheader": "🌐 Output language",
        "output_lang_caption": (
            "Controls the language of the generated CV, cover letter, and analysis — "
            "independent of the language of the CV or job description you provide below."
        ),
        "disclaimer_banner": (
            "⚠️ **Disclaimer:** AI-generated content can contain mistakes or inaccuracies. "
            "You are responsible for reviewing and validating the final CV and cover letter "
            "before sending them to an employer."
        ),
        "no_api_key_error": (
            "⚠️ No API key configured. "
            "Add `GOOGLE_API_KEY`, `GROQ_API_KEY`, or `ANTHROPIC_API_KEY` "
            "to Streamlit secrets (Settings → Secrets) or to a `.env` file."
        ),

        # ── Tabs ─────────────────────────────────────────────────────────
        "tab_guide": "📘 How to Use",
        "tab_input": "📤 Input",
        "tab_analysis": "🔍 CV Analysis",
        "tab_results": "✨ Results",

        # ── Input tab ────────────────────────────────────────────────────
        "input_cv_subheader": "Your CV",
        "input_cv_upload_label": "Upload your CV",
        "input_cv_paste_label": "Or paste your CV here",
        "input_cv_placeholder": "John Doe\njohn@email.com | LinkedIn\n\nEXPERIENCE\n...",
        "input_job_subheader": "Job description",
        "input_job_caption": "Optional — without it, you'll still get a general ATS analysis and a generally optimized CV.",
        "input_job_upload_label": "Upload the job description (optional)",
        "input_job_paste_label": "Or paste the job description here",
        "input_job_placeholder": "Job title: ...\nResponsibilities: ...\nRequired profile: ...",
        "input_anonymize_toggle": "🔒 Anonymize my personal data before sending it to the AI",
        "input_anonymize_help": (
            "Replaces name, email, phone, LinkedIn, and address with placeholders "
            "before sending to the API. The result will contain these placeholders — "
            "fill them in before submitting your application."
        ),
        "input_debug_toggle": "🐛 Debug mode — show the text sent to the AI",
        "input_debug_help": "Shows the exact content sent to the API, after anonymization. Useful to verify what's being sent.",
        "input_generate_btn": "🚀 Generate",
        "quota_remaining_caption": "AI generations remaining this session: {remaining}/{max}",
        "quota_exhausted_error": (
            "You've reached the {max} AI generations limit for this session. "
            "Refresh the page to start a new session."
        ),
        "input_error_no_api_key": "API key not configured. Contact the app administrator.",
        "input_error_cv_missing": "Missing CV (file or pasted text).",
        "input_error_cv_read": "Error reading CV: {error}",
        "input_error_job_read": "Error reading job description: {error}",
        "input_anon_expander_title": "🔒 {count} element(s) anonymized — click to view",
        "input_anon_replaced_with": "**Replaced with**",
        "input_anon_original_value": "**Original value**",
        "input_anon_caption": (
            "These placeholders will appear in the generated documents. "
            "Replace them with your real information before submitting."
        ),
        "input_anon_none_detected": "🔒 No personal data automatically detected.",
        "input_debug_expander_title": "🐛 Debug — exact text sent to the AI",
        "input_debug_cv_label": "**CV (after anonymization):**",
        "input_debug_job_label": "**Job description:**",
        "input_debug_provider_model": "Provider: {provider} | Model: {model}",
        "input_llm_init_failed": "LLM initialization failed: {error}",
        "progress_starting": "Starting...",
        "progress_analyzing": "Analyzing the CV...",
        "progress_optimizing": "Optimizing the CV for ATS...",
        "progress_writing_letter": "Writing the cover letter...",
        "progress_done": "Done!",
        "generation_success": "✅ Generation complete! Check the **CV Analysis** and **Results** tabs.",
        "generation_error": "Error during generation: {error}",
        "generation_error_hint": "Check your API key and internet connection.",

        # ── Analysis tab ─────────────────────────────────────────────────
        "analysis_empty_hint": "Run the generation in the **Input** tab to see the analysis.",

        # ── Results tab ──────────────────────────────────────────────────
        "results_empty_hint": "Run the generation in the **Input** tab to see the results.",
        "results_style_subheader": "🎨 Visual style",
        "results_style_caption": (
            "Choose how your CV and cover letter will look. This is a free, local preview — "
            "no AI tokens are used, change anything as much as you like."
        ),
        "style_mode_label": "Style mode",
        "style_mode_template": "Template",
        "style_mode_advanced": "Advanced (custom colors & font)",
        "style_template_label": "Choose a template",
        "style_color_text_label": "Main text color",
        "style_color_heading_label": "Headings color",
        "style_font_label": "Font",
        "results_style_live_note": "The CV and Cover Letter tabs below show this style applied live.",
        "results_subtab_cv": "CV",
        "results_subtab_letter": "Cover Letter",
        "results_cv_heading": "✨ Optimized CV (ATS)",
        "dl_cv_docx": "📥 Download CV (.docx)",
        "dl_cv_pdf": "📥 Download CV (.pdf)",
        "export_unavailable": "Export unavailable: {error}",
        "results_changes_heading": "🔄 Changes & explanations",
        "refine_cv_expander_title": "🔄 Refine this CV with AI",
        "refine_chat_examples": (
            "Examples: \"Make the tone more formal\", \"Add keywords related to project management\", "
            "\"Shorten the letter by 20%\"."
        ),
        "refine_chat_placeholder": "Your instruction...",
        "refine_quota_placeholder": "Generation limit reached for this session",
        "refine_processing": "Processing...",
        "refine_error": "Error: {error}",
        "diff_no_changes": "No changes detected.",
        "diff_accept_btn": "✓ Accept",
        "diff_ignore_btn": "✗ Ignore",
        "diff_accept_all_btn": "✓ Accept all",
        "diff_ignore_all_btn": "✗ Ignore all",
        "diff_irreversible_warning": (
            "⚠️ Once accepted, this cannot be undone. The accepted version becomes your new reference."
        ),
        "results_letter_heading": "📝 Cover letter",
        "dl_letter_docx": "📥 Download letter (.docx)",
        "dl_letter_pdf": "📥 Download letter (.pdf)",
        "refine_letter_expander_title": "🔄 Refine this cover letter with AI",
        "letter_refined_heading": "**Refined version**",
        "letter_replace_btn": "✓ Replace cover letter",
        "dl_all_zip": "📦 Download everything (.zip)",
    },
    "fr": {
        # ── Top of page ──────────────────────────────────────────────────
        "app_tagline": "CV + fiche de poste → CV optimisé ATS, lettre de motivation, analyse détaillée.",
        "output_lang_subheader": "🌐 Langue de sortie",
        "output_lang_caption": (
            "Détermine la langue du CV, de la lettre de motivation et de l'analyse générés — "
            "indépendamment de la langue du CV ou de la fiche de poste fournis ci-dessous."
        ),
        "disclaimer_banner": (
            "⚠️ **Avertissement :** le contenu généré par l'IA peut contenir des erreurs ou des "
            "imprécisions. Vous êtes responsable de relire et de valider le CV et la lettre de "
            "motivation finaux avant de les envoyer à un employeur."
        ),
        "no_api_key_error": (
            "⚠️ Aucune clé API configurée. "
            "Ajoutez `GOOGLE_API_KEY`, `GROQ_API_KEY` ou `ANTHROPIC_API_KEY` "
            "dans les secrets Streamlit (Settings → Secrets) ou dans un fichier `.env`."
        ),

        # ── Tabs ─────────────────────────────────────────────────────────
        "tab_guide": "📘 Comment utiliser",
        "tab_input": "📤 Entrée",
        "tab_analysis": "🔍 Analyse du CV",
        "tab_results": "✨ Résultats",

        # ── Input tab ────────────────────────────────────────────────────
        "input_cv_subheader": "Votre CV",
        "input_cv_upload_label": "Importer votre CV",
        "input_cv_paste_label": "Ou collez votre CV ici",
        "input_cv_placeholder": "Jean Dupont\njean@email.com | LinkedIn\n\nEXPÉRIENCE\n...",
        "input_job_subheader": "Fiche de poste",
        "input_job_caption": "Optionnel — sans elle, vous obtenez quand même une analyse ATS générale et un CV optimisé de façon générale.",
        "input_job_upload_label": "Importer la fiche de poste (optionnel)",
        "input_job_paste_label": "Ou collez la fiche de poste ici",
        "input_job_placeholder": "Titre du poste : ...\nMissions : ...\nProfil recherché : ...",
        "input_anonymize_toggle": "🔒 Anonymiser mes données personnelles avant envoi à l'IA",
        "input_anonymize_help": (
            "Remplace nom, email, téléphone, LinkedIn et adresse par des placeholders "
            "avant l'envoi à l'API. Le résultat contiendra ces placeholders — "
            "complétez-les avant d'envoyer votre candidature."
        ),
        "input_debug_toggle": "🐛 Mode debug — afficher le texte envoyé à l'IA",
        "input_debug_help": "Affiche le contenu exact transmis à l'API, après anonymisation. Utile pour vérifier ce qui part.",
        "input_generate_btn": "🚀 Générer",
        "quota_remaining_caption": "Générations IA restantes pour cette session : {remaining}/{max}",
        "quota_exhausted_error": (
            "Vous avez atteint la limite de {max} générations IA pour cette session. "
            "Rechargez la page pour démarrer une nouvelle session."
        ),
        "input_error_no_api_key": "Clé API non configurée. Contactez l'administrateur de l'application.",
        "input_error_cv_missing": "CV manquant (fichier ou texte collé).",
        "input_error_cv_read": "Erreur de lecture du CV : {error}",
        "input_error_job_read": "Erreur de lecture de la fiche de poste : {error}",
        "input_anon_expander_title": "🔒 {count} élément(s) anonymisé(s) — cliquez pour voir",
        "input_anon_replaced_with": "**Remplacé par**",
        "input_anon_original_value": "**Valeur d'origine**",
        "input_anon_caption": (
            "Ces placeholders apparaîtront dans les documents générés. "
            "Remplacez-les par vos vraies informations avant l'envoi."
        ),
        "input_anon_none_detected": "🔒 Aucune donnée personnelle détectée automatiquement.",
        "input_debug_expander_title": "🐛 Debug — texte exact envoyé à l'IA",
        "input_debug_cv_label": "**CV (après anonymisation) :**",
        "input_debug_job_label": "**Fiche de poste :**",
        "input_debug_provider_model": "Fournisseur : {provider} | Modèle : {model}",
        "input_llm_init_failed": "Échec de l'initialisation du LLM : {error}",
        "progress_starting": "Démarrage...",
        "progress_analyzing": "Analyse du CV en cours...",
        "progress_optimizing": "Optimisation ATS du CV...",
        "progress_writing_letter": "Rédaction de la lettre de motivation...",
        "progress_done": "Terminé !",
        "generation_success": "✅ Génération terminée ! Consultez les onglets **Analyse du CV** et **Résultats**.",
        "generation_error": "Erreur pendant la génération : {error}",
        "generation_error_hint": "Vérifiez votre clé API et votre connexion internet.",

        # ── Analysis tab ─────────────────────────────────────────────────
        "analysis_empty_hint": "Lancez la génération dans l'onglet **Entrée** pour voir l'analyse.",

        # ── Results tab ──────────────────────────────────────────────────
        "results_empty_hint": "Lancez la génération dans l'onglet **Entrée** pour voir les résultats.",
        "results_style_subheader": "🎨 Style visuel",
        "results_style_caption": (
            "Choisissez l'apparence de votre CV et de votre lettre. Cet aperçu est gratuit et local — "
            "aucun token IA n'est utilisé, vous pouvez tout essayer librement."
        ),
        "style_mode_label": "Mode de style",
        "style_mode_template": "Modèle",
        "style_mode_advanced": "Avancé (couleurs et police personnalisées)",
        "style_template_label": "Choisissez un modèle",
        "style_color_text_label": "Couleur du texte principal",
        "style_color_heading_label": "Couleur des titres",
        "style_font_label": "Police",
        "results_style_live_note": "Les onglets CV et Lettre de motivation ci-dessous appliquent ce style en direct.",
        "results_subtab_cv": "CV",
        "results_subtab_letter": "Lettre de motivation",
        "results_cv_heading": "✨ CV optimisé (ATS)",
        "dl_cv_docx": "📥 Télécharger le CV (.docx)",
        "dl_cv_pdf": "📥 Télécharger le CV (.pdf)",
        "export_unavailable": "Export indisponible : {error}",
        "results_changes_heading": "🔄 Modifications & explications",
        "refine_cv_expander_title": "🔄 Affiner ce CV avec l'IA",
        "refine_chat_examples": (
            "Exemples : « Rends le ton plus formel », « Ajoute des mots-clés liés à la gestion de projet », "
            "« Raccourcis la lettre de 20% »."
        ),
        "refine_chat_placeholder": "Votre instruction...",
        "refine_quota_placeholder": "Limite de génération atteinte pour cette session",
        "refine_processing": "Traitement en cours...",
        "refine_error": "Erreur : {error}",
        "diff_no_changes": "Aucun changement détecté.",
        "diff_accept_btn": "✓ Accepter",
        "diff_ignore_btn": "✗ Ignorer",
        "diff_accept_all_btn": "✓ Tout accepter",
        "diff_ignore_all_btn": "✗ Tout ignorer",
        "diff_irreversible_warning": (
            "⚠️ Une fois accepté, ceci est irréversible. La version acceptée devient votre nouvelle référence."
        ),
        "results_letter_heading": "📝 Lettre de motivation",
        "dl_letter_docx": "📥 Télécharger la lettre (.docx)",
        "dl_letter_pdf": "📥 Télécharger la lettre (.pdf)",
        "refine_letter_expander_title": "🔄 Affiner cette lettre avec l'IA",
        "letter_refined_heading": "**Version affinée**",
        "letter_replace_btn": "✓ Remplacer la lettre de motivation",
        "dl_all_zip": "📦 Tout télécharger (.zip)",
    },
}


def t(key: str, lang: str) -> str:
    """Look up a UI string by key for the given language, falling back to English."""
    table = UI.get(lang, UI["en"])
    return table.get(key, UI["en"].get(key, key))
