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
        row = self._find_job_row(job)
        if row is not None:
            job_id = int(row["id"])
            self._conn.execute(
                """
                UPDATE jobs SET title = ?, company = ?, hr_id = ?, city = ?, salary = ?,
                    jd_text = ?, jd_hash = ? WHERE id = ?
                """,
                (
                    job.title,
                    job.company,
                    job.hr_id,
                    job.city,
                    job.salary,
                    job.jd_text,
                    job.jd_hash,
                    job_id,
                ),
            )
            self._conn.commit()
            return job_id

        cur = self._conn.execute(
            """
            INSERT INTO jobs
                (platform_job_id, title, company, hr_id, city, salary, jd_text, jd_hash, first_seen_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job.platform_job_id or None,
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

    def _find_job_row(self, job: Job) -> sqlite3.Row | None:
        if job.platform_job_id:
            return self._conn.execute(
                "SELECT id FROM jobs WHERE platform_job_id = ?", (job.platform_job_id,)
            ).fetchone()
        if job.jd_text:
            row = self._conn.execute(
                "SELECT id FROM jobs WHERE jd_hash = ? AND jd_hash != ''", (job.jd_hash,)
            ).fetchone()
            if row is not None:
                return row
        return self._conn.execute(
            "SELECT id FROM jobs WHERE title = ? AND company = ? AND hr_id = ?",
            (job.title, job.company, job.hr_id),
        ).fetchone()

    def is_job_processed(self, job: Job) -> bool:
        """岗位是否已经产生过评估或沟通记录。"""
        row = self._find_job_row(job)
        if row is None:
            return False
        job_id = int(row["id"])
        processed = self._conn.execute(
            """
            SELECT 1 FROM evaluations WHERE job_id = ?
            UNION ALL
            SELECT 1 FROM conversations WHERE job_id = ?
            LIMIT 1
            """,
            (job_id, job_id),
        ).fetchone()
        return processed is not None

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

    # ===== send attempts / persistent guard =====
    def record_send_attempt(self, target: str, success: bool, job_id: int | None = None) -> None:
        self._conn.execute(
            "INSERT INTO send_attempts (job_id, target, attempted_at, success) VALUES (?, ?, ?, ?)",
            (job_id, target, int(time.time()), int(success)),
        )
        self._conn.commit()

    def last_attempt_ts(self) -> float:
        row = self._conn.execute("SELECT MAX(attempted_at) AS ts FROM send_attempts").fetchone()
        return float(row["ts"] or 0)

    def successful_sends_since(self, since_ts: int) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS count FROM send_attempts WHERE success = 1 AND attempted_at >= ?",
            (since_ts,),
        ).fetchone()
        return int(row["count"])

    def last_success_for_target(self, target: str) -> float | None:
        row = self._conn.execute(
            "SELECT MAX(attempted_at) AS ts FROM send_attempts WHERE target = ? AND success = 1",
            (target,),
        ).fetchone()
        return float(row["ts"]) if row["ts"] is not None else None

    def consecutive_send_failures(self) -> int:
        rows = self._conn.execute(
            "SELECT success FROM send_attempts ORDER BY id DESC LIMIT 5"
        ).fetchall()
        count = 0
        for row in rows:
            if bool(row["success"]):
                break
            count += 1
        return count

    def save_conversation_status(self, job_id: int, hr_id: str, status: str) -> None:
        now = time_utils.utc_now_iso()
        self._conn.execute(
            """
            INSERT INTO conversations
                (job_id, hr_id, status, last_message_at, last_interact_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (job_id, hr_id, status, now, now),
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

    def record_action(self, run_id: int) -> None:
        self._conn.execute(
            "UPDATE runs SET actions_count = actions_count + 1 WHERE id = ?", (run_id,)
        )
        self._conn.commit()
