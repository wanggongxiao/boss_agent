"""持久化仓库：岗位、评估、沟通、黑名单、冷却、运行记录的访问层。

基于 sqlite3.Connection 的薄封装，使用参数化查询，避免 SQL 注入。
"""

from __future__ import annotations

import json
import sqlite3
import time

from src.pipeline.models import Job
from src.utils import time_utils


class Repository:
    """对 SQLite 的读写封装。"""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    # ===== jobs =====
    def upsert_job(self, job: Job) -> int:
        """插入或更新岗位，返回内部 job id。"""
        row = self._conn.execute(
            "SELECT id FROM jobs WHERE platform_job_id = ?",
            (job.platform_job_id,),
        ).fetchone()
        if row is not None:
            return int(row["id"])

        cur = self._conn.execute(
            """
            INSERT INTO jobs
                (platform_job_id, title, company, hr_id, city, salary, jd_text, jd_hash, first_seen_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job.platform_job_id,
                job.title,
                job.company,
                job.hr_id,
                job.city,
                job.salary,
                job.jd_text,
                job.jd_hash,
                time_utils.utc_now_iso(),
            ),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    # ===== evaluations =====
    def save_evaluation(
        self,
        job_id: int,
        match_score: int,
        should_apply: bool,
        reasons: list[str],
        intro_text: str,
        model_version: str,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO evaluations
                (job_id, match_score, should_apply, reasons_json, intro_text, model_version, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_id,
                match_score,
                int(should_apply),
                json.dumps(reasons, ensure_ascii=False),
                intro_text,
                model_version,
                time_utils.utc_now_iso(),
            ),
        )
        self._conn.commit()

    # ===== blacklist =====
    def is_blacklisted(self, company: str = "", hr_id: str = "") -> bool:
        if hr_id:
            row = self._conn.execute(
                "SELECT id FROM blacklist WHERE hr_id = ?", (hr_id,)
            ).fetchone()
            if row:
                return True
        if company:
            row = self._conn.execute(
                "SELECT id FROM blacklist WHERE company = ?", (company,)
            ).fetchone()
            if row:
                return True
        return False

    def add_blacklist(self, company: str, hr_id: str, reason: str) -> None:
        self._conn.execute(
            "INSERT INTO blacklist (company, hr_id, reason, added_at) VALUES (?, ?, ?, ?)",
            (company, hr_id, reason, time_utils.utc_now_iso()),
        )
        self._conn.commit()

    # ===== cooldown =====
    def is_cooling_down(self, target: str, scope: str = "job") -> bool:
        row = self._conn.execute(
            "SELECT until_ts FROM cooldown WHERE scope = ? AND target = ?",
            (scope, target),
        ).fetchone()
        if row is None:
            return False
        return int(row["until_ts"]) > int(time.time())

    def add_cooldown(self, target: str, until_ts: int, reason: str, scope: str = "job") -> None:
        self._conn.execute(
            "INSERT INTO cooldown (scope, target, until_ts, reason) VALUES (?, ?, ?, ?)",
            (scope, target, until_ts, reason),
        )
        self._conn.commit()

    # ===== runs =====
    def start_run(self) -> int:
        cur = self._conn.execute(
            "INSERT INTO runs (started_at, actions_count, risk_events_count) VALUES (?, 0, 0)",
            (time_utils.utc_now_iso(),),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def end_run(self, run_id: int) -> None:
        self._conn.execute(
            "UPDATE runs SET ended_at = ? WHERE id = ?",
            (time_utils.utc_now_iso(), run_id),
        )
        self._conn.commit()

    def record_risk_event(self, run_id: int) -> None:
        self._conn.execute(
            "UPDATE runs SET risk_events_count = risk_events_count + 1 WHERE id = ?",
            (run_id,),
        )
        self._conn.commit()