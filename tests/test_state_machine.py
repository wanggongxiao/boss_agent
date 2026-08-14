"""状态机单元测试。"""

from __future__ import annotations

import pytest

from src.agent.state_machine import State, StateMachine


def test_initial_state_idle():
    sm = StateMachine()
    assert sm.state is State.IDLE


def test_valid_transition():
    sm = StateMachine()
    sm.transition(State.RETRIEVING)
    assert sm.state is State.RETRIEVING


def test_invalid_transition_raises():
    sm = StateMachine()
    # STOPPED 是终态，不能迁移到 RETRIEVING
    sm.transition(State.STOPPED)
    with pytest.raises(ValueError):
        sm.transition(State.RETRIEVING)


def test_can_transition():
    sm = StateMachine()
    assert sm.can_transition(State.RETRIEVING)
    assert not sm.can_transition(State.SENDING)