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
