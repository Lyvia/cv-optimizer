"""
parsers.py — Extract plain text from CV and job description files.
Supports: PDF, DOCX, TXT
"""

import io


def parse_document(file) -> str:
    """
    Parse an uploaded Streamlit file object and return its text content.

    Args:
        file: Streamlit UploadedFile object

    Returns:
        str: Extracted text content

    Raises:
        ValueError: If the file format is unsupported or parsing fails
    """
    name = file.name.lower()

    if name.endswith(".pdf"):
        return _parse_pdf(file)
    elif name.endswith(".docx"):
        return _parse_docx(file)
    elif name.endswith(".txt"):
        return _parse_txt(file)
    else:
        raise ValueError(
            f"Format non supporté : '{file.name}'. "
            "Formats acceptés : PDF, DOCX, TXT."
        )


# ─── Private parsers ──────────────────────────────────────────────────────────

def _parse_pdf(file) -> str:
    """Extract text from a PDF file using pdfplumber."""
    try:
        import pdfplumber
    except ImportError:
        raise ImportError(
            "pdfplumber n'est pas installé. Lance : pip install pdfplumber"
        )

    try:
        # pdfplumber accepts file-like objects
        file.seek(0)
        with pdfplumber.open(file) as pdf:
            pages_text = []
            for page in pdf.pages:
                text = page.extract_text()
                if text and text.strip():
                    pages_text.append(text.strip())

        if not pages_text:
            raise ValueError(
                "Aucun texte extrait du PDF. "
                "Le fichier est peut-être un scan image (non OCR)."
            )

        return "\n\n".join(pages_text)

    except Exception as e:
        if "pdfplumber" in str(type(e).__module__):
            raise ValueError(f"Erreur lecture PDF : {e}")
        raise


def _parse_docx(file) -> str:
    """Extract text from a DOCX file using python-docx."""
    try:
        from docx import Document
    except ImportError:
        raise ImportError(
            "python-docx n'est pas installé. Lance : pip install python-docx"
        )

    try:
        file.seek(0)
        doc = Document(io.BytesIO(file.read()))

        parts = []

        # Main body paragraphs
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                parts.append(text)

        # Tables (for CV tables)
        for table in doc.tables:
            for row in table.rows:
                row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if row_cells:
                    parts.append(" | ".join(row_cells))

        if not parts:
            raise ValueError("Aucun texte trouvé dans le fichier DOCX.")

        return "\n".join(parts)

    except Exception as e:
        raise ValueError(f"Erreur lecture DOCX : {e}")


def _parse_txt(file) -> str:
    """Read a plain text file."""
    try:
        file.seek(0)
        content = file.read()
        # Try UTF-8 first, fall back to latin-1
        try:
            return content.decode("utf-8").strip()
        except UnicodeDecodeError:
            return content.decode("latin-1").strip()
    except Exception as e:
        raise ValueError(f"Erreur lecture TXT : {e}")
