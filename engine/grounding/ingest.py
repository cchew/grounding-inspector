import io

from docx import Document
from pypdf import PdfReader

MAX_EXTRACTED_CHARS = 60_000

_PDF_MAGIC = b"%PDF-"
_ZIP_MAGIC = b"PK\x03\x04"


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


def _looks_like_text(raw: bytes) -> bool:
    """A .txt upload is accepted only if it decodes as UTF-8 with few
    replacement characters — a heuristic guard against a binary blob
    renamed to .txt padding out an expensive check."""
    if not raw:
        return False
    decoded = raw.decode("utf-8", errors="replace")
    bad = decoded.count("�")
    return bad / len(decoded) <= 0.10


def extract_reference_document(filename: str, file_bytes: bytes) -> list[dict]:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        if not file_bytes.startswith(_PDF_MAGIC):
            raise UnsupportedFileType(f"{filename} is not a PDF (bad file signature)")
        sections = extract_pdf(file_bytes)
    elif lower.endswith(".docx"):
        if not file_bytes.startswith(_ZIP_MAGIC):
            raise UnsupportedFileType(f"{filename} is not a DOCX (bad file signature)")
        sections = extract_docx(file_bytes)
    elif lower.endswith(".txt"):
        if not _looks_like_text(file_bytes):
            raise UnsupportedFileType(f"{filename} does not look like UTF-8 text")
        sections = extract_plain_text(file_bytes.decode("utf-8", errors="replace"))
    else:
        raise UnsupportedFileType(f"unsupported file type: {filename}")

    total_chars = sum(len(s["text"]) for s in sections)
    if total_chars > MAX_EXTRACTED_CHARS:
        raise DocumentTooLarge(f"extracted text ({total_chars} chars) exceeds the {MAX_EXTRACTED_CHARS}-char limit")
    if not sections:
        raise ValueError(f"no extractable text found in {filename}")
    return sections
