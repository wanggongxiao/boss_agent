"""向量检索（ChromaDB）封装。

ChromaDB 依赖较重，采用延迟导入；未安装时进入 no-op 降级（粗筛直接放行）。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from loguru import logger

from config.settings import settings as get_settings


@dataclass
class VectorHit:
    """一次向量召回结果。"""

    doc_id: str
    text: str
    score: float


class VectorStore:
    """简历知识库的 ChromaDB 封装（持久化到本地目录）。"""

    def __init__(self, persist_dir: Path, collection_name: str = "resume_chunks"):
        self._persist_dir = persist_dir
        self._collection_name = collection_name
        self._client = None
        self._collection = None

    def _ensure_client(self) -> bool:
        """惰性初始化 ChromaDB；失败返回 False 降级。"""
        if self._client is not None:
            return True
        try:
            import chromadb
        except ImportError:
            logger.warning("ChromaDB 未安装，RAG 粗筛降级为放行")
            return False

        self._persist_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(self._persist_dir))
        self._collection = self._client.get_or_create_collection(name=self._collection_name)
        return True

    def upsert_chunks(self, chunks: list[dict]) -> None:
        """写入简历切片。chunk 形如 {"id": str, "text": str}。"""
        if not self._ensure_client() or not chunks:
            return
        ids = [c["id"] for c in chunks]
        docs = [c["text"] for c in chunks]
        self._collection.upsert(ids=ids, documents=docs)
        logger.info("已写入 {} 条简历切片", len(chunks))

    def query(self, text: str, top_k: int = 5) -> list[VectorHit]:
        """查询与 text 语义最接近的简历切片。"""
        if not self._ensure_client():
            return []
        result = self._collection.query(query_texts=[text], n_results=top_k)
        hits: list[VectorHit] = []
        ids = result.get("ids", [[]])[0]
        docs = result.get("documents", [[]])[0]
        distances = result.get("distances", [[]])[0]
        for i, doc_id in enumerate(ids):
            hits.append(VectorHit(doc_id=doc_id, text=docs[i], score=1.0 - float(distances[i])))
        return hits


def default_vector_store(collection_name: str = "resume_chunks") -> VectorStore:
    """根据全局配置构造默认向量库实例。"""
    return VectorStore(get_settings().chroma_path, collection_name)