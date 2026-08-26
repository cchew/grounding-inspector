import io

from docx import Document
from pypdf import PdfReader

MAX_EXTRACTED_CHARS = 60_000


class UnsupportedFileType(ValueError):
    pass


class DocumentTooLarge(ValueError):
    pass


def extract_pdf(file_bytes: bytes) -> list[dict]:
    """One section per non-blank page -- the only real page boundaries GI has
    available for a live upload."""
    reader = PdfReader(io.BytesIO(file_bytes))
    sections = []
    for i, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if not text:
            continue
        sections.append({"id": f"p{i}", "page": i, "char_start": 0, "char_end": len(text), "text": text})
    return sections


def extract_docx(file_bytes: bytes) -> list[dict]:
    """DOCX has no fixed pagination without rendering -- the whole document
    becomes one section, page defaults to 1."""
    doc = Document(io.BytesIO(file_bytes))
    text = "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
    if not text:
        return []
    return [{"id": "s1", "page": 1, "char_start": 0, "char_end": len(text), "text": text}]


def extract_plain_text(text: str) -> list[dict]:
    text = text.strip()
    if not text:
        return []
    return [{"id": "s1", "page": 1, "char_start": 0, "char_end": len(text), "text": text}]


def extract_reference_document(filename: str, file_bytes: bytes) -> list[dict]:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        sections = extract_pdf(file_bytes)
    elif lower.endswith(".docx"):
        sections = extract_docx(file_bytes)
    elif lower.endswith(".txt"):
        sections = extract_plain_text(file_bytes.decode("utf-8", errors="replace"))
    else:
        raise UnsupportedFileType(f"unsupported file type: {filename}")

    total_chars = sum(len(s["text"]) for s in sections)
    if total_chars > MAX_EXTRACTED_CHARS:
        raise DocumentTooLarge(f"extracted text ({total_chars} chars) exceeds the {MAX_EXTRACTED_CHARS}-char limit")
    if not sections:
        raise ValueError(f"no extractable text found in {filename}")
    return sections
