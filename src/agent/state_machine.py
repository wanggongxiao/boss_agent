"""轻量 FSM 状态机。

状态集合与合法迁移集中定义，便于后续接入 LangGraph 时保持语义一致。
"""

from __future__ import annotations

from enum import Enum, auto


class State(Enum):
    """Agent 状态。"""

    IDLE = auto()
    RETRIEVING = auto()
    PARSING_JD = auto()
    COARSE_MATCHING = auto()
    FINE_MATCHING = auto()
    DECISION_READY = auto()
    GENERATING_INTRO = auto()
    SENDING = auto()
    WAITING_REPLY = auto()
    PAUSED = auto()
    STOPPED = auto()
    ERROR = auto()


# 允许的迁移（当前 -> 后继集合）
_TRANSITIONS: dict[State, set[State]] = {
    State.IDLE: {State.RETRIEVING, State.PARSING_JD, State.STOPPED, State.ERROR},
    State.RETRIEVING: {State.PARSING_JD, State.IDLE, State.PAUSED, State.ERROR},
    State.PARSING_JD: {State.COARSE_MATCHING, State.PAUSED, State.ERROR},
    State.COARSE_MATCHING: {State.FINE_MATCHING, State.DECISION_READY, State.ERROR},
    State.FINE_MATCHING: {State.DECISION_READY, State.GENERATING_INTRO, State.PAUSED, State.ERROR},
    State.DECISION_READY: {State.GENERATING_INTRO, State.SENDING, State.IDLE, State.STOPPED, State.PAUSED},
    State.GENERATING_INTRO: {State.DECISION_READY, State.SENDING, State.PAUSED, State.ERROR},
    State.SENDING: {State.WAITING_REPLY, State.IDLE, State.PAUSED, State.ERROR},
    State.WAITING_REPLY: {State.PARSING_JD, State.IDLE, State.STOPPED, State.PAUSED},
    State.PAUSED: {State.IDLE, State.RETRIEVING, State.STOPPED, State.ERROR},  # 人工恢复后回到安全点
    State.STOPPED: set(),
    State.ERROR: {State.IDLE, State.STOPPED},
}


class StateMachine:
    """维护当前状态，并校验迁移合法性。"""

    def __init__(self, initial: State = State.IDLE):
        self._state = initial

    @property
    def state(self) -> State:
        return self._state

    def can_transition(self, target: State) -> bool:
        return target in _TRANSITIONS.get(self._state, set())

    def transition(self, target: State) -> None:
        if not self.can_transition(target):
            raise ValueError(f"非法状态迁移: {self._state.name} -> {target.name}")
        self._state = target