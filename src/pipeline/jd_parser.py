"""JD 解析：从详情页抓取 JD 文本，并（可选）通过 LLM 结构化。

结构化解析依赖 llm 层，解耦为可注入的 JdStructuredParser 协议。
"""

from __future__ import annotations

from typing import Protocol

from loguru import logger

from config.selectors import SELECTORS
from src.browser.page_controller import PageController
from src.pipeline.models import Job, ParsedJd


class JdStructuredParser(Protocol):
    """JD 文本 -> 结构化 ParsedJd 的解析协议。"""

    def __call__(self, job: Job) -> ParsedJd: ...


class JdParser:
    """抓取岗位详情页 JD 文本，并交给结构化解析器。"""

    def __init__(self, page: PageController, structured_parser: JdStructuredParser | None = None):
        self._page = page
        self._structured_parser = structured_parser

    def parse(self, job: Job) -> ParsedJd:
        """抓取 job 的详情页 JD 文本到 job.jd_text，并返回结构化结果。"""
        if job.detail_url:
            self._page.get(job.detail_url)
            job.jd_text = self._fetch_jd_text()
        else:
            logger.warning("岗位缺少详情链接，无法保证 JD 对应关系：{} @ {}", job.title, job.company)
            job.jd_text = ""

        if self._structured_parser is None:
            logger.debug("未注入结构化解析器，返回空 ParsedJd")
            return ParsedJd(title=job.title, company_name=job.company, city=job.city)

        return self._structured_parser(job)

    def _fetch_jd_text(self) -> str:
        """抓取当前详情页的 JD 文本。"""
        try:
            text = self._page.text(SELECTORS["jd_text"])
        except Exception as exc:  # pragma: no cover
            logger.debug("抓取 JD 文本失败: {}", exc)
            return ""
        return text or ""
