"""SQLite schema migrations grouped by schema version."""

from __future__ import annotations

SCHEMA_VERSION = 2

_BASE_SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS jobs (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        platform_job_id TEXT UNIQUE,
        title           TEXT NOT NULL DEFAULT '',
        company         TEXT NOT NULL DEFAULT '',
        hr_id           TEXT NOT NULL DEFAULT '',
        city            TEXT NOT NULL DEFAULT '',
        salary          TEXT NOT NULL DEFAULT '',
        jd_text         TEXT NOT NULL DEFAULT '',
        jd_hash         TEXT NOT NULL DEFAULT '',
        first_seen_at   TEXT NOT NULL DEFAULT ''
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_jobs_jd_hash ON jobs (jd_hash)",
    """
    CREATE TABLE IF NOT EXISTS evaluations (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id        INTEGER NOT NULL,
        match_score   INTEGER NOT NULL DEFAULT 0,
        should_apply  INTEGER NOT NULL DEFAULT 0,
        reasons_json  TEXT NOT NULL DEFAULT '[]',
        intro_text    TEXT NOT NULL DEFAULT '',
        model_version TEXT NOT NULL DEFAULT '',
        created_at    TEXT NOT NULL DEFAULT '',
        FOREIGN KEY (job_id) REFERENCES jobs (id) ON DELETE CASCADE
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_evaluations_job_id ON evaluations (job_id)",
    """
    CREATE TABLE IF NOT EXISTS conversations (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id           INTEGER NOT NULL,
        hr_id            TEXT NOT NULL DEFAULT '',
        status           TEXT NOT NULL DEFAULT 'new',
        last_message_at  TEXT NOT NULL DEFAULT '',
        last_interact_at TEXT NOT NULL DEFAULT '',
        history_json     TEXT NOT NULL DEFAULT '[]',
        FOREIGN KEY (job_id) REFERENCES jobs (id) ON DELETE CASCADE
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_conversations_hr_id ON conversations (hr_id)",
    """
    CREATE TABLE IF NOT EXISTS blacklist (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        company  TEXT NOT NULL DEFAULT '',
        hr_id    TEXT NOT NULL DEFAULT '',
        reason   TEXT NOT NULL DEFAULT '',
        added_at TEXT NOT NULL DEFAULT ''
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_blacklist_hr_id ON blacklist (hr_id)",
    """
    CREATE TABLE IF NOT EXISTS runs (
        id                 INTEGER PRIMARY KEY AUTOINCREMENT,
        started_at         TEXT NOT NULL DEFAULT '',
        ended_at           TEXT NOT NULL DEFAULT '',
        actions_count      INTEGER NOT NULL DEFAULT 0,
        risk_events_count  INTEGER NOT NULL DEFAULT 0
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS cooldown (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        scope    TEXT NOT NULL DEFAULT '',
        target   TEXT NOT NULL DEFAULT '',
        until_ts INTEGER NOT NULL DEFAULT 0,
        reason   TEXT NOT NULL DEFAULT ''
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_cooldown_target ON cooldown (scope, target)",
]

_SEND_ATTEMPTS_SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS send_attempts (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id       INTEGER,
        target       TEXT NOT NULL DEFAULT '',
        attempted_at INTEGER NOT NULL DEFAULT 0,
        success      INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY (job_id) REFERENCES jobs (id) ON DELETE SET NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_send_attempts_time ON send_attempts (attempted_at)",
    "CREATE INDEX IF NOT EXISTS idx_send_attempts_target ON send_attempts (target, attempted_at)",
]

# v2 repeats the base DDL intentionally: early v1 databases only created the first
# statement due to the old migration runner. CREATE IF NOT EXISTS repairs them safely.
MIGRATIONS: list[list[str]] = [
    _BASE_SCHEMA,
    [*_BASE_SCHEMA, *_SEND_ATTEMPTS_SCHEMA],
]
