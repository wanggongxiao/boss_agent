"""SQLite 表定义（DDL）。

所有时间字段统一使用 UTC 的 ISO8601 字符串（`strftime('%Y-%m-%dT%H:%M:%fZ','now')`）
或直接由应用层 `src.utils.time_utils` 生成后写入，避免依赖数据库本地时区。
"""

from __future__ import annotations

SCHEMA_VERSION = 1

# 建表语句按迁移顺序排列，迁移器按序执行（见 migrations.py）
MIGRATIONS: list[str] = [
    # --- v1: 初始表结构 ---
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
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_jobs_jd_hash ON jobs (jd_hash);
    """,
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
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_evaluations_job_id ON evaluations (job_id);
    """,
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
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_conversations_hr_id ON conversations (hr_id);
    """,
    """
    CREATE TABLE IF NOT EXISTS blacklist (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        company  TEXT NOT NULL DEFAULT '',
        hr_id    TEXT NOT NULL DEFAULT '',
        reason   TEXT NOT NULL DEFAULT '',
        added_at TEXT NOT NULL DEFAULT ''
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_blacklist_hr_id ON blacklist (hr_id);
    """,
    """
    CREATE TABLE IF NOT EXISTS runs (
        id                 INTEGER PRIMARY KEY AUTOINCREMENT,
        started_at         TEXT NOT NULL DEFAULT '',
        ended_at           TEXT NOT NULL DEFAULT '',
        actions_count      INTEGER NOT NULL DEFAULT 0,
        risk_events_count  INTEGER NOT NULL DEFAULT 0
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS cooldown (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        scope    TEXT NOT NULL DEFAULT '',
        target   TEXT NOT NULL DEFAULT '',
        until_ts INTEGER NOT NULL DEFAULT 0,
        reason   TEXT NOT NULL DEFAULT ''
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_cooldown_target ON cooldown (scope, target);
    """,
]