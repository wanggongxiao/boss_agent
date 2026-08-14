"""JD 详情页关联测试。"""

from unittest.mock import Mock

from src.pipeline.jd_parser import JdParser
from src.pipeline.models import Job


def test_parse_opens_job_detail_before_reading_jd():
    page = Mock()
    page.text.return_value = "Python backend role"
    job = Job(title="Backend", detail_url="https://example.com/job/1")

    JdParser(page).parse(job)

    page.get.assert_called_once_with(job.detail_url)
    assert job.jd_text == "Python backend role"


def test_parse_does_not_read_unrelated_page_without_detail_url():
    page = Mock()
    job = Job(title="Backend")

    JdParser(page).parse(job)

    page.get.assert_not_called()
    page.text.assert_not_called()
    assert job.jd_text == ""
