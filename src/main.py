"""入口：装配完整流程并运行 Agent。

用法示例（在 boss-agent 目录下执行）：

    # 干跑：检索 + 解析 + 匹配 + 话术预览，但不真实发送
    python -m src.main --resume data/resume/resume.txt --limit 5

    # 真实发送（发送前仍会逐条人工确认，需二次 --live 开关）
    python -m src.main --resume data/resume/resume.txt --live

说明：
- 默认 dry-run，不真实发送。
- 缺少 DeepSeek Key 时自动跳过匹配精判与话术生成（只做检索/解析骨架）。
- 缺少 ChromaDB 时 RAG 粗筛放行。
- 缺少 DrissionPage 时给出安装提示并退出。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from config.settings import settings as get_settings
from src.agent.guard import CommunicationGuard
from src.agent.human_loop import HumanLoop
from src.agent.orchestration import AgentOrchestration
from src.browser.page_controller import PageController
from src.llm.client import DeepSeekClient
from src.memory.repo.db import default_database
from src.memory.repo.store import Repository
from src.memory.vector_store import VectorStore
from src.pipeline.communicator import Communicator
from src.pipeline.jd_parser import JdParser
from src.pipeline.matcher import JobMatcher
from src.pipeline.retriever import JobRetriever
from src.utils.logger import logger, setup_logging


def _load_resume(path: Path) -> str:
    """读取简历文本；文件不存在时返回空串并提示。"""
    if not path.exists():
        logger.warning("未找到简历文件：{}（跳过匹配与话术生成）", path)
        return ""
    return path.read_text(encoding="utf-8").strip()


def _build_llm() -> DeepSeekClient | None:
    """按需构建 DeepSeek 客户端；未配置 key 时返回 None。"""
    cfg = get_settings()
    if not cfg.deepseek_api_key:
        logger.warning("未配置 DEEPSEEK_API_KEY，跳过 LLM 精判与话术生成")
        return None
    try:
        return DeepSeekClient()
    except Exception as exc:  # pragma: no cover
        logger.warning("初始化 DeepSeek 客户端失败：{}", exc)
        return None


def _build_vector_store() -> VectorStore | None:
    """按需构建向量库；未安装 ChromaDB 时返回 None。"""
    cfg = get_settings()
    try:
        import chromadb  # noqa: F401
    except ImportError:
        logger.warning("未安装 ChromaDB，RAG 粗筛放行")
        return None
    return VectorStore(cfg.chroma_path)


def build_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="BOSS 直聘求职辅助智能体")
    parser.add_argument(
        "--resume",
        type=Path,
        default=Path("data/resume/resume.txt"),
        help="简历纯文本文件路径",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="本轮最多处理岗位数（0 表示不限制）",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="真实发送沟通（默认 dry-run；发送前仍逐条人工确认）",
    )
    return parser.parse_args()


def main() -> None:
    setup_logging()
    args = build_args()

    cfg = get_settings()
    logger.info(
        "boss-agent 启动 | tier={} | daily_limit={} | live={}",
        cfg.agent_safety_tier.value,
        cfg.effective_daily_send_limit,
        args.live,
    )

    # 简历
    resume_text = _load_resume(args.resume)

    # 可选组件
    llm = _build_llm()
    vector_store = _build_vector_store()
    conn = default_database().initialize()
    repository = Repository(conn)

    # 浏览器会话（DrissionPage 延迟导入）
    try:
        from src.browser.session import BrowserSession  # noqa: F401
    except RuntimeError as exc:
        logger.error(str(exc))
        print("\n请先安装依赖：pip install -r requirements.txt\n", file=sys.stderr)
        sys.exit(1)

    try:
        session = BrowserSession()
        page = PageController.from_session(session)
    except RuntimeError as exc:
        conn.close()
        logger.error(str(exc))
        print("\n浏览器启动失败，请检查 Chrome 与 DrissionPage 配置。\n", file=sys.stderr)
        sys.exit(1)

    try:
        human_loop = HumanLoop()
        retriever = JobRetriever(page, human_loop=human_loop)
        jd_parser = JdParser(page)  # 结构化解析器可后续注入 LLM 版本
        matcher = JobMatcher(resume_text, vector_store=vector_store, llm=llm)
        communicator = Communicator(page, dry_run=not args.live)

        orch = AgentOrchestration(
            retriever=retriever,
            jd_parser=jd_parser,
            matcher=matcher,
            communicator=communicator,
            resume_text=resume_text,
            llm=llm,
            vector_store=vector_store,
            human_loop=human_loop,
            guard=CommunicationGuard(repository),
            repository=repository,
            dry_run=not args.live,
        )

        orch.run_once(limit=args.limit)
    finally:
        page.close()
        conn.close()

    logger.info("本轮执行结束")


if __name__ == "__main__":
    main()
