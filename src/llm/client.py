"""DeepSeek 客户端封装（OpenAI 兼容协议）。

采用延迟导入 openai，避免未安装依赖时影响其它模块加载；
提供带重试的结构化 JSON 输出能力，基于 Pydantic 校验。
"""

from __future__ import annotations

import json
import time
from typing import TypeVar

from loguru import logger
from pydantic import BaseModel

from config.settings import settings as get_settings
from src.llm.prompt_loader import load_prompt

T = TypeVar("T", bound=BaseModel)


class DeepSeekClient:
    """封装 DeepSeek Chat Completions。"""

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        cfg = get_settings()
        self._api_key = api_key or cfg.deepseek_api_key
        self._base_url = base_url or cfg.deepseek_base_url
        self._model = cfg.deepseek_model
        self._chat_model = cfg.deepseek_chat_model
        self._client = None

    def _ensure_client(self):
        """惰性初始化 openai 客户端；未配置/未安装时抛错。"""
        if self._client is not None:
            return self._client
        if not self._api_key:
            raise RuntimeError("未配置 DEEPSEEK_API_KEY，无法调用 LLM")
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("未安装 openai，请先执行 pip install -r requirements.txt") from exc

        self._client = OpenAI(api_key=self._api_key, base_url=self._base_url)
        return self._client

    def complete_json(
        self,
        prompt: str,
        system: str | None = None,
        *,
        use_reasoner: bool = True,
        max_retries: int = 3,
    ) -> str:
        """调用 Chat Completions 并要求返回 JSON 字符串。

        :param use_reasoner: True 使用 deepseek-reasoner（重推理），False 使用 deepseek-chat
        """
        client = self._ensure_client()
        model = self._model if use_reasoner else self._chat_model
        system_text = system if system is not None else load_prompt("system.txt")

        messages: list[dict] = []
        if system_text:
            messages.append({"role": "system", "content": system_text})
        messages.append({"role": "user", "content": prompt})

        last_error: Exception | None = None
        for attempt in range(max_retries):
            try:
                resp = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=0.2,
                )
                content = resp.choices[0].message.content
                if not content:
                    raise ValueError("LLM 返回空内容")
                return content
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                logger.warning("LLM 调用失败（第 {} 次）：{}", attempt + 1, exc)
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)

        raise RuntimeError(f"LLM 调用失败: {last_error}")

    def complete_structured(
        self,
        prompt: str,
        schema: type[T],
        *,
        system: str | None = None,
        use_reasoner: bool = True,
    ) -> T:
        """调用 LLM 并解析为 Pydantic 模型。"""
        raw = self.complete_json(prompt, system=system, use_reasoner=use_reasoner)
        data = json.loads(raw)
        return schema.model_validate(data)