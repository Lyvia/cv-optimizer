"""
prompts.py — Prompt templates for CV analysis, optimization, cover letter, refinement.
All prompts enforce a specific output language passed at instantiation.
The job description is optional: when absent, prompts fall back to a
general-purpose version of the task instead of a job-specific one.
"""


class PromptBuilder:
    """
    Build task-specific prompts with language control.

    Args:
        language: Output language (e.g., "English", "Français", "Español")
    """

    def __init__(self, language: str = "English"):
        self.language = language
        self._lang_instruction = (
            f"IMPORTANT: Respond ONLY in {language}. "
            f"All produced content must be written in {language}."
        )

    # ─── Analysis ─────────────────────────────────────────────────────────────

    def analysis(self, cv: str, job: str) -> str:
        """
        Prompt: analyze the original CV, against the job description if provided.
        Output: structured markdown report.
        """
        if job.strip():
            job_block = f"=== JOB DESCRIPTION ===\n{job}"
            match_section = """## 1. Match score (0-100)
Give a numeric score and justify it in 3 sentences max. Be honest, even if the score is low."""
        else:
            job_block = "=== JOB DESCRIPTION ===\nNo job description provided — perform a general analysis of the CV."
            match_section = """## 1. Overall CV quality (0-100)
Rate the overall quality of the CV (clarity, structure, impact) in the absence of a job description. Justify in 3 sentences."""

        return f"""{self._lang_instruction}

Analyze this CV as an expert HR recruiter and ATS specialist.

=== ORIGINAL CV ===
{cv}

{job_block}

Produce a structured analysis with exactly these sections:

{match_section}

## 2. CV strengths
List 3 to 5 elements of the CV that are well aligned with the job. One line per point.

## 3. Critical gaps
List the missing skills, keywords, or experience that ATS systems and recruiters will look for. Distinguish:
- **Missing keywords** (terms from the job posting not present in the CV)
- **Missing skills** (genuine profile gaps)
- **Underrepresented experience** (probably present but poorly phrased)

## 4. Technical ATS issues
Identify format or structure issues that hurt ATS parsing:
- Non-standard section headings
- Information buried in tables/columns (invisible to ATS)
- Missing exact keywords from the job posting
- Undefined acronyms (or the reverse)
- Other issues

## 5. Top 5 priority actions
Rank 5 actions by decreasing impact. Phrase each as a concrete, actionable sentence.

Be direct. Do not soften the issues to spare the candidate."""

    # ─── CV Optimization ──────────────────────────────────────────────────────

    def optimize_cv(self, cv: str, job: str) -> str:
        """
        Prompt: rewrite the CV to be ATS-optimized for the specific job (or generally if no job).
        Output: optimized CV in markdown + separator + changes explanation.
        """
        if job.strip():
            job_block = f"=== JOB DESCRIPTION ===\n{job}"
            task_desc = "perfectly ATS-optimized for this specific job"
            keyword_rule = "- Naturally weave in the exact keywords from the job description (not keyword stuffing)"
            relevance_rule = "- Remove information irrelevant to THIS job"
        else:
            job_block = "=== JOB DESCRIPTION ===\nNo job description provided — optimize for a general-purpose ATS profile."
            task_desc = "ATS-optimized in general, with no specific target job"
            keyword_rule = "- Use strong, generic keywords for the industry/role identified in the CV"
            relevance_rule = "- Highlight the most transferable skills"

        cv_word_count = len(cv.split())
        length_rule = (
            f"- Keep the total length close to the original CV (~{cv_word_count} words) — "
            "it must fit on the same number of A4 pages as the original. If quantifying "
            "achievements adds length, trim equally elsewhere; do not let the document grow."
        )

        return f"""{self._lang_instruction}

Rewrite this CV so it is {task_desc}.

=== ORIGINAL CV ===
{cv}

{job_block}

=== RULES FOR THE OPTIMIZED CV ===

**Content:**
{keyword_rule}
- Quantify EVERY achievement possible — if the figure is unknown, use [FIGURE TO COMPLETE]
- Start every bullet point with a strong action verb
{relevance_rule}
{length_rule}

**ATS-friendly structure:**
- Header: Name | Contact | LinkedIn | City
- Sections in this order: Professional Summary > Experience > Skills > Education > (others if relevant)
- Standard section headings: "Professional Experience", "Skills", "Education"
- NO tables, columns, headers/footers, images

**Output format:**
Write the complete CV in clean Markdown.
Then place exactly this separator line:
---CHANGES---
Then write the section below.

=== SECTION AFTER THE SEPARATOR ===

## Changes made and why

Explain each significant change:
1. **What changed**: describe the precise modification
2. **Why**: impact on ATS parsing or recruiter impression
3. **Action required from the candidate**: flag with [ACTION REQUIRED] anything to verify or complete

Be thorough but concise. This section is meant to help the candidate understand the reasoning."""

    # ─── Cover Letter ─────────────────────────────────────────────────────────

    def cover_letter(self, cv: str, job: str) -> str:
        """
        Prompt: write a tailored cover letter. If no job description, write a general one.
        Output: the letter only, in markdown.
        """
        if not job.strip():
            job_note = (
                "No job description provided. Write a general cover letter highlighting the "
                "candidate's profile, without targeting a specific job. Use [COMPANY NAME] and "
                "[TARGET POSITION] as placeholders."
            )
        else:
            job_note = ""

        return f"""{self._lang_instruction}

Write a compelling cover letter for this application.
{job_note}

=== CANDIDATE'S CV ===
{cv}

=== JOB DESCRIPTION ===
{job}

=== RULES ===

**Structure (4 paragraphs max):**
1. **Opening**: an original opening line that is not "I am writing to apply for...". Mention the exact job title.
2. **Body (1-2 paragraphs)**: connect 2-3 specific experiences from the CV to the job's concrete requirements. Use facts and figures.
3. **Added value**: what sets the candidate apart from a standard profile.
4. **Closing**: clear call-to-action, professional sign-off.

**Forbidden:**
- "I am a dynamic and motivated person"
- "Teamwork" as the main selling point
- Repeating the CV word for word
- Exceeding 350 words

**Placeholders to use:**
- [CANDIDATE NAME] for the name
- [COMPANY NAME] for the company
- [DATE] for the date

Write only the letter, with no title or surrounding explanation."""

    # ─── Refinement ───────────────────────────────────────────────────────────

    def refine(self, current_content: str, instruction: str) -> str:
        """
        Prompt: apply user's refinement instruction to current documents.
        Output: updated document(s) with change summary.
        """
        return f"""{self._lang_instruction}

A candidate wants to refine their application documents. Apply their instruction precisely.

=== CURRENT DOCUMENTS ===
{current_content}

=== USER INSTRUCTION ===
{instruction}

=== GUIDELINES ===
- Apply the requested instruction
- If the instruction is ambiguous, choose the most reasonable interpretation and flag it
- Return the modified document in full (not only the changed parts)
- Then place exactly this separator line:
---CHANGES---
- Then add a short note: "**Changes made:** [list of changes]"

Do not ask for confirmation. Act directly."""
