"""
Evaluation utilities for routing and behavior alignment.

评估工具：
- 路线指标：route length, backtracking, time efficiency
- 真实行为对齐：Jaccard, Overlap, DTW
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple

import numpy as np
import pandas as pd

from .routing import haversine_km, route_length_km


@dataclass
class RouteMetrics:
    length_km: float
    backtracking_ratio: float
    time_efficiency: float


def compute_backtracking_ratio(pois: pd.DataFrame, order: Sequence[int]) -> float:
    """Heuristic backtracking ratio.

    定义（启发式）：
    - 假设按最近邻排序可以作为“无明显回头”的基线
    - backtracking_ratio = route_length / baseline_length
      越接近 1 越好，大于 1 表示有额外绕路/回头
    """

    if len(order) <= 1:
        return 1.0

    # 基线：按经纬度排序（使用位置索引）
    # Assumes pois already has continuous indices (0 to n-1)
    baseline = list(
        pois.assign(lat_norm=lambda x: (x["lat"] - x["lat"].min()))
        .sort_values(["lat_norm", "lon"])
        .index
    )
    baseline_len = route_length_km(pois, baseline)
    if baseline_len <= 0:
        return 1.0

    route_len = route_length_km(pois, order)
    return float(route_len / baseline_len)


def compute_time_efficiency(
    pois: pd.DataFrame,
    order: Sequence[int],
    walk_speed_kmh: float = 4.0,
) -> float:
    """Compute time efficiency = visit_time / (visit_time + travel_time).

    - visit_time: sum of duration_min
    - travel_time: 根据路线长度和步行速度估算
    """

    if len(order) == 0:
        return 0.0

    # Use iloc since order contains position indices (assumes continuous indices 0 to n-1)
    visit_time_min = float(pois.iloc[order]["duration_min"].sum())
    dist_km = route_length_km(pois, order)
    travel_time_min = dist_km / walk_speed_kmh * 60.0
    total = visit_time_min + travel_time_min
    if total <= 0:
        return 0.0
    return float(visit_time_min / total)


def evaluate_route(pois: pd.DataFrame, order: Sequence[int]) -> RouteMetrics:
    """Compute all route metrics.
    
    Note: Assumes pois has continuous indices (0 to n-1) and order contains position indices.
    """

    # Reset index to ensure continuous position indices
    pois_reset = pois.reset_index(drop=True)
    length = route_length_km(pois_reset, order)
    backtrack = compute_backtracking_ratio(pois_reset, order)
    time_eff = compute_time_efficiency(pois_reset, order)
    return RouteMetrics(
        length_km=length,
        backtracking_ratio=backtrack,
        time_efficiency=time_eff,
    )


# ==== Real-world behavior alignment metrics ====


def jaccard_similarity(set_a: Iterable, set_b: Iterable) -> float:
    a, b = set(set_a), set(set_b)
    if not a and not b:
        return 1.0
    inter = len(a & b)
    union = len(a | b)
    if union == 0:
        return 0.0
    return float(inter / union)


def overlap_coefficient(set_a: Iterable, set_b: Iterable) -> float:
    a, b = set(set_a), set(set_b)
    if not a or not b:
        return 0.0
    inter = len(a & b)
    denom = min(len(a), len(b))
    return float(inter / denom)


def dtw_distance(seq_a: Sequence[int], seq_b: Sequence[int]) -> float:
    """Simple DTW distance using 0/1 cost (match or mismatch).

    为避免额外依赖，这里使用 O(n*m) 动态规划。
    """

    n, m = len(seq_a), len(seq_b)
    if n == 0 and m == 0:
        return 0.0
    if n == 0 or m == 0:
        return float(max(n, m))

    dp = np.full((n + 1, m + 1), np.inf)
    dp[0, 0] = 0.0

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = 0.0 if seq_a[i - 1] == seq_b[j - 1] else 1.0
            dp[i, j] = cost + min(dp[i - 1, j], dp[i, j - 1], dp[i - 1, j - 1])
    return float(dp[n, m])


@dataclass
class AlignmentMetrics:
    jaccard: float
    overlap: float
    dtw: float


def evaluate_alignment(
    planned_route: Sequence[int],
    real_trajectory: Sequence[int],
) -> AlignmentMetrics:
    """Compare planned POI visit sequence to real trajectory."""

    jacc = jaccard_similarity(planned_route, real_trajectory)
    ov = overlap_coefficient(planned_route, real_trajectory)
    dtw = dtw_distance(planned_route, real_trajectory)
    return AlignmentMetrics(jaccard=jacc, overlap=ov, dtw=dtw)


