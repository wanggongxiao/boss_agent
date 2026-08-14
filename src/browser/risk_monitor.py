"""风控监听：检测页面是否触发了验证/限制/异常提示。

只负责检测与上报，不做任何自动绕过；触发后由上层 Agent 挂起并移交人工。
"""

from __future__ import annotations

from dataclasses import dataclass

from loguru import logger

from src.browser.page_controller import PageController

# 常见风控/限制关键词（用于对页面文本做粗粒度匹配）
_RISK_KEYWORDS = (
    "操作频繁",
    "频繁",
    "验证码",
    "滑块",
    "极验",
    "账号异常",
    "登录失效",
    "请完成验证",
    "访问过于频繁",
)


@dataclass
class RiskEvent:
    """一次风控事件。"""

    keyword: str
    snippet: str


class RiskMonitor:
    """基于页面文本的风控监听器。"""

    def __init__(self, page: PageController):
        self._page = page

    def detect(self) -> RiskEvent | None:
        """返回命中的风控事件；未命中返回 None。"""
        try:
            text = self._page.text()
        except Exception as exc:  # pragma: no cover - 页面已关闭等异常
            logger.debug("读取页面文本失败，跳过风控检测: {}", exc)
            return None

        if not text:
            return None

        for keyword in _RISK_KEYWORDS:
            if keyword in text:
                event = RiskEvent(keyword=keyword, snippet=text[:200])
                logger.warning("检测到风控关键词: {}", keyword)
                return event
        return None