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


# ==== POI Popularity Alignment Metrics ====


@dataclass
class PopularityAlignmentMetrics:
    """Metrics for POI popularity alignment between planned and real-world visits."""
    top_k_overlap: float  # Overlap of top-K POIs
    spearman_correlation: float  # Rank correlation
    coverage_at_k: float  # Coverage@K: how many of top-K real POIs are covered


def top_k_overlap(
    planned_popularity: List[Tuple[int, float]],
    real_popularity: List[Tuple[int, float]],
    k: int,
) -> float:
    """Calculate overlap between top-K POIs from planned and real popularity rankings.
    
    Args:
        planned_popularity: List of (poi_id, popularity_score) tuples from planned routes
        real_popularity: List of (poi_id, popularity_score) tuples from real trajectories
        k: Number of top POIs to consider
    
    Returns:
        Overlap ratio (0 to 1): |top_k_planned ∩ top_k_real| / k
    """
    if k <= 0 or not planned_popularity or not real_popularity:
        return 0.0
    
    # Get top-K POI IDs
    top_k_planned = set([poi_id for poi_id, _ in planned_popularity[:k]])
    top_k_real = set([poi_id for poi_id, _ in real_popularity[:k]])
    
    # Calculate overlap
    overlap = len(top_k_planned & top_k_real)
    return float(overlap / k)


def spearman_rank_correlation(
    planned_popularity: List[Tuple[int, float]],
    real_popularity: List[Tuple[int, float]],
) -> float:
    """Calculate Spearman rank correlation between planned and real POI popularity.
    
    Args:
        planned_popularity: List of (poi_id, popularity_score) tuples from planned routes
        real_popularity: List of (poi_id, popularity_score) tuples from real trajectories
    
    Returns:
        Spearman correlation coefficient (-1 to 1)
    """
    if not planned_popularity or not real_popularity:
        return 0.0
    
    # Create rank mappings
    planned_ranks = {poi_id: rank for rank, (poi_id, _) in enumerate(planned_popularity, 1)}
    real_ranks = {poi_id: rank for rank, (poi_id, _) in enumerate(real_popularity, 1)}
    
    # Find common POIs
    common_pois = set(planned_ranks.keys()) & set(real_ranks.keys())
    
    if len(common_pois) < 2:
        return 0.0
    
    # Get ranks for common POIs
    planned_rank_values = [planned_ranks[poi_id] for poi_id in common_pois]
    real_rank_values = [real_ranks[poi_id] for poi_id in common_pois]
    
    # Calculate Spearman correlation using numpy
    try:
        from scipy.stats import spearmanr
        correlation, _ = spearmanr(planned_rank_values, real_rank_values)
        return float(correlation) if not np.isnan(correlation) else 0.0
    except ImportError:
        # Fallback: use numpy correlation on ranks
        correlation = np.corrcoef(planned_rank_values, real_rank_values)[0, 1]
        return float(correlation) if not np.isnan(correlation) else 0.0


def coverage_at_k(
    planned_popularity: List[Tuple[int, float]],
    real_popularity: List[Tuple[int, float]],
    k: int,
) -> float:
    """Calculate coverage@K: how many of the top-K real POIs are covered in planned routes.
    
    Args:
        planned_popularity: List of (poi_id, popularity_score) tuples from planned routes
        real_popularity: List of (poi_id, popularity_score) tuples from real trajectories
        k: Number of top real POIs to consider
    
    Returns:
        Coverage ratio (0 to 1): |top_k_real ∩ all_planned| / k
    """
    if k <= 0 or not planned_popularity or not real_popularity:
        return 0.0
    
    # Get top-K real POI IDs
    top_k_real = set([poi_id for poi_id, _ in real_popularity[:k]])
    
    # Get all planned POI IDs
    all_planned = set([poi_id for poi_id, _ in planned_popularity])
    
    # Calculate coverage
    covered = len(top_k_real & all_planned)
    return float(covered / k)


def evaluate_poi_popularity_alignment(
    planned_popularity: List[Tuple[int, float]],
    real_popularity: List[Tuple[int, float]],
    k: int = 10,
) -> PopularityAlignmentMetrics:
    """Evaluate alignment between planned and real POI popularity.
    
    Args:
        planned_popularity: List of (poi_id, popularity_score) sorted by popularity (descending)
        real_popularity: List of (poi_id, popularity_score) sorted by popularity (descending)
        k: Number of top POIs to consider for Top-K metrics
    
    Returns:
        PopularityAlignmentMetrics with top_k_overlap, spearman_correlation, and coverage_at_k
    """
    top_k_ov = top_k_overlap(planned_popularity, real_popularity, k)
    spearman_corr = spearman_rank_correlation(planned_popularity, real_popularity)
    coverage_k = coverage_at_k(planned_popularity, real_popularity, k)
    
    return PopularityAlignmentMetrics(
        top_k_overlap=top_k_ov,
        spearman_correlation=spearman_corr,
        coverage_at_k=coverage_k,
    )


