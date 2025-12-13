"""
Data loading utilities for Gowalla trajectories and OSM POIs.

数据加载模块：
- Gowalla_totalCheckins.txt: 用户签到轨迹
- OSM POIs: 景点（lat, lon, category, name, opening_hours, tags）
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import pandas as pd

from .config import CONFIG, DataPaths, POIFilterConfig
from .llm_recommender import load_llm_recommended_pois


@dataclass
class POI:
    """Point of Interest representation.
    """

    poi_id: str
    lat: float
    lon: float
    category: str
    rating: float
    duration_min: float
    popularity: float = 0.0
    name: Optional[str] = None
    opening_hours: Optional[str] = None
    tags: Optional[Dict[str, str]] = None


def load_osm_pois(path: Optional[Path] = None) -> pd.DataFrame:
    """Load OSM POIs from a preprocessed CSV.
    
    - poi_id
    - lat, lon
    - category
    - rating
    - duration_min
    - popularity
    - name
    - opening_hours
    - tags (JSON string or semi-structured text)
    """

    if path is None:
        path = CONFIG.data.osm_poi

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"OSM POI file not found: {path}. 请先预处理 OSM 数据并保存为 CSV。"
        )

    df = pd.read_csv(path)
    return df


def load_pois() -> pd.DataFrame:
    """Load POIs from configured source (OSM or LLM).
    
    根据配置决定从OSM CSV文件加载还是通过LLM推荐加载POI。
    
    Returns:
        DataFrame with POI data
    """
    if CONFIG.llm.enabled:
        # Load from LLM recommendation
        if not CONFIG.llm.city:
            raise ValueError(
                "LLM mode is enabled but city is not specified. "
                "Please set CONFIG.llm.city or disable LLM mode."
            )
        
        cache_path = CONFIG.data.llm_poi_cache / f"{CONFIG.llm.city.lower().replace(' ', '_')}.csv"
        
        df = load_llm_recommended_pois(
            city=CONFIG.llm.city,
            num_days=CONFIG.llm.num_days,
            preferences=CONFIG.llm.preferences,
            budget=CONFIG.llm.budget,
            interests=CONFIG.llm.interests,
            num_pois=CONFIG.llm.num_pois,
            cache_path=cache_path,
            use_cache=CONFIG.llm.use_cache,
        )
        return df
    else:
        # Load from OSM CSV (default)
        return load_osm_pois()


def clean_poi_name(name: str, category: str, poi_id: str) -> str:
    """Generate a meaningful name for POI if name is missing or Unknown.
    
    Args:
        name: Original POI name
        category: POI category
        poi_id: POI identifier
    
    Returns:
        Cleaned POI name
    """
    if pd.isna(name) or str(name).strip().lower() in ['unknown', '', 'nan']:
        # Generate name from category
        category_parts = str(category).split(',')
        if category_parts:
            first_cat = category_parts[0].strip()
            # Extract readable category name
            if '=' in first_cat:
                cat_type = first_cat.split('=')[0]
                cat_value = first_cat.split('=')[1]
                # Map to Chinese/English names
                category_map = {
                    'tourism': {'museum': '博物馆', 'gallery': '美术馆', 'attraction': '景点'},
                    'amenity': {'restaurant': '餐厅', 'cafe': '咖啡厅', 'park': '公园'},
                    'leisure': {'park': '公园', 'garden': '花园'},
                    'historic': {'ruins': '遗址', 'tomb': '古墓', 'castle': '古堡'}
                }
                if cat_type in category_map and cat_value in category_map[cat_type]:
                    return f"{category_map[cat_type][cat_value]} ({cat_value})"
                return f"{cat_type} {cat_value}"
        # Fallback: use POI ID
        return f"POI-{poi_id[:8]}"
    return str(name).strip()


def filter_pois(
    pois: pd.DataFrame,
    filter_config: Optional[POIFilterConfig] = None,
) -> pd.DataFrame:
    """Filter POIs based on criteria.
    
    根据配置筛选 POI：
    - 按评分过滤（min_rating）
    - 数据清洗：处理 Unknown 名称
    - 按类别限制（category_limit）
    - 优先选择特定类别（preferred_categories）
    - 限制总数（max_pois）
    
    Args:
        pois: 原始 POI DataFrame
        filter_config: 过滤配置（默认使用 CONFIG.poi_filter）
    
    Returns:
        筛选后的 POI DataFrame
    """
    if filter_config is None:
        filter_config = CONFIG.poi_filter
    
    df = pois.copy()
    
    # 0. 数据清洗：处理 Unknown 名称
    if 'name' in df.columns and 'category' in df.columns:
        df['name'] = df.apply(
            lambda row: clean_poi_name(row.get('name'), row.get('category'), row.get('poi_id', '')),
            axis=1
        )
        
        # 过滤掉 Unknown 名称（如果配置要求）
        if filter_config.filter_unknown_names:
            # Now filter out any that are still "Unknown" after cleaning
            df = df[~df['name'].str.lower().str.contains('unknown', na=False)].copy()
    
    # 1. 按评分过滤
    if 'rating' in df.columns:
        df = df[df['rating'] >= filter_config.min_rating].copy()
    
    # 2. 优先选择特定类别
    if filter_config.preferred_categories:
        # 为每个 POI 添加优先级分数
        df['priority'] = 0
        for pref_cat in filter_config.preferred_categories:
            # 检查 category 是否包含该前缀
            mask = df['category'].str.contains(pref_cat, case=False, na=False)
            df.loc[mask, 'priority'] = 1
        
        # 先按优先级排序，再按评分排序
        df = df.sort_values(['priority', 'rating'], ascending=[False, False])
    else:
        # 只按评分排序
        if 'rating' in df.columns:
            df = df.sort_values('rating', ascending=False)
    
    # 3. 按类别限制数量
    if filter_config.category_limit is not None:
        selected = []
        for category, group in df.groupby('category'):
            group_limit = min(filter_config.category_limit, len(group))
            selected.append(group.head(group_limit))
        
        if selected:
            df = pd.concat(selected, ignore_index=True)
            # 重新排序
            if 'priority' in df.columns:
                df = df.sort_values(['priority', 'rating'], ascending=[False, False])
            elif 'rating' in df.columns:
                df = df.sort_values('rating', ascending=False)
    
    # 4. 限制总数
    if filter_config.max_pois is not None and len(df) > filter_config.max_pois:
        df = df.head(filter_config.max_pois).copy()
    
    # 删除临时列
    if 'priority' in df.columns:
        df = df.drop(columns=['priority'])
    
    return df.reset_index(drop=True)


def load_gowalla_checkins(
    path: Optional[Path] = None,
    city_bbox: Optional[Tuple[float, float, float, float]] = None,
) -> pd.DataFrame:
    """Load Gowalla_totalCheckins.txt into a DataFrame.

    原始 Gowalla_totalCheckins.txt 格式通常为（tab 分隔）:
    user_id  checkin_time  latitude  longitude  location_id
    
    Args:
        path: Path to Gowalla_totalCheckins.txt file
        city_bbox: Optional bounding box (lat_min, lat_max, lon_min, lon_max) to filter by city
    
    Returns:
        DataFrame with columns: user_id, timestamp, lat, lon, location_id
    """

    if path is None:
        path = CONFIG.data.gowalla_checkins

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"Gowalla checkins file not found: {path}. 请将 Gowalla_totalCheckins.txt 放入 data/ 目录。"
        )

    # Load in chunks to handle large file efficiently
    if city_bbox is not None:
        lat_min, lat_max, lon_min, lon_max = city_bbox
        chunks = []
        
        for chunk in pd.read_csv(path, sep="\t", header=None, chunksize=500000):
            if chunk.shape[1] >= 5:
                chunk.columns = ["user_id", "timestamp", "lat", "lon", "location_id"]
            
            # Filter by bounding box
            filtered = chunk[
                (chunk["lat"] >= lat_min) & (chunk["lat"] <= lat_max) &
                (chunk["lon"] >= lon_min) & (chunk["lon"] <= lon_max)
            ]
            
            if len(filtered) > 0:
                chunks.append(filtered)
        
        if chunks:
            df = pd.concat(chunks, ignore_index=True)
        else:
            # Return empty DataFrame with correct columns
            df = pd.DataFrame(columns=["user_id", "timestamp", "lat", "lon", "location_id"])
    else:
        df = pd.read_csv(path, sep="\t", header=None)
        if df.shape[1] >= 5:
            df.columns = ["user_id", "timestamp", "lat", "lon", "location_id"]
    
    return df


def df_to_pois(df: pd.DataFrame) -> List[POI]:
    """Convert a POI DataFrame into a list of POI dataclass instances.

    将 DataFrame 转为 POI 对象列表，便于后续模块复用。
    """

    required_cols = ["poi_id", "lat", "lon", "category", "rating", "duration_min"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Missing required column in POI DataFrame: {col}")

    pois: List[POI] = []
    for _, row in df.iterrows():
        pois.append(
            POI(
                poi_id=str(row["poi_id"]),
                lat=float(row["lat"]),
                lon=float(row["lon"]),
                category=str(row["category"]),
                rating=float(row.get("rating", 0.0)),
                duration_min=float(row.get("duration_min", 60.0)),
                popularity=float(row.get("popularity", 0.0)),
                name=row.get("name"),
                opening_hours=row.get("opening_hours"),
                tags=None,
            )
        )
    return pois


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great circle distance between two points on Earth (in km).
    
    Args:
        lat1, lon1: First point coordinates
        lat2, lon2: Second point coordinates
    
    Returns:
        Distance in kilometers
    """
    from math import radians, sin, cos, sqrt, atan2
    
    R = 6371.0  # Earth radius in kilometers
    
    lat1_rad = radians(lat1)
    lon1_rad = radians(lon1)
    lat2_rad = radians(lat2)
    lon2_rad = radians(lon2)
    
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = sin(dlat / 2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    
    distance = R * c
    return distance


def match_gowalla_to_pois(
    gowalla_df: pd.DataFrame,
    pois_df: pd.DataFrame,
    max_distance_km: float = 0.5,
) -> pd.DataFrame:
    """Match Gowalla check-ins to OSM POIs based on spatial proximity.
    
    为每个 Gowalla location_id 找到最近的 OSM POI。
    
    Args:
        gowalla_df: Gowalla check-ins DataFrame
        pois_df: OSM POIs DataFrame
        max_distance_km: Maximum distance threshold for matching (default 0.5 km)
    
    Returns:
        DataFrame with matched records containing both Gowalla and POI information
    """
    # Get unique Gowalla locations
    unique_locations = gowalla_df[["location_id", "lat", "lon"]].drop_duplicates()
    
    matches = []
    
    for _, loc in unique_locations.iterrows():
        loc_id = loc["location_id"]
        loc_lat = loc["lat"]
        loc_lon = loc["lon"]
        
        # Calculate distance to all POIs
        min_dist = float('inf')
        best_poi_idx = None
        
        for poi_idx, poi in pois_df.iterrows():
            dist = haversine_distance(loc_lat, loc_lon, poi["lat"], poi["lon"])
            if dist < min_dist:
                min_dist = dist
                best_poi_idx = poi_idx
        
        # Only keep matches within threshold
        if best_poi_idx is not None and min_dist <= max_distance_km:
            matches.append({
                "location_id": loc_id,
                "gowalla_lat": loc_lat,
                "gowalla_lon": loc_lon,
                "poi_idx": best_poi_idx,
                "poi_id": pois_df.iloc[best_poi_idx]["poi_id"],
                "poi_name": pois_df.iloc[best_poi_idx].get("name", "Unknown"),
                "distance_km": min_dist,
            })
    
    return pd.DataFrame(matches)


def extract_user_trajectories(
    gowalla_df: pd.DataFrame,
    location_poi_mapping: pd.DataFrame,
    min_checkins: int = 5,
    remove_duplicates: bool = True,
    max_time_gap_hours: Optional[float] = None,
) -> Dict[int, List[int]]:
    """Extract user trajectories as sequences of POI indices.
    
    从 Gowalla 签到数据中提取用户轨迹，转换为 POI 索引序列。
    
    Args:
        gowalla_df: Gowalla check-ins DataFrame
        location_poi_mapping: Mapping from location_id to poi_idx
        min_checkins: Minimum number of check-ins for a user to be included
        remove_duplicates: If True, remove consecutive duplicate POIs
        max_time_gap_hours: If set, split trajectory when time gap exceeds this value
    
    Returns:
        Dictionary mapping user_id to list of POI indices (chronological order)
    """
    # Create location_id -> poi_idx mapping
    loc_to_poi = dict(zip(location_poi_mapping["location_id"], location_poi_mapping["poi_idx"]))
    
    # Filter to only matched locations
    matched_checkins = gowalla_df[gowalla_df["location_id"].isin(loc_to_poi.keys())].copy()
    
    # Convert timestamp to datetime for sorting
    matched_checkins["timestamp"] = pd.to_datetime(matched_checkins["timestamp"])
    
    # Sort by user and time
    matched_checkins = matched_checkins.sort_values(["user_id", "timestamp"])
    
    # Map location_id to poi_idx
    matched_checkins["poi_idx"] = matched_checkins["location_id"].map(loc_to_poi)
    
    # Group by user
    user_trajectories = {}
    for user_id, group in matched_checkins.groupby("user_id"):
        trajectory = group["poi_idx"].tolist()
        
        # Remove consecutive duplicates if requested
        if remove_duplicates and len(trajectory) > 0:
            trajectory = [trajectory[0]] + [trajectory[i] for i in range(1, len(trajectory)) 
                                           if trajectory[i] != trajectory[i-1]]
        
        # Split by time gap if requested
        if max_time_gap_hours is not None and len(trajectory) > 1:
            timestamps = group["timestamp"].tolist()
            sub_trajectories = []
            current_traj = [trajectory[0]]
            
            for i in range(1, len(trajectory)):
                time_gap = (timestamps[i] - timestamps[i-1]).total_seconds() / 3600
                if time_gap <= max_time_gap_hours:
                    current_traj.append(trajectory[i])
                else:
                    if len(current_traj) >= min_checkins:
                        sub_trajectories.append(current_traj)
                    current_traj = [trajectory[i]]
            
            # Add last trajectory
            if len(current_traj) >= min_checkins:
                sub_trajectories.append(current_traj)
            
            # Use the longest sub-trajectory
            if sub_trajectories:
                trajectory = max(sub_trajectories, key=len)
            else:
                trajectory = []
        
        # Only include users with sufficient check-ins
        if len(trajectory) >= min_checkins:
            user_trajectories[int(user_id)] = trajectory
    
    return user_trajectories


