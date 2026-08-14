"""拟真行为：高斯分布延迟、贝塞尔轨迹、打字拟真、分段滚动。

设计目标：让自动化动作贴近“真人低频浏览”，禁止固定时长休眠。
"""

from __future__ import annotations

import random
import time


def gaussian_sleep(mean: float, sigma: float, floor: float = 0.0) -> float:
    """按高斯分布休眠，返回值供调用方观测（用于调试/审计）。

    :param mean: 均值（秒）
    :param sigma: 标准差（秒）
    :param floor: 下限（秒），防止负值或过短
    """
    delay = max(floor, random.gauss(mean, sigma))
    time.sleep(delay)
    return delay


def typing_interval(min_ms: float = 40.0, max_ms: float = 180.0) -> float:
    """单字符间隔（毫秒）：均匀区间内随机，避免固定节奏。"""
    return random.uniform(min_ms, max_ms)


def human_type_text(text: str, typo_rate: float = 0.03) -> None:
    """模拟打字：逐字符随机间隔，偶发回删重打（typo 概率）。"""
    for _ in text:
        interval_s = typing_interval() / 1000.0
        time.sleep(interval_s)

        # 偶发“打错-回删-重打”
        if random.random() < typo_rate:
            time.sleep(random.uniform(0.1, 0.3))


def _bezier_point(p0: float, p1: float, p2: float, p3: float, t: float) -> float:
    """三阶贝塞尔曲线上 t 处的坐标分量。"""
    u = 1.0 - t
    return (
        u * u * u * p0
        + 3 * u * u * t * p1
        + 3 * u * t * t * p2
        + t * t * t * p3
    )


def bezier_trajectory(
    start: tuple[float, float],
    end: tuple[float, float],
    steps: int = 30,
    curvature: float = 0.2,
) -> list[tuple[float, float]]:
    """生成从 start 到 end 的三阶贝塞尔鼠标轨迹。

    :param curvature: 控制点相对位移的偏移比例（0~0.5），越大越弯曲。
    """
    x0, y0 = start
    x3, y3 = end
    dx = x3 - x0
    dy = y3 - y0

    # 两个控制点沿直线方向，并加入正交扰动形成弧线
    cx1 = x0 + dx * 0.25 - dy * curvature
    cy1 = y0 + dy * 0.25 + dx * curvature
    cx2 = x0 + dx * 0.75 + dy * curvature
    cy2 = y0 + dy * 0.75 - dx * curvature

    points: list[tuple[float, float]] = []
    for i in range(steps + 1):
        t = i / steps
        x = _bezier_point(x0, cx1, cx2, x3, t)
        y = _bezier_point(y0, cy1, cy2, y3, t)
        points.append((x, y))
    return points


def scroll_pause(mean: float = 1.5, sigma: float = 0.6, floor: float = 0.3) -> float:
    """滚动后停顿：高斯分布。"""
    return gaussian_sleep(mean, sigma, floor)