"""
anonymizer.py — Replace PII in CV text with placeholders before sending to LLM.

What is detected and replaced:
  - Full name (heuristic: first line that looks like a name)
  - Email addresses
  - Phone numbers (French and international formats)
  - LinkedIn profile URLs
  - GitHub profile URLs
  - Other personal URLs
  - French postal addresses (partial — city + zip code)

The LLM receives only placeholders. The output will contain those placeholders,
which is fine: the user sees the result and can fill them in before use.
"""

import re
from dataclasses import dataclass, field


@dataclass
class AnonymizationResult:
    anonymized_text: str
    replacements: dict           # placeholder -> original value
    summary: list[str]           # human-readable list of what was replaced


def anonymize(text: str) -> AnonymizationResult:
    """
    Detect and replace PII in the input text.

    Args:
        text: Raw CV or document text

    Returns:
        AnonymizationResult with anonymized text and replacement map
    """
    result = text
    replacements: dict[str, str] = {}
    summary: list[str] = []

    # ── 1. Email addresses ────────────────────────────────────────────────────
    emails = re.findall(
        r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b',
        result
    )
    for i, email in enumerate(dict.fromkeys(emails)):  # preserve order, deduplicate
        placeholder = f"[EMAIL_{i + 1}]"
        replacements[placeholder] = email
        result = result.replace(email, placeholder)
        summary.append(f"Email : {email[:3]}***@***")

    # ── 2. Phone numbers ──────────────────────────────────────────────────────
    # Matches: +33 6 12 34 56 78 / 06.12.34.56.78 / 0612345678 / +1 (555) 000-0000
    phone_pattern = re.compile(
        r'(?<!\d)'                          # not preceded by digit
        r'(\+?\d{1,3}[\s.\-]?)?'           # optional country code
        r'(\(?\d{1,4}\)?[\s.\-]?)'         # area code
        r'(\d{1,4}[\s.\-]?){2,6}'          # number groups
        r'(?!\d)'                           # not followed by digit
    )
    phones_found = []
    for m in phone_pattern.finditer(result):
        raw = m.group().strip()
        digits_only = re.sub(r'\D', '', raw)
        if 8 <= len(digits_only) <= 15:
            phones_found.append((m.start(), m.end(), raw))

    # Replace in reverse order to preserve positions
    for i, (start, end, raw) in enumerate(reversed(phones_found)):
        placeholder = f"[TÉLÉPHONE_{len(phones_found) - i}]"
        if raw not in replacements.values():
            replacements[placeholder] = raw
            result = result[:start] + placeholder + result[end:]
            summary.append(f"Téléphone : {raw[:4]}***")

    # ── 3. LinkedIn URLs ──────────────────────────────────────────────────────
    linkedin_urls = re.findall(
        r'(?:https?://)?(?:www\.)?linkedin\.com/in/[\w\-]+/?',
        result,
        re.IGNORECASE
    )
    for i, url in enumerate(dict.fromkeys(linkedin_urls)):
        placeholder = f"[LINKEDIN_{i + 1}]"
        replacements[placeholder] = url
        result = result.replace(url, placeholder)
        summary.append("URL LinkedIn")

    # ── 4. GitHub URLs ────────────────────────────────────────────────────────
    github_urls = re.findall(
        r'(?:https?://)?(?:www\.)?github\.com/[\w\-]+/?',
        result,
        re.IGNORECASE
    )
    for i, url in enumerate(dict.fromkeys(github_urls)):
        placeholder = f"[GITHUB_{i + 1}]"
        replacements[placeholder] = url
        result = result.replace(url, placeholder)
        summary.append("URL GitHub")

    # ── 5. Other personal URLs (portfolio, personal site) ────────────────────
    other_urls = re.findall(
        r'https?://(?!(?:www\.)?(?:linkedin|github)\.com)[\w\-\.]+\.[a-z]{2,}(?:/[\w\-\./\?=&#%]*)?',
        result,
        re.IGNORECASE
    )
    for i, url in enumerate(dict.fromkeys(other_urls)):
        placeholder = f"[URL_PERSO_{i + 1}]"
        replacements[placeholder] = url
        result = result.replace(url, placeholder)
        summary.append(f"URL personnelle")

    # ── 6. French postal codes + city ─────────────────────────────────────────
    postal = re.findall(r'\b\d{5}\b(?:\s+[A-ZÀ-Ÿ][a-zA-ZÀ-ÿ\-\s]{2,30})?', result)
    for i, addr in enumerate(dict.fromkeys(postal)):
        placeholder = f"[ADRESSE_{i + 1}]"
        replacements[placeholder] = addr
        result = result.replace(addr, placeholder)
        summary.append(f"Code postal/ville : {addr[:5]}***")

    # ── 7. Full name (heuristic) ──────────────────────────────────────────────
    # Looks at the first non-empty lines for a name-like pattern
    # (1-4 words, only letters/hyphens/apostrophes, no numbers)
    lines = [ln.strip() for ln in text.split('\n') if ln.strip()]
    for line in lines[:5]:  # only check first 5 non-empty lines
        words = line.split()
        is_name_like = (
            1 <= len(words) <= 4
            and all(re.match(r"^[A-Za-zÀ-ÿ'\-]+$", w) for w in words)
            and not any(w.lower() in _COMMON_CV_WORDS for w in words)
        )
        if is_name_like:
            placeholder = "[NOM COMPLET]"
            replacements[placeholder] = line
            result = result.replace(line, placeholder)
            summary.append(f"Nom : {line[:1]}***")
            break

    return AnonymizationResult(
        anonymized_text=result,
        replacements=replacements,
        summary=summary,
    )


# Words that look like names but are CV section headers
_COMMON_CV_WORDS = {
    "expérience", "experience", "formation", "education", "compétences",
    "skills", "profil", "profile", "résumé", "summary", "objectif",
    "objective", "references", "références", "langues", "languages",
    "certifications", "projets", "projects", "bénévolat", "volunteer",
    "cv", "curriculum", "vitae", "contact",
}
