"""
Experiment 4 — Ablation studies.

消融实验：
- 是否使用 category / popularity 特征
- 是否使用 2-opt 改善
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import pandas as pd

from .clustering import _build_feature_matrix, select_best_clustering
from .routing import build_route
from .evaluation import evaluate_route


@dataclass
class AblationResult:
    setting_name: str
    route_length_km: float
    time_efficiency: float


def toggle_features(pois: pd.DataFrame, use_category: bool, use_popularity: bool) -> pd.DataFrame:
    """Return a modified copy of POI DataFrame with toggled features.

    - 如果 use_popularity=False，则将 popularity 置零
    - category 在当前 demo 实现中主要体现在后续扩展，
      这里给出接口以便后续做基于类别的筛选或权重。
    """

    df = pois.copy()
    if not use_popularity and "popularity" in df.columns:
        df["popularity"] = 0.0
    # category 的更复杂使用可以在此扩展
    return df


def run_ablation_experiments(pois: pd.DataFrame) -> Dict[str, AblationResult]:
    """Run ablation for:
    - with/without popularity
    - with/without 2-opt
    """

    results: Dict[str, AblationResult] = {}
    for use_pop in [True, False]:
        for use_two_opt in [True, False]:
            setting = f"pop_{int(use_pop)}_2opt_{int(use_two_opt)}"
            df_mod = toggle_features(pois, use_category=True, use_popularity=use_pop)
            # 简单用 rating-based 作为基线路线
            route = build_route(df_mod, method="rating", use_two_opt=use_two_opt)
            metrics = evaluate_route(df_mod, route)
            results[setting] = AblationResult(
                setting_name=setting,
                route_length_km=metrics.length_km,
                time_efficiency=metrics.time_efficiency,
            )
    return results


