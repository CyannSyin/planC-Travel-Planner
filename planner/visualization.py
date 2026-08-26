"""Compact visualizations retained for the research evaluation runner."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def _finish(fig, output_path: Path, show_plot: bool):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, bbox_inches="tight")
    if show_plot:
        plt.show()
    else:
        plt.close(fig)
    return fig


def visualize_experiment_1_clustering_map(
    pois: pd.DataFrame,
    cluster_result,
    output_path: Optional[Path] = None,
    figsize: tuple = (10, 8),
    dpi: int = 100,
    show_plot: bool = True,
):
    if pois.empty:
        return None
    labels = np.asarray(cluster_result.labels)
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    scatter = ax.scatter(pois["lon"], pois["lat"], c=labels, cmap="tab10", s=45)
    ax.set(title=f"POI day clusters ({cluster_result.method})", xlabel="Longitude", ylabel="Latitude")
    fig.colorbar(scatter, ax=ax, label="Day cluster")
    return _finish(fig, output_path or Path("results/experiment1_clustering_map.pdf"), show_plot)


def visualize_experiment_1_clustering(
    cluster_results: Dict,
    output_path: Optional[Path] = None,
    figsize: tuple = (10, 6),
    dpi: int = 100,
    show_plot: bool = True,
):
    rows = [
        {
            "method": method,
            "silhouette": result.silhouette or 0.0,
            "sci": result.sci or 0.0,
        }
        for method, result in cluster_results.items()
    ]
    if not rows:
        return None
    frame = pd.DataFrame(rows).set_index("method")
    fig, axes = plt.subplots(1, 2, figsize=figsize, dpi=dpi)
    frame["silhouette"].plot.bar(ax=axes[0], title="Silhouette", color="#4C78A8")
    frame["sci"].plot.bar(ax=axes[1], title="SCI", color="#F58518")
    return _finish(fig, output_path or Path("results/experiment1_clustering.pdf"), show_plot)


def visualize_experiment_2_routes_map(
    day_pois: Dict[int, pd.DataFrame],
    routes: Dict[int, list],
    output_path: Optional[Path] = None,
    figsize: tuple = (10, 8),
    dpi: int = 100,
    show_plot: bool = True,
):
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    colors = plt.cm.tab10(np.linspace(0, 1, max(1, len(routes))))
    for color, day in zip(colors, sorted(routes)):
        ordered = day_pois[day].reset_index(drop=True).iloc[routes[day]]
        ax.plot(ordered["lon"], ordered["lat"], marker="o", color=color, label=f"Day {day}")
    ax.set(title="Daily routes", xlabel="Longitude", ylabel="Latitude")
    ax.legend()
    return _finish(fig, output_path or Path("results/experiment2_routes_map.pdf"), show_plot)


def visualize_experiment_2_routes(
    route_metrics: Dict[int, Dict],
    day_pois: Optional[Dict[int, pd.DataFrame]] = None,
    output_path: Optional[Path] = None,
    figsize: tuple = (10, 6),
    dpi: int = 100,
    show_plot: bool = True,
):
    frame = pd.DataFrame.from_dict(route_metrics, orient="index").sort_index()
    if frame.empty:
        return None
    fig, axes = plt.subplots(1, 2, figsize=figsize, dpi=dpi)
    frame["length_km"].plot.bar(ax=axes[0], title="Route length (km)", color="#4C78A8")
    frame["time_efficiency"].plot.bar(ax=axes[1], title="Time efficiency", color="#54A24B")
    return _finish(fig, output_path or Path("results/experiment2_routes.pdf"), show_plot)


def visualize_experiment_5_popularity_alignment(
    popularity_metrics: Dict,
    planned_popularity,
    real_popularity,
    output_path: Optional[Path] = None,
    figsize: tuple = (9, 5),
    dpi: int = 100,
    show_plot: bool = True,
):
    labels = ["Top-K overlap", "Spearman", "Coverage@K"]
    values = [
        popularity_metrics.get("top_k_overlap", 0.0),
        popularity_metrics.get("spearman_correlation", 0.0),
        popularity_metrics.get("coverage_at_k", 0.0),
    ]
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    ax.bar(labels, values, color=["#4C78A8", "#F58518", "#54A24B"])
    ax.set(title="POI popularity alignment", ylabel="Score", ylim=(-1, 1))
    return _finish(fig, output_path or Path("results/experiment5_popularity.pdf"), show_plot)
