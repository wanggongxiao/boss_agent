"""Prompt 模板渲染测试。"""

from src.llm.prompt_loader import load_prompt


def test_match_prompt_renders_json_example_without_format_key_error():
    prompt = load_prompt("match_prompt.txt").format(
        resume="Python、OpenCV",
        title="视觉算法工程师",
        jd="负责目标检测",
    )

    assert '"match_score"' in prompt
    assert "Python、OpenCV" in prompt
    assert "视觉算法工程师" in prompt
    assert "负责目标检测" in prompt
