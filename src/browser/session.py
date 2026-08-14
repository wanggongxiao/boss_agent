"""浏览器会话管理：持久化 user_data_dir，启动/恢复 Chromium 实例。

DrissionPage 采用延迟导入，避免在尚未安装依赖时影响纯逻辑模块导入。
"""

from __future__ import annotations

from pathlib import Path

from loguru import logger

from config.settings import settings as get_settings


class BrowserSession:
    """负责构建带持久化配置的 DrissionPage ChromiumOptions / ChromiumPage。"""

    def __init__(self):
        cfg = get_settings()
        self._user_data_dir = cfg.browser_user_data_path
        self._executable_path = cfg.browser_executable_path or ""
        self._user_data_dir.mkdir(parents=True, exist_ok=True)

    def _build_chromium_options(self):
        """构建 ChromiumOptions（延迟导入 DrissionPage）。"""
        try:
            from DrissionPage import ChromiumOptions
        except ImportError as exc:  # pragma: no cover - 依赖缺失场景
            logger.error("未安装 DrissionPage，请先执行 pip install -r requirements.txt")
            raise RuntimeError("DrissionPage 未安装") from exc

        options = ChromiumOptions()
        options.set_local_port()  # 自动分配本地调试端口
        options.set_user_data_path(str(self._user_data_dir))
        if self._executable_path:
            options.set_browser_path(self._executable_path)

        # 关闭自动化特征明显的自动化提示（避免自动化信息条）
        options.set_argument("--disable-blink-features=AutomationControlled")
        return options

    def new_page(self):
        """创建新的 ChromiumPage 实例（延迟导入 DrissionPage）。"""
        try:
            from DrissionPage import ChromiumPage
        except ImportError as exc:  # pragma: no cover
            logger.error("未安装 DrissionPage，请先执行 pip install -r requirements.txt")
            raise RuntimeError("DrissionPage 未安装") from exc

        options = self._build_chromium_options()
        page = ChromiumPage(addr_or_opts=options)
        logger.info("浏览器会话已就绪，user_data_dir={}", self._user_data_dir)
        return page

    @property
    def user_data_dir(self) -> Path:
        return self._user_data_dir