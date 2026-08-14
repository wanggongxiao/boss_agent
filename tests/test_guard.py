"""发送守卫持久化测试。"""

from src.agent.guard import CommunicationGuard
from src.memory.repo.store import Repository
from tests.test_repository import _connection


def test_cooldown_survives_guard_recreation():
    repository = Repository(_connection())
    first_guard = CommunicationGuard(repository)
    first_guard._min_interval_s = 0
    first_guard.record_send("company|hr", True)

    recreated_guard = CommunicationGuard(repository)
    recreated_guard._min_interval_s = 0
    allowed, reason = recreated_guard.allow_send("company|hr")

    assert not allowed
    assert "冷却期" in reason


def test_failed_attempt_also_triggers_global_interval():
    repository = Repository(_connection())
    guard = CommunicationGuard(repository)
    guard._min_interval_s = 60
    guard.record_send("company|hr", False)

    allowed, reason = guard.allow_send("another|hr")

    assert not allowed
    assert "最小间隔" in reason
