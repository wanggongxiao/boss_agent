"""匹配器：RAG 粗筛 + LLM 精判。

- 粗筛：用 JD 查询简历向量库；无向量库（未安装 ChromaDB）时直接放行。
- 精判：用 DeepSeek 对通过粗筛的 JD 做结构化匹配评估。
"""

from __future__ import annotations

from loguru import logger

from config.settings import settings as get_settings
from src.llm.client import DeepSeekClient
from src.llm.prompt_loader import load_prompt
from src.llm.schemas import JobEvaluation
from src.memory.vector_store import VectorStore
from src.pipeline.models import Job


class JobMatcher:
    """组合向量粗筛与 LLM 精判。"""

    def __init__(
        self,
        resume_text: str,
        vector_store: VectorStore | None = None,
        llm: DeepSeekClient | None = None,
        coarse_threshold: float | None = None,
    ):
        self._resume_text = resume_text
        self._vector_store = vector_store
        self._llm = llm
        self._coarse_threshold = (
            get_settings().match_coarse_threshold
            if coarse_threshold is None
            else coarse_threshold
        )

    def coarse_pass(self, job: Job) -> bool:
        """RAG 粗筛：JD 与简历向量是否足够相似。

        未配置向量库时返回 True（放行到 LLM 精判）。
        """
        if self._vector_store is None or not job.jd_text.strip():
            return True

        hits = self._vector_store.query(job.jd_text, top_k=3)
        if not hits:
            # 向量库为空或无结果，放行给 LLM 精判，避免误杀
            return True

        best = max(h.score for h in hits)
        passed = best >= self._coarse_threshold
        logger.info(
            "RAG 粗筛：{} @ {} | best={:.3f} | threshold={:.3f} | passed={}",
            job.title,
            job.company,
            best,
            self._coarse_threshold,
            passed,
        )
        return passed

    def evaluate(self, job: Job) -> JobEvaluation | None:
        """LLM 精判；未配置 LLM 时返回 None。"""
        if not self.coarse_pass(job):
            logger.info("粗筛淘汰：{} @ {}", job.title, job.company)
            return None

        if self._llm is None:
            logger.debug("未配置 LLM，跳过精判：{}", job.title)
            return None

        prompt = load_prompt("match_prompt.txt").format(
            resume=self._resume_text,
            title=job.title,
            jd=job.jd_text or "",
        )
        return self._llm.complete_structured(prompt, JobEvaluation, use_reasoner=True)
