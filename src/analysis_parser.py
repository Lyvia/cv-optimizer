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


_SECTION_RE = re.compile(r"^##\s*(\d+)\.\s*.*$", re.MULTILINE)
_BULLET_RE = re.compile(r"^[ \t]*[-*]\s+(.*)$", re.MULTILINE)
_NUMBERED_RE = re.compile(r"^[ \t]*\d+[.)]\s+(.*)$", re.MULTILINE)
_SCORE_RE = re.compile(r"(\d{1,3})\s*(?:/\s*100|\s+out of\s+100)?")


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


def _extract_score(section1_text: str) -> int | None:
    if not section1_text:
        return None
    m = _SCORE_RE.search(section1_text)
    if not m:
        return None
    return max(0, min(100, int(m.group(1))))


def parse_analysis(text: str) -> ParsedAnalysis:
    """Parse the LLM's analysis markdown into structured fields. Any
    section that doesn't match the expected shape is left empty/None
    rather than raising — callers fall back to showing the raw markdown
    when score is None."""
    if not text:
        return ParsedAnalysis()

    sections = _split_sections(text)
    return ParsedAnalysis(
        score=_extract_score(sections.get(1, "")),
        strengths=_list_items(sections.get(2, "")),
        gaps=_list_items(sections.get(3, "")),
        ats_issues=_list_items(sections.get(4, "")),
        top_actions=_list_items(sections.get(5, "")),
    )
