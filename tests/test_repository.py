"""SQLite 迁移与持久化仓库测试。"""

from __future__ import annotations

import sqlite3

from src.memory.repo.migrations import migrate
from src.memory.repo.store import Repository
from src.pipeline.models import Job


def _connection() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    migrate(conn)
    return conn


def test_fresh_migration_creates_all_tables():
    conn = _connection()
    names = {
        row["name"]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }

    assert {"jobs", "evaluations", "conversations", "runs", "send_attempts"} <= names
    assert conn.execute("PRAGMA user_version").fetchone()[0] == 2


def test_v1_database_is_repaired_on_upgrade():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    # Old runner created only the first v1 statement: the complete jobs table.
    conn.execute(
        """
        CREATE TABLE jobs (
            id INTEGER PRIMARY KEY, platform_job_id TEXT UNIQUE, title TEXT NOT NULL DEFAULT '',
            company TEXT NOT NULL DEFAULT '', hr_id TEXT NOT NULL DEFAULT '',
            city TEXT NOT NULL DEFAULT '', salary TEXT NOT NULL DEFAULT '',
            jd_text TEXT NOT NULL DEFAULT '', jd_hash TEXT NOT NULL DEFAULT '',
            first_seen_at TEXT NOT NULL DEFAULT ''
        )
        """
    )
    conn.execute("PRAGMA user_version = 1")

    migrate(conn)

    names = {
        row["name"]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }
    assert "evaluations" in names
    assert "send_attempts" in names


def test_jobs_without_platform_id_do_not_collide():
    repository = Repository(_connection())

    first_id = repository.upsert_job(Job(title="Backend", company="A", hr_id="1"))
    second_id = repository.upsert_job(Job(title="Frontend", company="B", hr_id="2"))

    assert first_id != second_id
