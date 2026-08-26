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
