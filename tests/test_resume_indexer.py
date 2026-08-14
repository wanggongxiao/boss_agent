"""简历切片清洗测试。"""

from src.memory.resume_indexer import _split_paragraphs


def test_separator_only_paragraphs_are_removed():
    chunks = _split_paragraphs("Python 与 OpenCV 项目经验\n\n==============================")

    assert chunks == ["Python 与 OpenCV 项目经验"]
