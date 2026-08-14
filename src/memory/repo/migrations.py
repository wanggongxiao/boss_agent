"""轻量迁移器：按顺序执行 tables.MIGRATIONS，并记录 schema_version。

使用 `PRAGMA user_version` 保存已应用版本，避免重复执行幂等 DDL。
"""

from __future__ import annotations

import sqlite3

from loguru import logger

from src.memory.repo.tables import MIGRATIONS, SCHEMA_VERSION


def migrate(conn: sqlite3.Connection) -> None:
    """将数据库迁移到最新 schema 版本。"""
    current = conn.execute("PRAGMA user_version").fetchone()[0]

    if current >= SCHEMA_VERSION:
        return

    logger.info("开始迁移 SQLite schema：{} -> {}", current, SCHEMA_VERSION)

    try:
        conn.execute("BEGIN")
        for version in range(current, SCHEMA_VERSION):
            # MIGRATIONS 列表索引从 0 开始，对应版本 1；迁移第 v+1 个版本
            index = version
            if index >= len(MIGRATIONS):
                break
            conn.execute(MIGRATIONS[index])
            conn.execute(f"PRAGMA user_version = {version + 1}")
            logger.info("已应用迁移版本 {}", version + 1)
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    logger.info("SQLite 迁移完成，当前版本 {}", SCHEMA_VERSION)