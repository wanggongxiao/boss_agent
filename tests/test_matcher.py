"""岗位匹配粗筛测试。"""

from unittest.mock import Mock

from src.memory.vector_store import VectorHit
from src.pipeline.matcher import JobMatcher
from src.pipeline.models import Job


def test_relevant_score_passes_calibrated_threshold():
    store = Mock()
    store.query.return_value = [VectorHit("1", "视觉项目", 0.18)]
    matcher = JobMatcher("resume", vector_store=store, coarse_threshold=0.12)

    assert matcher.coarse_pass(Job(title="视觉算法", jd_text="计算机视觉岗位"))


def test_low_score_is_still_filtered():
    store = Mock()
    store.query.return_value = [VectorHit("1", "无关经历", 0.05)]
    matcher = JobMatcher("resume", vector_store=store, coarse_threshold=0.12)

    assert not matcher.coarse_pass(Job(title="无关岗位", jd_text="完全不同的岗位"))
