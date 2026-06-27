"""
prompts.py — Prompt templates for CV analysis, optimization, cover letter, refinement.
All prompts enforce a specific output language passed at instantiation.
"""


class PromptBuilder:
    """
    Build task-specific prompts with language control.

    Args:
        language: Output language (e.g., "Français", "English", "Español")
    """

    def __init__(self, language: str = "Français"):
        self.language = language
        self._lang_instruction = (
            f"IMPORTANT : Réponds UNIQUEMENT en {language}. "
            f"Tout le contenu produit doit être rédigé en {language}."
        )

    # ─── Analysis ─────────────────────────────────────────────────────────────

    def analysis(self, cv: str, job: str) -> str:
        """
        Prompt: analyze the original CV against the job description.
        Output: structured markdown report.
        """
        if job.strip():
            job_block = f"=== FICHE DE POSTE ===\n{job}"
            match_section = """## 1. Score de correspondance (0-100)
Donne un score chiffré et justifie-le en 3 phrases maximum. Sois honnête, même si le score est faible."""
        else:
            job_block = "=== FICHE DE POSTE ===\nAucune fiche de poste fournie — réalise une analyse générale du CV."
            match_section = """## 1. Qualité globale du CV (0-100)
Évalue la qualité globale du CV (clarté, structure, impact) en l'absence de fiche de poste. Justifie en 3 phrases."""

        return f"""{self._lang_instruction}

Analyse ce CV avec un regard d'expert RH et spécialiste ATS.

=== CV ORIGINAL ===
{cv}

{job_block}

Produis une analyse structurée avec exactement ces sections :

{match_section}

## 2. Points forts du CV
Liste 3 à 5 éléments du CV qui sont bien alignés avec le poste. Une ligne par point.

## 3. Lacunes critiques
Liste les compétences, mots-clés ou expériences manquants que les systèmes ATS et les recruteurs vont chercher. Distingue :
- **Mots-clés absents** (termes du poste non présents dans le CV)
- **Compétences manquantes** (réelles lacunes de profil)
- **Expériences non mises en valeur** (probablement présentes mais mal formulées)

## 4. Problèmes ATS techniques
Identifie les problèmes de format ou de structure qui pénalisent le parsing ATS :
- Intitulés de sections non standard
- Informations enfouies dans des tableaux/colonnes (invisibles pour ATS)
- Manque de mots-clés exacts du poste
- Acronymes sans développement (ou inversement)
- Autres

## 5. Top 5 des actions prioritaires
Classe 5 actions par ordre d'impact décroissant. Formule chacune en une phrase concrète et actionnable.

Sois direct. Ne minimise pas les problèmes pour ménager le candidat."""

    # ─── CV Optimization ──────────────────────────────────────────────────────

    def optimize_cv(self, cv: str, job: str) -> str:
        """
        Prompt: rewrite the CV to be ATS-optimized for the specific job (or generally if no job).
        Output: optimized CV in markdown + separator + changes explanation.
        """
        if job.strip():
            job_block = f"=== FICHE DE POSTE ===\n{job}"
            task_desc = "parfaitement optimisé ATS pour ce poste spécifique"
            keyword_rule = "- Intègre naturellement les mots-clés exacts de la fiche de poste (pas du keyword stuffing)"
            relevance_rule = "{relevance_rule}"
        else:
            job_block = "=== FICHE DE POSTE ===\nAucune fiche fournie — optimise pour un profil ATS généraliste."
            task_desc = "optimisé ATS de façon générale, sans poste cible spécifique"
            keyword_rule = "- Utilise des mots-clés génériques forts pour le secteur/métier identifié dans le CV"
            relevance_rule = "- Mets en avant les compétences les plus transférables"

        return f"""{self._lang_instruction}

Réécris ce CV pour qu'il soit {task_desc}.

=== CV ORIGINAL ===
{cv}

{job_block}

=== RÈGLES POUR LE CV OPTIMISÉ ===

**Contenu :**
{keyword_rule}
- Quantifie TOUTES les réalisations possibles — si la donnée est inconnue, mets [CHIFFRE À COMPLÉTER]
- Commence chaque bullet point par un verbe d'action fort
{relevance_rule}

**Structure ATS-friendly :**
- En-tête : Nom | Contact | LinkedIn | Ville
- Sections dans cet ordre : Résumé professionnel > Expérience > Compétences > Formation > (autres si pertinent)
- Intitulés de section standard : "Expérience professionnelle", "Compétences", "Formation"
- PAS de tableaux, colonnes, headers/footers, images

**Format de sortie :**
Écris le CV complet en Markdown propre.
Puis place exactement cette ligne séparatrice :
---CHANGES---
Puis écris la section ci-dessous.

=== SECTION APRÈS LE SÉPARATEUR ===

## Modifications apportées et pourquoi

Explique chaque changement significatif :
1. **Ce qui a changé** : décris la modification précise
2. **Pourquoi** : impact sur l'ATS ou l'impression du recruteur
3. **Action requise du candidat** : signale avec [ACTION REQUISE] tout élément à vérifier ou compléter

Sois exhaustif mais concis. Cette section est destinée au candidat pour comprendre la logique."""

    # ─── Cover Letter ─────────────────────────────────────────────────────────

    def cover_letter(self, cv: str, job: str) -> str:
        """
        Prompt: write a tailored cover letter. If no job description, write a general one.
        Output: the letter only, in markdown.
        """
        if not job.strip():
            job_note = "Aucune fiche de poste fournie. Rédige une lettre de motivation générale mettant en valeur le profil du candidat, sans cibler un poste spécifique. Utilise [NOM DE L'ENTREPRISE] et [POSTE VISÉ] comme placeholders."
        else:
            job_note = ""

        return f"""{self._lang_instruction}

Rédige une lettre de motivation percutante pour cette candidature.
{job_note}

=== CV DU CANDIDAT ===
{cv}

=== FICHE DE POSTE ===
{job}

=== RÈGLES ===

**Structure (4 paragraphes max) :**
1. **Accroche** : phrase d'ouverture originale qui n'est pas "Je me permets de vous adresser ma candidature". Mentionne le poste exact.
2. **Corps (1-2 paragraphes)** : connecte 2-3 expériences spécifiques du CV aux exigences concrètes du poste. Utilise des faits et chiffres.
3. **Valeur ajoutée** : ce que le candidat apporte de différenciant par rapport à un profil standard.
4. **Conclusion** : call-to-action clair, formule de politesse professionnelle.

**Interdits :**
- "Je suis quelqu'un de dynamique et motivé"
- "Travail en équipe" comme qualité principale
- Répéter le CV mot pour mot
- Dépasser 350 mots

**Placeholders à utiliser :**
- [NOM DU CANDIDAT] pour le nom
- [NOM DE L'ENTREPRISE] pour l'entreprise
- [DATE] pour la date

Écris uniquement la lettre, sans titre ni explication autour."""

    # ─── Refinement ───────────────────────────────────────────────────────────

    def refine(self, current_content: str, instruction: str) -> str:
        """
        Prompt: apply user's refinement instruction to current documents.
        Output: updated document(s) with change summary.
        """
        return f"""{self._lang_instruction}

Un candidat veut affiner ses documents de candidature. Applique son instruction avec précision.

=== DOCUMENTS ACTUELS ===
{current_content}

=== INSTRUCTION DE L'UTILISATEUR ===
{instruction}

=== CONSIGNES ===
- Applique l'instruction demandée
- Si l'instruction est ambiguë, choisis l'interprétation la plus raisonnable et signale-le
- Retourne le document modifié en entier (pas uniquement les parties changées)
- Après le document, ajoute une note courte : "**Modifications effectuées :** [liste des changements]"

Ne demande pas de confirmation. Agis directement."""
