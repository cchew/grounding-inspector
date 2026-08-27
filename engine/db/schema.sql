CREATE TABLE IF NOT EXISTS gi_quota (
    quota_key TEXT NOT NULL,
    check_date DATE NOT NULL,
    checks_used INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (quota_key, check_date)
);

-- Lease-based per-device concurrency lock. Replaces pg_try_advisory_lock,
-- which is session-scoped and therefore unsafe behind the PgBouncer
-- transaction-mode pooling the production Neon connection string uses.
CREATE TABLE IF NOT EXISTS gi_device_lock (
    device_token TEXT PRIMARY KEY,
    locked_until TIMESTAMPTZ NOT NULL
);
