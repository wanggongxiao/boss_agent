"""索引本地简历文本文件到向量库。

用法：
    python scripts/index_resume.py data/resume/resume.txt
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.memory.resume_indexer import ResumeIndexer  # noqa: E402
from src.memory.vector_store import default_vector_store  # noqa: E402
from src.utils.logger import setup_logging  # noqa: E402


def main() -> None:
    setup_logging()

    if len(sys.argv) < 2:
        print("用法: python scripts/index_resume.py <简历txt路径>")
        sys.exit(1)

    resume_path = Path(sys.argv[1])
    if not resume_path.exists():
        print(f"文件不存在: {resume_path}")
        sys.exit(1)

    store = default_vector_store()
    indexer = ResumeIndexer(store)
    count = indexer.index_file(resume_path)
    print(f"简历索引完成，共 {count} 段")


if __name__ == "__main__":
    main()