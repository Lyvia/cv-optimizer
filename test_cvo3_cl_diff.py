"""
test_cvo3_cl_diff.py — Regression test for CVO-3 (diff behavior inconsistent
between CV and cover letter): the cover letter refine flow must use the same
line-by-line diff / per-chunk Accept/Ignore mechanism as the CV, not a
full-replace-only flow.

Run with: python -m pytest test_cvo3_cl_diff.py -v

No real LLM call: a fake google.genai client is installed via sys.modules
(same shape as test_f7_diff_view.py / test_llm_client_gemini.py).
"""

import sys
import types as pytypes

from streamlit.testing.v1 import AppTest

SAMPLE_CV = "Jane Smith\njane@example.com\n\nEXPERIENCE\nMarketing Coordinator - Acme Inc\n- Ran campaigns\n\nSKILLS\nPython, SQL"

INITIAL_CV_RESPONSE = """# Jane Smith

## Skills
Python, SQL, Excel
---CHANGES---
**Changes made:** rewrote for ATS.
"""

INITIAL_CL_RESPONSE = """# Cover Letter

Dear Hiring Manager,

I am writing to apply for the Marketing Coordinator position.

I have four years of experience in digital campaigns.

Sincerely,
Jane Smith
---CHANGES---
**Changes made:** initial draft.
"""

REFINED_CL_RESPONSE = """# Cover Letter

Dear Hiring Manager,

I am thrilled to apply for the Marketing Coordinator position.

I have four years of experience in digital campaigns.

Sincerely,
Jane Smith
---CHANGES---
**Changes made:** stronger opening line.
"""


class _FakeResponse:
    def __init__(self, text):
        self.text = text


class _FakeModels:
    def generate_content(self, *, model, contents, config=None):
        low = contents.lower()
        if "candidate wants to refine" in low and "dear hiring manager" in low:
            return _FakeResponse(REFINED_CL_RESPONSE)
        if "candidate wants to refine" in low:
            return _FakeResponse(INITIAL_CV_RESPONSE)
        if "rewrite this cv" in low:
            return _FakeResponse(INITIAL_CV_RESPONSE)
        if "analyze this cv" in low:
            return _FakeResponse("## 1. Match score (0-100)\n70/100.")
        if "write a compelling cover letter" in low:
            return _FakeResponse(INITIAL_CL_RESPONSE)
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
    return "\n".join(el.value for el in at.markdown)


def _generate(at: AppTest):
    at.text_area[0].set_value(SAMPLE_CV)
    next(b for b in at.button if "Generate" in b.label).click()
    at.run()


def _submit_cl_refine(at: AppTest, instruction: str):
    """See test_f7_diff_view.py's _submit_cv_refine docstring re: the
    AppTest + st.rerun(scope="fragment") harness-only quirk this works
    around with a second .run()."""
    cl_chat = next(c for c in at.get("chat_input") if c.key == "cl_chat_input")
    cl_chat.set_value(instruction)
    at.run()
    at.run()


def test_cover_letter_refine_offers_per_chunk_accept_ignore_not_just_replace(monkeypatch):
    """CVO-3: the cover letter must support per-change Accept/Ignore, like
    the CV -- not only a single "replace the whole letter" action."""
    _install_fake_genai(monkeypatch)

    at = AppTest.from_file("app.py")
    at.run()
    _generate(at)
    assert not at.exception

    _submit_cl_refine(at, "Make the opening line more enthusiastic")
    assert not at.exception

    accept_buttons = [b for b in at.button if b.label == "✓ Accept"]
    ignore_buttons = [b for b in at.button if b.label == "✗ Ignore"]
    assert accept_buttons, "expected a per-chunk Accept button, found none"
    assert ignore_buttons, "expected a per-chunk Ignore button, found none"

    # Unchanged lines must stay visible as context (same as the CV's diff).
    rendered = _all_rendered_text(at)
    assert "Dear Hiring Manager" in rendered
    assert "four years of experience" in rendered
    assert "I am thrilled to apply" in rendered


def test_cover_letter_diff_round_ids_dont_collide_with_cv(monkeypatch):
    """CV and cover letter diff rounds are namespaced (cv_N / cl_N) so an
    Accept/Ignore on one document can never resolve a chunk belonging to
    the other, even if both reach the same round number."""
    _install_fake_genai(monkeypatch)

    at = AppTest.from_file("app.py")
    at.run()
    _generate(at)

    _submit_cl_refine(at, "Make the opening line more enthusiastic")
    assert not at.exception

    chunk_ids = {
        b.key.split("accept_", 1)[1]
        for b in at.button
        if b.key and b.key.startswith("accept_cl_")
    }
    assert chunk_ids, "expected at least one cl_-namespaced chunk id"
    assert all(cid.startswith("cl_") for cid in chunk_ids)


def test_cover_letter_accept_all_clears_diff_and_returns_to_single_static_view(monkeypatch):
    _install_fake_genai(monkeypatch)

    at = AppTest.from_file("app.py")
    at.run()
    _generate(at)

    _submit_cl_refine(at, "Make the opening line more enthusiastic")

    accept_all = next(b for b in at.button if "Accept all" in b.label)
    accept_all.click()
    at.run()
    at.run()

    assert not at.exception
    assert at.session_state["cl_pending_diff"] is None
    assert "I am thrilled to apply" in at.session_state["current_cl"]
    assert not any("Accept all" in b.label for b in at.button)
