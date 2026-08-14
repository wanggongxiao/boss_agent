"""Prompt 加载：从 config/prompts 读取模板文本。"""

from __future__ import annotations

from pathlib import Path

from config.settings import settings as get_settings

_PROMPTS_DIR = get_settings().project_root / "config" / "prompts"


def load_prompt(name: str) -> str:
    """读取 prompt 文件内容；文件不存在时返回空字符串。"""
    path = _PROMPTS_DIR / name
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()