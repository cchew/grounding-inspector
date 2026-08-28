import pytest
from grounding.ingest import (
    extract_pdf, extract_docx, extract_plain_text, extract_reference_document,
    DocumentTooLarge, UnsupportedFileType, MAX_EXTRACTED_CHARS,
)


class FakePage:
    def __init__(self, text):
        self._text = text

    def extract_text(self):
        return self._text


class FakePdfReader:
    def __init__(self, file_bytes):
        self.pages = [FakePage("Page one text."), FakePage("Page two text.")]


def test_extract_pdf_one_section_per_page(monkeypatch):
    import grounding.ingest as ingest_mod
    monkeypatch.setattr(ingest_mod, "PdfReader", FakePdfReader)
    sections = extract_pdf(b"fake-pdf-bytes")
    assert [s["id"] for s in sections] == ["p1", "p2"]
    assert [s["page"] for s in sections] == [1, 2]
    assert sections[0]["text"] == "Page one text."
    assert sections[0]["char_start"] == 0
    assert sections[0]["char_end"] == len("Page one text.")


def test_extract_pdf_skips_blank_pages(monkeypatch):
    import grounding.ingest as ingest_mod

    class ReaderWithBlank:
        def __init__(self, b):
            self.pages = [FakePage("Real content."), FakePage(""), FakePage(None)]

    monkeypatch.setattr(ingest_mod, "PdfReader", ReaderWithBlank)
    sections = extract_pdf(b"fake")
    assert len(sections) == 1
    assert sections[0]["text"] == "Real content."


class FakeParagraph:
    def __init__(self, text):
        self.text = text


class FakeDocxDocument:
    def __init__(self, file_like):
        self.paragraphs = [FakeParagraph("First para."), FakeParagraph(""), FakeParagraph("Second para.")]


def test_extract_docx_joins_nonempty_paragraphs(monkeypatch):
    import grounding.ingest as ingest_mod
    monkeypatch.setattr(ingest_mod, "Document", FakeDocxDocument)
    sections = extract_docx(b"fake-docx-bytes")
    assert len(sections) == 1
    assert sections[0]["text"] == "First para.\n\nSecond para."
    assert sections[0]["page"] == 1
    assert sections[0]["id"] == "s1"


def test_extract_docx_no_content_returns_no_sections(monkeypatch):
    import grounding.ingest as ingest_mod

    class EmptyDoc:
        def __init__(self, b):
            self.paragraphs = [FakeParagraph(""), FakeParagraph("   ")]

    monkeypatch.setattr(ingest_mod, "Document", EmptyDoc)
    assert extract_docx(b"fake") == []


def test_extract_plain_text_wraps_single_section():
    sections = extract_plain_text("  Hello world.  ")
    assert sections == [{"id": "s1", "page": 1, "char_start": 0, "char_end": 12, "text": "Hello world."}]


def test_extract_plain_text_empty_returns_no_sections():
    assert extract_plain_text("   ") == []


def test_reference_document_rejects_pdf_extension_with_non_pdf_bytes():
    with pytest.raises(UnsupportedFileType):
        extract_reference_document("policy.pdf", b"this is definitely not a pdf")


def test_reference_document_rejects_docx_extension_with_non_zip_bytes():
    with pytest.raises(UnsupportedFileType):
        extract_reference_document("policy.docx", b"plain text, not a zip container")


def test_reference_document_rejects_txt_that_is_mostly_binary():
    blob = bytes(range(256)) * 8  # ~66% non-decodable as utf-8 text
    with pytest.raises(UnsupportedFileType):
        extract_reference_document("notes.txt", blob)


def test_reference_document_accepts_valid_pdf_magic(monkeypatch):
    import grounding.ingest as ingest_mod
    monkeypatch.setattr(ingest_mod, "PdfReader", FakePdfReader)
    sections = extract_reference_document("policy.pdf", b"%PDF-1.4\n" + b"x" * 20)
    assert sections[0]["id"] == "p1"


def test_reference_document_accepts_valid_docx_magic(monkeypatch):
    import grounding.ingest as ingest_mod
    monkeypatch.setattr(ingest_mod, "Document", FakeDocxDocument)
    sections = extract_reference_document("policy.docx", b"PK\x03\x04" + b"x" * 20)
    assert sections[0]["id"] == "s1"


def test_extract_reference_document_dispatches_pdf(monkeypatch):
    import grounding.ingest as ingest_mod
    monkeypatch.setattr(ingest_mod, "PdfReader", FakePdfReader)
    sections = extract_reference_document("policy.pdf", b"%PDF-1.4\nfake")
    assert sections[0]["id"] == "p1"


def test_extract_reference_document_dispatches_docx(monkeypatch):
    import grounding.ingest as ingest_mod
    monkeypatch.setattr(ingest_mod, "Document", FakeDocxDocument)
    sections = extract_reference_document("policy.docx", b"PK\x03\x04fake")
    assert sections[0]["id"] == "s1"


def test_extract_reference_document_dispatches_txt():
    sections = extract_reference_document("policy.txt", b"Plain text content.")
    assert sections[0]["text"] == "Plain text content."


def test_extract_reference_document_rejects_unsupported_extension():
    with pytest.raises(UnsupportedFileType):
        extract_reference_document("policy.exe", b"fake")


def test_extract_reference_document_rejects_oversized_text():
    huge = "x" * (MAX_EXTRACTED_CHARS + 1)
    with pytest.raises(DocumentTooLarge):
        extract_reference_document("policy.txt", huge.encode("utf-8"))


def test_extract_reference_document_rejects_empty_extraction(monkeypatch):
    import grounding.ingest as ingest_mod

    class EmptyReader:
        def __init__(self, b):
            self.pages = [FakePage("")]

    monkeypatch.setattr(ingest_mod, "PdfReader", EmptyReader)
    with pytest.raises(ValueError, match="no extractable text"):
        extract_reference_document("empty.pdf", b"%PDF-1.4\nfake")
