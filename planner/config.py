"""
Global configuration for the PlanC Travel Planner system.

全局配置：数据路径、默认参数等。
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class DataPaths:
    """Paths related to raw and processed data.

    数据路径配置（请根据本地环境修改为真实路径）:
    - gowalla_checkins: Gowalla_totalCheckins.txt 原始轨迹文件
    - osm_poi: 预处理后的 OSM POI 列表（CSV/Parquet）
    """

    root: Path = Path("data")
    gowalla_checkins: Path = root / "Gowalla_totalCheckins.txt"
    osm_poi: Path = root / "city_pois.csv"


@dataclass
class POIFilterConfig:
    """Config for filtering POIs before experiments.
    
    POI 过滤配置：用于筛选感兴趣的 POI。
    """
    
    min_rating: float = 4.0  # 最低评分
    max_pois: Optional[int] = 10  # 最多选择多少个 POI（None 表示不限制）
    category_limit: Optional[int] = 5  # 每个类别最多选择多少个 POI（None 表示不限制）
    preferred_categories: List[str] = field(default_factory=lambda: [
        "tourism=attraction",
        "tourism=museum", 
        "tourism=gallery",
        "historic",
        "leisure=park",
    ])  # 优先选择的类别前缀
    max_visit_time_hours: Optional[float] = 8.0  # 每天最大浏览时长（小时），None表示不限制
    filter_unknown_names: bool = True  # 是否过滤掉名称为Unknown的POI


@dataclass
class ClusteringConfig:
    """Config for Experiment 1 — POI clustering.

    聚类实验配置。
    """

    methods: List[str] = field(default_factory=lambda: ["kmeans", "dbscan", "hac", "spectral"])
    max_days: int = 7  # 最大天数（最大聚类数）


@dataclass
class RoutingConfig:
    """Config for Experiment 2 — daily route optimization.

    路径优化实验配置。
    """

    methods: List[str] = field(default_factory=lambda: ["random", "rating", "nn", "two_opt"])
    max_daily_hours: float = 10.0  # 每天最大游玩时间（小时）
    max_visit_time_hours: float = 5.0  # 每天最大浏览时长（小时），不包括交通时间
    start_time: str = "09:00"
    end_time: str = "19:00"


@dataclass
class AlignmentConfig:
    """Config for Experiment 3 — behavior alignment."""

    # 最大采样的 Gowalla 轨迹数，避免过大内存
    max_trajectories: int = 5000


@dataclass
class AblationConfig:
    """Config for Experiment 4 — ablation."""

    consider_category: bool = True
    consider_popularity: bool = True
    enable_two_opt: bool = True


@dataclass
class ExperimentConfig:
    """Top-level configuration wrapper.

    顶层实验配置封装。
    """

    data: DataPaths = field(default_factory=DataPaths)
    poi_filter: POIFilterConfig = field(default_factory=POIFilterConfig)
    clustering: ClusteringConfig = field(default_factory=ClusteringConfig)
    routing: RoutingConfig = field(default_factory=RoutingConfig)
    alignment: AlignmentConfig = field(default_factory=AlignmentConfig)
    ablation: AblationConfig = field(default_factory=AblationConfig)


# Default global config instance
CONFIG = ExperimentConfig()


