"""
test_cvo9_zip_download.py — Regression test for CVO-9 (ZIP download missing
PDFs and contains original AI version instead of user-revised version).

Run with: python -m pytest test_cvo9_zip_download.py -v

No real LLM call: a fake google.genai client is installed via sys.modules
(same shape as test_f7_diff_view.py / test_llm_client_gemini.py).

AppTest's download_button element doesn't expose the generated file bytes
(the proto only carries a `url` into Streamlit's internal media file
storage, not the data itself) -- so the "_build_zip() produces 4 correctly
named files" check below extracts and runs the real `_build_zip` function
straight out of app.py's source (it's pure stdlib, no Streamlit dependency),
rather than reimplementing it. The "ZIP reflects the accepted revision, not
the original AI output" check instead drives the real app through an
Accept All round and inspects `current_cv` in session_state, which is
exactly what the real call site in app.py feeds into the exporters.
"""

import ast
import io
import sys
import types as pytypes
import zipfile

from streamlit.testing.v1 import AppTest

SAMPLE_CV = "Jane Smith\njane@example.com\n\nEXPERIENCE\nMarketing Coordinator - Acme Inc\n- Ran campaigns\n\nSKILLS\nPython, SQL"

INITIAL_CV_RESPONSE = """# Jane Smith

## Professional Experience
**Marketing Coordinator** — Acme Inc (2020-2024)
- Ran social media campaigns

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

## Skills
Python, SQL, Excel
---CHANGES---
**Changes made:** added a professional summary.
"""

INITIAL_CL_RESPONSE = "# Cover Letter\n\nDear Hiring Manager,\n\nBody.\n"


class _FakeResponse:
    def __init__(self, text):
        self.text = text


class _FakeModels:
    def generate_content(self, *, model, contents, config=None):
        low = contents.lower()
        if "candidate wants to refine" in low:
            return _FakeResponse(REFINED_CV_RESPONSE)
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


def _generate(at: AppTest):
    at.text_area[0].set_value(SAMPLE_CV)
    next(b for b in at.button if "Generate" in b.label).click()
    at.run()


def _submit_cv_refine(at: AppTest, instruction: str):
    """See test_f7_diff_view.py's _submit_cv_refine docstring re: the
    AppTest + st.rerun(scope="fragment") harness-only quirk."""
    cv_chat = next(c for c in at.get("chat_input") if c.key == "cv_chat_input")
    cv_chat.set_value(instruction)
    at.run()
    at.run()


def _real_build_zip():
    """Extract and execute the actual `_build_zip` function from app.py's
    source so this test exercises the real code, not a reimplementation."""
    with open("app.py", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename="app.py")
    func_node = next(
        n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_build_zip"
    )
    namespace = {"io": io, "zipfile": zipfile}
    exec(compile(ast.Module(body=[func_node], type_ignores=[]), "app.py", "exec"), namespace)
    return namespace["_build_zip"]


def test_build_zip_includes_docx_and_pdf_for_both_documents():
    build_zip = _real_build_zip()
    zip_bytes = build_zip(b"cv-docx", b"cv-pdf", b"cl-docx", b"cl-pdf")

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        assert set(zf.namelist()) == {
            "Optimized_CV.docx",
            "Optimized_CV.pdf",
            "Cover_Letter.docx",
            "Cover_Letter.pdf",
        }
        assert zf.read("Optimized_CV.docx") == b"cv-docx"
        assert zf.read("Optimized_CV.pdf") == b"cv-pdf"
        assert zf.read("Cover_Letter.docx") == b"cl-docx"
        assert zf.read("Cover_Letter.pdf") == b"cl-pdf"


def test_current_cv_reflects_accepted_revision_not_original_ai_output(monkeypatch):
    """CVO-9: whatever feeds the ZIP (current_cv) must be the user-revised
    version (post Accept/Reject), not the original, untouched AI output --
    this is the exact value the real call site in app.py passes to the
    DOCX/PDF exporters before zipping."""
    _install_fake_genai(monkeypatch)

    at = AppTest.from_file("app.py")
    at.run()
    _generate(at)

    _submit_cv_refine(at, "Add a professional summary")
    accept_all = next(b for b in at.button if "Accept all" in b.label)
    accept_all.click()
    at.run()
    at.run()

    assert not at.exception
    assert "Results-driven Marketing Coordinator" in at.session_state["current_cv"]
    assert at.session_state["current_cv"] != at.session_state["optimized_cv"]
