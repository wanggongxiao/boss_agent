"""时间工具：统一 UTC/本地时间戳，避免跨模块时间不一致。"""

from __future__ import annotations

from datetime import UTC, datetime


def utc_now_iso() -> str:
    """返回 UTC 时间的 ISO8601 字符串（含时区）。"""
    return datetime.now(UTC).isoformat()


def local_now_iso() -> str:
    """返回本地时间的 ISO8601 字符串（含时区）。"""
    return datetime.now().astimezone().isoformat()


def utc_timestamp() -> int:
    """返回 Unix 秒级时间戳（UTC）。"""
    return int(datetime.now(UTC).timestamp())
