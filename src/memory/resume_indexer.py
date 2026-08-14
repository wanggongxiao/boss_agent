"""简历切片与向量化。

将纯文本简历按段落切片，写入向量库，供 RAG 粗筛使用。
"""

from __future__ import annotations

from pathlib import Path

from loguru import logger

from src.memory.vector_store import VectorStore


def _split_paragraphs(text: str) -> list[str]:
    """按空行/换行拆成段落，过滤空段与过短段。"""
    parts = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not parts:
        parts = [p.strip() for p in text.split("\n") if p.strip()]
    return [p for p in parts if len(p) >= 8 and any(char.isalnum() for char in p)]


class ResumeIndexer:
    """读取简历文本文件并写入向量库。"""

    def __init__(self, store: VectorStore):
        self._store = store

    def index_text(self, text: str) -> int:
        """将简历纯文本切片并写入向量库，返回切片数量。"""
        chunks = _split_paragraphs(text)
        payload = [
            {"id": f"chunk_{i}", "text": chunk}
            for i, chunk in enumerate(chunks)
        ]
        self._store.replace_chunks(payload)
        logger.info("简历切片完成，共 {} 段", len(payload))
        return len(payload)

    def index_file(self, path: Path) -> int:
        """读取简历文件并索引。"""
        text = path.read_text(encoding="utf-8")
        return self.index_text(text)
