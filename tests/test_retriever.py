"""岗位检索风控人工接管测试。"""

from unittest.mock import Mock

from src.browser.risk_monitor import RiskEvent
from src.pipeline.retriever import JobRetriever


def _risk_event() -> RiskEvent:
    return RiskEvent(keyword="验证码", snippet="请完成验证码")


def test_risk_can_resume_after_manual_handling():
    page = Mock()
    page.elements.return_value = []
    human_loop = Mock()
    retriever = JobRetriever(page, human_loop=human_loop)
    retriever._risk_monitor = Mock()
    retriever._risk_monitor.detect.side_effect = [_risk_event(), None]

    jobs = retriever.retrieve()

    assert jobs == []
    human_loop.wait_for_resume.assert_called_once_with()
    page.elements.assert_called_once()


def test_risk_stops_after_retry_limit():
    page = Mock()
    human_loop = Mock()
    retriever = JobRetriever(page, human_loop=human_loop, max_risk_retries=2)
    retriever._risk_monitor = Mock()
    retriever._risk_monitor.detect.side_effect = [_risk_event(), _risk_event(), _risk_event()]

    jobs = retriever.retrieve()

    assert jobs == []
    assert human_loop.wait_for_resume.call_count == 2
    page.elements.assert_not_called()
