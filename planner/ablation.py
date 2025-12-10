"""
Experiment 4 — Ablation studies.

消融实验：
- 是否在聚类时使用 popularity 特征（影响分天结果）
- 是否在路线规划时使用 2-opt 优化

注意：popularity 的影响主要在聚类阶段，会影响POI如何被分配到不同的天数中。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import pandas as pd

from .config import CONFIG
from .clustering import select_best_clustering
from .routing import build_route
from .evaluation import evaluate_route
# Note: assign_pois_to_days is imported inside the function to avoid circular import


@dataclass
class AblationResult:
    setting_name: str
    route_length_km: float
    time_efficiency: float
    clustering_silhouette: float  # 添加聚类质量指标
    n_days: int  # 添加天数信息


def toggle_popularity_feature(pois: pd.DataFrame, use_popularity: bool) -> pd.DataFrame:
    """Return a modified copy of POI DataFrame with toggled popularity feature.
    
    在聚类阶段，如果 use_popularity=False，则将 popularity 置零。
    这会影响聚类的特征矩阵，从而影响POI如何被分配到不同的天数。
    
    Args:
        pois: Original POI DataFrame
        use_popularity: Whether to use popularity feature in clustering
    
    Returns:
        Modified DataFrame with popularity potentially zeroed out
    """

    df = pois.copy()
    if not use_popularity and "popularity" in df.columns:
        # 将popularity置零，这样在聚类时不会影响结果
        df["popularity"] = 0.0
    return df


def run_ablation_experiments(pois: pd.DataFrame) -> Dict[str, AblationResult]:
    """Run ablation experiments with full pipeline.
    
    完整的消融实验流程：
    1. 修改popularity特征（影响聚类）
    2. 运行聚类（使用kmeans方法）
    3. 分配POI到天数
    4. 对每天运行路线规划
    5. 评估整体路线质量
    
    Ablation factors:
    - popularity: 是否在聚类时使用popularity特征
    - 2-opt: 是否在路线规划时使用2-opt优化
    
    Returns:
        Dictionary mapping setting names to ablation results
    """
    
    from dataclasses import asdict
    # Import here to avoid circular import
    from .experiments import assign_pois_to_days

    results: Dict[str, AblationResult] = {}
    
    # 确定固定天数（如果LLM模式启用）
    fixed_days = None
    if CONFIG.llm.enabled and CONFIG.llm.num_days:
        fixed_days = CONFIG.llm.num_days
    
    for use_pop in [True, False]:
        for use_two_opt in [True, False]:
            setting = f"pop_{int(use_pop)}_2opt_{int(use_two_opt)}"
            print(f"  Running ablation: {setting}...", end=" ", flush=True)
            
            # Step 1: 修改popularity特征（影响聚类阶段）
            df_mod = toggle_popularity_feature(pois, use_popularity=use_pop)
            
            # Step 2: 运行聚类（使用固定天数或自动选择）
            cluster_results = select_best_clustering(
                df_mod,
                max_days=CONFIG.clustering.max_days,
                fixed_days=fixed_days
            )
            
            # 选择kmeans结果（如果存在）
            if "kmeans" not in cluster_results:
                best_method = next(iter(cluster_results.keys()))
            else:
                best_method = "kmeans"
            
            clustering_result = cluster_results[best_method]
            labels = clustering_result.labels
            silhouette = clustering_result.silhouette or 0.0
            
            # Step 3: 分配POI到天数
            day_pois = assign_pois_to_days(
                df_mod,
                labels,
                max_visit_time_hours=CONFIG.poi_filter.max_visit_time_hours,
                min_visit_time_hours=CONFIG.poi_filter.min_visit_time_hours
            )
            n_days = len(day_pois)
            
            # Step 4 & 5: 对每天进行路线规划并评估
            total_route_length = 0.0
            total_time_efficiency = 0.0
            valid_days = 0
            
            for day, day_df in day_pois.items():
                if len(day_df) == 0:
                    continue
                
                # 使用NN方法进行路线规划
                route = build_route(day_df, method="nn", use_two_opt=use_two_opt)
                metrics = evaluate_route(day_df, route)
                
                total_route_length += metrics.length_km
                total_time_efficiency += metrics.time_efficiency
                valid_days += 1
            
            # 计算平均值
            avg_route_length = total_route_length / valid_days if valid_days > 0 else 0.0
            avg_time_efficiency = total_time_efficiency / valid_days if valid_days > 0 else 0.0
            
            results[setting] = AblationResult(
                setting_name=setting,
                route_length_km=avg_route_length,
                time_efficiency=avg_time_efficiency,
                clustering_silhouette=silhouette,
                n_days=n_days,
            )
            print("Done")
    
    return {k: asdict(v) for k, v in results.items()}


