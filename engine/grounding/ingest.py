import io
import re

from docx import Document
from pypdf import PdfReader

MAX_EXTRACTED_CHARS = 60_000


def _sections_from_blocks(blocks) -> list[dict]:
    """One section per non-empty block, ids s1, s2, ... All page 1: neither
    plain text nor DOCX carries real pagination. char_end is the block's own
    length (page-relative, only used defensively downstream)."""
    out: list[dict] = []
    for raw in blocks:
        block = raw.strip()
        if not block:
            continue
        out.append({
            "id": f"s{len(out) + 1}", "page": 1,
            "char_start": 0, "char_end": len(block), "text": block,
        })
    return out

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
    """DOCX has no fixed pagination without rendering. Split into sections on
    blank paragraphs, and start a new section at a Heading-styled paragraph."""
    doc = Document(io.BytesIO(file_bytes))
    blocks: list[str] = []
    current: list[str] = []

    def flush() -> None:
        if current:
            blocks.append("\n".join(current))
            current.clear()

    for p in doc.paragraphs:
        style = getattr(p, "style", None)
        is_heading = bool(style and (getattr(style, "name", "") or "").startswith("Heading"))
        if not p.text.strip():
            flush()
            continue
        if is_heading:
            flush()
        current.append(p.text)
    flush()
    return _sections_from_blocks(blocks)


def extract_plain_text(text: str) -> list[dict]:
    return _sections_from_blocks(re.split(r"\n\s*\n+", text))


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
    """`filename` is used for extension dispatch only. It is the raw multipart
    Content-Disposition value -- unbounded and attacker-controlled -- and the
    API layer logs these exception messages, so none of them interpolate it.
    The branch already identifies the extension."""
    lower = filename.lower()
    if lower.endswith(".pdf"):
        if not file_bytes.startswith(_PDF_MAGIC):
            raise UnsupportedFileType("upload does not match its .pdf extension (bad file signature)")
        sections = extract_pdf(file_bytes)
    elif lower.endswith(".docx"):
        if not file_bytes.startswith(_ZIP_MAGIC):
            raise UnsupportedFileType("upload does not match its .docx extension (bad file signature)")
        sections = extract_docx(file_bytes)
    elif lower.endswith(".txt"):
        if not _looks_like_text(file_bytes):
            raise UnsupportedFileType("upload does not match its .txt extension (not UTF-8 text)")
        sections = extract_plain_text(file_bytes.decode("utf-8", errors="replace"))
    else:
        raise UnsupportedFileType("unsupported file type")

    total_chars = sum(len(s["text"]) for s in sections)
    if total_chars > MAX_EXTRACTED_CHARS:
        raise DocumentTooLarge(f"extracted text ({total_chars} chars) exceeds the {MAX_EXTRACTED_CHARS}-char limit")
    if not sections:
        raise ValueError("no extractable text found in the uploaded document")
    return sections
