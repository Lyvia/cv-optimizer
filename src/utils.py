"""
utils.py — Small shared helpers for cleaning LLM output before use.
"""

_FENCE_MARKER = "```"


def strip_fences(text: str) -> str:
    """
    Remove a leading/trailing Markdown code fence the LLM sometimes wraps
    its entire response in (e.g. ```markdown ... ``` or ``` ... ```).

    Args:
        text: Raw LLM output, possibly fenced

    Returns:
        str: The text with the surrounding fence removed, if present
    """
    cleaned = text.strip()
    lines = cleaned.split("\n")

    if lines and lines[0].strip().startswith(_FENCE_MARKER):
        lines = lines[1:]
    if lines and lines[-1].strip() == _FENCE_MARKER:
        lines = lines[:-1]

    return "\n".join(lines).strip()
