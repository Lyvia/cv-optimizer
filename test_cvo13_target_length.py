"""
test_cvo13_target_length.py — Regression tests for CVO-13's target-length
option: optimize_cv() must support an explicit 1-page/2-page budget on top
of the original "match original length" default, and the app must warn
the user (rather than silently fail) when the LLM doesn't actually meet
that budget.

Run with: python -m pytest test_cvo13_target_length.py -v
"""

import sys
import types as pytypes

from streamlit.testing.v1 import AppTest

from src.prompts import PromptBuilder
from src.styles import WORDS_PER_PAGE_ESTIMATE

SAMPLE_CV = "John Doe\n" + ("Experienced engineer. " * 30)


def test_default_keeps_length_relative_to_original():
    pb = PromptBuilder()
    word_count = len(SAMPLE_CV.split())

    prompt = pb.optimize_cv(SAMPLE_CV, "")

    assert f"close to the original CV (~{word_count} words)" in prompt
    assert "MUST fit within" not in prompt


def test_target_pages_one_uses_absolute_word_budget():
    pb = PromptBuilder()

    prompt = pb.optimize_cv(SAMPLE_CV, "", target_pages=1)

    assert f"MUST fit within 1 A4 page (~{WORDS_PER_PAGE_ESTIMATE} words total" in prompt
    assert "close to the original CV" not in prompt


def test_target_pages_two_doubles_the_budget_and_uses_plural():
    pb = PromptBuilder()

    prompt = pb.optimize_cv(SAMPLE_CV, "", target_pages=2)

    assert f"MUST fit within 2 A4 pages (~{2 * WORDS_PER_PAGE_ESTIMATE} words total" in prompt


def test_target_pages_applies_with_a_job_description_too():
    pb = PromptBuilder()

    prompt = pb.optimize_cv(SAMPLE_CV, "Senior Engineer role", target_pages=1)

    assert f"MUST fit within 1 A4 page (~{WORDS_PER_PAGE_ESTIMATE} words total" in prompt
    assert "Senior Engineer role" in prompt


# ─── App-level: warn when the LLM doesn't actually meet the target ─────────

SAMPLE_INPUT_CV = "Jane Smith\njane@example.com\n\nEXPERIENCE\nMarketing Coordinator - Acme Inc\n- Ran campaigns\n\nSKILLS\nPython, SQL"

_LONG_BULLET = (
    "- Led integrated marketing campaigns across multiple channels, increasing "
    "qualified leads by 27 percent year over year and reducing acquisition cost\n"
)

# Deliberately long enough to overflow 1 page regardless of the prompt's
# target_pages instruction -- the mock represents an LLM that didn't comply.
OVERLONG_CV_RESPONSE = (
    "# Jane Smith\n\n## Professional Experience\n**Marketing Coordinator** — Acme Inc (2020-2024)\n"
    + (_LONG_BULLET * 24)
    + "\n## Skills\nPython, SQL, Excel, HubSpot, Salesforce\n\n## Education\nMaster in Marketing (2018)\n"
    "---CHANGES---\n**Changes made:** rewrote for ATS.\n"
)


class _FakeResponse:
    def __init__(self, text):
        self.text = text


class _FakeModels:
    def generate_content(self, *, model, contents, config=None):
        low = contents.lower()
        if "rewrite this cv" in low:
            return _FakeResponse(OVERLONG_CV_RESPONSE)
        if "analyze this cv" in low:
            return _FakeResponse("## 1. Match score (0-100)\n70/100.")
        if "write a compelling cover letter" in low:
            return _FakeResponse("# Cover Letter\n\nDear Hiring Manager,\n\nBody.\n")
        return _FakeResponse("Mock response.")


class _FakeClient:
    def __init__(self, api_key=None):
        self.models = _FakeModels()


class _FakeThinkingConfig:
    def __init__(self, thinking_budget=None, **_ignored):
        self.thinking_budget = thinking_budget


class _FakeGenerateContentConfig:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def _install_fake_genai(monkeypatch):
    fake_types = pytypes.SimpleNamespace(
        GenerateContentConfig=_FakeGenerateContentConfig,
        ThinkingConfig=_FakeThinkingConfig,
    )
    fake_genai = pytypes.SimpleNamespace(Client=_FakeClient, types=fake_types)
    monkeypatch.setitem(sys.modules, "google.genai", fake_genai)
    monkeypatch.setitem(sys.modules, "google.genai.types", fake_types)


def test_warns_when_llm_does_not_meet_the_one_page_target(monkeypatch):
    _install_fake_genai(monkeypatch)

    at = AppTest.from_file("app.py")
    at.run()

    at.text_area[0].set_value(SAMPLE_INPUT_CV)
    next(r for r in at.radio if r.key == "target_length_choice").set_value("1 page")
    next(b for b in at.button if "Generate" in b.label).click()
    at.run()

    assert not at.exception
    warnings = [w.value for w in at.warning]
    assert any("despite the 1-page target" in w for w in warnings), warnings


def test_no_warning_when_match_original_length_is_selected(monkeypatch):
    """With the default "match original" choice, target_pages is None and
    the overflow check must not run at all (nothing to compare against)."""
    _install_fake_genai(monkeypatch)

    at = AppTest.from_file("app.py")
    at.run()

    at.text_area[0].set_value(SAMPLE_INPUT_CV)
    next(b for b in at.button if "Generate" in b.label).click()
    at.run()

    assert not at.exception
    warnings = [w.value for w in at.warning]
    assert not any("page target" in w for w in warnings), warnings
