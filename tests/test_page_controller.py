"""页面控制器定位语义测试。"""

from unittest.mock import Mock

from src.browser.page_controller import PageController


def test_css_selectors_are_passed_with_explicit_css_prefix():
    raw_page = Mock()
    raw_page.eles.return_value = []
    controller = PageController(raw_page)

    controller.elements(".search-input-box .input")

    raw_page.eles.assert_called_once_with("css:.search-input-box .input")


def test_child_css_selector_uses_explicit_prefix():
    raw_page = Mock()
    child = Mock()
    child.text = "岗位"
    card = Mock()
    card.ele.return_value = child
    controller = PageController(raw_page)

    assert controller.child_text(card, ".job-title .job-name") == "岗位"
    card.ele.assert_called_once_with("css:.job-title .job-name")
