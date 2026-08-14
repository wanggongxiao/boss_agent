"""岗位检索风控人工接管测试。"""

from unittest.mock import Mock

from src.browser.risk_monitor import RiskEvent
from src.pipeline.retriever import JobRetriever


def _risk_event() -> RiskEvent:
    return RiskEvent(keyword="验证码", snippet="请完成验证码")


def test_risk_can_resume_after_manual_handling():
    page = Mock()
    page.wait_for_elements.return_value = []
    page.snapshot.return_value = Mock(
        url="https://www.zhipin.com/web/geek/job",
        title="岗位搜索",
        screenshot_path="snapshot.png",
        text_snippet="",
    )
    human_loop = Mock()
    retriever = JobRetriever(page, human_loop=human_loop)
    retriever._risk_monitor = Mock()
    retriever._risk_monitor.detect.side_effect = [_risk_event(), None, None]

    jobs = retriever.retrieve()

    assert jobs == []
    human_loop.wait_for_resume.assert_called_once_with()
    assert page.get.call_count == 2
    page.wait_for_elements.assert_called_once()


def test_risk_stops_after_retry_limit():
    page = Mock()
    human_loop = Mock()
    retriever = JobRetriever(page, human_loop=human_loop, max_risk_retries=2)
    retriever._risk_monitor = Mock()
    retriever._risk_monitor.detect.side_effect = [_risk_event(), _risk_event(), _risk_event()]

    jobs = retriever.retrieve()

    assert jobs == []
    assert human_loop.wait_for_resume.call_count == 2
    page.wait_for_elements.assert_not_called()
