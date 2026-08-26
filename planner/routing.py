"""
Experiment 2 — Daily Route Optimization.

实现日内路线规划算法：
- Random: 随机顺序
- Rating-based: 按评分排序
- Nearest Neighbor (NN): 最近邻启发式
- 2-opt: 在已有路线基础上进行 2-opt 改善
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable, Dict, List, Sequence

import numpy as np
import pandas as pd


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    """Compute haversine distance in kilometers."""

    R = 6371.0
    lat1_rad, lon1_rad = np.radians(lat1), np.radians(lon1)
    lat2_rad, lon2_rad = np.radians(lat2), np.radians(lon2)
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = (
        np.sin(dlat / 2.0) ** 2
        + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2.0) ** 2
    )
    c = 2 * np.arcsin(np.sqrt(a))
    return float(R * c)


def route_length_km(pois: pd.DataFrame, order: Sequence[int]) -> float:
    """Total route length (km) following index order."""

    if len(order) <= 1:
        return 0.0
    total = 0.0
    for i in range(len(order) - 1):
        a = pois.iloc[order[i]]
        b = pois.iloc[order[i + 1]]
        total += haversine_km(a["lat"], a["lon"], b["lat"], b["lon"])
    return float(total)


def random_route(pois: pd.DataFrame, rng: np.random.Generator | None = None) -> List[int]:
    """Random permutation of POIs."""

    if rng is None:
        rng = np.random.default_rng(seed=42)
    order = list(range(len(pois)))
    rng.shuffle(order)
    return order


def rating_based_route(pois: pd.DataFrame) -> List[int]:
    """Sort POIs by rating (descending).
    
    Returns position indices (0 to n-1) based on iloc.
    Assumes input DataFrame has continuous indices (0 to n-1).
    """
    # Sort by rating and return position indices in sorted order
    sorted_indices = pois.sort_values("rating", ascending=False).index.tolist()
    return sorted_indices


def nearest_neighbor_route(pois: pd.DataFrame) -> List[int]:
    """Simple nearest-neighbor heuristic route.
    
    Returns position indices (0 to n-1) based on iloc.
    Assumes input DataFrame has continuous indices (0 to n-1).
    
    For large datasets (>1000 POIs), uses more efficient computation.
    """

    n = len(pois)
    if n == 0:
        return []

    # Precompute coordinates for faster access
    coords = pois[["lat", "lon"]].values
    
    remaining = set(range(n))
    # 以评分最高的点作为起点（使用位置索引）
    start_idx = int(pois["rating"].idxmax())
    route = [start_idx]
    remaining.remove(start_idx)

    while remaining:
        last_idx = route[-1]
        last_lat, last_lon = coords[last_idx]
        
        # For large sets, limit search to nearest candidates to speed up
        if len(remaining) > 500:
            # Sample a subset of remaining points to check
            remaining_list = list(remaining)
            sample_size = min(100, len(remaining_list))
            candidates = random.sample(remaining_list, sample_size)
        else:
            candidates = remaining
        
        min_dist = float('inf')
        next_idx = None
        
        for idx in candidates:
            poi_lat, poi_lon = coords[idx]
            d = haversine_km(last_lat, last_lon, poi_lat, poi_lon)
            if d < min_dist:
                min_dist = d
                next_idx = idx
        
        if next_idx is not None:
            route.append(next_idx)
            remaining.remove(next_idx)
        else:
            # Fallback: just add any remaining point
            next_idx = remaining.pop()
            route.append(next_idx)

    return route


def two_opt(route: List[int], pois: pd.DataFrame, max_iter: int = 100) -> List[int]:
    """2-opt local search to improve an existing route.
    
    For large routes (>500 POIs), uses adaptive iteration limits and early stopping.
    """
    best_route = route[:]
    n = len(best_route)
    
    # For very large routes, skip 2-opt or use limited iterations
    if n > 1000:
        # Skip 2-opt for very large routes as it's too slow
        return best_route
    elif n > 500:
        # Reduce iterations for large routes
        max_iter = min(max_iter, 10)
    
    improved = True
    iter_count = 0

    while improved and iter_count < max_iter:
        improved = False
        iter_count += 1
        
        # Preserve the first POI, but allow improving the final edge of this
        # open route. Compare only changed edges instead of recomputing the
        # complete route for every candidate reversal.
        if n > 200:
            step = max(1, n // 50)
            indices_i = range(1, n - 1, step)
        else:
            indices_i = range(1, n - 1)
        
        for i in indices_i:
            for j in range(i + 1, n):
                prev_poi = pois.iloc[best_route[i - 1]]
                first_poi = pois.iloc[best_route[i]]
                last_poi = pois.iloc[best_route[j]]
                old_edges = haversine_km(
                    prev_poi["lat"], prev_poi["lon"], first_poi["lat"], first_poi["lon"]
                )
                new_edges = haversine_km(
                    prev_poi["lat"], prev_poi["lon"], last_poi["lat"], last_poi["lon"]
                )
                if j + 1 < n:
                    next_poi = pois.iloc[best_route[j + 1]]
                    old_edges += haversine_km(
                        last_poi["lat"], last_poi["lon"], next_poi["lat"], next_poi["lon"]
                    )
                    new_edges += haversine_km(
                        first_poi["lat"], first_poi["lon"], next_poi["lat"], next_poi["lon"]
                    )

                if new_edges + 1e-9 < old_edges:
                    best_route[i : j + 1] = reversed(best_route[i : j + 1])
                    improved = True
                    break
            if improved:
                break
    return best_route


ROUTING_METHODS: Dict[str, Callable[[pd.DataFrame], List[int]]] = {
    "random": random_route,
    "rating": rating_based_route,
    "nn": nearest_neighbor_route,
}


def build_route(
    pois: pd.DataFrame,
    method: str,
    use_two_opt: bool = False,
) -> List[int]:
    """Build a route for a set of POIs using specified method.

    - method in {random, rating, nn}
    - use_two_opt: 是否在已有结果上做 2-opt 改善
    
    Returns position indices (0 to n-1) relative to the input DataFrame.
    Note: The input DataFrame should have continuous indices or will be reset.
    """

    if method not in ROUTING_METHODS:
        raise ValueError(f"Unknown routing method: {method}")

    # Make a copy and reset index to ensure consistent position indices
    pois_clean = pois.reset_index(drop=True).copy()
    
    base_route = ROUTING_METHODS[method](pois_clean)
    if use_two_opt:
        return two_opt(base_route, pois_clean)
    return base_route

