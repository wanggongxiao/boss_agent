"""统一日志初始化：loguru，控制台 + 文件双 sink。

日志文件写到项目根目录下的 `logs/`，文件名 `boss-agent.log`，按天轮转。
"""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

from config.settings import settings as get_settings

_CONSOLE_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)

_FILE_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
    "{name}:{function}:{line} | {message}"
)

_initialized = False


def setup_logging() -> None:
    """配置 loguru 的全局 logger（幂等，重复调用不重复添加 sink）。"""
    global _initialized
    if _initialized:
        return

    logger.remove()

    # 控制台 sink（标准错误，兼容 IDE / 重定向场景）
    logger.add(
        sys.stderr,
        level="DEBUG",
        format=_CONSOLE_FORMAT,
        colorize=True,
    )

    # 文件 sink
    log_dir = get_settings().project_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "boss-agent.log"
    logger.add(
        str(log_path),
        level="INFO",
        format=_FILE_FORMAT,
        rotation="10 MB",
        retention="7 days",
        encoding="utf-8",
        enqueue=True,
    )

    _initialized = True


__all__ = ["logger", "setup_logging"]