"""
analysis_parser.py — Extract structured fields (score, strengths, gaps, ATS
issues, top actions) from the LLM's free-form analysis markdown.

This is a local, best-effort regex parser over the fixed section structure
that PromptBuilder.analysis() asks the LLM to produce (src/prompts.py):
"## 1. Match score (0-100)" / "## 2. CV strengths" / "## 3. Critical gaps" /
"## 4. Technical ATS issues" / "## 5. Top 5 priority actions". No LLM call
is involved here, and src/prompts.py is not touched — if the model's
heading wording drifts, fields degrade to empty/None rather than raising.
"""

import re
from dataclasses import dataclass, field


@dataclass
class ParsedAnalysis:
    score: int | None = None
    strengths: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    ats_issues: list[str] = field(default_factory=list)
    top_actions: list[str] = field(default_factory=list)


_SECTION_RE = re.compile(r"^(?:#{1,4}|\*{1,2})\s*(\d+)[.\):]?\s", re.MULTILINE)
_BULLET_RE = re.compile(r"^[ \t]*[-*]\s+(.*)$", re.MULTILINE)
_NUMBERED_RE = re.compile(r"^[ \t]*\d+[.)]\s+(.*)$", re.MULTILINE)
_SCORE_RE = re.compile(r"(\d{1,3})\s*/\s*100")
_SCORE_FALLBACK_RE = re.compile(r"(?:score|note)\D{0,6}(\d{1,3})", re.IGNORECASE)


def _split_sections(text: str) -> dict[int, str]:
    matches = list(_SECTION_RE.finditer(text))
    sections: dict[int, str] = {}
    for i, m in enumerate(matches):
        num = int(m.group(1))
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections[num] = text[start:end].strip()
    return sections


def _list_items(section_text: str) -> list[str]:
    """Bullets if present, else a numbered list, else empty."""
    items = [b.strip() for b in _BULLET_RE.findall(section_text) if b.strip()]
    if items:
        return items
    return [n.strip() for n in _NUMBERED_RE.findall(section_text) if n.strip()]


def _extract_score(text: str) -> int | None:
    """Prefer an explicit "NN/100" (avoids false positives like grabbing
    a "6" from "6 years experience" mentioned before the actual score);
    fall back to a number near the word score/note (FR) if "/100" isn't
    present verbatim."""
    if not text:
        return None
    m = _SCORE_RE.search(text)
    if not m:
        m = _SCORE_FALLBACK_RE.search(text)
    if not m:
        return None
    return max(0, min(100, int(m.group(1))))


def parse_analysis(text: str) -> ParsedAnalysis:
    """Parse the LLM's analysis markdown into structured fields. Any
    section that doesn't match the expected shape is left empty/None
    rather than raising — callers fall back to showing the raw markdown
    when score is None.

    Section splitting tolerates some drift in how the model formats its
    numbered headings (##, ###, or **bold**; with a period, parenthesis,
    colon, or nothing after the number) since a different/updated model
    doesn't always reproduce the prompt's exact "## 1. Match score"
    formatting. If a section still can't be found at all (score section
    included), the score is searched for across the *whole* text as a
    last resort, so a genuine formatting miss on section 1 alone doesn't
    necessarily hide the whole score-hero view."""
    if not text:
        return ParsedAnalysis()

    sections = _split_sections(text)
    score = _extract_score(sections.get(1, ""))
    if score is None:
        score = _extract_score(text)

    return ParsedAnalysis(
        score=score,
        strengths=_list_items(sections.get(2, "")),
        gaps=_list_items(sections.get(3, "")),
        ats_issues=_list_items(sections.get(4, "")),
        top_actions=_list_items(sections.get(5, "")),
    )
