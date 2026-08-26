"""
High-level experiment runners.

整体实验控制：
- Experiment 1: POI Clustering → 推断出天数（clusters）
- Experiment 2: Daily Route Optimization
- Experiment 3: Real-world Behavior Alignment（基于 Gowalla）- 路线级对齐
- Experiment 5: POI Popularity Alignment（基于 Gowalla）- POI 热度对齐
"""

from __future__ import annotations

import re
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from .config import CONFIG, CITY_BBOXES
from .data_loader import (
    load_gowalla_checkins,
    load_osm_pois,
    load_pois,
    filter_pois,
    match_gowalla_to_pois,
    extract_user_trajectories,
)
from .clustering import ClusteringResult, select_best_clustering
from .routing import build_route
from .evaluation import evaluate_route, evaluate_alignment, evaluate_poi_popularity_alignment
from .results_evaluation import evaluate_experiment_results, print_evaluation_summary, save_evaluation_report
from .visualization import (
    visualize_experiment_1_clustering,
    visualize_experiment_1_clustering_map,
    visualize_experiment_2_routes,
    visualize_experiment_2_routes_map,
    visualize_experiment_5_popularity_alignment,
)


def experiment_1_poi_clustering(pois: pd.DataFrame) -> Dict[str, ClusteringResult]:
    """Experiment 1 — run clustering and select best clustering for each method.
    
    当LLM模式启用时，自动使用CONFIG.llm.num_days作为固定天数。
    """

    # 如果LLM模式启用，使用LLM配置的天数作为固定天数
    fixed_days = None
    if CONFIG.llm.enabled and CONFIG.llm.num_days:
        fixed_days = CONFIG.llm.num_days
    
    results = select_best_clustering(
        pois, 
        max_days=CONFIG.clustering.max_days,
        fixed_days=fixed_days
    )
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
    # Keep the original filtered-POI position so real Gowalla trajectories and
    # planned routes use the same identifier space during alignment.
    pois["_source_index"] = list(range(len(pois)))
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


def experiment_5_poi_popularity_alignment(
    planned_routes: Dict[int, List[int]],
    day_pois: Dict[int, pd.DataFrame],
    real_trajectories: List[List[int]],
    pois: pd.DataFrame,
    k: int = 10,
):
    """Experiment 5 — POI popularity alignment between planned routes and real-world behavior.
    
    与 Experiment 3 不同，这个实验关注 POI 热度对齐而非路线级对齐。
    
    Args:
        planned_routes: Dict mapping day to list of POI indices (visit order)
        day_pois: Dict mapping day to POI DataFrame
        real_trajectories: List of real user trajectories (each is a list of POI indices)
        pois: Full POI DataFrame with all POIs
        k: Number of top POIs to consider for Top-K metrics
    
    Returns:
        Dict with popularity alignment metrics
    """
    from collections import Counter
    
    # Calculate planned POI popularity (visit frequency across all planned routes)
    planned_poi_counts = Counter()
    for day, route in planned_routes.items():
        day_df = day_pois[day]
        for pos_idx in route:
            # Get the actual POI ID from the day's DataFrame
            poi_row = day_df.iloc[pos_idx]
            poi_id = poi_row.name if 'poi_id' not in poi_row else poi_row['poi_id']
            planned_poi_counts[poi_id] += 1
    
    # Sort by popularity (descending)
    planned_popularity = sorted(
        [(poi_id, count) for poi_id, count in planned_poi_counts.items()],
        key=lambda x: x[1],
        reverse=True
    )
    
    # Calculate real POI popularity (visit frequency in real trajectories)
    real_poi_counts = Counter()
    for traj in real_trajectories:
        for poi_idx in traj:
            # POI index in real trajectories should correspond to POI ID in the full dataset
            if poi_idx < len(pois):
                poi_id = pois.iloc[poi_idx].name if 'poi_id' not in pois.iloc[poi_idx] else pois.iloc[poi_idx]['poi_id']
                real_poi_counts[poi_id] += 1
    
    # Sort by popularity (descending)
    real_popularity = sorted(
        [(poi_id, count) for poi_id, count in real_poi_counts.items()],
        key=lambda x: x[1],
        reverse=True
    )
    
    # Evaluate popularity alignment
    metrics = evaluate_poi_popularity_alignment(
        planned_popularity=planned_popularity,
        real_popularity=real_popularity,
        k=k,
    )
    
    return {
        'top_k_overlap': metrics.top_k_overlap,
        'spearman_correlation': metrics.spearman_correlation,
        'coverage_at_k': metrics.coverage_at_k,
        'k': k,
        'planned_unique_pois': len(planned_popularity),
        'real_unique_pois': len(real_popularity),
    }


def get_real_gowalla_trajectories(
    pois: pd.DataFrame,
    city: str = "beijing",
    max_trajectories: Optional[int] = None,
) -> List[List[int]]:
    """Get real Gowalla user trajectories matched to POIs.
    
    从 Gowalla 数据中提取真实用户轨迹，并匹配到 OSM POI。
    
    Args:
        pois: POI DataFrame
        city: City name (beijing, shanghai, chengdu)
        max_trajectories: Maximum number of trajectories to return
    
    Returns:
        List of trajectories, where each trajectory is a list of POI indices
    """
    city_lower = city.lower()
    
    if city_lower not in CITY_BBOXES:
        print(f"Warning: City '{city}' not in CITY_BBOXES, using synthetic data")
        return []
    
    try:
        # Load Gowalla data for the city
        bbox = CITY_BBOXES[city_lower]
        print(f"  Loading Gowalla data for {city} (bbox: {bbox})...")
        gowalla_df = load_gowalla_checkins(city_bbox=bbox)
        
        if len(gowalla_df) == 0:
            print(f"  No Gowalla check-ins found in {city} area")
            return []
        
        print(f"  Found {len(gowalla_df):,} check-ins in {city}")
        
        # Match Gowalla locations to POIs
        print(f"  Matching Gowalla locations to {len(pois)} POIs...")
        matching = match_gowalla_to_pois(
            gowalla_df,
            pois,
            max_distance_km=CONFIG.alignment.max_matching_distance_km,
        )
        
        if len(matching) == 0:
            print(f"  No Gowalla locations matched to POIs (try increasing max_distance_km)")
            return []
        
        print(f"  Matched {len(matching)} unique locations to POIs")
        
        # Extract user trajectories
        print(f"  Extracting user trajectories...")
        user_trajectories = extract_user_trajectories(
            gowalla_df,
            matching,
            min_checkins=CONFIG.alignment.min_checkins_per_user,
        )
        
        if len(user_trajectories) == 0:
            print(f"  No valid user trajectories found")
            return []
        
        print(f"  Extracted {len(user_trajectories)} user trajectories")
        
        # Convert to list and limit if needed
        trajectories = list(user_trajectories.values())
        
        if max_trajectories is not None and len(trajectories) > max_trajectories:
            trajectories = trajectories[:max_trajectories]
            print(f"  Limited to {max_trajectories} trajectories")
        
        return trajectories
        
    except Exception as e:
        print(f"  Error loading Gowalla data: {e}")
        return []


def run_all_experiments():
    """Convenience function to run all experiments end-to-end.

    注意：这里假设你已经准备好 OSM POI CSV 和 Gowalla 数据，
    并在 config 中配置好路径。
    """

    # Load POIs from configured source (OSM or LLM)
    if CONFIG.llm.enabled:
        print("=== LLM POI Recommendation ===")
        print(f"City: {CONFIG.llm.city}")
        print(f"Number of days: {CONFIG.llm.num_days}")
        if CONFIG.llm.preferences:
            print(f"Preferences: {CONFIG.llm.preferences}")
        if CONFIG.llm.interests:
            print(f"Interests: {', '.join(CONFIG.llm.interests)}")
        pois_raw = load_pois()
    else:
        print("=== Loading OSM POIs ===")
        pois_raw = load_osm_pois()
    
    # Gowalla is optional. Only check its presence here; the city-filtered
    # loader runs later and avoids loading the full multi-million-row file.
    print("\n=== Loading Gowalla Data (Optional) ===")
    gowalla_path = Path(CONFIG.data.gowalla_checkins)
    if not gowalla_path.exists():
        print("  ℹ️  Gowalla data not found - Experiment 3 will use synthetic data")
        print("  (To use real Gowalla data, place Gowalla_totalCheckins.txt in data/ directory)")
        gowalla_available = False
    else:
        print(f"  ✓ Gowalla data found: {gowalla_path}")
        gowalla_available = True

    print("\n=== POI Filtering ===")
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
    
    # 如果LLM模式启用，显示使用的固定天数
    if CONFIG.llm.enabled and CONFIG.llm.num_days:
        print(f"Using fixed number of days from LLM config: {CONFIG.llm.num_days}")
    
    cluster_results = experiment_1_poi_clustering(pois)
    for method, res in cluster_results.items():
        silhouette_str = f"{res.silhouette:.3f}" if res.silhouette is not None else "NA"
        print(f"{method}: n_clusters={res.n_clusters}, silhouette={silhouette_str}")
    
    # Visualize Experiment 1 results
    print("\n=== Generating Experiment 1 Visualizations ===")
    try:
        visualize_experiment_1_clustering(
            cluster_results=cluster_results,
            output_path=Path("results/experiment1_clustering.pdf"),
            show_plot=False,
        )
        print("✓ Experiment 1 clustering metrics visualization generated successfully")
    except Exception as e:
        print(f"Note: Could not generate Experiment 1 metrics visualizations: {e}")
        print("  (This is optional - install matplotlib for visualization)")

    # 选一个方法（比如 KMeans）作为最终分天方案
    if "kmeans" not in cluster_results:
        print("KMeans result not found, fallback to first method.")
        best_method = next(iter(cluster_results.keys()))
    else:
        best_method = "kmeans"
    labels = cluster_results[best_method].labels
    # if "DBSCAN" not in cluster_results:
    #     print("DBSCAN result not found, fallback to first method.")
    #     best_method = next(iter(cluster_results.keys()))
    # else:
    #     best_method = "DBSCAN"
    # labels = cluster_results[best_method].labels
    
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
    
    # Visualize Experiment 1 clustering map
    try:
        visualize_experiment_1_clustering_map(
            pois=pois,
            cluster_result=cluster_results[best_method],
            output_path=Path("results/experiment1_clustering_map.pdf"),
            show_plot=False,
        )
        print("✓ Experiment 1 clustering map visualization generated successfully")
    except Exception as e:
        print(f"Note: Could not generate Experiment 1 clustering map: {e}")
        print("  (This is optional - install matplotlib for visualization)")

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
    
    # Visualize Experiment 2 results
    print("\n=== Generating Experiment 2 Visualizations ===")
    try:
        visualize_experiment_2_routes(
            route_metrics=route_metrics,
            day_pois=day_pois,
            output_path=Path("results/experiment2_routes.pdf"),
            show_plot=False,
        )
        print("✓ Experiment 2 routes metrics visualization generated successfully")
    except Exception as e:
        print(f"Note: Could not generate Experiment 2 metrics visualizations: {e}")
        print("  (This is optional - install matplotlib for visualization)")
    
    # Visualize Experiment 2 routes map
    try:
        visualize_experiment_2_routes_map(
            day_pois=day_pois,
            routes=routes,
            output_path=Path("results/experiment2_routes_map.pdf"),
            show_plot=False,
        )
        print("✓ Experiment 2 routes map visualization generated successfully")
    except Exception as e:
        print(f"Note: Could not generate Experiment 2 routes map: {e}")
        print("  (This is optional - install matplotlib for visualization)")

    print("\n=== Experiment 3: Real-world Behavior Alignment ===")
    
    # Get city name from config
    city = CONFIG.llm.city if CONFIG.llm.enabled and CONFIG.llm.city else "beijing"
    
    # Initialize align_metrics
    align_metrics = None
    
    if gowalla_available:
        print(f"Loading real Gowalla trajectories for {city}...")
        real_trajectories = get_real_gowalla_trajectories(
            pois=pois,
            city=city,
            max_trajectories=CONFIG.alignment.max_trajectories,
        )
        
        if len(real_trajectories) > 0:
            print(f"\n✓ Successfully loaded {len(real_trajectories)} real user trajectories")
            
            # Compare planned routes with real trajectories
            sample_day = next(iter(routes.keys()))
            planned_route = [
                int(day_pois[sample_day].iloc[position]["_source_index"])
                for position in routes[sample_day]
            ]
            
            # Calculate alignment metrics for multiple real trajectories
            all_metrics = []
            for i, real_traj in enumerate(real_trajectories[:10]):  # Compare with first 10
                metrics = experiment_3_behavior_alignment(planned_route, real_traj)
                all_metrics.append(metrics)
            
            # Average metrics
            if all_metrics:
                align_metrics = {
                    key: sum(m[key] for m in all_metrics) / len(all_metrics)
                    for key in all_metrics[0].keys()
                }
                print("\nAverage alignment metrics (comparing with 10 real trajectories):")
                for key, value in align_metrics.items():
                    print(f"  {key}: {value:.4f}")
            
            # Show example comparison
            print(f"\nExample comparison:")
            print(f"  Planned route (Day {sample_day}): {len(planned_route)} POIs")
            print(f"  Real trajectory example: {len(real_trajectories[0])} POIs")
            print(f"  First alignment metrics: {all_metrics[0]}")
        else:
            print("  ⚠️  No real Gowalla trajectories found, using synthetic data for demonstration")
            sample_day = next(iter(routes.keys()))
            planned_route = [
                int(day_pois[sample_day].iloc[position]["_source_index"])
                for position in routes[sample_day]
            ]
            real_traj = planned_route[::-1]  # Fallback: reversed route
            align_metrics = experiment_3_behavior_alignment(planned_route, real_traj)
            print("Alignment metrics (synthetic):", align_metrics)
    else:
        print("  ℹ️  Gowalla data not available, using synthetic trajectory")
        sample_day = next(iter(routes.keys()))
        planned_route = [
            int(day_pois[sample_day].iloc[position]["_source_index"])
            for position in routes[sample_day]
        ]
        real_traj = planned_route[::-1]  # Fallback: reversed route
        align_metrics = experiment_3_behavior_alignment(planned_route, real_traj)
        print("Alignment metrics (synthetic):", align_metrics)

    print("\n=== Experiment 5: POI Popularity Alignment ===")
    print("Comparing POI popularity between planned routes and real-world behavior")
    
    # Initialize popularity_metrics
    popularity_metrics = None
    
    if gowalla_available:
        print(f"Using real Gowalla trajectories for {city}...")
        
        # Reuse real trajectories from Experiment 3
        if 'real_trajectories' not in locals():
            real_trajectories = get_real_gowalla_trajectories(
                pois=pois,
                city=city,
                max_trajectories=CONFIG.alignment.max_trajectories,
            )
        
        if len(real_trajectories) > 0:
            print(f"✓ Analyzing POI popularity across {len(real_trajectories)} real trajectories")
            
            # Run popularity alignment experiment
            popularity_metrics = experiment_5_poi_popularity_alignment(
                planned_routes=routes,
                day_pois=day_pois,
                real_trajectories=real_trajectories,
                pois=pois,
                k=10,  # Top-10 POIs
            )
            
            print(f"\nPOI Popularity Alignment Metrics (Top-{popularity_metrics['k']}):")
            print(f"  Top-K POI Overlap: {popularity_metrics['top_k_overlap']:.4f}")
            print(f"  Spearman Rank Correlation: {popularity_metrics['spearman_correlation']:.4f}")
            print(f"  Coverage@K: {popularity_metrics['coverage_at_k']:.4f}")
            print(f"  Planned unique POIs: {popularity_metrics['planned_unique_pois']}")
            print(f"  Real unique POIs: {popularity_metrics['real_unique_pois']}")
        else:
            print("  ⚠️  No real Gowalla trajectories found, skipping popularity alignment")
    else:
        print("  ℹ️  Gowalla data not available, skipping popularity alignment")
    
    # Visualize Experiment 5 results (if data available)
    if popularity_metrics and gowalla_available and len(real_trajectories) > 0:
        print("\n=== Generating Experiment 5 Visualizations ===")
        try:
            from collections import Counter
            
            # Calculate planned POI popularity
            planned_poi_counts = Counter()
            for day, route in routes.items():
                day_df = day_pois[day]
                for pos_idx in route:
                    poi_row = day_df.iloc[pos_idx]
                    poi_id = poi_row.name if 'poi_id' not in poi_row else poi_row['poi_id']
                    planned_poi_counts[poi_id] += 1
            
            planned_popularity_data = sorted(
                [(poi_id, count) for poi_id, count in planned_poi_counts.items()],
                key=lambda x: x[1],
                reverse=True
            )
            
            # Calculate real POI popularity
            real_poi_counts = Counter()
            for traj in real_trajectories:
                for poi_idx in traj:
                    if poi_idx < len(pois):
                        poi_id = pois.iloc[poi_idx].name if 'poi_id' not in pois.iloc[poi_idx] else pois.iloc[poi_idx]['poi_id']
                        real_poi_counts[poi_id] += 1
            
            real_popularity_data = sorted(
                [(poi_id, count) for poi_id, count in real_poi_counts.items()],
                key=lambda x: x[1],
                reverse=True
            )
            
            visualize_experiment_5_popularity_alignment(
                popularity_metrics=popularity_metrics,
                planned_popularity=planned_popularity_data,
                real_popularity=real_popularity_data,
                output_path=Path("results/experiment5_popularity.pdf"),
                show_plot=False,
            )
            print("✓ Experiment 5 popularity alignment visualization generated successfully")
        except Exception as e:
            print(f"Note: Could not generate Experiment 5 visualizations: {e}")
            print("  (This is optional - install matplotlib for visualization)")
    
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
