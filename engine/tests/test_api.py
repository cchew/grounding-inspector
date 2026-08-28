import io
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from grounding.api import (
    FREE_TIER_DAILY_LIMIT,
    IP_DAILY_BACKSTOP,
    MAX_AI_OUTPUT_CHARS,
    MAX_UPLOAD_BYTES,
    UNREADABLE_DOCUMENT_DETAIL as api_UNREADABLE_DETAIL,
    create_app,
)
from grounding.quota import mint_device_token

SECRET = b"test-secret"


class FakeCursor:
    """Stands in for the four statements grounding.quota issues. Matched on
    the table name plus the statement verb rather than on any single
    Postgres-specific function, so the lease-lock rewrite (which replaced
    pg_try_advisory_lock with an INSERT .. ON CONFLICT on gi_device_lock)
    doesn't silently stop being exercised."""

    def __init__(self, store, held_locks, released_locks):
        self.store = store
        self.held_locks = held_locks
        self.released_locks = released_locks
        self._last = None

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, params):
        if "INSERT INTO gi_device_lock" in sql:
            key = params[0]
            if self.store["locks"].get(key):
                self._last = None  # lease still held by another request
            else:
                self.store["locks"][key] = True
                self.held_locks.add(key)
                self._last = (key,)
        elif "DELETE FROM gi_device_lock" in sql:
            key = params[0]
            self.store["locks"].pop(key, None)
            self.held_locks.discard(key)
            self.released_locks.append(key)
            self._last = None
        elif "INSERT INTO gi_quota" in sql:
            quota_key, check_date, limit = params
            used = self.store["quota"].get((quota_key, check_date), 0)
            if used < limit:
                self.store["quota"][(quota_key, check_date)] = used + 1
                self._last = (used + 1,)
            else:
                self._last = None
        elif "UPDATE gi_quota" in sql:
            quota_key, check_date = params
            used = self.store["quota"].get((quota_key, check_date))
            if used is not None:
                self.store["quota"][(quota_key, check_date)] = max(used - 1, 0)
            self._last = None

    def fetchone(self):
        return self._last


class FakeConn:
    def __init__(self, store):
        self.store = store
        self.held_locks = set()
        self.released_locks = store.setdefault("released_locks", [])

    def cursor(self):
        return FakeCursor(self.store, self.held_locks, self.released_locks)

    def commit(self):
        pass

    def close(self):
        # The real lease row survives a connection close (that's the whole
        # point of I10's rewrite) -- only an explicit release, or lease
        # expiry, frees it. Closing must therefore free nothing here.
        pass


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
    assert "10MB" in response.json()["detail"]


def test_check_rejects_oversized_body_from_content_length_before_parsing(monkeypatch):
    # The Content-Length guard runs as middleware, i.e. before FastAPI's
    # multipart parser touches the body -- so the endpoint must never be
    # entered at all for an over-cap request.
    import grounding.api as api_mod

    def must_not_run(*a, **k):
        raise AssertionError("endpoint body ran despite an over-cap Content-Length")

    monkeypatch.setattr(api_mod, "extract_reference_document", must_not_run)
    client, _ = _make_client()
    response = client.post(
        "/check",
        content=b"x" * (MAX_UPLOAD_BYTES + 1),
        headers={"content-type": "multipart/form-data; boundary=zzz"},
    )
    assert response.status_code == 400
    assert "10MB" in response.json()["detail"]


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


def test_check_sets_device_token_cookie_even_when_first_request_is_rejected_by_quota(monkeypatch):
    # Regression: a first-time visitor (no cookie yet) whose very first
    # request hits an error path after _resolve_device_token must still
    # receive Set-Cookie -- otherwise every retry mints a fresh token and
    # the per-device quota never binds them.
    import grounding.api as api_mod
    monkeypatch.setattr(api_mod, "run_live_check", lambda *a, **k: {"claims": [], "groundedness": {}})
    # TestClient's default client address host is "testclient" -- pre-exhaust
    # the IP backstop so the brand-new device's very first request 429s.
    store = {"quota": {("ip:testclient", date.today()): IP_DAILY_BACKSTOP}, "locks": {}}
    client, _ = _make_client(quota_store=store)
    response = client.post("/check", data={"ai_output": "x"}, files=_files())
    assert response.status_code == 429
    assert "gi_device_token" in response.cookies


def test_check_success_returns_claims_and_groundedness(monkeypatch):
    import grounding.api as api_mod
    fake_result = {"claims": [{"id": "c1", "label": "grounded"}], "groundedness": {"score": 100}}
    monkeypatch.setattr(api_mod, "run_live_check", lambda *a, **k: fake_result)
    client, _ = _make_client()
    response = client.post("/check", data={"ai_output": "x"}, files=_files())
    assert response.status_code == 200
    assert response.json() == fake_result


def test_device_token_cookie_is_samesite_none(monkeypatch):
    # netlify.app -> modal.run is cross-site, so a Lax cookie is never sent
    # back on the frontend's fetch() and the per-device quota never binds.
    import grounding.api as api_mod
    monkeypatch.setattr(api_mod, "run_live_check", lambda *a, **k: {"claims": [], "groundedness": {}})
    client, _ = _make_client()
    response = client.post("/check", data={"ai_output": "x"}, files=_files())
    set_cookie = response.headers["set-cookie"].lower()
    assert "samesite=none" in set_cookie
    assert "secure" in set_cookie


def test_unreadable_document_returns_generic_400_with_cookie():
    # pypdf raises PdfReadError, which is not a ValueError -- it used to
    # escape as an unhandled 500 that also dropped the Set-Cookie header.
    client, _ = _make_client()
    files = {"reference_file": ("policy.pdf", io.BytesIO(b"not a real pdf at all"), "application/pdf")}
    response = client.post("/check", data={"ai_output": "x"}, files=files)
    assert response.status_code == 400
    assert response.json()["detail"] == api_UNREADABLE_DETAIL
    assert "gi_device_token" in response.cookies


def test_pipeline_failure_refunds_the_device_quota(monkeypatch):
    import grounding.api as api_mod

    def failing_check(*a, **k):
        raise RuntimeError("boom")

    monkeypatch.setattr(api_mod, "run_live_check", failing_check)
    client, store = _make_client()
    token = mint_device_token(SECRET)
    client.cookies.set("gi_device_token", token)
    r = client.post("/check", data={"ai_output": "x"}, files=_files())
    assert r.status_code == 502
    assert store["quota"].get((f"device:{token}", date.today()), 0) == 0


def test_ip_backstop_rejection_does_not_burn_device_quota(monkeypatch):
    import grounding.api as api_mod
    monkeypatch.setattr(api_mod, "run_live_check", lambda *a, **k: {"claims": [], "groundedness": {}})
    store = {"quota": {("ip:testclient", date.today()): IP_DAILY_BACKSTOP}, "locks": {}}
    client, _ = _make_client(quota_store=store)
    token = mint_device_token(SECRET)
    client.cookies.set("gi_device_token", token)
    r = client.post("/check", data={"ai_output": "x"}, files=_files())
    assert r.status_code == 429
    assert store["quota"].get((f"device:{token}", date.today()), 0) == 0


def test_device_lock_is_released_when_the_request_finishes(monkeypatch):
    # The lease row outlives the connection, so without an explicit release
    # the next legitimate check from the same device waits out the lease.
    import grounding.api as api_mod
    monkeypatch.setattr(api_mod, "run_live_check", lambda *a, **k: {"claims": [], "groundedness": {}})
    client, store = _make_client()
    token = mint_device_token(SECRET)
    client.cookies.set("gi_device_token", token)
    assert client.post("/check", data={"ai_output": "x"}, files=_files()).status_code == 200
    assert store["locks"] == {}
    assert store["released_locks"] == [token]
    # ...and a second, sequential check is admitted rather than 429ing.
    assert client.post("/check", data={"ai_output": "x"}, files=_files()).status_code == 200


def test_device_lock_blocks_a_concurrent_check_for_the_same_device(monkeypatch):
    import grounding.api as api_mod
    monkeypatch.setattr(api_mod, "run_live_check", lambda *a, **k: {"claims": [], "groundedness": {}})
    token = mint_device_token(SECRET)
    store = {"quota": {}, "locks": {token: True}}  # a check is already in flight
    client, _ = _make_client(quota_store=store)
    client.cookies.set("gi_device_token", token)
    r = client.post("/check", data={"ai_output": "x"}, files=_files())
    assert r.status_code == 429
    assert "already running" in r.json()["detail"]
    # The in-flight request's lease must survive the blocked request's finally.
    assert store["locks"] == {token: True}


def test_check_rejects_a_document_that_fans_out_too_far(monkeypatch):
    import grounding.api as api_mod
    from grounding.live import CheckTooComplex

    def too_complex(*a, **k):
        raise CheckTooComplex("42 claims exceeds the per-check limit")

    monkeypatch.setattr(api_mod, "run_live_check", too_complex)
    client, _ = _make_client()
    r = client.post("/check", data={"ai_output": "x"}, files=_files())
    assert r.status_code == 400
    assert "internal" not in r.text.lower()
    assert "exceeds the per-check limit" not in r.text  # no raw exception text
    assert "gi_device_token" in r.cookies


def test_fan_out_rejection_does_not_burn_device_quota(monkeypatch):
    import grounding.api as api_mod
    from grounding.live import CheckTooComplex

    monkeypatch.setattr(api_mod, "run_live_check", lambda *a, **k: (_ for _ in ()).throw(CheckTooComplex("too big")))
    client, store = _make_client()
    token = mint_device_token(SECRET)
    client.cookies.set("gi_device_token", token)
    r = client.post("/check", data={"ai_output": "x"}, files=_files())
    assert r.status_code == 400
    assert store["quota"].get((f"device:{token}", date.today()), 0) == 0


def _freeze_minute(monkeypatch, api_mod, now=1_700_000_000.0):
    """Pin the clock api.py reads so an epoch-minute rollover mid-test can't
    move the bucket key and let an over-cap request through. Swaps the module's
    `time` binding rather than patching the stdlib module itself, so nothing
    else running under the test client sees a frozen clock."""
    monkeypatch.setattr(api_mod, "time", SimpleNamespace(time=lambda: now))
    return now


def test_per_minute_ip_burst_limit_blocks_the_eleventh_request(monkeypatch):
    import grounding.api as api_mod
    monkeypatch.setattr(api_mod, "run_live_check", lambda *a, **k: {"claims": [], "groundedness": {}})
    _freeze_minute(monkeypatch, api_mod)
    # Isolate the per-minute gate: the IP daily backstop and the device quota
    # (default 3) both run after the burst check and would 429 with a
    # *different* message once the run exceeds them. Lift the device quota
    # clear of the 10-request run; IP_DAILY_BACKSTOP stays at its default 50
    # (> 10) so it never interferes. The "minute" assertion below then proves
    # the 429 is the burst limit and not another gate.
    monkeypatch.setattr(api_mod, "FREE_TIER_DAILY_LIMIT", 100)
    client, _ = _make_client()
    # each request from TestClient shares host "testclient"; device tokens
    # rotate per call unless we pin one, and the device lock is released each
    # time, so only the per-minute IP bucket should bite.
    client.cookies.set("gi_device_token", mint_device_token(SECRET))
    for i in range(api_mod.IP_PER_MINUTE_LIMIT):
        assert client.post("/check", data={"ai_output": "x"}, files=_files()).status_code == 200
    r = client.post("/check", data={"ai_output": "x"}, files=_files())
    assert r.status_code == 429
    assert "minute" in r.json()["detail"].lower()


def test_per_minute_limit_rejection_does_not_burn_device_quota(monkeypatch):
    import grounding.api as api_mod
    from datetime import date
    monkeypatch.setattr(api_mod, "run_live_check", lambda *a, **k: {"claims": [], "groundedness": {}})
    now = _freeze_minute(monkeypatch, api_mod)
    minute_key = f"ip:testclient:m{int(now // 60)}"
    store = {"quota": {(minute_key, date.today()): api_mod.IP_PER_MINUTE_LIMIT}, "locks": {}}
    client, _ = _make_client(quota_store=store)
    token = mint_device_token(SECRET)
    client.cookies.set("gi_device_token", token)
    r = client.post("/check", data={"ai_output": "x"}, files=_files())
    assert r.status_code == 429
    assert store["quota"].get((f"device:{token}", date.today()), 0) == 0


def test_per_minute_rejection_does_not_burn_the_ip_daily_backstop(monkeypatch):
    # The burst gate must run before the daily backstop. With the old order a
    # burst-rejected request still charged a daily unit, so 100 req/min drained
    # the 50/day allowance in under a minute -- the exact scenario the burst
    # gate exists to prevent.
    import grounding.api as api_mod
    monkeypatch.setattr(api_mod, "run_live_check", lambda *a, **k: {"claims": [], "groundedness": {}})
    now = _freeze_minute(monkeypatch, api_mod)
    minute_key = f"ip:testclient:m{int(now // 60)}"
    store = {"quota": {(minute_key, date.today()): api_mod.IP_PER_MINUTE_LIMIT}, "locks": {}}
    client, _ = _make_client(quota_store=store)
    client.cookies.set("gi_device_token", mint_device_token(SECRET))
    r = client.post("/check", data={"ai_output": "x"}, files=_files())
    assert r.status_code == 429
    assert "minute" in r.json()["detail"].lower()
    assert store["quota"].get(("ip:testclient", date.today()), 0) == 0


def test_interactive_docs_are_disabled():
    client, _ = _make_client()
    assert client.get("/docs").status_code == 404
    assert client.get("/redoc").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_cors_allows_configured_origin_and_rejects_others(monkeypatch):
    import grounding.api as api_mod
    monkeypatch.setattr(api_mod, "run_live_check", lambda *a, **k: {"claims": [], "groundedness": {}})
    client, _ = _make_client()

    ok = client.post("/check", data={"ai_output": "x"}, files=_files(),
                     headers={"origin": "https://grounding-inspector.netlify.app"})
    assert ok.headers.get("access-control-allow-origin") == "https://grounding-inspector.netlify.app"

    bad = client.post("/check", data={"ai_output": "x"}, files=_files(),
                      headers={"origin": "https://evil.example"})
    assert bad.headers.get("access-control-allow-origin") in (None, "")
