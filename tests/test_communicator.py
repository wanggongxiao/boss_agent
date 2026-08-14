"""沟通动作测试。"""

from unittest.mock import Mock

from config.selectors import SELECTORS
from src.pipeline.communicator import Communicator


def test_live_communication_waits_for_chat_navigation_without_followup_message():
    page = Mock()
    page.url = "https://www.zhipin.com/job_detail/123.html"

    def navigate_after_click(_selector):
        page.url = "https://www.zhipin.com/web/geek/chat"

    page.click.side_effect = navigate_after_click
    communicator = Communicator(page, dry_run=False)

    assert communicator.send_intro("建议的自定义话术")
    page.click.assert_called_once_with(SELECTORS["chat_button"])
    page.input.assert_not_called()


def test_live_communication_fails_when_chat_navigation_does_not_happen():
    page = Mock()
    page.url = "https://www.zhipin.com/job_detail/123.html"
    communicator = Communicator(page, dry_run=False)

    assert not communicator.send_intro("建议话术")
