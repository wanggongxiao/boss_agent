"""人工接管与确认：CLI 交互回执。

凡需“发起沟通”的决策，默认需人工确认；用户可随时 pause/skip。
"""

from __future__ import annotations

from loguru import logger


class HumanLoop:
    """提供基于标准输入的人工确认。"""

    def confirm_send(self, title: str, intro: str) -> bool:
        """要求人工确认是否发送开场话术。

        :return: True 表示确认发送；False 表示跳过/拒绝。
        """
        print("\n" + "=" * 60)
        print(f"岗位：{title}")
        print(f"话术：{intro}")
        print("=" * 60)
        answer = input("是否发送？(y=发送 / n=跳过 / q=退出) [n]：").strip().lower()
        if answer == "q":
            logger.info("用户选择退出")
            raise SystemExit(0)
        return answer == "y"

    def wait_for_resume(self) -> None:
        """风控/验证后，等待人工在浏览器处理完成并输入恢复指令。"""
        input("人工处理完成后，按回车键继续（或 Ctrl+C 退出）...")

    def ask_yes_no(self, prompt: str, default: bool = False) -> bool:
        """通用 yes/no 交互。"""
        suffix = "[Y/n]" if default else "[y/N]"
        answer = input(f"{prompt} {suffix}：").strip().lower()
        if answer == "":
            return default
        return answer in ("y", "yes")