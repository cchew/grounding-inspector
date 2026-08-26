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
