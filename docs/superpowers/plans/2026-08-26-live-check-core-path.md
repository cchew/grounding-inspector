# Live Document Upload — Core Check Path Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship build cycle 1 from the live-upload design — a live FastAPI-on-Modal backend that lets a visitor upload a PDF/DOCX/TXT reference document plus pasted AI output and get a real grounding check, wired to a new default-landing "check your document" view in the existing Vue frontend, gated by a device-token free-tier quota.

**Architecture:** New `engine/grounding/ingest.py` extracts page-aware sections from an uploaded file. New `engine/grounding/live.py` orchestrates the existing `decompose_output_claude` → `label_claims` → `groundedness` pipeline into one live-check call, deliberately without a `scorecard` (see Global Constraints). New `engine/quota.py` provides signed device tokens and atomic Postgres-backed quota/lock primitives. New `engine/api.py` (FastAPI) wires these together behind a `POST /check` endpoint; `engine/modal_app.py` deploys it on Modal, matching the existing Act Alike (`term-comparison`) deploy pattern. The frontend gains `web/src/components/UploadView.vue` as the new default view, with the existing fixture browser demoted to a secondary link.

**Tech Stack:** Python 3.11 (FastAPI, psycopg[binary] 3.x, pypdf, python-docx, anthropic), Modal (deployment), Neon Postgres (existing instance, new table), Vue 3 + Vite + TypeScript (existing frontend), vitest + Playwright (existing test stack).

**Spec:** `docs/superpowers/specs/2026-08-26-live-upload-design.md`

## Global Constraints

- **No live-check `scorecard`**: recall/kappa are corpus-level validation stats measured once against a benchmark, not computable per live document. All five committed fixtures use `verifier_model: "flan-t5-large"` (MiniCheck); the live path runs Claude only. Reusing MiniCheck's numbers for a Claude-verified result would misrepresent that verifier's actual measured reliability — never populate a live result's response with MiniCheck's recall/kappa/CI numbers. Live results get `live_disclosure` prose instead (Task 7).
- **File size cap**: `MAX_UPLOAD_BYTES = 10 * 1024 * 1024` (10MB) — bounds both cost and memory.
- **Extracted text cap**: `MAX_EXTRACTED_CHARS = 60_000` (~12-15 pages) — bounds `decompose`/`verify` API cost per request.
- **AI-output text cap**: `MAX_AI_OUTPUT_CHARS = 20_000`.
- **Free-tier daily quota**: `FREE_TIER_DAILY_LIMIT = 3` checks per device token per day.
- **Per-IP backstop**: `IP_DAILY_BACKSTOP = 50` checks per IP per day — a day-granularity backstop (not hourly) for cycle-1 simplicity, since the quota table is date-keyed; high enough to never bother a shared-IP office, low enough to blunt direct scripted abuse.
- **CORS**: `allow_origins` is an explicit list (`https://grounding-inspector.netlify.app`, `http://localhost:5173`), never `["*"]` — this endpoint holds per-user quota state tied to cookies, unlike Act Alike's open `/definitions` endpoint.
- **No BYO-key, no retention**: out of scope for this plan (build cycles 3 and 4 per the spec's sequencing). The `/check` endpoint only supports the free-tier device-token path.
- **Error responses never leak exception text** — every pipeline failure returns a fixed generic message; details are logged server-side only.
- **Reuse, don't duplicate**: the live path calls the existing `decompose_output_claude`, `label_claims`, `groundedness`, `verify_subclaim_claude` functions directly — never reimplement pipeline logic.

---

### Task 1: Document ingestion (`engine/grounding/ingest.py`)

**Files:**
- Create: `engine/grounding/ingest.py`
- Test: `engine/tests/test_ingest.py`
- Modify: `engine/requirements.txt` (add `pypdf>=5.0`, `python-docx>=1.1`)

**Interfaces:**
- Produces: `extract_pdf(file_bytes: bytes) -> list[dict]`, `extract_docx(file_bytes: bytes) -> list[dict]`, `extract_plain_text(text: str) -> list[dict]`, `extract_reference_document(filename: str, file_bytes: bytes) -> list[dict]`, exceptions `UnsupportedFileType(ValueError)`, `DocumentTooLarge(ValueError)`, constant `MAX_EXTRACTED_CHARS = 60_000`. Every returned section dict matches the fixture schema's section shape: `{"id": str, "page": int, "char_start": int, "char_end": int, "text": str}`.

- [ ] **Step 1: Add the new dependencies**

Edit `engine/requirements.txt`, add two lines:
```
pypdf>=5.0
python-docx>=1.1
```
Run: `cd engine && pip install -r requirements.txt`

- [ ] **Step 2: Write the failing tests**

Create `engine/tests/test_ingest.py`:
```python
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
    assert sections == [{"id": "s1", "page": 1, "char_start": 0, "char_end": 11, "text": "Hello world."}]


def test_extract_plain_text_empty_returns_no_sections():
    assert extract_plain_text("   ") == []


def test_extract_reference_document_dispatches_pdf(monkeypatch):
    import grounding.ingest as ingest_mod
    monkeypatch.setattr(ingest_mod, "PdfReader", FakePdfReader)
    sections = extract_reference_document("policy.pdf", b"fake")
    assert sections[0]["id"] == "p1"


def test_extract_reference_document_dispatches_docx(monkeypatch):
    import grounding.ingest as ingest_mod
    monkeypatch.setattr(ingest_mod, "Document", FakeDocxDocument)
    sections = extract_reference_document("policy.docx", b"fake")
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
        extract_reference_document("empty.pdf", b"fake")
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd engine && python -m pytest tests/test_ingest.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'grounding.ingest'`

- [ ] **Step 4: Write the implementation**

Create `engine/grounding/ingest.py`:
```python
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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd engine && python -m pytest tests/test_ingest.py -v`
Expected: PASS (13 tests)

- [ ] **Step 6: Commit**

```bash
git add engine/grounding/ingest.py engine/tests/test_ingest.py engine/requirements.txt
git commit -m "feat: add PDF/DOCX/TXT ingestion for live document uploads"
```

---

### Task 2: Live-check orchestration (`engine/grounding/live.py`)

**Files:**
- Create: `engine/grounding/live.py`
- Test: `engine/tests/test_live.py`

**Interfaces:**
- Consumes: `decompose_output_claude(text: str, client, model: str = "claude-haiku-4-5-20251001") -> list[dict]` from `grounding.decompose`; `label_claims(decomposed, full_text, sections, verifier_fn, recorder=None, verifier_model="unknown") -> list[dict]` from `grounding.pipeline`; `groundedness(labels: list[str]) -> dict` from `grounding.metrics`; `verify_subclaim_claude(subclaim, doc_chunks, client, model) -> bool` from `grounding.verify`.
- Produces: `run_live_check(ai_output: str, sections: list[dict], client, verifier_model: str = DEFAULT_VERIFIER_MODEL) -> dict`, constant `DEFAULT_VERIFIER_MODEL = "claude-haiku-4-5-20251001"`. Returns `{"ai_output": str, "source": {"sections": [...]}, "claims": [...], "groundedness": {...}, "verifier_model": str}` — no `scorecard` key.

- [ ] **Step 1: Write the failing tests**

Create `engine/tests/test_live.py`:
```python
import json

from grounding.live import run_live_check

SECTIONS = [
    {"id": "s1", "page": 1, "char_start": 0, "char_end": 40, "text": "Medical expenses covered up to $10,000."},
]


class FakeContentBlock:
    def __init__(self, text):
        self.text = text


class FakeMessage:
    def __init__(self, text):
        self.content = [FakeContentBlock(text)]


class FakeMessages:
    def __init__(self, decompose_response, verify_responses):
        self.decompose_response = decompose_response
        self.verify_responses = list(verify_responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if len(self.calls) == 1:
            return FakeMessage(self.decompose_response)
        return FakeMessage(self.verify_responses.pop(0))


class FakeClient:
    def __init__(self, decompose_response, verify_responses):
        self.messages = FakeMessages(decompose_response, verify_responses)


def test_run_live_check_returns_claims_and_groundedness_no_scorecard():
    decompose_json = json.dumps([
        {"claim": "Medical is covered up to $10,000.", "subclaims": ["medical covered to $10,000"]},
    ])
    client = FakeClient(decompose_json, ["SUPPORTED"])
    result = run_live_check("Medical is covered up to $10,000.", SECTIONS, client)
    assert result["claims"][0]["label"] == "grounded"
    assert result["groundedness"]["n_grounded"] == 1
    assert "scorecard" not in result
    assert result["verifier_model"] == "claude-haiku-4-5-20251001"
    assert result["ai_output"] == "Medical is covered up to $10,000."
    assert result["source"]["sections"] == SECTIONS


def test_run_live_check_unsupported_subclaim_yields_unsupported_label():
    decompose_json = json.dumps([
        {"claim": "Dental is fully covered.", "subclaims": ["dental fully covered"]},
    ])
    client = FakeClient(decompose_json, ["UNSUPPORTED"])
    result = run_live_check("Dental is fully covered.", SECTIONS, client)
    assert result["claims"][0]["label"] == "unsupported"


def test_run_live_check_uses_custom_verifier_model():
    decompose_json = json.dumps([{"claim": "x", "subclaims": ["x"]}])
    client = FakeClient(decompose_json, ["SUPPORTED"])
    result = run_live_check("x", SECTIONS, client, verifier_model="claude-opus-4")
    assert result["verifier_model"] == "claude-opus-4"
    assert client.messages.calls[1]["model"] == "claude-opus-4"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd engine && python -m pytest tests/test_live.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'grounding.live'`

- [ ] **Step 3: Write the implementation**

Create `engine/grounding/live.py`:
```python
from grounding.decompose import decompose_output_claude
from grounding.metrics import groundedness
from grounding.pipeline import label_claims
from grounding.verify import verify_subclaim_claude

DEFAULT_VERIFIER_MODEL = "claude-haiku-4-5-20251001"


def _claude_verifier(client, model):
    def verify(subclaim, chunks):
        return (verify_subclaim_claude(subclaim, chunks, client, model), None, None)
    return verify


def run_live_check(
    ai_output: str, sections: list[dict], client, verifier_model: str = DEFAULT_VERIFIER_MODEL,
) -> dict:
    """Orchestrates a single live grounding check: decompose -> verify -> label -> score.

    Deliberately returns no `scorecard` -- recall/kappa are corpus-level
    validation stats with no committed measurement for the live Claude
    verifier (every committed fixture validates flan-t5-large/MiniCheck
    instead). Reusing those numbers here would misrepresent this verifier's
    actual measured reliability. Callers needing a user-facing disclosure
    should use `verifier_model` to build one, not fabricate scorecard fields.
    """
    full_text = "".join(s["text"] for s in sections)
    decomposed = decompose_output_claude(ai_output, client)
    verifier_fn = _claude_verifier(client, verifier_model)
    claims = label_claims(decomposed, full_text, sections, verifier_fn, verifier_model=verifier_model)
    return {
        "ai_output": ai_output,
        "source": {"sections": sections},
        "claims": claims,
        "groundedness": groundedness([c["label"] for c in claims]),
        "verifier_model": verifier_model,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd engine && python -m pytest tests/test_live.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add engine/grounding/live.py engine/tests/test_live.py
git commit -m "feat: add live grounding-check orchestration"
```

---

### Task 3: Device-token quota (`engine/grounding/quota.py`)

**Files:**
- Create: `engine/grounding/quota.py`
- Create: `engine/db/schema.sql`
- Test: `engine/tests/test_quota.py`
- Modify: `engine/requirements.txt` (add `psycopg[binary]>=3.2`)

**Interfaces:**
- Produces: `mint_device_token(secret: bytes) -> str`, `verify_device_token(token: str, secret: bytes) -> str | None`, `check_and_increment(conn, quota_key: str, daily_limit: int, today: date | None = None) -> bool`, `try_acquire_device_lock(conn, device_token: str) -> bool`.

- [ ] **Step 1: Add the new dependency and schema file**

Edit `engine/requirements.txt`, add:
```
psycopg[binary]>=3.2
```

Create `engine/db/schema.sql`:
```sql
CREATE TABLE IF NOT EXISTS gi_quota (
    quota_key TEXT NOT NULL,
    check_date DATE NOT NULL,
    checks_used INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (quota_key, check_date)
);
```

Run: `cd engine && pip install -r requirements.txt`

- [ ] **Step 2: Write the failing pure-function tests**

Create `engine/tests/test_quota.py`:
```python
import os
from datetime import date

import pytest

from grounding.quota import check_and_increment, mint_device_token, try_acquire_device_lock, verify_device_token

SECRET = b"test-secret-not-used-in-prod"


def test_mint_and_verify_roundtrip():
    token = mint_device_token(SECRET)
    assert verify_device_token(token, SECRET) is not None


def test_verify_rejects_tampered_token():
    token = mint_device_token(SECRET)
    tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
    assert verify_device_token(tampered, SECRET) is None


def test_verify_rejects_token_signed_with_different_secret():
    token = mint_device_token(SECRET)
    assert verify_device_token(token, b"a-different-secret") is None


def test_verify_rejects_garbage_input():
    assert verify_device_token("not-base64-!!!", SECRET) is None
    assert verify_device_token("", SECRET) is None


def test_two_mints_produce_different_tokens():
    assert mint_device_token(SECRET) != mint_device_token(SECRET)


# --- Integration tests against a real Postgres, opt-in only ---
# Set GI_TEST_DATABASE_URL to a real (throwaway) Postgres connection string to
# run these -- e.g. `docker run -p 5433:5432 -e POSTGRES_PASSWORD=x postgres:16`
# then `export GI_TEST_DATABASE_URL=postgresql://postgres:x@localhost:5433/postgres`.
# Matches this repo's existing convention of gating real-external-dependency
# tests behind an explicit opt-in (see comprehensiveness_qa's allow_llm_calls)
# rather than mocking Postgres-specific semantics (ON CONFLICT upsert
# atomicity, advisory locks) that a fake connection object can't meaningfully
# reproduce.
DB_URL = os.environ.get("GI_TEST_DATABASE_URL")
requires_db = pytest.mark.skipif(not DB_URL, reason="GI_TEST_DATABASE_URL not set")


@pytest.fixture
def db_conn():
    import psycopg

    conn = psycopg.connect(DB_URL)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS gi_quota ("
        "quota_key TEXT NOT NULL, check_date DATE NOT NULL, "
        "checks_used INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (quota_key, check_date))"
    )
    conn.execute("DELETE FROM gi_quota WHERE quota_key LIKE 'test:%'")
    conn.commit()
    yield conn
    conn.execute("DELETE FROM gi_quota WHERE quota_key LIKE 'test:%'")
    conn.commit()
    conn.close()


@requires_db
def test_check_and_increment_allows_under_limit(db_conn):
    assert check_and_increment(db_conn, "test:device-a", daily_limit=3, today=date(2026, 1, 1)) is True
    assert check_and_increment(db_conn, "test:device-a", daily_limit=3, today=date(2026, 1, 1)) is True


@requires_db
def test_check_and_increment_blocks_over_limit(db_conn):
    for _ in range(2):
        check_and_increment(db_conn, "test:device-b", daily_limit=2, today=date(2026, 1, 1))
    assert check_and_increment(db_conn, "test:device-b", daily_limit=2, today=date(2026, 1, 1)) is False


@requires_db
def test_check_and_increment_resets_on_new_day(db_conn):
    for _ in range(2):
        check_and_increment(db_conn, "test:device-c", daily_limit=2, today=date(2026, 1, 1))
    assert check_and_increment(db_conn, "test:device-c", daily_limit=2, today=date(2026, 1, 1)) is False
    assert check_and_increment(db_conn, "test:device-c", daily_limit=2, today=date(2026, 1, 2)) is True


@requires_db
def test_advisory_lock_blocks_concurrent_acquire(db_conn):
    import psycopg

    second_conn = psycopg.connect(DB_URL)
    try:
        assert try_acquire_device_lock(db_conn, "test-device-lock") is True
        assert try_acquire_device_lock(second_conn, "test-device-lock") is False
    finally:
        second_conn.close()
```

- [ ] **Step 3: Run the pure-function tests to verify they fail**

Run: `cd engine && python -m pytest tests/test_quota.py -v -k "not requires_db"`
Expected: FAIL with `ModuleNotFoundError: No module named 'grounding.quota'`

- [ ] **Step 4: Write the implementation**

Create `engine/grounding/quota.py` (inside the `grounding` package, alongside `ingest.py`, so the import resolves via the existing `engine/conftest.py` sys.path setup):
```python
import base64
import hashlib
import hmac
import secrets
from datetime import date

TOKEN_BYTES = 16


def mint_device_token(secret: bytes) -> str:
    raw = secrets.token_bytes(TOKEN_BYTES)
    sig = hmac.new(secret, raw, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(raw + sig).decode("ascii")


def verify_device_token(token: str, secret: bytes) -> str | None:
    try:
        decoded = base64.urlsafe_b64decode(token.encode("ascii"))
    except Exception:
        return None
    if len(decoded) != TOKEN_BYTES + 32:
        return None
    raw, sig = decoded[:TOKEN_BYTES], decoded[TOKEN_BYTES:]
    expected = hmac.new(secret, raw, hashlib.sha256).digest()
    if not hmac.compare_digest(sig, expected):
        return None
    return base64.urlsafe_b64encode(raw).decode("ascii")


def check_and_increment(conn, quota_key: str, daily_limit: int, today: date | None = None) -> bool:
    """Atomically increments quota_key's usage for `today` and returns True if
    the request is allowed, False if the caller is already at daily_limit.
    Single INSERT..ON CONFLICT statement so two concurrent requests for the
    same key can't both read a stale count and both be admitted."""
    today = today or date.today()
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO gi_quota (quota_key, check_date, checks_used)
            VALUES (%s, %s, 1)
            ON CONFLICT (quota_key, check_date)
            DO UPDATE SET checks_used = gi_quota.checks_used + 1
            WHERE gi_quota.checks_used < %s
            RETURNING checks_used
            """,
            (quota_key, today, daily_limit),
        )
        row = cur.fetchone()
    conn.commit()
    return row is not None


def try_acquire_device_lock(conn, device_token: str) -> bool:
    """Non-blocking Postgres advisory lock keyed by the device token, scoped
    to this connection -- released automatically when the connection closes.
    Prevents a burst of concurrent requests from the same device from
    overlapping; the daily count alone only bounds totals, not concurrency."""
    with conn.cursor() as cur:
        cur.execute("SELECT pg_try_advisory_lock(hashtext(%s))", (device_token,))
        return cur.fetchone()[0]
```

- [ ] **Step 5: Run the pure-function tests to verify they pass**

Run: `cd engine && python -m pytest tests/test_quota.py -v -k "not requires_db"`
Expected: PASS (5 tests)

- [ ] **Step 6: Run the DB integration tests if a test database is available**

If `GI_TEST_DATABASE_URL` is set:
Run: `cd engine && python -m pytest tests/test_quota.py -v`
Expected: PASS (9 tests). If not set, these 4 tests are skipped — that's fine for this task; they'll run for real once Task 5 provisions the Neon connection.

- [ ] **Step 7: Commit**

```bash
git add engine/grounding/quota.py engine/db/schema.sql engine/tests/test_quota.py engine/requirements.txt
git commit -m "feat: add signed device-token quota and advisory-lock primitives"
```

---

### Task 4: FastAPI check endpoint (`engine/grounding/api.py`)

**Files:**
- Create: `engine/grounding/api.py`
- Test: `engine/tests/test_api.py`
- Modify: `engine/requirements.txt` (add `fastapi>=0.115`, `python-multipart>=0.0.9`)

**Interfaces:**
- Consumes: `extract_reference_document(filename, file_bytes) -> list[dict]`, `UnsupportedFileType`, `DocumentTooLarge` from `grounding.ingest`; `run_live_check(ai_output, sections, client, verifier_model=...) -> dict` from `grounding.live`; `mint_device_token`, `verify_device_token`, `check_and_increment`, `try_acquire_device_lock` from `grounding.quota`.
- Produces: `create_app(client, db_conn_factory, device_token_secret: bytes) -> FastAPI` — `db_conn_factory` is a zero-arg callable returning a fresh `psycopg` connection (a factory, not a shared connection, since Modal can run concurrent requests per container).

- [ ] **Step 1: Write the failing tests**

Create `engine/tests/test_api.py`:
```python
import io
from datetime import date
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from grounding.api import FREE_TIER_DAILY_LIMIT, MAX_AI_OUTPUT_CHARS, MAX_UPLOAD_BYTES, create_app
from grounding.quota import mint_device_token

SECRET = b"test-secret"


class FakeCursor:
    def __init__(self, store, held_locks):
        self.store = store
        self.held_locks = held_locks
        self._last = None

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, params):
        if "pg_try_advisory_lock" in sql:
            key = params[0]
            if self.store["locks"].get(key):
                self._last = (False,)
            else:
                self.store["locks"][key] = True
                self.held_locks.add(key)
                self._last = (True,)
        elif "INSERT INTO gi_quota" in sql:
            quota_key, check_date, limit = params
            used = self.store["quota"].get((quota_key, check_date), 0)
            if used < limit:
                self.store["quota"][(quota_key, check_date)] = used + 1
                self._last = (used + 1,)
            else:
                self._last = None

    def fetchone(self):
        return self._last


class FakeConn:
    def __init__(self, store):
        self.store = store
        self.held_locks = set()

    def cursor(self):
        return FakeCursor(self.store, self.held_locks)

    def commit(self):
        pass

    def close(self):
        for key in self.held_locks:
            self.store["locks"].pop(key, None)


def _make_client(anthropic_client=None, quota_store=None):
    store = quota_store if quota_store is not None else {"quota": {}, "locks": {}}
    app = create_app(
        client=anthropic_client or MagicMock(),
        db_conn_factory=lambda: FakeConn(store),
        device_token_secret=SECRET,
    )
    return TestClient(app), store


def _files():
    return {"reference_file": ("policy.txt", io.BytesIO(b"Medical is covered up to $10,000."), "text/plain")}


def test_check_rejects_ai_output_over_limit():
    client, _ = _make_client()
    response = client.post("/check", data={"ai_output": "x" * (MAX_AI_OUTPUT_CHARS + 1)}, files=_files())
    assert response.status_code == 400


def test_check_rejects_oversized_file():
    client, _ = _make_client()
    big_file = {"reference_file": ("policy.txt", io.BytesIO(b"x" * (MAX_UPLOAD_BYTES + 1)), "text/plain")}
    response = client.post("/check", data={"ai_output": "some claim"}, files=big_file)
    assert response.status_code == 400


def test_check_rejects_unsupported_file_type():
    client, _ = _make_client()
    files = {"reference_file": ("policy.exe", io.BytesIO(b"whatever"), "application/octet-stream")}
    response = client.post("/check", data={"ai_output": "some claim"}, files=files)
    assert response.status_code == 400


def test_check_sets_device_token_cookie_when_absent(monkeypatch):
    import grounding.api as api_mod
    monkeypatch.setattr(api_mod, "run_live_check", lambda *a, **k: {"claims": [], "groundedness": {}})
    client, _ = _make_client()
    response = client.post("/check", data={"ai_output": "x"}, files=_files())
    assert "gi_device_token" in response.cookies


def test_check_reuses_existing_valid_device_token_cookie(monkeypatch):
    import grounding.api as api_mod
    monkeypatch.setattr(api_mod, "run_live_check", lambda *a, **k: {"claims": [], "groundedness": {}})
    client, store = _make_client()
    token = mint_device_token(SECRET)
    client.cookies.set("gi_device_token", token)
    client.post("/check", data={"ai_output": "x"}, files=_files())
    assert store["quota"].get((f"device:{token}", date.today()), 0) == 1


def test_check_blocks_after_daily_limit_exhausted(monkeypatch):
    import grounding.api as api_mod
    monkeypatch.setattr(api_mod, "run_live_check", lambda *a, **k: {"claims": [], "groundedness": {}})
    client, _ = _make_client()
    token = mint_device_token(SECRET)
    client.cookies.set("gi_device_token", token)
    for _ in range(FREE_TIER_DAILY_LIMIT):
        r = client.post("/check", data={"ai_output": "x"}, files=_files())
        assert r.status_code == 200
    r = client.post("/check", data={"ai_output": "x"}, files=_files())
    assert r.status_code == 429


def test_check_returns_generic_message_on_pipeline_failure(monkeypatch):
    import grounding.api as api_mod

    def failing_check(*a, **k):
        raise RuntimeError("some internal detail that must not leak")

    monkeypatch.setattr(api_mod, "run_live_check", failing_check)
    client, _ = _make_client()
    response = client.post("/check", data={"ai_output": "x"}, files=_files())
    assert response.status_code == 502
    assert "internal detail" not in response.text


def test_check_success_returns_claims_and_groundedness(monkeypatch):
    import grounding.api as api_mod
    fake_result = {"claims": [{"id": "c1", "label": "grounded"}], "groundedness": {"score": 100}}
    monkeypatch.setattr(api_mod, "run_live_check", lambda *a, **k: fake_result)
    client, _ = _make_client()
    response = client.post("/check", data={"ai_output": "x"}, files=_files())
    assert response.status_code == 200
    assert response.json() == fake_result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd engine && python -m pytest tests/test_api.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'grounding.api'`

- [ ] **Step 3: Add the new dependencies**

Edit `engine/requirements.txt`, add:
```
fastapi>=0.115
python-multipart>=0.0.9
```
Run: `cd engine && pip install -r requirements.txt`

- [ ] **Step 4: Write the implementation**

Create `engine/grounding/api.py`:
```python
from __future__ import annotations

import logging
from datetime import date

from fastapi import FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from grounding.ingest import DocumentTooLarge, UnsupportedFileType, extract_reference_document
from grounding.live import run_live_check
from grounding.quota import check_and_increment, mint_device_token, try_acquire_device_lock, verify_device_token

logger = logging.getLogger("grounding_inspector.api")

MAX_AI_OUTPUT_CHARS = 20_000
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
FREE_TIER_DAILY_LIMIT = 3
IP_DAILY_BACKSTOP = 50
DEVICE_TOKEN_COOKIE = "gi_device_token"

ALLOWED_ORIGINS = [
    "https://grounding-inspector.netlify.app",
    "http://localhost:5173",
]


def create_app(client, db_conn_factory, device_token_secret: bytes) -> FastAPI:
    app = FastAPI(title="grounding-inspector-live", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_methods=["POST"],
        allow_headers=["*"],
        allow_credentials=True,
    )

    def _resolve_device_token(request: Request, response: Response) -> str:
        raw = request.cookies.get(DEVICE_TOKEN_COOKIE)
        verified = verify_device_token(raw, device_token_secret) if raw else None
        if verified is not None:
            return raw
        new_token = mint_device_token(device_token_secret)
        response.set_cookie(
            DEVICE_TOKEN_COOKIE, new_token,
            httponly=True, secure=True, samesite="lax", max_age=60 * 60 * 24 * 365,
        )
        return new_token

    @app.post("/check")
    def post_check(
        request: Request,
        response: Response,
        ai_output: str = Form(...),
        reference_file: UploadFile = File(...),
    ) -> dict:
        if len(ai_output) > MAX_AI_OUTPUT_CHARS:
            raise HTTPException(status_code=400, detail=f"AI output exceeds {MAX_AI_OUTPUT_CHARS} characters")

        file_bytes = reference_file.file.read(MAX_UPLOAD_BYTES + 1)
        if len(file_bytes) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=400,
                detail=f"Reference document exceeds {MAX_UPLOAD_BYTES // (1024 * 1024)}MB",
            )

        try:
            sections = extract_reference_document(reference_file.filename or "upload.txt", file_bytes)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        device_token = _resolve_device_token(request, response)
        client_ip = request.client.host if request.client else "unknown"

        conn = db_conn_factory()
        try:
            if not try_acquire_device_lock(conn, device_token):
                raise HTTPException(
                    status_code=429,
                    detail="A check is already running for this device — please wait for it to finish",
                )
            if not check_and_increment(conn, f"device:{device_token}", FREE_TIER_DAILY_LIMIT, date.today()):
                raise HTTPException(status_code=429, detail="Today's free checks are used up. Try again tomorrow.")
            if not check_and_increment(conn, f"ip:{client_ip}", IP_DAILY_BACKSTOP, date.today()):
                raise HTTPException(
                    status_code=429, detail="Too many checks from this network today. Try again tomorrow.",
                )

            try:
                return run_live_check(ai_output, sections, client)
            except Exception:
                logger.exception("live check pipeline failed")
                raise HTTPException(status_code=502, detail="The grounding check failed. Please try again.")
        finally:
            conn.close()

    return app
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd engine && python -m pytest tests/test_api.py -v`
Expected: PASS (8 tests)

- [ ] **Step 6: Run the full engine suite to confirm no regressions**

Run: `cd engine && python -m pytest -v`
Expected: PASS (all existing tests plus the new ones from Tasks 1-4)

- [ ] **Step 7: Commit**

```bash
git add engine/grounding/api.py engine/tests/test_api.py engine/requirements.txt
git commit -m "feat: add POST /check endpoint wiring ingestion, live-check, and quota"
```

---

### Task 5: Modal deployment (`engine/modal_app.py`)

**Files:**
- Create: `engine/modal_app.py`

**Interfaces:**
- Consumes: `create_app` from `grounding.api`.

This task is deploy/ops configuration, not TDD — it has no automated test of its own; correctness is confirmed by the manual smoke-test in Step 5.

- [ ] **Step 1: Write the Modal app**

Create `engine/modal_app.py`:
```python
from __future__ import annotations

from pathlib import Path

import modal

REPO_ROOT = Path(__file__).resolve().parent  # engine/

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        "fastapi>=0.115",
        "python-multipart>=0.0.9",
        "anthropic>=0.30.0",
        "pypdf>=5.0",
        "python-docx>=1.1",
        "psycopg[binary]>=3.2",
    )
    .add_local_python_source("grounding")
)

app = modal.App("grounding-inspector-live", image=image)


@app.function(
    min_containers=1,
    secrets=[
        modal.Secret.from_name("anthropic-api-key"),      # shared with Act Alike — reuse, don't recreate
        modal.Secret.from_name("gi-neon-db"),              # DATABASE_URL
        modal.Secret.from_name("gi-device-token-secret"),  # DEVICE_TOKEN_SECRET
    ],
)
@modal.asgi_app(label="grounding-inspector-live-api")
def fastapi_app():
    import os

    import anthropic
    import psycopg

    from grounding.api import create_app

    client = anthropic.Anthropic()
    database_url = os.environ["DATABASE_URL"]
    device_token_secret = os.environ["DEVICE_TOKEN_SECRET"].encode("utf-8")

    return create_app(
        client=client,
        db_conn_factory=lambda: psycopg.connect(database_url),
        device_token_secret=device_token_secret,
    )
```

- [ ] **Step 2: Apply the quota table to the existing Neon instance**

Run: `psql "$DATABASE_URL" -f engine/db/schema.sql` (using the same Neon connection string that already backs self-hosted Umami — confirm with Ching before running against that instance if the URL isn't already at hand locally)

- [ ] **Step 3: Create the two new Modal secrets**

Run:
```bash
modal secret create gi-neon-db DATABASE_URL="<neon-connection-string>"
modal secret create gi-device-token-secret DEVICE_TOKEN_SECRET="$(openssl rand -hex 32)"
modal secret list  # confirm anthropic-api-key already exists from Act Alike — reuse it, do not recreate
```

- [ ] **Step 4: Deploy**

Run: `cd engine && modal deploy modal_app.py`
Expected output includes a deployed URL of the form `https://<workspace>--grounding-inspector-live-api.modal.run`

- [ ] **Step 5: Manual smoke test against the real deployment**

Run:
```bash
curl -s -X POST "<deployed-url>/check" \
  -F "ai_output=Medical is covered up to \$10,000." \
  -F "reference_file=@/tmp/smoke-test.txt;type=text/plain"
```
(first create `/tmp/smoke-test.txt` with a short line of text, e.g. `echo "Medical expenses covered up to \$10,000." > /tmp/smoke-test.txt`)
Expected: HTTP 200, JSON body with `claims` and `groundedness` keys, a `Set-Cookie: gi_device_token=...` response header.

- [ ] **Step 6: Record the deployed URL and commit**

```bash
git add engine/modal_app.py
git commit -m "feat: deploy live-check API to Modal"
```

---

### Task 6: Frontend types and the check API client

**Files:**
- Modify: `web/src/types.ts`
- Create: `web/src/live-check-api.ts`
- Test: `web/tests/live-check-api.test.ts`

**Interfaces:**
- Produces: `LiveCheckResult` type in `types.ts`; `Fixture.scorecard` becomes optional (`scorecard?: Scorecard`); new optional `Fixture.live_disclosure?: string`; `checkDocument(aiOutput: string, file: File) -> Promise<Fixture>` in `live-check-api.ts`.

- [ ] **Step 1: Edit types.ts**

In `web/src/types.ts`, change:
```ts
export interface Fixture {
  fixture_id: string;
  source: { title: string; sections: Section[] };
  ai_output: string;
  claims: Claim[];
  groundedness: Groundedness;
  scorecard: Scorecard;
  omissions?: OmissionEntry[];
}
```
to:
```ts
export interface Fixture {
  fixture_id: string;
  source: { title: string; sections: Section[] };
  ai_output: string;
  claims: Claim[];
  groundedness: Groundedness;
  // Optional: live-check results have no corpus-level validation stats (see
  // live_disclosure below) — only browsed fixtures carry a real scorecard.
  scorecard?: Scorecard;
  omissions?: OmissionEntry[];
  // Present only for live-check results; HelpModal shows this in place of
  // the scorecard-based domain-note paragraph when set.
  live_disclosure?: string;
}

export interface LiveCheckApiResponse {
  ai_output: string;
  source: { sections: Section[] };
  claims: Claim[];
  groundedness: Groundedness;
  verifier_model: string;
}
```

- [ ] **Step 2: Write the failing test**

Create `web/tests/live-check-api.test.ts`:
```ts
import { describe, it, expect, vi, beforeEach } from "vitest";
import { checkDocument } from "../src/live-check-api";

beforeEach(() => {
  global.fetch = vi.fn();
});

function makeFile(content: string, name = "policy.txt") {
  return new File([content], name, { type: "text/plain" });
}

describe("checkDocument", () => {
  it("posts multipart form data and returns a fixture-shaped result", async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            ai_output: "Medical is covered up to $10,000.",
            source: { sections: [{ id: "s1", page: 1, char_start: 0, char_end: 10, text: "Medical..." }] },
            claims: [
              { id: "c1", text: "x", label: "grounded", evidence_span_ids: [], quote: null, page: null, rationale: "" },
            ],
            groundedness: { score: 100, n_grounded: 1, n_partial: 0, n_unsupported: 0 },
            verifier_model: "claude-haiku-4-5-20251001",
          }),
      } as Response)
    ) as unknown as typeof fetch;

    const result = await checkDocument("Medical is covered up to $10,000.", makeFile("Medical..."));

    expect(result.fixture_id).toBe("live-check");
    expect(result.claims[0].label).toBe("grounded");
    expect(result.live_disclosure).toContain("claude-haiku-4-5-20251001");

    const [, init] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(init.method).toBe("POST");
    expect(init.credentials).toBe("include");
    expect(init.body).toBeInstanceOf(FormData);
  });

  it("throws the server's error detail on a non-ok response", async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: false,
        status: 429,
        json: () => Promise.resolve({ detail: "Today's free checks are used up. Try again tomorrow." }),
      } as Response)
    ) as unknown as typeof fetch;

    await expect(checkDocument("x", makeFile("y"))).rejects.toThrow("free checks are used up");
  });

  it("falls back to a status-code message when the response has no JSON body", async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({ ok: false, status: 500, json: () => Promise.reject(new Error("no body")) } as Response)
    ) as unknown as typeof fetch;

    await expect(checkDocument("x", makeFile("y"))).rejects.toThrow("HTTP 500");
  });
});
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd web && npx vitest run tests/live-check-api.test.ts`
Expected: FAIL — `Cannot find module '../src/live-check-api'`

- [ ] **Step 4: Write the implementation**

Create `web/src/live-check-api.ts`:
```ts
import type { Fixture, LiveCheckApiResponse } from "./types";

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string) ?? "http://127.0.0.1:8000";

export async function checkDocument(aiOutput: string, file: File): Promise<Fixture> {
  const form = new FormData();
  form.append("ai_output", aiOutput);
  form.append("reference_file", file);

  const res = await fetch(`${API_BASE}/check`, { method: "POST", body: form, credentials: "include" });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail ?? `HTTP ${res.status}`);
  }

  const result = (await res.json()) as LiveCheckApiResponse;
  return {
    fixture_id: "live-check",
    source: { title: file.name, sections: result.source.sections },
    ai_output: result.ai_output,
    claims: result.claims,
    groundedness: result.groundedness,
    live_disclosure:
      `This check used the same Claude verifier (${result.verifier_model}) as Grounding Inspector's other checks. ` +
      "Independent accuracy validation (recall/agreement numbers) exists for the MiniCheck verifier shown in the " +
      "sample fixtures, not yet for this one — treat results as a research signal, not a certified score.",
  };
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd web && npx vitest run tests/live-check-api.test.ts`
Expected: PASS (3 tests)

- [ ] **Step 6: Commit**

```bash
git add web/src/types.ts web/src/live-check-api.ts web/tests/live-check-api.test.ts
git commit -m "feat: add live-check API client and fixture-shaped response types"
```

---

### Task 7: UploadView component and App.vue integration

**Files:**
- Create: `web/src/components/UploadView.vue`
- Test: `web/tests/UploadView.test.ts`
- Modify: `web/src/App.vue`
- Modify: `web/src/components/HelpModal.vue`
- Create: `web/.env.local` (gitignored; not committed) — set `VITE_API_BASE_URL=http://127.0.0.1:8000` for local dev against `uvicorn grounding.api:create_app` or the deployed Modal URL
- Modify: `web/.env.production` (new file if none exists) — `VITE_API_BASE_URL=<the Modal URL from Task 5, Step 4>`

**Interfaces:**
- Consumes: `checkDocument` from `../live-check-api`, `Fixture` from `../types`.
- Produces: `UploadView.vue` emits `result: [Fixture]` and `browseSample: []`.

- [ ] **Step 1: Write the failing component tests**

Create `web/tests/UploadView.test.ts`:
```ts
import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises, type VueWrapper } from "@vue/test-utils";
import UploadView from "../src/components/UploadView.vue";

vi.mock("../src/live-check-api", () => ({
  checkDocument: vi.fn(),
}));

import { checkDocument } from "../src/live-check-api";

beforeEach(() => {
  vi.clearAllMocks();
});

function selectFile(wrapper: VueWrapper, name = "policy.txt") {
  const file = new File(["Medical is covered up to $10,000."], name, { type: "text/plain" });
  const input = wrapper.find('[data-testid="reference-file-input"]');
  Object.defineProperty(input.element, "files", { value: [file], writable: false });
  return input.trigger("change");
}

describe("UploadView", () => {
  it("shows a validation error when submitting without a file", async () => {
    const wrapper = mount(UploadView);
    await wrapper.find('[data-testid="ai-output-input"]').setValue("Some AI claim.");
    await wrapper.find('[data-testid="submit-check"]').trigger("click");
    expect(wrapper.find('[data-testid="upload-error"]').text()).toContain("choose a reference document");
    expect(checkDocument).not.toHaveBeenCalled();
  });

  it("calls checkDocument and emits the result on success", async () => {
    const fakeFixture = {
      fixture_id: "live-check",
      source: { title: "policy.txt", sections: [] },
      ai_output: "Some AI claim.",
      claims: [{ id: "c1", text: "x", label: "grounded", evidence_span_ids: [], quote: null, page: null, rationale: "" }],
      groundedness: { score: 100, n_grounded: 1, n_partial: 0, n_unsupported: 0 },
      live_disclosure: "disclosure text",
    };
    (checkDocument as ReturnType<typeof vi.fn>).mockResolvedValue(fakeFixture);

    const wrapper = mount(UploadView);
    await wrapper.find('[data-testid="ai-output-input"]').setValue("Some AI claim.");
    await selectFile(wrapper);
    await wrapper.find('[data-testid="submit-check"]').trigger("click");
    await flushPromises();

    expect(checkDocument).toHaveBeenCalledWith("Some AI claim.", expect.any(File));
    expect(wrapper.emitted("result")).toBeTruthy();
    expect((wrapper.emitted("result")![0] as [typeof fakeFixture])[0].fixture_id).toBe("live-check");
  });

  it("shows the server's error message on a failed check", async () => {
    (checkDocument as ReturnType<typeof vi.fn>).mockRejectedValue(
      new Error("Today's free checks are used up. Try again tomorrow.")
    );

    const wrapper = mount(UploadView);
    await wrapper.find('[data-testid="ai-output-input"]').setValue("Some AI claim.");
    await selectFile(wrapper);
    await wrapper.find('[data-testid="submit-check"]').trigger("click");
    await flushPromises();

    expect(wrapper.find('[data-testid="upload-error"]').text()).toContain("free checks are used up");
  });

  it("emits browseSample when the sample link is clicked", async () => {
    const wrapper = mount(UploadView);
    await wrapper.find(".sample-link").trigger("click");
    expect(wrapper.emitted("browseSample")).toBeTruthy();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd web && npx vitest run tests/UploadView.test.ts`
Expected: FAIL — `Cannot find module '../src/components/UploadView.vue'`

- [ ] **Step 3: Write UploadView.vue**

Create `web/src/components/UploadView.vue`:
```vue
<script setup lang="ts">
import { ref } from "vue";
import type { Fixture } from "../types";
import { checkDocument } from "../live-check-api";
import { track } from "../analytics";

const emit = defineEmits<{ result: [Fixture]; browseSample: [] }>();

const aiOutput = ref("");
const file = ref<File | null>(null);
const loading = ref(false);
const error = ref<string | null>(null);

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement;
  file.value = input.files?.[0] ?? null;
}

async function submitCheck() {
  if (!aiOutput.value.trim() || !file.value) {
    error.value = "Paste the AI output and choose a reference document first.";
    return;
  }
  loading.value = true;
  error.value = null;
  try {
    const fixture = await checkDocument(aiOutput.value, file.value);
    track("live_check_submitted");
    emit("result", fixture);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Check failed. Please try again.";
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="upload-view">
    <label class="field-label" for="ai-output-input">AI output to check</label>
    <textarea
      id="ai-output-input"
      data-testid="ai-output-input"
      v-model="aiOutput"
      class="ai-output-textarea"
      placeholder="Paste the AI-generated text you want to check for grounding..."
      rows="6"
    ></textarea>

    <label class="field-label" for="reference-file-input">Reference document (PDF, DOCX, or TXT)</label>
    <input
      id="reference-file-input"
      data-testid="reference-file-input"
      type="file"
      accept=".pdf,.docx,.txt"
      @change="onFileChange"
    />

    <button data-testid="submit-check" class="submit-btn" :disabled="loading" @click="submitCheck">
      {{ loading ? "Checking..." : "Check grounding" }}
    </button>

    <p v-if="error" data-testid="upload-error" class="upload-error">{{ error }}</p>

    <button type="button" class="sample-link" @click="$emit('browseSample')">
      No document handy? Try a sample fixture instead.
    </button>
  </div>
</template>

<style scoped>
.upload-view {
  display: flex;
  flex-direction: column;
  gap: var(--s-3);
  max-width: 640px;
  margin: 0 auto;
  padding: var(--s-5) 0;
}
.field-label {
  font-family: var(--font-ui);
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-ink-2);
}
.ai-output-textarea {
  font-family: var(--font-ui);
  font-size: 0.875rem;
  padding: var(--s-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  color: var(--color-ink);
  resize: vertical;
}
.submit-btn {
  font-family: var(--font-ui);
  font-size: 0.875rem;
  font-weight: 600;
  padding: var(--s-2) var(--s-4);
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-ink);
  background: var(--color-ink);
  color: var(--color-bg);
  cursor: pointer;
  align-self: flex-start;
}
.submit-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.upload-error {
  color: var(--chip-unsupported-text);
  font-size: 0.875rem;
}
.sample-link {
  align-self: flex-start;
  font-family: var(--font-ui);
  font-size: 0.75rem;
  background: none;
  border: none;
  color: var(--color-ink-2);
  text-decoration: underline;
  cursor: pointer;
  padding: 0;
}
</style>
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd web && npx vitest run tests/UploadView.test.ts`
Expected: PASS (4 tests)

- [ ] **Step 5: Wire UploadView into App.vue as the default view**

In `web/src/App.vue`, add a `mode` ref and a `liveResult` ref, stop auto-selecting the first fixture on mount, and render `UploadView` by default:

Change the script section — replace:
```ts
const fixtureIds = ref<string[]>([]);
const selectedId = ref<string | null>(null);
const fixture = ref<Fixture | null>(null);
const error = ref<string | null>(null);
const loading = ref(false);
const helpOpen = ref(false);
const appVersion = __APP_VERSION__;
let tourFired = false;

onMounted(async () => {
  track("gate_pass");
  try {
    const res = await fetch("/fixtures/index.json");
    fixtureIds.value = await res.json();
    if (fixtureIds.value.length > 0) selectedId.value = fixtureIds.value[0] ?? null;
  } catch (e) {
    error.value = "Could not load fixture list";
  }
});
```
with:
```ts
import UploadView from "./components/UploadView.vue";

const mode = ref<"upload" | "browse">("upload");
const fixtureIds = ref<string[]>([]);
const selectedId = ref<string | null>(null);
const fixture = ref<Fixture | null>(null);
const liveResult = ref<Fixture | null>(null);
const error = ref<string | null>(null);
const loading = ref(false);
const helpOpen = ref(false);
const appVersion = __APP_VERSION__;
let tourFired = false;

onMounted(async () => {
  track("gate_pass");
  try {
    const res = await fetch("/fixtures/index.json");
    fixtureIds.value = await res.json();
  } catch (e) {
    error.value = "Could not load fixture list";
  }
});

function switchToBrowse() {
  mode.value = "browse";
  liveResult.value = null;
  if (!selectedId.value && fixtureIds.value.length > 0) {
    selectedId.value = fixtureIds.value[0] ?? null;
  }
}

function onLiveResult(result: Fixture) {
  liveResult.value = result;
}
```

Then change the template's `<nav>` and `<main>` sections — replace:
```html
      <nav class="fixture-nav" v-if="fixtureIds.length">
        <button
          v-for="id in fixtureIds"
          :key="id"
          :class="['fixture-btn', { active: id === selectedId }]"
          @click="selectedId = id"
        >{{ label(id) }}</button>
      </nav>
    </header>
    <main>
      <Inspector v-if="fixture" :fixture="fixture" />
      <p v-else-if="error" class="load-error">{{ error }}</p>
      <p v-else-if="loading" class="loading">Loading...</p>
    </main>
```
with:
```html
      <nav class="fixture-nav" v-if="mode === 'browse' && fixtureIds.length">
        <button
          v-for="id in fixtureIds"
          :key="id"
          :class="['fixture-btn', { active: id === selectedId }]"
          @click="selectedId = id"
        >{{ label(id) }}</button>
      </nav>
    </header>
    <main>
      <UploadView
        v-if="mode === 'upload' && !liveResult"
        @result="onLiveResult"
        @browse-sample="switchToBrowse"
      />
      <Inspector v-else-if="mode === 'upload' && liveResult" :fixture="liveResult" />
      <Inspector v-else-if="mode === 'browse' && fixture" :fixture="fixture" />
      <p v-else-if="mode === 'browse' && error" class="load-error">{{ error }}</p>
      <p v-else-if="mode === 'browse' && loading" class="loading">Loading...</p>
    </main>
```

And the `HelpModal` mount at the bottom — replace:
```html
    <HelpModal v-if="fixture" :fixture="fixture" :open="helpOpen" @close="helpOpen = false" />
```
with:
```html
    <HelpModal
      v-if="mode === 'upload' ? liveResult : fixture"
      :fixture="(mode === 'upload' ? liveResult : fixture)!"
      :open="helpOpen"
      @close="helpOpen = false"
    />
```

- [ ] **Step 6: Make HelpModal's domain-note paragraph conditional on live_disclosure**

In `web/src/components/HelpModal.vue`, find the line:
```html
<li><strong>Domain.</strong> The recall/agreement numbers above are measured on RAGTruth, a general summarisation benchmark — not on insurance, legal, or regulatory text. The travel-insurance fixtures shown here are illustrative, not a validated domain.</li>
```
Wrap it in a conditional and add the live-check equivalent immediately after:
```html
<li v-if="!fixture.live_disclosure"><strong>Domain.</strong> The recall/agreement numbers above are measured on RAGTruth, a general summarisation benchmark — not on insurance, legal, or regulatory text. The travel-insurance fixtures shown here are illustrative, not a validated domain.</li>
<li v-else><strong>This check.</strong> {{ fixture.live_disclosure }}</li>
```

- [ ] **Step 7: Set the local dev API base URL**

Create `web/.env.local` (already gitignored — confirm with `git check-ignore web/.env.local`, matching the existing `web/.env.local` gitignore entry used for `VITE_UMAMI_WEBSITE_ID`):
```
VITE_API_BASE_URL=http://127.0.0.1:8000
```

- [ ] **Step 8: Run the full frontend test suite**

Run: `cd web && npm run build && npx vitest run`
Expected: PASS — the build step also catches any TypeScript errors from the `Fixture.scorecard` type change (Step 1 of Task 6) against existing components.

- [ ] **Step 9: Commit**

```bash
git add web/src/App.vue web/src/components/UploadView.vue web/src/components/HelpModal.vue web/tests/UploadView.test.ts
git commit -m "feat: make live document check the default landing view"
```

---

### Task 8: End-to-end coverage for the live-check flow

**Files:**
- Create: `web/tests/e2e-live-check.spec.ts`

**Interfaces:**
- Consumes: `data-testid` attributes from `UploadView.vue` (Task 7) and `.fixture-nav`/`.sample-link` classes from `App.vue`/`UploadView.vue`.

This E2E suite mocks the `/check` network call via Playwright's `page.route()` — matching the existing project convention (the omission-mitigation build's E2E fix used the same interception approach rather than committing test fixtures or hitting a real API) — so it runs in ordinary CI without Anthropic spend. A real-Modal live E2E is deliberately out of scope for this task per the design's testing section (gate that to a manual/pre-release trigger, not routine CI).

- [ ] **Step 1: Write the E2E spec**

Create `web/tests/e2e-live-check.spec.ts`:
```ts
import { test, expect } from "@playwright/test";

test("live check: upload flow renders claims from a mocked API response", async ({ page }) => {
  await page.route("**/check", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        ai_output: "Medical is covered up to $10,000.",
        source: {
          sections: [
            { id: "s1", page: 1, char_start: 0, char_end: 40, text: "Medical expenses covered up to $10,000." },
          ],
        },
        claims: [
          {
            id: "c1",
            text: "Medical is covered up to $10,000.",
            label: "grounded",
            evidence_span_ids: ["s1"],
            quote: "covered up to $10,000",
            page: 1,
            rationale: "",
          },
        ],
        groundedness: { score: 100, n_grounded: 1, n_partial: 0, n_unsupported: 0 },
        verifier_model: "claude-haiku-4-5-20251001",
      }),
    });
  });

  await page.goto("/");
  await expect(page.getByTestId("ai-output-input")).toBeVisible();

  await page.getByTestId("ai-output-input").fill("Medical is covered up to $10,000.");
  await page.getByTestId("reference-file-input").setInputFiles({
    name: "policy.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("Medical expenses covered up to $10,000."),
  });
  await page.getByTestId("submit-check").click();

  await expect(page.getByText("Medical is covered up to $10,000.")).toBeVisible();
});

test("live check: server error surfaces the returned detail message", async ({ page }) => {
  await page.route("**/check", async (route) => {
    await route.fulfill({
      status: 429,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Today's free checks are used up. Try again tomorrow." }),
    });
  });

  await page.goto("/");
  await page.getByTestId("ai-output-input").fill("x");
  await page.getByTestId("reference-file-input").setInputFiles({
    name: "policy.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("y"),
  });
  await page.getByTestId("submit-check").click();

  await expect(page.getByTestId("upload-error")).toContainText("free checks are used up");
});

test("live check: sample link switches to the fixture browser", async ({ page }) => {
  await page.goto("/");
  await page.getByText("No document handy? Try a sample fixture instead.").click();
  await expect(page.locator(".fixture-nav")).toBeVisible();
});
```

- [ ] **Step 2: Run the new E2E spec**

Run: `cd web && npm run build && npx playwright test tests/e2e-live-check.spec.ts`
Expected: PASS (3 tests)

- [ ] **Step 3: Run the full E2E suite to confirm no regressions**

Run: `cd web && npx playwright test`
Expected: PASS (all existing specs plus the 3 new ones)

- [ ] **Step 4: Commit**

```bash
git add web/tests/e2e-live-check.spec.ts
git commit -m "test: add E2E coverage for the live document-check flow"
```

---

## Self-Review Notes

- **Spec coverage**: Architecture (Tasks 4-5), data flow free-tier path (Tasks 3-4), frontend upload-first UX (Tasks 6-7), server-side-only enforcement (Task 4 — quota/size checks all happen in `create_app`, never trusted from the client), device-token limitation disclosure (implicit in the courtesy-limit design, not a UI string — no task requires user-facing copy about it, which is consistent with the spec treating it as an internal design trade-off, not a promise made to users). Security-hardening-pass items (prompt-injection audit across all live-path calls, `v-html` audit) and BYO-key/retention/alerting are explicitly out of scope per the spec's own sequencing (cycles 2-5) — not gaps in this plan.
- **Type consistency checked**: `run_live_check`'s return dict keys (`ai_output`, `source`, `claims`, `groundedness`, `verifier_model`) match what `api.py` passes straight through as the response body, which match `LiveCheckApiResponse` in `types.ts`, which match what `checkDocument` reads in `live-check-api.ts`. `check_and_increment`/`try_acquire_device_lock` signatures are identical between their Task 3 definition and Task 4's `api.py` usage and test fakes.
