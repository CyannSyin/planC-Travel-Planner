"""
High-level experiment runners.

整体实验控制：
- Experiment 1: POI Clustering → 推断出天数（clusters）
- Experiment 2: Daily Route Optimization
- Experiment 3: Real-world Behavior Alignment（基于 Gowalla）
- Experiment 4: Ablation Study
"""

from __future__ import annotations

import re
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from .config import CONFIG
from .data_loader import load_gowalla_checkins, load_osm_pois, filter_pois
from .clustering import ClusteringResult, select_best_clustering
from .routing import build_route
from .evaluation import evaluate_route, evaluate_alignment
from .ablation import run_ablation_experiments
from .results_evaluation import evaluate_experiment_results, print_evaluation_summary, save_evaluation_report


def experiment_1_poi_clustering(pois: pd.DataFrame) -> Dict[str, ClusteringResult]:
    """Experiment 1 — run clustering and select best clustering for each method."""

    results = select_best_clustering(pois, max_days=CONFIG.clustering.max_days)
    return results


def assign_pois_to_days(
    pois: pd.DataFrame, 
    labels,
    max_visit_time_hours: Optional[float] = None,
    min_visit_time_hours: Optional[float] = None
) -> Dict[int, pd.DataFrame]:
    """Group POIs by cluster label (day).
    
    Applies constraints:
    - Maximum visit time constraint: removes POIs that exceed the time limit
    - Minimum visit time constraint: ensures each day has at least min_visit_time_hours
      by redistributing POIs from days that exceed max time or have excess capacity
    
    Returns DataFrames with reset indices (0 to n-1) for each day.
    """

    pois = pois.copy()
    pois["day"] = labels
    day_groups: Dict[int, pd.DataFrame] = {}
    unassigned_pois: List[pd.DataFrame] = []  # POIs removed due to max time constraint
    
    # Step 1: Initial assignment with max time constraint
    for day, group in pois.groupby("day"):
        if day >= 0:
            # Reset index to ensure continuous position indices (0 to n-1)
            day_df = group.drop(columns=["day"]).reset_index(drop=True)
            
            # Apply maximum visit time constraint if specified
            if max_visit_time_hours is not None and 'duration_min' in day_df.columns:
                max_time_min = max_visit_time_hours * 60.0
                cumulative_time = 0.0
                selected_indices = []
                
                # Sort by rating (descending) to prioritize high-rating POIs
                sorted_df = day_df.sort_values('rating', ascending=False)
                
                for idx in sorted_df.index:
                    duration = float(sorted_df.loc[idx, 'duration_min'])
                    if cumulative_time + duration <= max_time_min:
                        selected_indices.append(idx)
                        cumulative_time += duration
                    else:
                        # Store unassigned POI for potential redistribution
                        unassigned_pois.append(sorted_df.loc[[idx]])
                
                if selected_indices:
                    day_df = sorted_df.loc[selected_indices].reset_index(drop=True)
                else:
                    # If even the first POI exceeds limit, take just the first one
                    day_df = sorted_df.head(1).reset_index(drop=True)
            
            day_groups[int(day)] = day_df
    
    # Step 2: Apply minimum visit time constraint
    if min_visit_time_hours is not None and 'duration_min' in pois.columns:
        min_time_min = min_visit_time_hours * 60.0
        
        # Collect all unassigned POIs into a single DataFrame
        if unassigned_pois:
            unassigned_df = pd.concat(unassigned_pois, ignore_index=True)
            unassigned_df = unassigned_df.sort_values('rating', ascending=False)
        else:
            unassigned_df = pd.DataFrame()
        
        # Check each day and fill if below minimum
        for day in sorted(day_groups.keys()):
            day_df = day_groups[day]
            if 'duration_min' not in day_df.columns:
                continue
                
            total_time = day_df['duration_min'].sum()
            
            if total_time < min_time_min:
                # Need to add more POIs to meet minimum
                needed_time = min_time_min - total_time
                
                # Try to get POIs from unassigned pool
                added_indices = []
                cumulative_time = 0.0
                
                for idx in unassigned_df.index:
                    if cumulative_time >= needed_time:
                        break
                    duration = float(unassigned_df.loc[idx, 'duration_min'])
                    if cumulative_time + duration <= needed_time + 30:  # Allow small overflow
                        added_indices.append(idx)
                        cumulative_time += duration
                
                if added_indices:
                    # Add POIs to this day
                    new_pois = unassigned_df.loc[added_indices].copy()
                    day_df = pd.concat([day_df, new_pois], ignore_index=True)
                    day_groups[day] = day_df
                    
                    # Remove added POIs from unassigned pool
                    unassigned_df = unassigned_df.drop(added_indices).reset_index(drop=True)
                else:
                    # If no unassigned POIs available, try to borrow from other days
                    # (only if they exceed minimum significantly)
                    for other_day in sorted(day_groups.keys()):
                        if other_day == day:
                            continue
                        other_df = day_groups[other_day]
                        if 'duration_min' not in other_df.columns:
                            continue
                        other_time = other_df['duration_min'].sum()
                        
                        # Only borrow if other day has significantly more than minimum
                        if other_time > min_time_min + 60:  # At least 1 hour above minimum
                            # Try to borrow one high-rating POI
                            other_df_sorted = other_df.sort_values('rating', ascending=False)
                            for idx in other_df_sorted.index:
                                duration = float(other_df_sorted.loc[idx, 'duration_min'])
                                if duration <= needed_time + 30:
                                    # Borrow this POI
                                    borrowed = other_df_sorted.loc[[idx]]
                                    day_df = pd.concat([day_df, borrowed], ignore_index=True)
                                    day_groups[day] = day_df
                                    
                                    # Remove from other day
                                    other_df = other_df_sorted.drop([idx]).reset_index(drop=True)
                                    day_groups[other_day] = other_df
                                    break
                            break  # Only borrow from one day
    
    return day_groups


def experiment_2_daily_routes(
    day_pois: Dict[int, pd.DataFrame],
    method: str,
    use_two_opt: bool = False,
):
    """Experiment 2 — optimize routes for each day."""

    routes = {}
    metrics = {}
    total_days = len(day_pois)
    
    for day_idx, (day, df) in enumerate(sorted(day_pois.items()), 1):
        n_pois = len(df)
        print(f"  Processing Day {day} ({n_pois} POIs)...", end=" ", flush=True)
        
        # For very large POI sets, skip 2-opt to save time
        if n_pois > 500 and use_two_opt:
            print(f"(skipping 2-opt for large dataset)", end=" ", flush=True)
            use_two_opt_day = False
        else:
            use_two_opt_day = use_two_opt
        
        order = build_route(df, method=method, use_two_opt=use_two_opt_day)
        routes[day] = order
        metrics[day] = asdict(evaluate_route(df, order))
        print("Done", flush=True)
    
    return routes, metrics


def experiment_3_behavior_alignment(
    planned_route: List[int],
    gowalla_traj: List[int],
):
    """Experiment 3 — compare planned route to real-world Gowalla behavior."""

    metrics = evaluate_alignment(planned_route, gowalla_traj)
    return asdict(metrics)


def build_synthetic_gowalla_sequence(pois: pd.DataFrame, order: List[int]) -> List[int]:
    """Toy helper: map POI indices to synthetic location IDs.

    真正实验中，你会根据 Gowalla_totalCheckins 中的 location_id
    与 OSM POI 做匹配（例如基于 spatial join），这里仅提供接口示例。
    """
    location_ids = []
    for i in order:
        poi_id_str = str(pois.iloc[i]["poi_id"])
        
        # Handle different POI ID formats:
        # 1. Plain integer: "12345"
        # 2. Tuple string: "('node', 5222387777)"
        # 3. Other formats
        
        # Try to extract numeric ID from tuple format
        match = re.search(r'(\d+)', poi_id_str)
        if match:
            numeric_id = int(match.group(1))
        else:
            # Fallback: use hash of string as ID
            numeric_id = abs(hash(poi_id_str)) % (10**10)
        
        location_ids.append(numeric_id)
    
    return location_ids


def experiment_4_ablation(pois: pd.DataFrame):
    """Experiment 4 — ablation (category/popularity, 2-opt)."""

    results = run_ablation_experiments(pois)
    return {k: asdict(v) for k, v in results.items()}


def run_all_experiments():
    """Convenience function to run all experiments end-to-end.

    注意：这里假设你已经准备好 OSM POI CSV 和 Gowalla 数据，
    并在 config 中配置好路径。
    """

    pois_raw = load_osm_pois()
    gowalla = load_gowalla_checkins()

    print("=== POI Filtering ===")
    print(f"Total POIs loaded: {len(pois_raw)}")
    
    # Filter POIs to get a reasonable subset
    pois = filter_pois(pois_raw, filter_config=CONFIG.poi_filter)
    print(f"POIs after filtering:")
    print(f"  - Min rating: {CONFIG.poi_filter.min_rating}")
    print(f"  - Max POIs: {CONFIG.poi_filter.max_pois}")
    print(f"  - Category limit: {CONFIG.poi_filter.category_limit}")
    print(f"  - Selected POIs: {len(pois)}")

    print("\n=== Experiment 1: POI Clustering ===")
    print("(This experiment clusters POIs into days. Route planning is in Experiment 2)")
    print(f"Total POIs for clustering: {len(pois)}")
    cluster_results = experiment_1_poi_clustering(pois)
    for method, res in cluster_results.items():
        silhouette_str = f"{res.silhouette:.3f}" if res.silhouette is not None else "NA"
        print(f"{method}: n_clusters={res.n_clusters}, silhouette={silhouette_str}")

    # 选一个方法（比如 KMeans）作为最终分天方案
    if "kmeans" not in cluster_results:
        print("KMeans result not found, fallback to first method.")
        best_method = next(iter(cluster_results.keys()))
    else:
        best_method = "kmeans"
    labels = cluster_results[best_method].labels
    # Apply maximum and minimum visit time constraints if configured
    max_visit_time = CONFIG.poi_filter.max_visit_time_hours
    min_visit_time = CONFIG.poi_filter.min_visit_time_hours
    day_pois = assign_pois_to_days(
        pois, 
        labels, 
        max_visit_time_hours=max_visit_time,
        min_visit_time_hours=min_visit_time
    )
    
    print(f"\nUsing {best_method} clustering result: {len(day_pois)} days")
    if max_visit_time:
        print(f"  (Applied max visit time constraint: {max_visit_time} hours/day)")
    if min_visit_time:
        print(f"  (Applied min visit time constraint: {min_visit_time} hours/day)")
    for day in sorted(day_pois.keys()):
        n_pois = len(day_pois[day])
        total_time = day_pois[day]['duration_min'].sum() / 60.0 if 'duration_min' in day_pois[day].columns else 0.0
        min_met = "✓" if min_visit_time is None or total_time >= min_visit_time else "✗"
        print(f"  Day {day}: {n_pois} POIs ({total_time:.1f} hours) {min_met}")

    print("\n=== Experiment 2: Daily Route Optimization (NN + 2-opt) ===")
    routes, route_metrics = experiment_2_daily_routes(
        day_pois, method="nn", use_two_opt=True
    )
    for day, m in sorted(route_metrics.items()):
        print(f"\nDay {day}:")
        print(f"  Total length: {m['length_km']:.2f} km")
        print(f"  Time efficiency: {m['time_efficiency']:.2f}")
        print(f"  Backtracking ratio: {m['backtracking_ratio']:.3f}")
        
        # Show detailed route with POI names
        day_route = routes[day]
        day_df = day_pois[day].reset_index(drop=True)  # Reset index for clean access
        print(f"  Route (visiting {len(day_route)} POIs):")
        total_duration = 0.0
        for idx, poi_idx in enumerate(day_route, 1):
            poi = day_df.iloc[poi_idx]
            # Safe access to pandas Series values
            poi_name = str(poi.get('name', poi.get('poi_id', f'POI-{poi_idx}')))
            poi_cat = str(poi.get('category', 'unknown'))
            try:
                poi_rating = float(poi.get('rating', 0.0))
            except (ValueError, TypeError):
                poi_rating = 0.0
            try:
                poi_duration = float(poi.get('duration_min', 60.0))
            except (ValueError, TypeError):
                poi_duration = 60.0
            total_duration += poi_duration
            # Truncate long names for better display
            if len(poi_name) > 40:
                poi_name = poi_name[:37] + "..."
            print(f"    {idx}. {poi_name} ({poi_cat}) - Rating: {poi_rating:.1f}, Duration: {poi_duration:.0f}min")
        print(f"  Total visit time: {total_duration/60:.1f} hours")
    
    # Summary of all routes
    print("\n  --- Route Summary ---")
    total_route_length = sum(m['length_km'] for m in route_metrics.values())
    total_pois = sum(len(routes[day]) for day in routes.keys())
    print(f"  Total route length across all days: {total_route_length:.2f} km")
    print(f"  Total POIs to visit: {total_pois}")

    print("\n=== Experiment 3: Real-world Behavior Alignment (toy) ===")
    # 这里只做一个示例：选一天，把 planned_route 映射为 location_id 列表；
    # 实际上你会从 gowalla DataFrame 中提取真实轨迹进行对比。
    sample_day = next(iter(routes.keys()))
    planned = build_synthetic_gowalla_sequence(day_pois[sample_day], routes[sample_day])
    # toy: 假设真实轨迹与 planned 稍有扰动
    real_traj = planned[::-1]
    align_metrics = experiment_3_behavior_alignment(planned, real_traj)
    print("Alignment metrics:", align_metrics)

    print("\n=== Experiment 4: Ablation ===")
    ablation = experiment_4_ablation(pois)
    for name, res in ablation.items():
        print(f"{name}: length={res['route_length_km']:.2f} km, time_eff={res['time_efficiency']:.2f}")
    
    # Generate evaluation summary
    print("\n=== Generating Evaluation Report ===")
    summary = evaluate_experiment_results(
        pois=pois,
        cluster_results=cluster_results,
        day_pois=day_pois,
        routes=routes,
        route_metrics=route_metrics,
        best_clustering_method=best_method,
        routing_method="nn",
        use_two_opt=True,
        alignment_metrics=align_metrics,
        ablation_results=ablation,
    )
    
    print_evaluation_summary(summary)
    
    # Optionally save report to file
    try:
        save_evaluation_report(summary, Path("results/evaluation_summary.csv"))
    except Exception as e:
        print(f"\nNote: Could not save evaluation report: {e}")
    
    print("\n" + "=" * 60)
    print("All experiments completed!")
    print("=" * 60)


if __name__ == "__main__":
    """Main entry point when running as a module."""
    try:
        run_all_experiments()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("\nPlease ensure:")
        print("1. OSM POI data is in data/city_pois.csv")
        print("2. Gowalla data is in data/Gowalla_totalCheckins.txt")
        print("\nYou can download the data using:")
        print("  python scripts/download_data.py --city 'Your City Name'")
    except Exception as e:
        print(f"Error running experiments: {e}")
        import traceback
        traceback.print_exc()

