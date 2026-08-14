"""沟通动作：通过 BOSS 网页向岗位发起首次沟通。

默认 dry-run（不真正发送）；发送前必须人工确认。

BOSS 当前网页在点击“立即沟通”时会自动发送账号配置的预设招呼语，
因此这里不再向聊天框追加第二条自定义消息，避免连续重复发送。
"""

from __future__ import annotations

from loguru import logger

from config.selectors import SELECTORS
from src.browser.page_controller import PageController


class Communicator:
    """发起首次沟通。"""

    def __init__(self, page: PageController, dry_run: bool = True):
        self._page = page
        self._dry_run = dry_run

    def send_intro(self, intro: str) -> bool:
        """发送开场话术。

        :param intro: 已人工确认的话术内容
        :return: 是否执行了真实发送（dry_run 恒为 False）
        """
        if self._dry_run:
            logger.info("[dry-run] 不真实发送，话术预览：{}", intro)
            return False

        try:
            previous_url = self._page.url
            self._page.click(SELECTORS["chat_button"])
            self._page.wait_for_url_change(previous_url, timeout_s=12.0)
            if "/web/geek/chat" not in self._page.url:
                logger.error("点击立即沟通后未进入聊天页，当前 URL={}", self._page.url)
                return False
            logger.info("已发起沟通；BOSS 已发送账号预设招呼语，自定义建议话术未追加")
            return True
        except Exception as exc:  # pragma: no cover - 选择器需按页面校准
            logger.error("发送开场话术失败：{}", exc)
            return False

    @property
    def dry_run(self) -> bool:
        return self._dry_run
