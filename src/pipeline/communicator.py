"""沟通动作：向岗位发起首次沟通。

默认 dry-run（不真正发送）；发送前必须人工确认。
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
            self._page.click(SELECTORS["chat_button"])
            self._page.input(SELECTORS["chat_input"], intro)
            self._page.click(SELECTORS["chat_send"])
            logger.info("已发送开场话术")
            return True
        except Exception as exc:  # pragma: no cover - 选择器需按页面校准
            logger.error("发送开场话术失败：{}", exc)
            return False

    @property
    def dry_run(self) -> bool:
        return self._dry_run