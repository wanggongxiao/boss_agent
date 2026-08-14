"""全局配置：基于 pydantic-settings 从环境变量 / .env 加载。

所有路径均以项目根目录（boss-agent/）为基准转换为绝对路径，便于任意 CWD 运行。
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


class SafetyTier(StrEnum):
    """每日沟通限速分档。"""

    CONSERVATIVE = "conservative"  # 20/天，默认
    NORMAL = "normal"  # 50/天
    AGGRESSIVE = "aggressive"  # 200/天，需显式选择并确认风险


# 各分档对应的每日沟通上限
_TIER_DAILY_LIMITS: dict[SafetyTier, int] = {
    SafetyTier.CONSERVATIVE: 20,
    SafetyTier.NORMAL: 50,
    SafetyTier.AGGRESSIVE: 200,
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ===== DeepSeek LLM =====
    deepseek_api_key: str = Field(default="", repr=False)
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-reasoner"
    deepseek_chat_model: str = "deepseek-chat"

    # ===== 浏览器 =====
    browser_executable_path: str = ""
    browser_user_data_dir: str = "./data/browser_profile"

    # ===== 存储 =====
    db_path: str = "./data/sqlite/boss.db"
    chroma_dir: str = "./data/chroma"
    match_coarse_threshold: float = Field(default=0.12, ge=-1.0, le=1.0)

    # ===== 通知 =====
    notify_kind: str = "none"

    # ===== 安全/限速 =====
    agent_safety_tier: SafetyTier = SafetyTier.CONSERVATIVE
    agent_daily_send_limit: int = 200  # 配置上限，实际按分档生效
    agent_global_min_interval_s: float = 45.0
    agent_cooldown_same_target_d: int = 7

    # ===== 派生属性 =====
    @property
    def project_root(self) -> Path:
        return _PROJECT_ROOT

    @property
    def browser_user_data_path(self) -> Path:
        return self._resolve(self.browser_user_data_dir)

    @property
    def db_path_resolved(self) -> Path:
        return self._resolve(self.db_path)

    @property
    def chroma_path(self) -> Path:
        return self._resolve(self.chroma_dir)

    @property
    def effective_daily_send_limit(self) -> int:
        """实际生效的每日沟通上限：取分档值与配置上限的较小者。"""
        tier_limit = _TIER_DAILY_LIMITS.get(self.agent_safety_tier, 20)
        return min(tier_limit, self.agent_daily_send_limit)

    def _resolve(self, raw: str) -> Path:
        p = Path(raw)
        if p.is_absolute():
            return p
        return _PROJECT_ROOT / p


def get_settings() -> Settings:
    """返回全局单例配置。"""
    return Settings()


_settings: Settings | None = None


def settings() -> Settings:
    """惰性单例：避免多次实例化重复读取 .env / 触发 Pydantic 校验。"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
