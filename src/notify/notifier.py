"""通知器：本轮固定 none，仅本地日志与控制台提示音。

保留接口，后续如需外发（PushDeer / Server酱 / Telegram）在此扩展。
"""

from __future__ import annotations

import sys

from loguru import logger

try:
    import winsound  # Windows 专用，Linux/macOS 降级
except ImportError:  # pragma: no cover
    winsound = None


class Notifier:
    """本地告警通知器。"""

    def alert(self, message: str) -> None:
        """输出醒目告警并播放提示音。"""
        logger.warning("【风控告警】{}", message)
        print("\n[!!] " + message + "\n", file=sys.stderr)

        if winsound is not None:
            try:
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            except Exception:  # pragma: no cover
                pass

    def info(self, message: str) -> None:
        logger.info(message)