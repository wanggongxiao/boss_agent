"""页面操作统一封装：打开页面、等待、点击、输入、滚动、截图快照。

封装 DrissionPage 的 ChromiumPage，供上层 pipeline 使用，不暴露 DrissionPage 细节。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from loguru import logger

from src.browser.human_behavior import gaussian_sleep
from src.browser.session import BrowserSession


@dataclass
class PageSnapshot:
    """页面状态快照：用于风控监听与错误留证。"""

    url: str
    title: str
    text_snippet: str
    screenshot_path: str | None = None


class PageController:
    """对单个 ChromiumPage 的薄封装。"""

    def __init__(self, page):
        self._page = page

    @classmethod
    def from_session(cls, session: BrowserSession) -> "PageController":
        return cls(session.new_page())

    def get(self, url: str, wait_s: float = 3.0) -> None:
        """打开 URL 并等待加载。"""
        self._page.get(url)
        gaussian_sleep(mean=wait_s, sigma=0.6, floor=0.5)

    def click(self, locator: str, by: str = "css") -> None:
        """点击元素。locator 为选择器值，by 支持 css/xpath/text。"""
        element = self._find(locator, by)
        element.click()
        gaussian_sleep(mean=0.6, sigma=0.2, floor=0.2)

    def input(self, locator: str, text: str, by: str = "css") -> None:
        """向元素输入文本（先清空再输入）。"""
        element = self._find(locator, by)
        element.clear()
        element.input(text)

    def scroll_down(self, distance: int = 800) -> None:
        """向下滚动指定距离。"""
        self._page.scroll.down(distance)
        gaussian_sleep(mean=1.2, sigma=0.5, floor=0.3)

    def text(self, locator: str | None = None, by: str = "css") -> str:
        """获取页面或元素文本。locator 为空时返回整页文本。"""
        if locator is None:
            return self._page.ele("tag:body").text
        element = self._find(locator, by)
        return element.text

    def elements(self, locator: str, by: str = "css") -> list:
        """获取匹配的元素列表。"""
        if by == "css":
            return self._page.eles(locator)
        if by == "xpath":
            return self._page.eles(f"xpath:{locator}")
        raise ValueError(f"不支持的定位方式: {by}")

    def child_text(self, element, locator: str, by: str = "css") -> str:
        """获取元素内部匹配子元素的文本。

        :param element: DrissionPage 元素对象
        """
        if by == "css":
            child = element.ele(locator)
        elif by == "xpath":
            child = element.ele(f"xpath:{locator}")
        else:
            raise ValueError(f"不支持的定位方式: {by}")
        if child is None:
            return ""
        return child.text

    def child_attribute(self, element, locator: str, name: str, by: str = "css") -> str:
        """读取元素内部子元素的属性，缺失时返回空字符串。"""
        if by == "css":
            child = element.ele(locator)
        elif by == "xpath":
            child = element.ele(f"xpath:{locator}")
        else:
            raise ValueError(f"不支持的定位方式: {by}")
        if child is None:
            return ""
        return self.element_attribute(child, name)

    def element_attribute(self, element, name: str) -> str:
        """读取元素属性值，缺失返回空字符串。"""
        try:
            value = element.attr(name)
        except Exception:  # pragma: no cover - 属性不存在
            return ""
        return value or ""

    def snapshot(self, screenshot_dir: Path | None = None) -> PageSnapshot:
        """生成页面状态快照，可选保存截图。"""
        snapshot = PageSnapshot(
            url=self._page.url,
            title=self._page.title,
            text_snippet=self._page.ele("tag:body").text[:2000],
        )
        if screenshot_dir is not None:
            screenshot_dir.mkdir(parents=True, exist_ok=True)
            path = screenshot_dir / "snapshot.png"
            self._page.get_screenshot(path=str(path))
            snapshot.screenshot_path = str(path)
        return snapshot

    @property
    def url(self) -> str:
        return self._page.url

    def _find(self, locator: str, by: str):
        if by == "css":
            return self._page.ele(locator)
        if by == "xpath":
            return self._page.ele(f"xpath:{locator}")
        if by == "text":
            return self._page.ele(f"text:{locator}")
        raise ValueError(f"不支持的定位方式: {by}")

    def close(self) -> None:
        try:
            self._page.quit()
        except Exception as exc:  # pragma: no cover - 浏览器已关闭场景
            logger.debug("关闭页面忽略异常: {}", exc)
