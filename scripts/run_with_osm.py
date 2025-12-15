"""
Example script to run experiments with OSM POI data (no LLM).

使用OSM数据运行实验的示例脚本。
"""

from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from planner.config import CONFIG
from planner.experiments import run_all_experiments


def main():
    """Run experiments with OSM POI data."""
    
    # Disable LLM mode to use OSM data
    CONFIG.llm.enabled = False
    
    # Optional: configure POI filter settings
    CONFIG.poi_filter.max_pois = 50  # 最多选择50个POI
    CONFIG.poi_filter.min_rating = 3.5  # 最低评分
    CONFIG.poi_filter.category_limit = 10  # 每个类别最多10个POI
    
    # Optional: configure routing settings
    CONFIG.routing.max_daily_hours = 8.0  # 每天最大游玩时间
    
    # Optional: configure alignment settings (for Experiment 3 & 5)
    CONFIG.alignment.max_matching_distance_km = 1.0  # Gowalla匹配距离阈值
    CONFIG.alignment.min_checkins_per_user = 3  # 最少签到数
    
    print("=" * 60)
    print("Running experiments with OSM POI data")
    print("=" * 60)
    print(f"OSM POI file: {CONFIG.data.osm_poi}")
    print(f"LLM mode: {CONFIG.llm.enabled}")
    print(f"Max POIs: {CONFIG.poi_filter.max_pois}")
    print("=" * 60)
    print()
    
    # Run experiments
    run_all_experiments()


if __name__ == "__main__":
    main()

