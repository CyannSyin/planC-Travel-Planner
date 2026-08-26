"""
Experiment 1 — POI Clustering.

实现聚类方法：
- K-means
- DBSCAN
- HAC（层次聚类）
- Spectral Clustering

评估指标：
- silhouette score
- Davies–Bouldin index
- Calinski–Harabasz index
- SCI（简单结构紧凑度指数，自定义）
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from .config import CONFIG


def _haversine_distance_matrix(lat_lon: np.ndarray) -> np.ndarray:
    """Compute pairwise haversine distance matrix (in km) for (lat, lon) array."""

    lat = np.radians(lat_lon[:, 0])[:, None]
    lon = np.radians(lat_lon[:, 1])[:, None]
    dlat = lat - lat.T
    dlon = lon - lon.T

    a = (
        np.sin(dlat / 2.0) ** 2
        + np.cos(lat) * np.cos(lat.T) * np.sin(dlon / 2.0) ** 2
    )
    c = 2 * np.arcsin(np.sqrt(a))
    R = 6371.0
    return R * c


def _build_feature_matrix(pois: pd.DataFrame) -> np.ndarray:
    """Construct feature matrix from POI DataFrame.

    简单特征组合：
    - 归一化后的 lat, lon
    - rating
    - duration_min
    - popularity
    """

    required_cols = ["lat", "lon", "rating", "duration_min", "popularity"]
    for col in required_cols:
        if col not in pois.columns:
            raise ValueError(f"Missing required column for clustering: {col}")

    features = pois[required_cols].astype(float).to_numpy()
    # 简单标准化
    mean = features.mean(axis=0)
    std = features.std(axis=0) + 1e-8
    return (features - mean) / std


def geographic_kmeans_labels(pois: pd.DataFrame, n_days: int) -> np.ndarray:
    """Cluster POIs into travel days using local geographic coordinates.

    The research pipeline mixes geography, rating, duration, and popularity in
    one feature vector. For a user-facing itinerary, geographic compactness is
    the primary concern, so this projection keeps distances in approximately
    kilometers before applying KMeans.
    """

    if not {"lat", "lon"}.issubset(pois.columns):
        raise ValueError("POIs must contain lat and lon columns")
    if n_days < 1:
        raise ValueError("n_days must be at least 1")
    if len(pois) < n_days:
        raise ValueError("The number of POIs must be at least the number of days")
    if n_days == 1:
        return np.zeros(len(pois), dtype=int)

    lat = np.radians(pois["lat"].astype(float).to_numpy())
    lon = np.radians(pois["lon"].astype(float).to_numpy())
    mean_lat = float(lat.mean())
    earth_radius_km = 6371.0
    coordinates_km = np.column_stack(
        (
            earth_radius_km * lon * np.cos(mean_lat),
            earth_radius_km * lat,
        )
    )
    rng = np.random.default_rng(42)
    best_labels = None
    best_inertia = np.inf

    # Deterministic multi-start KMeans++ implemented with NumPy keeps the
    # product path independent from the heavier research-only sklearn stack.
    for _ in range(20):
        centers = [coordinates_km[int(rng.integers(len(coordinates_km)))]]
        while len(centers) < n_days:
            distances_sq = np.min(
                np.sum((coordinates_km[:, None, :] - np.asarray(centers)[None, :, :]) ** 2, axis=2),
                axis=1,
            )
            total = float(distances_sq.sum())
            if total <= 0:
                remaining = [
                    index
                    for index, point in enumerate(coordinates_km)
                    if not any(np.array_equal(point, center) for center in centers)
                ]
                fallback_index = remaining[0] if remaining else len(centers) % len(coordinates_km)
                centers.append(coordinates_km[fallback_index])
            else:
                centers.append(coordinates_km[int(rng.choice(len(coordinates_km), p=distances_sq / total))])
        centers_array = np.asarray(centers, dtype=float)

        for _ in range(100):
            distances_sq = np.sum(
                (coordinates_km[:, None, :] - centers_array[None, :, :]) ** 2,
                axis=2,
            )
            labels = np.argmin(distances_sq, axis=1)
            new_centers = centers_array.copy()
            for cluster_id in range(n_days):
                members = coordinates_km[labels == cluster_id]
                if len(members):
                    new_centers[cluster_id] = members.mean(axis=0)
                else:
                    farthest = int(np.argmax(np.min(distances_sq, axis=1)))
                    new_centers[cluster_id] = coordinates_km[farthest]
            if np.allclose(new_centers, centers_array, rtol=0, atol=1e-8):
                centers_array = new_centers
                break
            centers_array = new_centers

        final_distances_sq = np.sum(
            (coordinates_km[:, None, :] - centers_array[None, :, :]) ** 2,
            axis=2,
        )
        labels = np.argmin(final_distances_sq, axis=1)
        inertia = float(np.sum(final_distances_sq[np.arange(len(labels)), labels]))
        if inertia < best_inertia:
            best_inertia = inertia
            best_labels = labels.copy()

    if best_labels is None:
        raise RuntimeError("KMeans failed to produce labels")

    # Coincident coordinates can collapse multiple centers. Keep the API
    # contract of exactly one non-empty cluster per requested day by splitting
    # the largest clusters deterministically when needed.
    missing_clusters = sorted(set(range(n_days)) - set(best_labels.tolist()))
    for missing_cluster in missing_clusters:
        cluster_sizes = np.bincount(best_labels, minlength=n_days)
        donor = int(np.argmax(cluster_sizes))
        donor_indices = np.flatnonzero(best_labels == donor)
        if len(donor_indices) <= 1:
            raise RuntimeError("Unable to create a non-empty cluster for every day")
        donor_center = coordinates_km[donor_indices].mean(axis=0)
        farthest_offset = int(
            np.argmax(np.sum((coordinates_km[donor_indices] - donor_center) ** 2, axis=1))
        )
        best_labels[donor_indices[farthest_offset]] = missing_cluster

    return best_labels


def sci_index(X: np.ndarray, labels: np.ndarray) -> float:
    """Compute a simple Structural Compactness Index (SCI).

    定义（示例版）：
    SCI = inter_cluster_dist / (intra_cluster_dist + 1e-8)
    - intra_cluster_dist: 簇内平均距离
    - inter_cluster_dist: 簇中心之间的平均距离
    """

    unique_labels = np.unique(labels)
    unique_labels = unique_labels[unique_labels >= 0]
    if len(unique_labels) <= 1:
        return 0.0

    centroids = []
    intra_dists = []
    for lbl in unique_labels:
        cluster_pts = X[labels == lbl]
        if len(cluster_pts) == 0:
            continue
        centroid = cluster_pts.mean(axis=0)
        centroids.append(centroid)
        intra = np.linalg.norm(cluster_pts - centroid, axis=1).mean()
        intra_dists.append(intra)

    if len(centroids) <= 1:
        return 0.0

    centroids = np.stack(centroids, axis=0)
    # pairwise distances between centroids
    diff = centroids[:, None, :] - centroids[None, :, :]
    dists = np.linalg.norm(diff, axis=-1)
    inter = dists[np.triu_indices_from(dists, k=1)].mean()

    intra_mean = float(np.mean(intra_dists)) if intra_dists else 0.0
    return float(inter / (intra_mean + 1e-8))


@dataclass
class ClusteringResult:
    labels: np.ndarray
    n_clusters: int
    method: str
    silhouette: Optional[float]
    davies_bouldin: Optional[float]
    calinski_harabasz: Optional[float]
    sci: Optional[float]


def evaluate_clustering(X: np.ndarray, labels: np.ndarray, method: str) -> ClusteringResult:
    """Compute clustering metrics for given labels."""

    from sklearn.metrics import (
        calinski_harabasz_score,
        davies_bouldin_score,
        silhouette_score,
    )

    # Ignore noise label -1 from DBSCAN for n_clusters
    valid_labels = labels[labels >= 0]
    unique = np.unique(valid_labels)
    n_clusters = len(unique)
    if n_clusters <= 1:
        return ClusteringResult(
            labels=labels,
            n_clusters=n_clusters,
            method=method,
            silhouette=None,
            davies_bouldin=None,
            calinski_harabasz=None,
            sci=None,
        )

    mask = labels >= 0
    X_valid = X[mask]
    labels_valid = labels[mask]

    silhouette = float(silhouette_score(X_valid, labels_valid))
    davies = float(davies_bouldin_score(X_valid, labels_valid))
    ch = float(calinski_harabasz_score(X_valid, labels_valid))
    sci_val = sci_index(X_valid, labels_valid)

    return ClusteringResult(
        labels=labels,
        n_clusters=n_clusters,
        method=method,
        silhouette=silhouette,
        davies_bouldin=davies,
        calinski_harabasz=ch,
        sci=sci_val,
    )


def run_kmeans(pois: pd.DataFrame, k: int) -> ClusteringResult:
    from sklearn.cluster import KMeans

    X = _build_feature_matrix(pois)
    model = KMeans(n_clusters=k, n_init=10, random_state=42)
    labels = model.fit_predict(X)
    return evaluate_clustering(X, labels, method="kmeans")


def run_hac(pois: pd.DataFrame, k: int) -> ClusteringResult:
    from sklearn.cluster import AgglomerativeClustering

    X = _build_feature_matrix(pois)
    model = AgglomerativeClustering(n_clusters=k)
    labels = model.fit_predict(X)
    return evaluate_clustering(X, labels, method="hac")


def run_spectral(pois: pd.DataFrame, k: int) -> ClusteringResult:
    from sklearn.cluster import SpectralClustering

    X = _build_feature_matrix(pois)
    n_samples = X.shape[0]
    # Adjust n_neighbors to be at most n_samples - 1 (each point needs at least 1 neighbor)
    n_neighbors = min(10, max(1, n_samples - 1))
    model = SpectralClustering(
        n_clusters=k,
        affinity="nearest_neighbors",
        n_neighbors=n_neighbors,
        random_state=42,
    )
    labels = model.fit_predict(X)
    return evaluate_clustering(X, labels, method="spectral")


def run_dbscan(pois: pd.DataFrame, eps_km: float = 1.0, min_samples: int = 5) -> ClusteringResult:
    """Run DBSCAN using geographic distance (Haversine)."""

    from sklearn.cluster import DBSCAN

    lat_lon = pois[["lat", "lon"]].astype(float).to_numpy()
    dist_mat = _haversine_distance_matrix(lat_lon)
    # Convert eps in km to distance in matrix directly
    model = DBSCAN(eps=eps_km, min_samples=min_samples, metric="precomputed")
    labels = model.fit_predict(dist_mat)
    # For DBSCAN, metrics computed on lat/lon only
    X = lat_lon
    return evaluate_clustering(X, labels, method="dbscan")


def select_best_clustering(
    pois: pd.DataFrame,
    max_days: Optional[int] = None,
    fixed_days: Optional[int] = None,
) -> Dict[str, ClusteringResult]:
    """Run multiple clustering methods and select best clustering per method.

    返回：
    - 每种方法对应的最佳结果（按 silhouette 优先，其次 SCI）。

    对于使用 k 的方法（KMeans/HAC/Spectral）：
    - 如果 fixed_days 已设置，直接使用该天数
    - 否则在 k=2..max_days 之间搜索最佳值
    """

    if max_days is None:
        max_days = CONFIG.clustering.max_days
    
    # 如果配置中指定了固定天数，优先使用配置值
    if fixed_days is None:
        fixed_days = CONFIG.clustering.fixed_days

    results: Dict[str, ClusteringResult] = {}
    methods = CONFIG.clustering.methods

    for method in methods:
        best: Optional[ClusteringResult] = None
        if method in {"kmeans", "hac", "spectral"}:
            if fixed_days is not None:
                # 固定天数模式：直接使用指定天数
                k = fixed_days
                if method == "kmeans":
                    res = run_kmeans(pois, k)
                elif method == "hac":
                    res = run_hac(pois, k)
                else:
                    res = run_spectral(pois, k)
                
                if res.silhouette is not None:
                    best = res
            else:
                # 自动搜索模式：在 k=2..max_days 之间搜索最佳值
                for k in range(2, max_days + 1):
                    if method == "kmeans":
                        res = run_kmeans(pois, k)
                    elif method == "hac":
                        res = run_hac(pois, k)
                    else:
                        res = run_spectral(pois, k)

                    if res.silhouette is None:
                        continue
                    if best is None:
                        best = res
                    else:
                        # 优先更高 silhouette，其次更高 SCI
                        if res.silhouette > (best.silhouette or -1):
                            best = res
                        elif res.silhouette == best.silhouette and (res.sci or 0) > (best.sci or 0):
                            best = res
        elif method == "dbscan":
            # DBSCAN 不支持固定天数，始终使用搜索模式
            # 粗略扫描 eps
            for eps in [0.5, 1.0, 2.0, 3.0]:
                res = run_dbscan(pois, eps_km=eps)
                if res.silhouette is None:
                    continue
                if best is None or res.silhouette > (best.silhouette or -1):
                    best = res

        if best is not None:
            results[method] = best

    return results
