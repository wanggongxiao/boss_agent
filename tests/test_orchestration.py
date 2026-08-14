"""主流程编排的关键决策测试。"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

from src.agent.orchestration import AgentOrchestration
from src.agent.state_machine import State, StateMachine
from src.pipeline.models import Job


def _orchestration(*, jobs: list[Job], evaluation, confirmed: bool = True):
    retriever = Mock()
    retriever.retrieve.return_value = jobs
    parser = Mock()
    matcher = Mock()
    matcher.evaluate.return_value = evaluation
    communicator = Mock()
    communicator.send_intro.return_value = False
    human_loop = Mock()
    human_loop.confirm_send.return_value = confirmed
    guard = Mock()
    guard.allow_send.return_value = (True, "")

    orchestration = AgentOrchestration(
        retriever=retriever,
        jd_parser=parser,
        matcher=matcher,
        communicator=communicator,
        resume_text="resume",
        human_loop=human_loop,
        guard=guard,
        dry_run=True,
    )
    return orchestration, parser, communicator, human_loop


def test_run_once_honors_limit():
    jobs = [Job(title=f"job-{index}") for index in range(3)]
    evaluation = SimpleNamespace(should_apply=False, custom_intro=None)
    orchestration, parser, _, _ = _orchestration(jobs=jobs, evaluation=evaluation)

    orchestration.run_once(limit=2)

    assert parser.parse.call_count == 2


def test_negative_evaluation_never_reaches_human_or_sender():
    evaluation = SimpleNamespace(should_apply=False, custom_intro="不应发送")
    orchestration, _, communicator, human_loop = _orchestration(
        jobs=[], evaluation=evaluation
    )
    state_machine = StateMachine()

    orchestration._process_job(Job(title="test"), state_machine)

    assert state_machine.state is State.SKIPPED
    human_loop.confirm_send.assert_not_called()
    communicator.send_intro.assert_not_called()


def test_dry_run_finishes_without_recording_real_send():
    evaluation = SimpleNamespace(should_apply=True, custom_intro="你好")
    orchestration, _, communicator, _ = _orchestration(jobs=[], evaluation=evaluation)
    state_machine = StateMachine()

    orchestration._process_job(Job(title="test"), state_machine)

    assert state_machine.state is State.COMPLETED
    communicator.send_intro.assert_called_once_with("你好")
