CREATE TABLE IF NOT EXISTS gi_quota (
    quota_key TEXT NOT NULL,
    check_date DATE NOT NULL,
    checks_used INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (quota_key, check_date)
);
