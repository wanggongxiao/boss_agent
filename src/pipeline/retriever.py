"""岗位检索：驱动页面打开检索页并抓取岗位卡片列表。

依赖 PageController；抓取逻辑与选择器解耦（选择器集中在 config/selectors.py）。
"""

from __future__ import annotations

from urllib.parse import urljoin

from loguru import logger

from config.selectors import SEARCH_URL, SELECTORS
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

    def retrieve(self) -> list[Job]:
        """打开检索页并抓取当前页岗位列表。"""
        self._page.get(SEARCH_URL)

        if not self._wait_until_risk_cleared():
            logger.warning("人工处理后风控仍未解除，停止检索并返回空列表")
            return []

        return self._parse_cards()

    def _wait_until_risk_cleared(self) -> bool:
        """检测到验证时暂停，等待人工处理并有限次数复检。"""
        event = self._risk_monitor.detect()
        if event is None:
            return True

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
                return True

        return False

    def _parse_cards(self) -> list[Job]:
        """解析岗位卡片，逐卡片提取标题/公司/城市/薪资。"""
        jobs: list[Job] = []
        cards = self._page.elements(SELECTORS["job_card"])

        for card in cards:
            detail_href = self._page.child_attribute(card, SELECTORS["job_link"], "href")
            detail_href = detail_href or self._page.element_attribute(card, "href")
            job = Job(
                title=self._page.child_text(card, SELECTORS["job_title"]),
                company=self._page.child_text(card, SELECTORS["job_company"]),
                city=self._page.child_text(card, SELECTORS["job_city"]),
                salary=self._page.child_text(card, SELECTORS["job_salary"]),
                platform_job_id=self._page.element_attribute(card, "data-jobid") or "",
                hr_id=self._page.element_attribute(card, "data-hrid") or "",
                detail_url=urljoin(SEARCH_URL, detail_href) if detail_href else "",
            )
            if job.title or job.company:
                jobs.append(job)

        logger.info("检索到岗位卡片 {} 条", len(jobs))
        return jobs
