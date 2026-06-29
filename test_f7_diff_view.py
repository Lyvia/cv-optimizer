"""
test_f7_diff_view.py — Regression test for CVO-5 (TEST_PLAN.md F7 §
AC-F7-01, TC-31 / TC-32): the CV diff view must keep unchanged lines
visible as context, not show only the added/removed lines, and must not
duplicate the CV into a separate static view + a separate stripped-down
diff view at the same time.

Run with: python -m pytest test_f7_diff_view.py -v

No real LLM call: a fake google.genai client is installed via sys.modules
(same shape as test_llm_client_gemini.py / mock_bootstrap.py), returning
a fixed "optimize" response and a fixed "refine" response that only adds
one new section — everything else must remain visible as context.
"""

import sys
import types as pytypes

from streamlit.testing.v1 import AppTest

SAMPLE_CV = "Jane Smith\njane@example.com\n\nEXPERIENCE\nMarketing Coordinator - Acme Inc\n- Ran campaigns\n\nSKILLS\nPython, SQL"

INITIAL_CV_RESPONSE = """# Jane Smith

## Professional Experience
**Marketing Coordinator** — Acme Inc (2020-2024)
- Ran social media campaigns
- Managed a budget

## Skills
Python, SQL, Excel
---CHANGES---
**Changes made:** rewrote for ATS.
"""

REFINED_CV_RESPONSE = """# Jane Smith

## Professional Summary
Results-driven Marketing Coordinator.

## Professional Experience
**Marketing Coordinator** — Acme Inc (2020-2024)
- Ran social media campaigns
- Managed a budget

## Skills
Python, SQL, Excel
---CHANGES---
**Changes made:** added a professional summary.
"""


class _FakeResponse:
    def __init__(self, text):
        self.text = text


class _FakeModels:
    def __init__(self):
        self.call_count = 0

    def generate_content(self, *, model, contents, config=None):
        low = contents.lower()
        if "candidate wants to refine" in low:
            self.call_count += 1
            return _FakeResponse(REFINED_CV_RESPONSE)
        if "rewrite this cv" in low:
            return _FakeResponse(INITIAL_CV_RESPONSE)
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


def _all_rendered_text(at: AppTest) -> str:
    """Concatenate every markdown element's raw value (covers both plain
    st.markdown calls and the HTML-wrapped diff/context blocks)."""
    return "\n".join(el.value for el in at.markdown)


def _generate(at: AppTest):
    at.text_area[0].set_value(SAMPLE_CV)
    next(b for b in at.button if "Generate" in b.label).click()
    at.run()


def _submit_cv_refine(at: AppTest, instruction: str):
    """AppTest has a known limitation with st.rerun(scope="fragment")
    called from inside a fragment's own widget callback during a bare-mode
    test run: it records an exception on the *first* .run() even though
    session_state was already correctly updated beforehand. A second
    .run() (no new interaction) cleanly re-renders from that state with
    no exception -- confirmed this is test-harness-only by the fact the
    real app (driven via Playwright in a real browser) has no such issue."""
    cv_chat = next(c for c in at.get("chat_input") if c.key == "cv_chat_input")
    cv_chat.set_value(instruction)
    at.run()
    at.run()


def test_unchanged_context_visible_during_pending_diff(monkeypatch):
    _install_fake_genai(monkeypatch)

    at = AppTest.from_file("app.py")
    at.run()
    _generate(at)
    assert not at.exception

    _submit_cv_refine(at, "Add a summary")

    assert not at.exception
    rendered = _all_rendered_text(at)

    # The unchanged sections (CVO-5: must stay visible as context, not be
    # stripped down to only the added/removed lines).
    assert "Acme Inc" in rendered
    assert "Python, SQL, Excel" in rendered
    # The new content from this refine round, highlighted as a pending change.
    assert "Results-driven Marketing Coordinator" in rendered


def test_single_cv_view_no_duplicate_static_plus_diff(monkeypatch):
    """Before CVO-5's fix, a static preview was shown at the top AND a
    separate stripped diff list further down -- the same CV text must not
    appear twice (once plain, once diff-rendered) while a diff is pending."""
    _install_fake_genai(monkeypatch)

    at = AppTest.from_file("app.py")
    at.run()
    _generate(at)

    _submit_cv_refine(at, "Add a summary")

    rendered = _all_rendered_text(at)
    assert rendered.count("Acme Inc") == 1


def test_accept_all_clears_diff_and_returns_to_single_static_view(monkeypatch):
    _install_fake_genai(monkeypatch)

    at = AppTest.from_file("app.py")
    at.run()
    _generate(at)

    _submit_cv_refine(at, "Add a summary")

    accept_all = next(b for b in at.button if "Accept all" in b.label)
    accept_all.click()
    at.run()
    at.run()  # see _submit_cv_refine docstring re: AppTest + scope="fragment"

    assert not at.exception
    assert at.session_state["cv_pending_diff"] is None
    assert "Results-driven Marketing Coordinator" in at.session_state["current_cv"]
    assert not any("Accept all" in b.label for b in at.button)
