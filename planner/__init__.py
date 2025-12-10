"""
Core package for the PlanC Travel Planner system.

This package is organized into the following main modules:
- config: global paths and experiment settings
- data_loader: loaders and preprocessors for Gowalla and OSM POIs
- clustering: POI clustering algorithms and clustering-quality metrics
- routing: intra-day routing algorithms (Random, Rating-based, NN, 2-opt)
- evaluation: metrics for routes and real-world behavior alignment
- experiments: high-level experiment runners (Experiments 1–4)
- ablation: utilities for ablation studies
- visualization: visualization utilities for experiment results
"""

__all__ = [
    "config",
    "data_loader",
    "clustering",
    "routing",
    "evaluation",
    "experiments",
    "ablation",
    "visualization",
]


