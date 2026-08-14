"""岗位检索：驱动页面打开检索页并抓取岗位卡片列表。

依赖 PageController；抓取逻辑与选择器解耦（选择器集中在 config/selectors.py）。
"""

from __future__ import annotations

from pathlib import PurePosixPath
from urllib.parse import urljoin, urlparse

from loguru import logger

from config.selectors import SEARCH_URL, SELECTORS
from config.settings import settings as get_settings
from src.agent.human_loop import HumanLoop
from src.browser.page_controller import PageController
from src.browser.risk_monitor import RiskMonitor
from src.pipeline.models import Job


class JobRetriever:
    """从检索页抓取岗位卡片列表。"""

    def __init__(
        self,
        page: PageController,
        human_loop: HumanLoop | None = None,
        max_risk_retries: int = 3,
    ):
        self._page = page
        self._risk_monitor = RiskMonitor(page)
        self._human_loop = human_loop or HumanLoop()
        self._max_risk_retries = max(1, max_risk_retries)

    def retrieve(self, keywords: list[str] | None = None) -> list[Job]:
        """打开检索页，按关键词搜索并抓取岗位列表。"""
        self._page.get(SEARCH_URL)

        cleared, handled_risk = self._wait_until_risk_cleared()
        if not cleared:
            logger.warning("人工处理后风控仍未解除，停止检索并返回空列表")
            return []

        if handled_risk:
            logger.info("验证解除后重新打开岗位搜索页")
            self._page.get(SEARCH_URL)
            cleared, _ = self._wait_until_risk_cleared()
            if not cleared:
                logger.warning("重新进入搜索页后再次触发风控，停止本轮检索")
                return []

        normalized = list(dict.fromkeys(k.strip() for k in keywords or [] if k.strip()))
        if not normalized:
            return self._parse_cards()

        jobs: list[Job] = []
        seen: set[str] = set()
        for keyword in normalized:
            if not self._search(keyword):
                continue
            for job in self._parse_cards():
                key = job.platform_job_id or job.detail_url or f"{job.title}|{job.company}"
                if key not in seen:
                    seen.add(key)
                    jobs.append(job)

        logger.info("{} 个关键词共检索到 {} 个去重岗位", len(normalized), len(jobs))
        return jobs

    def _search(self, keyword: str) -> bool:
        """在当前职位页执行一次关键词搜索。"""
        logger.info("搜索岗位关键词：{}", keyword)
        previous_url = self._page.url
        try:
            self._page.input(SELECTORS["search_input"], keyword)
            self._page.click(SELECTORS["search_button"])
        except Exception as exc:  # pragma: no cover - 页面改版诊断
            logger.error("执行岗位搜索失败：{}", exc)
            return False

        if not self._page.wait_for_url_change(previous_url):
            logger.debug("搜索后 URL 未变化，继续按页面结果检测：{}", self._page.url)

        cleared, handled_risk = self._wait_until_risk_cleared()
        if not cleared:
            logger.warning("搜索关键词 {} 后风控未解除", keyword)
            return False
        if handled_risk:
            logger.info("验证解除后重新提交关键词：{}", keyword)
            self._page.input(SELECTORS["search_input"], keyword)
            self._page.click(SELECTORS["search_button"])
        return True

    def _wait_until_risk_cleared(self) -> tuple[bool, bool]:
        """检测到验证时暂停，等待人工处理并有限次数复检。"""
        event = self._risk_monitor.detect()
        if event is None:
            return True, False

        for attempt in range(1, self._max_risk_retries + 1):
            logger.warning(
                "检测到风控（{}），请在浏览器中人工处理；复检 {}/{}",
                event.keyword,
                attempt,
                self._max_risk_retries,
            )
            self._human_loop.wait_for_resume()
            event = self._risk_monitor.detect()
            if event is None:
                logger.info("风控验证已解除，恢复岗位检索")
                return True, True

        return False, True

    def _parse_cards(self) -> list[Job]:
        """解析岗位卡片，逐卡片提取标题/公司/城市/薪资。"""
        jobs: list[Job] = []
        cards = self._page.wait_for_elements(SELECTORS["job_card"], timeout_s=12.0)

        if not cards:
            self._record_empty_result_diagnostics()
            return []

        for card in cards:
            detail_href = self._page.child_attribute(card, SELECTORS["job_link"], "href")
            detail_href = detail_href or self._page.element_attribute(card, "href")
            detail_url = urljoin(SEARCH_URL, detail_href) if detail_href else ""
            platform_job_id = self._page.element_attribute(card, "data-jobid") or ""
            if not platform_job_id and detail_url:
                platform_job_id = PurePosixPath(urlparse(detail_url).path).stem
            job = Job(
                title=self._page.child_text(card, SELECTORS["job_title"]),
                company=self._page.child_text(card, SELECTORS["job_company"]),
                city=self._page.child_text(card, SELECTORS["job_city"]),
                salary=self._page.child_text(card, SELECTORS["job_salary"]),
                platform_job_id=platform_job_id,
                hr_id=self._page.element_attribute(card, "data-hrid") or "",
                detail_url=detail_url,
            )
            if job.title or job.company:
                jobs.append(job)

        logger.info("检索到岗位卡片 {} 条", len(jobs))
        return jobs

    def _record_empty_result_diagnostics(self) -> None:
        """岗位为零时保存现场，区分空结果与选择器失效。"""
        try:
            output_dir = get_settings().project_root / "data" / "diagnostics"
            snapshot = self._page.snapshot(output_dir)
            logger.warning(
                "未找到岗位卡片 | url={} | title={} | screenshot={}",
                snapshot.url,
                snapshot.title,
                snapshot.screenshot_path,
            )
            logger.debug("页面文本片段：{}", snapshot.text_snippet[:500])
        except Exception as exc:  # pragma: no cover - 诊断失败不影响安全退出
            logger.warning("保存零结果诊断现场失败：{}", exc)
