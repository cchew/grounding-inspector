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


def decrement(conn, quota_key: str, today: date | None = None) -> None:
    """Give back one unit of quota, for when a check was counted up front but
    then failed for a reason the caller didn't cause (pipeline error). Floors
    at zero so a double-refund can't hand out free checks. Not the inverse of
    check_and_increment's admission decision -- only ever call it after an
    increment that this same request actually made."""
    today = today or date.today()
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE gi_quota
            SET checks_used = GREATEST(gi_quota.checks_used - 1, 0)
            WHERE quota_key = %s AND check_date = %s
            """,
            (quota_key, today),
        )
    conn.commit()


LOCK_LEASE_SECONDS = 30


def try_acquire_device_lock(conn, device_token: str) -> bool:
    """Acquire a short-lived lease-based lock keyed by device_token, via a
    row in gi_device_lock. Connection-pooling-safe by construction (no
    reliance on Postgres session state), unlike pg_try_advisory_lock --
    required because the production Neon connection uses PgBouncer
    transaction-mode pooling, where session-scoped advisory locks are
    unsupported and can leak onto unrelated backends. The lease expires
    automatically after LOCK_LEASE_SECONDS, so a crashed or slow request
    can't hold the lock forever."""
    with conn.cursor() as cur:
        cur.execute(
            # make_interval(secs => %s) rather than the more obvious
            # interval '%s seconds': psycopg3's default cursor binds
            # server-side, so a %s inside a quoted SQL string literal is NOT
            # substituted -- it would reach Postgres as the literal text
            # "$2 seconds" and fail at parse time.
            """
            INSERT INTO gi_device_lock (device_token, locked_until)
            VALUES (%s, now() + make_interval(secs => %s))
            ON CONFLICT (device_token) DO UPDATE
            SET locked_until = EXCLUDED.locked_until
            WHERE gi_device_lock.locked_until < now()
            RETURNING device_token
            """,
            # float, not int: make_interval's `secs` argument is
            # double precision, and psycopg adapts a Python int to int2 --
            # which resolves only via an implicit cast. Sending float8
            # outright makes it an exact signature match.
            (device_token, float(LOCK_LEASE_SECONDS)),
        )
        row = cur.fetchone()
    conn.commit()
    return row is not None


def release_device_lock(conn, device_token: str) -> None:
    """Explicitly release a device lock early (rather than waiting out the
    full lease) once a request finishes -- keeps sequential legitimate
    requests from the same device from waiting the full lease window."""
    with conn.cursor() as cur:
        cur.execute("DELETE FROM gi_device_lock WHERE device_token = %s", (device_token,))
    conn.commit()
