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

    - gowalla_checkins: Gowalla_totalCheckins.txt 原始轨迹文件
    - osm_poi: 预处理后的 OSM POI 列表（CSV/Parquet）
    - llm_poi_cache: LLM推荐的POI缓存目录
    """

    root: Path = Path("data")
    gowalla_checkins: Path = root / "Gowalla_totalCheckins.txt"
    osm_poi: Path = root / "city_pois.csv"
    llm_poi_cache: Path = root / "llm_pois"


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
    max_visit_time_hours: Optional[float] = 6.0  # 每天最大浏览时长（小时），None表示不限制
    min_visit_time_hours: float = 4.0  # 每天最小浏览时长（小时），确保每天至少有足够的游玩时间
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
    max_daily_hours: float = 8.0  # 每天最大游玩时间（小时）
    max_visit_time_hours: float = 7.0  # 每天最大浏览时长（小时），不包括交通时间
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
class LLMConfig:
    """Config for LLM-based POI recommendation.
    
    LLM推荐配置：用于通过大语言模型推荐POI。
    """
    
    enabled: bool = False  # 是否启用LLM推荐模式
    provider: str = "openai"  # LLM提供商: openai, anthropic, google
    model: str = "gpt-4"  # 模型名称
    temperature: float = 0.7  # 生成温度 (0.0-2.0)
    use_cache: bool = True  # 是否使用缓存
    city: Optional[str] = None  # 目标城市名称
    num_days: int = 3  # 旅行天数
    preferences: Optional[str] = None  # 用户偏好描述
    budget: Optional[str] = None  # 预算水平: budget, mid-range, luxury
    interests: Optional[List[str]] = None  # 兴趣列表
    num_pois: Optional[int] = None  # 目标POI数量（None表示自动计算）


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
    llm: LLMConfig = field(default_factory=LLMConfig)


# Default global config instance
CONFIG = ExperimentConfig()


