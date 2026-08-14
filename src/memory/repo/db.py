"""SQLite 连接管理与初始化。"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from loguru import logger

from config.settings import settings as get_settings
from src.memory.repo.migrations import migrate


class Database:
    """线程安全的最低限度封装：每线程持有一个连接（check_same_thread=False）。

    本项目的 SQLite 访问集中在单一 worker 线程，简单封装已足够；
    后续如需多线程写入，再切换到 WAL + 显式连接池。
    """

    def __init__(self, db_path: Path):
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        """建立连接并开启外键约束。"""
        conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def initialize(self) -> sqlite3.Connection:
        """建库目录、建立连接并执行迁移，返回可用连接。"""
        conn = self.connect()
        migrate(conn)
        logger.info("SQLite 已就绪：{}", self._db_path)
        return conn


def default_database() -> Database:
    """根据全局配置构造默认 Database 实例。"""
    return Database(get_settings().db_path_resolved)