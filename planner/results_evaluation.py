"""
Experiment Results Evaluation Module.

实验结果评估模块：汇总、分析和可视化实验结果。
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
from pathlib import Path

import pandas as pd


@dataclass
class ExperimentSummary:
    """Summary of experiment results."""
    
    total_pois: int
    n_days: int
    total_route_length_km: float
    avg_route_length_per_day: float
    avg_pois_per_day: float
    avg_time_efficiency: float
    avg_backtracking_ratio: float
    total_visit_time_hours: float
    avg_visit_time_per_day: float
    
    # Experiment 1 metrics
    clustering_method: str
    clustering_silhouette: Optional[float]
    
    # Experiment 2 metrics
    routing_method: str
    use_two_opt: bool
    
    # Experiment 3 metrics (optional)
    alignment_jaccard: Optional[float] = None
    alignment_overlap: Optional[float] = None
    alignment_dtw: Optional[float] = None
    
    # Experiment 4 metrics (optional)
    ablation_results: Optional[Dict] = None


def evaluate_experiment_results(
    pois: pd.DataFrame,
    cluster_results: Dict,
    day_pois: Dict[int, pd.DataFrame],
    routes: Dict[int, List[int]],
    route_metrics: Dict[int, Dict],
    best_clustering_method: str,
    routing_method: str,
    use_two_opt: bool,
    alignment_metrics: Optional[Dict] = None,
    ablation_results: Optional[Dict] = None,
) -> ExperimentSummary:
    """Evaluate and summarize experiment results.
    
    Args:
        pois: Filtered POIs used in experiments
        cluster_results: Results from Experiment 1
        day_pois: POIs assigned to each day
        routes: Routes for each day
        route_metrics: Route metrics for each day
        best_clustering_method: Clustering method used
        routing_method: Routing method used
        use_two_opt: Whether 2-opt was used
        alignment_metrics: Results from Experiment 3 (optional)
        ablation_results: Results from Experiment 4 (optional)
    
    Returns:
        ExperimentSummary with aggregated metrics
    """
    
    # Basic statistics
    total_pois = len(pois)
    n_days = len(day_pois)
    
    # Route statistics
    total_route_length = sum(m.get('length_km', 0.0) for m in route_metrics.values())
    avg_route_length = total_route_length / n_days if n_days > 0 else 0.0
    
    total_pois_in_routes = sum(len(routes[day]) for day in routes.keys())
    avg_pois_per_day = total_pois_in_routes / n_days if n_days > 0 else 0.0
    
    # Average metrics
    avg_time_efficiency = sum(m.get('time_efficiency', 0.0) for m in route_metrics.values()) / n_days if n_days > 0 else 0.0
    avg_backtracking = sum(m.get('backtracking_ratio', 0.0) for m in route_metrics.values()) / n_days if n_days > 0 else 0.0
    
    # Visit time statistics
    total_visit_time = 0.0
    for day, df in day_pois.items():
        if day in routes:
            route = routes[day]
            day_df = df.reset_index(drop=True)
            for poi_idx in route:
                duration = day_df.iloc[poi_idx].get('duration_min', 60.0)
                total_visit_time += float(duration)
    
    total_visit_time_hours = total_visit_time / 60.0
    avg_visit_time = total_visit_time_hours / n_days if n_days > 0 else 0.0
    
    # Clustering metrics
    clustering_result = cluster_results.get(best_clustering_method)
    clustering_silhouette = clustering_result.silhouette if clustering_result else None
    
    # Alignment metrics
    align_jaccard = alignment_metrics.get('jaccard') if alignment_metrics else None
    align_overlap = alignment_metrics.get('overlap') if alignment_metrics else None
    align_dtw = alignment_metrics.get('dtw') if alignment_metrics else None
    
    return ExperimentSummary(
        total_pois=total_pois,
        n_days=n_days,
        total_route_length_km=total_route_length,
        avg_route_length_per_day=avg_route_length,
        avg_pois_per_day=avg_pois_per_day,
        avg_time_efficiency=avg_time_efficiency,
        avg_backtracking_ratio=avg_backtracking,
        total_visit_time_hours=total_visit_time_hours,
        avg_visit_time_per_day=avg_visit_time,
        clustering_method=best_clustering_method,
        clustering_silhouette=clustering_silhouette,
        routing_method=routing_method,
        use_two_opt=use_two_opt,
        alignment_jaccard=align_jaccard,
        alignment_overlap=align_overlap,
        alignment_dtw=align_dtw,
        ablation_results=ablation_results,
    )


def print_evaluation_summary(summary: ExperimentSummary):
    """Print formatted evaluation summary."""
    
    print("\n" + "=" * 60)
    print("EXPERIMENT RESULTS EVALUATION / 实验结果评估")
    print("=" * 60)
    
    print("\n📊 Overall Statistics / 总体统计:")
    print(f"  Total POIs: {summary.total_pois}")
    print(f"  Number of days: {summary.n_days}")
    print(f"  Average POIs per day: {summary.avg_pois_per_day:.1f}")
    
    print("\n🗺️  Route Statistics / 路线统计:")
    print(f"  Total route length: {summary.total_route_length_km:.2f} km")
    print(f"  Average route length per day: {summary.avg_route_length_per_day:.2f} km")
    print(f"  Average time efficiency: {summary.avg_time_efficiency:.2f}")
    print(f"  Average backtracking ratio: {summary.avg_backtracking_ratio:.3f}")
    print(f"    (Lower is better, <1.0 means better than baseline)")
    
    print("\n⏰ Time Statistics / 时间统计:")
    print(f"  Total visit time: {summary.total_visit_time_hours:.1f} hours")
    print(f"  Average visit time per day: {summary.avg_visit_time_per_day:.1f} hours")
    
    print("\n🔬 Experiment Details / 实验详情:")
    print(f"  Clustering method: {summary.clustering_method}")
    if summary.clustering_silhouette:
        print(f"  Clustering silhouette score: {summary.clustering_silhouette:.3f}")
    print(f"  Routing method: {summary.routing_method}")
    print(f"  Used 2-opt optimization: {summary.use_two_opt}")
    
    if summary.alignment_jaccard is not None:
        print("\n📈 Real-world Alignment / 真实行为对齐:")
        print(f"  Jaccard similarity: {summary.alignment_jaccard:.3f}")
        print(f"  Overlap coefficient: {summary.alignment_overlap:.3f}")
        print(f"  DTW distance: {summary.alignment_dtw:.3f}")
    
    if summary.ablation_results:
        print("\n🧪 Ablation Study / 消融实验:")
        for name, res in summary.ablation_results.items():
            print(f"  {name}:")
            print(f"    Days: {res.get('n_days', 0)}")
            print(f"    Clustering silhouette: {res.get('clustering_silhouette', 0):.3f}")
            print(f"    Route length: {res.get('route_length_km', 0):.2f} km")
            print(f"    Time efficiency: {res.get('time_efficiency', 0):.2f}")
    
    print("\n" + "=" * 60)


def save_evaluation_report(
    summary: ExperimentSummary,
    output_path: Optional[Path] = None,
    format: str = "csv"
):
    """Save evaluation summary to file.
    
    Args:
        summary: Experiment summary
        output_path: Output file path (default: results/evaluation_summary.csv)
        format: Output format ('csv' or 'json')
    """
    if output_path is None:
        output_path = Path("results/evaluation_summary.csv")
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    summary_dict = asdict(summary)
    
    if format.lower() == "csv":
        # Convert to DataFrame for CSV
        df = pd.DataFrame([summary_dict])
        df.to_csv(output_path, index=False)
    elif format.lower() == "json":
        import json
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(summary_dict, f, indent=2, ensure_ascii=False)
    else:
        raise ValueError(f"Unsupported format: {format}")
    
    print(f"\n✓ Evaluation report saved to: {output_path}")

