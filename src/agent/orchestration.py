"""编排器：把检索 → 解析 → 匹配 → 人工确认 → 沟通串联成流程。

- 每个岗位使用独立的局部状态机，避免跨岗位状态残留。
- 默认 dry-run（不真实发送），dry-run 不计入失败熔断。
"""

from __future__ import annotations

from loguru import logger

from src.agent.guard import CommunicationGuard
from src.agent.human_loop import HumanLoop
from src.agent.state_machine import State, StateMachine
from src.llm.client import DeepSeekClient
from src.llm.prompt_loader import load_prompt
from src.llm.schemas import IntroGeneration
from src.memory.repo.store import Repository
from src.memory.vector_store import VectorStore
from src.pipeline.communicator import Communicator
from src.pipeline.jd_parser import JdParser
from src.pipeline.matcher import JobMatcher
from src.pipeline.models import Job
from src.pipeline.retriever import JobRetriever


class AgentOrchestration:
    """Agent 主流程编排。"""

    def __init__(
        self,
        retriever: JobRetriever,
        jd_parser: JdParser,
        matcher: JobMatcher,
        communicator: Communicator,
        resume_text: str,
        llm: DeepSeekClient | None = None,
        vector_store: VectorStore | None = None,
        human_loop: HumanLoop | None = None,
        guard: CommunicationGuard | None = None,
        repository: Repository | None = None,
        dry_run: bool = True,
    ):
        self._retriever = retriever
        self._jd_parser = jd_parser
        self._matcher = matcher
        self._communicator = communicator
        self._resume_text = resume_text
        self._llm = llm
        self._vector_store = vector_store
        self._human_loop = human_loop or HumanLoop()
        self._guard = guard or CommunicationGuard()
        self._repository = repository
        self._dry_run = dry_run
        self._run_sm = StateMachine()

    def run_once(self, limit: int = 0) -> None:
        """执行一轮最小闭环。"""
        run_id = self._repository.start_run() if self._repository is not None else None
        try:
            self._run_sm.transition(State.RETRIEVING)
            jobs = self._retriever.retrieve()
            logger.info("本轮共检索到 {} 个岗位", len(jobs))
            if limit > 0:
                jobs = jobs[:limit]
                logger.info("按 limit={} 处理 {} 个岗位", limit, len(jobs))

            for job in jobs:
                if self._should_skip_persisted(job):
                    continue
                job_sm = StateMachine()
                try:
                    self._process_job(job, job_sm)
                except Exception:  # noqa: BLE001 - 单岗位失败不终止整轮
                    if job_sm.can_transition(State.ERROR):
                        job_sm.transition(State.ERROR)
                    logger.exception("处理岗位失败，继续下一条：{} @ {}", job.title, job.company)
                finally:
                    if self._repository is not None and run_id is not None:
                        self._repository.record_action(run_id)

            self._run_sm.transition(State.IDLE)
        finally:
            if self._repository is not None and run_id is not None:
                self._repository.end_run(run_id)

    def _should_skip_persisted(self, job: Job) -> bool:
        if self._repository is None:
            return False
        if self._repository.is_blacklisted(job.company, job.hr_id):
            logger.info("黑名单跳过：{} @ {}", job.title, job.company)
            return True
        if self._repository.is_job_processed(job):
            logger.info("已处理岗位跳过：{} @ {}", job.title, job.company)
            return True
        return False

    def _process_job(self, job: Job, sm: StateMachine) -> None:
        """处理单个岗位（使用独立状态机 sm）。"""
        sm.transition(State.PARSING_JD)
        self._jd_parser.parse(job)
        job_id = self._repository.upsert_job(job) if self._repository is not None else None

        sm.transition(State.COARSE_MATCHING)
        evaluation = self._matcher.evaluate(job)

        if evaluation is not None and self._repository is not None and job_id is not None:
            self._repository.save_evaluation(
                job_id=job_id,
                match_score=evaluation.match_score,
                should_apply=evaluation.should_apply,
                reasons=evaluation.reasons,
                intro_text=evaluation.custom_intro or "",
                model_version="deepseek",
            )

        sm.transition(State.FINE_MATCHING)
        if evaluation is None or not evaluation.should_apply:
            sm.transition(State.SKIPPED)
            logger.info("匹配评估不建议沟通，跳过：{} @ {}", job.title, job.company)
            return

        intro = self._generate_intro(job, evaluation.custom_intro, sm)

        sm.transition(State.DECISION_READY)
        if intro is None:
            sm.transition(State.SKIPPED)
            logger.info("跳过（无建议）：{} @ {}", job.title, job.company)
            return

        if not self._human_loop.confirm_send(job.title, intro):
            sm.transition(State.SKIPPED)
            logger.info("人工跳过：{} @ {}", job.title, job.company)
            return

        sm.transition(State.SENDING)
        target_key = f"{job.company}|{job.hr_id}"
        allowed, reason = self._guard.allow_send(target_key)
        if not allowed:
            sm.transition(State.BLOCKED)
            logger.warning("guard 拦截发送：{}", reason)
            return

        success = self._communicator.send_intro(intro)

        if self._dry_run:
            # dry-run 未真实发送，不属于失败，不计入 guard 统计
            logger.info("[dry-run] 未真实发送，不计入熔断统计")
            sm.transition(State.COMPLETED)
            return

        self._guard.record_send(target_key, success, job_id)

        if self._repository is not None and job_id is not None:
            self._repository.save_conversation_status(
                job_id, job.hr_id, "sent" if success else "failed"
            )

        if success:
            sm.transition(State.WAITING_REPLY)
        else:
            sm.transition(State.IDLE)

    def _generate_intro(
        self, job: Job, custom_intro: str | None, sm: StateMachine
    ) -> str | None:
        """生成开场话术：优先用匹配阶段的 custom_intro，否则调用 LLM。"""
        if custom_intro:
            return custom_intro

        if self._llm is None:
            logger.debug("未配置 LLM，使用空话术（跳过）")
            return None

        sm.transition(State.GENERATING_INTRO)
        prompt = load_prompt("intro_prompt.txt").format(
            resume=self._resume_text,
            title=job.title,
            company=job.company,
        )
        result = self._llm.complete_structured(prompt, IntroGeneration, use_reasoner=False)
        return result.intro
