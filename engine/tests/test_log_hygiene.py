import io
import logging
from datetime import date
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from grounding.api import create_app
from grounding.quota import mint_device_token

SECRET = b"test-secret"
SENTINEL_DOC = "CANARY_DOC_TEXT_zzz987 confidential clause"
SENTINEL_AI = "CANARY_AI_OUTPUT_zzz987 sensitive summary"
FAKE_KEY = "sk-ant-CANARYKEY0000000000"


class _Cur:
    def __init__(self, store): self.store = store; self._last = None
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def execute(self, sql, params):
        if "INSERT INTO gi_device_lock" in sql: self._last = (params[0],)
        elif "INSERT INTO gi_quota" in sql: self._last = (1,)
        else: self._last = None
    def fetchone(self): return self._last


class _Conn:
    def __init__(self, store): self.store = store
    def cursor(self): return _Cur(self.store)
    def commit(self): pass
    def close(self): pass


def _client(anthropic_client):
    app = create_app(client=anthropic_client, db_conn_factory=lambda: _Conn({}),
                     device_token_secret=SECRET)
    return TestClient(app)


def test_pipeline_failure_does_not_log_raw_document_or_ai_text(caplog, monkeypatch):
    # A generic pipeline fault. The fake deliberately does NOT interpolate the
    # request body or an API key into its message: this test pins our own
    # logging hygiene (the /check handler must never echo the submitted
    # ai_output, the uploaded document text, or a key into the logs), not the
    # traceback-formatting behaviour of whatever exception the real pipeline
    # happens to raise.
    def boom(*a, **k):
        raise RuntimeError("live check pipeline failed (simulated)")

    import grounding.api as api_mod
    monkeypatch.setattr(api_mod, "run_live_check", boom)  # bypass the real pipeline
    caplog.set_level(logging.DEBUG)
    client = _client(MagicMock())
    client.cookies.set("gi_device_token", mint_device_token(SECRET))
    r = client.post("/check", data={"ai_output": SENTINEL_AI},
                    files={"reference_file": ("p.txt", io.BytesIO(SENTINEL_DOC.encode()), "text/plain")})
    assert r.status_code == 502
    assert SENTINEL_DOC not in caplog.text
    assert SENTINEL_AI not in caplog.text
    assert "CANARY_AI_OUTPUT" not in caplog.text
    assert "CANARY_DOC_TEXT" not in caplog.text
    # our code must never construct or forward a log message with a key in it.
    assert FAKE_KEY not in caplog.text
    assert "sk-ant-" not in caplog.text


def test_extraction_failure_does_not_log_the_uploaded_filename(caplog):
    # reference_file.filename is the raw multipart Content-Disposition value:
    # unbounded and attacker-controlled. It must not reach the logs via an
    # exception message we build ourselves.
    caplog.set_level(logging.DEBUG)
    client = _client(MagicMock())
    client.cookies.set("gi_device_token", mint_device_token(SECRET))
    r = client.post(
        "/check", data={"ai_output": "x"},
        files={"reference_file": ("CANARY_FNAME_zzz.pdf",
                                  io.BytesIO(b"definitely not a pdf"), "application/pdf")},
    )
    assert r.status_code == 400
    assert "CANARY_FNAME_zzz" not in caplog.text
    assert "CANARY_FNAME" not in caplog.text


def test_decompose_parse_error_message_has_no_model_text():
    from grounding.decompose import decompose_output_claude

    class FakeBlock:
        text = '{"claim": "x"  <<< MODEL EMITTED GARBAGE HERE >>>'

    class FakeMsg:
        content = [FakeBlock()]

    class FakeMsgs:
        def create(self, **k): return FakeMsg()

    class FakeClient:
        messages = FakeMsgs()

    import pytest
    with pytest.raises(ValueError) as ei:
        decompose_output_claude("input", FakeClient())
    assert "MODEL EMITTED GARBAGE" not in str(ei.value)
