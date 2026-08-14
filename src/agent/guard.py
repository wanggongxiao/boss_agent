"""守卫：全局最小间隔、每日沟通上限、同一目标冷却、连续失败熔断。

这是生产级稳定性与账号保护的核心。所有“发送”类动作都必须先通过 guard。
"""

from __future__ import annotations

import time

from config.settings import settings as get_settings


class CommunicationGuard:
    """沟通动作的限速/冷却/熔断守卫。"""

    def __init__(self):
        cfg = get_settings()
        self._min_interval_s = cfg.agent_global_min_interval_s
        self._daily_limit = cfg.effective_daily_send_limit
        self._cooldown_days = cfg.agent_cooldown_same_target_d

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

    def record_send(self, target_key: str, success: bool) -> None:
        """记录一次发送结果。"""
        now = time.time()
        self._last_action_ts = now
        if success:
            self._day_count += 1
            self._target_last_send[target_key] = now
            self._consecutive_failures = 0
        else:
            self._consecutive_failures += 1