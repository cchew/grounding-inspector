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


_C0C1 = (
    set(range(0x00, 0x09)) | {0x0B, 0x0C} | set(range(0x0E, 0x20)) | set(range(0x7F, 0xA0))
)


def _detect_text_encoding(raw: bytes) -> str | None:
    """Encoding a .txt upload decodes cleanly as, else None. Accepts UTF-8,
    UTF-16 (BOM), and Latin-1; rejects a blob with > 15% C0/C1 control bytes
    (tab/newline/CR excluded) as binary padding for an expensive check.

    A strict-UTF-8 failure with a low control-byte share is treated as Latin-1
    before the lossy UTF-8-replace fallback: real Latin-1 prose (French/English
    accents) sits well under the 10% replacement ratio, so an earlier ratio
    check would silently mojibake it as UTF-8."""
    if not raw:
        return None
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return "utf-16"
    try:
        raw.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        pass
    if sum(1 for b in raw if b in _C0C1) / len(raw) <= 0.15:
        return "latin-1"
    replaced = raw.decode("utf-8", errors="replace")
    if replaced.count("�") / len(replaced) <= 0.10:
        return "utf-8"
    return None


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
        encoding = _detect_text_encoding(file_bytes)
        if encoding is None:
            raise UnsupportedFileType("upload does not match its .txt extension (not text)")
        sections = extract_plain_text(file_bytes.decode(encoding, errors="replace"))
    else:
        raise UnsupportedFileType("unsupported file type")

    total_chars = sum(len(s["text"]) for s in sections)
    if total_chars > MAX_EXTRACTED_CHARS:
        raise DocumentTooLarge(f"extracted text ({total_chars} chars) exceeds the {MAX_EXTRACTED_CHARS}-char limit")
    if not sections:
        raise ValueError("no extractable text found in the uploaded document")
    return sections
