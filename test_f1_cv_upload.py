"""
test_f1_cv_upload.py — Automated tests for TEST_PLAN.md § F1 (CV File Upload).

Run with: python -m pytest test_f1_cv_upload.py -v

Covers (see TEST_PLAN.md for the full acceptance criteria / Gherkin):
- TC-01: Valid PDF upload is accepted and its text is extracted
- TC-02: Valid DOCX upload is accepted and its text is extracted
- TC-04: An unsupported file type is rejected before any parsing is attempted
- TC-05: Submitting without a CV shows a validation message and never reaches the LLM
- TC-06: A password-protected PDF is rejected with a clear error, not a crash

Two test-plan items are intentionally NOT automated here, because the behavior
they describe does not exist in the app today (not because they're hard to
test) — flagging instead of silently skipping or faking a pass:
- TC-03 (file size limit): there is no app-level size check. Oversized files
  are rejected by Streamlit's own `server.maxUploadSize` before any of our
  code ever runs, which a unit/AppTest test can't meaningfully exercise.
- ".txt is unsupported": the test plan lists .txt among the rejected types,
  but `src/parsers.py` explicitly supports .txt as a valid CV format. Tested
  below is the actual behavior (.txt accepted), with the discrepancy noted.
- "Generate button becomes available [after upload]" (part of TC-01/02):
  the Generate button is always present and enabled; validation happens on
  click, not on upload. Not testable as worded because that gating doesn't
  exist.

No real LLM call is made anywhere in this file (project convention) — the
LLM-reaching tests use Streamlit's AppTest, which runs the real app.py
script in-process, and assert the validation path exits via st.stop()
before any LLMClient is ever constructed.
"""

import io
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pytest

from src.parsers import parse_document


class _FakeUploadedFile(io.BytesIO):
    """Minimal stand-in for Streamlit's UploadedFile: BytesIO + a .name."""

    def __init__(self, name: str, content: bytes):
        super().__init__(content)
        self.name = name


def _make_pdf_bytes(lines: list[str]) -> bytes:
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    for line in lines:
        pdf.cell(0, 10, text=line, new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())


def _make_docx_bytes(lines: list[str]) -> bytes:
    from docx import Document

    doc = Document()
    for line in lines:
        doc.add_paragraph(line)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# ─── TC-01 — Valid PDF upload ───────────────────────────────────────────────

def test_tc01_valid_pdf_upload_extracts_text():
    content = _make_pdf_bytes(["John Doe", "Software Engineer", "Python, SQL"])
    uploaded = _FakeUploadedFile("cv.pdf", content)

    text = parse_document(uploaded)

    assert "John Doe" in text
    assert "Software Engineer" in text
    assert "Python, SQL" in text


# ─── TC-02 — Valid DOCX upload ──────────────────────────────────────────────

def test_tc02_valid_docx_upload_extracts_text():
    content = _make_docx_bytes(["Jane Smith", "Product Manager", "SQL, Excel"])
    uploaded = _FakeUploadedFile("cv.docx", content)

    text = parse_document(uploaded)

    assert "Jane Smith" in text
    assert "Product Manager" in text
    assert "SQL, Excel" in text


def test_txt_is_actually_supported_contrary_to_test_plan_wording():
    """The test plan's TC-04 example lists .txt as an unsupported type, but
    src/parsers.py explicitly handles it as a valid CV format. This documents
    the actual behavior rather than the test plan's wording."""
    uploaded = _FakeUploadedFile("cv.txt", "Alex Doe\nDesigner".encode("utf-8"))

    text = parse_document(uploaded)

    assert "Alex Doe" in text
    assert "Designer" in text


# ─── TC-04 — Unsupported file type (using a genuinely unsupported one) ─────

def test_tc04_unsupported_file_type_rejected_without_parsing():
    uploaded = _FakeUploadedFile("photo.png", b"\x89PNG\r\n\x1a\nnot a real png body")

    with pytest.raises(ValueError, match="Unsupported format"):
        parse_document(uploaded)


def test_tc04_unsupported_extension_rejected_even_with_valid_pdf_bytes():
    """Rejection must be based on the file extension before any parsing is
    attempted — confirmed by feeding real PDF bytes under a bad extension
    and checking it's still rejected by name, not partially parsed."""
    content = _make_pdf_bytes(["Should never be read"])
    uploaded = _FakeUploadedFile("cv.exe", content)

    with pytest.raises(ValueError, match="Unsupported format"):
        parse_document(uploaded)


# ─── TC-06 — Password-protected PDF ─────────────────────────────────────────

def test_tc06_password_protected_pdf_raises_a_catchable_error(monkeypatch):
    """Simulates what pdfplumber/pdfminer raise on a real encrypted PDF
    (PDFPasswordIncorrect) via monkeypatch, instead of needing an actual
    encrypted binary fixture or a new dependency to create one."""
    import pdfplumber
    from pdfminer.pdfdocument import PDFPasswordIncorrect

    def fake_open(file):
        raise PDFPasswordIncorrect("password required")

    monkeypatch.setattr(pdfplumber, "open", fake_open)
    uploaded = _FakeUploadedFile("protected.pdf", b"%PDF-1.4 fake encrypted body")

    # Must surface as a normal Exception (not e.g. crash the interpreter or
    # raise a BaseException that would slip past app.py's `except Exception`)
    # so the app can show a controlled message instead of a traceback.
    with pytest.raises(Exception):
        parse_document(uploaded)


def test_tc06_password_protected_pdf_shows_friendly_error_in_app(monkeypatch):
    """End-to-end version of TC-06 through the real app: uploads a
    simulated encrypted PDF and confirms a controlled error is rendered,
    not a Python traceback / unhandled exception."""
    import pdfplumber
    from pdfminer.pdfdocument import PDFPasswordIncorrect
    from streamlit.testing.v1 import AppTest

    def fake_open(file):
        raise PDFPasswordIncorrect("password required")

    monkeypatch.setattr(pdfplumber, "open", fake_open)

    at = AppTest.from_file("app.py")
    at.run()

    cv_uploader = at.get("file_uploader")[0]
    cv_uploader.upload("protected.pdf", b"%PDF-1.4 fake encrypted body", "application/pdf")
    at.run()

    generate_button = next(b for b in at.button if "Generate" in b.label)
    generate_button.click()
    at.run()

    assert not at.exception
    assert at.session_state["generated"] is False
    assert at.session_state["llm"] is None
    assert any("Error reading CV" in e.value for e in at.error)


# ─── TC-05 — Submit without a CV ────────────────────────────────────────────

def test_tc05_submit_without_cv_shows_validation_and_never_calls_llm():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("app.py")
    at.run()

    # No file uploaded, no text pasted — submit immediately.
    generate_button = next(b for b in at.button if "Generate" in b.label)
    generate_button.click()
    at.run()

    assert not at.exception
    assert at.session_state["llm"] is None
    assert at.session_state["generated"] is False
    assert any("CV" in e.value for e in at.error)
