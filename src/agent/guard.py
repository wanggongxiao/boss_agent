"""守卫：全局最小间隔、每日沟通上限、同一目标冷却、连续失败熔断。

这是生产级稳定性与账号保护的核心。所有“发送”类动作都必须先通过 guard。
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import TYPE_CHECKING

from config.settings import settings as get_settings

if TYPE_CHECKING:
    from src.memory.repo.store import Repository


class CommunicationGuard:
    """沟通动作的限速/冷却/熔断守卫。"""

    def __init__(self, repository: Repository | None = None):
        cfg = get_settings()
        self._min_interval_s = cfg.agent_global_min_interval_s
        self._daily_limit = cfg.effective_daily_send_limit
        self._cooldown_days = cfg.agent_cooldown_same_target_d
        self._repository = repository

        self._last_action_ts = 0.0
        self._day_key = ""
        self._day_count = 0
        self._target_last_send: dict[str, float] = {}
        self._consecutive_failures = 0

    def allow_send(self, target_key: str) -> tuple[bool, str]:
        """判断是否允许向 target 发送沟通。

        :param target_key: 唯一标识，建议为 company + hr_id
        :return: (是否允许, 拒绝原因)
        """
        now = time.time()

        if self._repository is not None:
            return self._allow_send_persistent(target_key, now)

        # 全局最小间隔
        elapsed = now - self._last_action_ts
        if self._last_action_ts > 0 and elapsed < self._min_interval_s:
            wait = self._min_interval_s - elapsed
            return False, f"全局最小间隔未到（还需 {wait:.0f}s）"

        # 每日上限
        today = time.strftime("%Y-%m-%d")
        if today != self._day_key:
            self._day_key = today
            self._day_count = 0
        if self._day_count >= self._daily_limit:
            return False, f"已达每日沟通上限 {self._daily_limit}"

        # 同一目标冷却
        last = self._target_last_send.get(target_key)
        if last is not None:
            cooldown_s = self._cooldown_days * 86400
            if now - last < cooldown_s:
                return False, f"目标 {target_key} 处于冷却期"

        # 熔断：连续失败
        if self._consecutive_failures >= 5:
            return False, "连续失败次数过多，已熔断（请人工检查）"

        return True, ""

    def _allow_send_persistent(self, target_key: str, now: float) -> tuple[bool, str]:
        last_attempt = self._repository.last_attempt_ts()
        if last_attempt > 0 and now - last_attempt < self._min_interval_s:
            wait = self._min_interval_s - (now - last_attempt)
            return False, f"全局最小间隔未到（还需 {wait:.0f}s）"

        local_now = datetime.now().astimezone()
        day_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
        if self._repository.successful_sends_since(int(day_start.timestamp())) >= self._daily_limit:
            return False, f"已达每日沟通上限 {self._daily_limit}"

        last_success = self._repository.last_success_for_target(target_key)
        if last_success is not None and now - last_success < self._cooldown_days * 86400:
            return False, f"目标 {target_key} 处于冷却期"

        if self._repository.consecutive_send_failures() >= 5:
            return False, "连续失败次数过多，已熔断（请人工检查）"
        return True, ""

    def record_send(self, target_key: str, success: bool, job_id: int | None = None) -> None:
        """记录一次发送结果。"""
        if self._repository is not None:
            self._repository.record_send_attempt(target_key, success, job_id)
            return

        now = time.time()
        self._last_action_ts = now
        if success:
            self._day_count += 1
            self._target_last_send[target_key] = now
            self._consecutive_failures = 0
        else:
            self._consecutive_failures += 1
