"""初始化 SQLite 数据库（建库目录 + 建表迁移）。

用法：
    python scripts/init_db.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# 将项目根目录加入 sys.path，便于以任意 CWD 运行脚本
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.memory.repo.db import default_database  # noqa: E402
from src.utils.logger import setup_logging  # noqa: E402


def main() -> None:
    setup_logging()
    db = default_database()
    conn = db.initialize()
    conn.close()
    print("数据库初始化完成")


if __name__ == "__main__":
    main()