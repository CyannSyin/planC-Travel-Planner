"""
Example script to run experiments with LLM-based POI recommendations.

使用LLM推荐POI并运行实验的示例脚本。
"""

from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from planner.config import CONFIG
from planner.experiments import run_all_experiments


def main():
    """Run experiments with LLM recommendations."""
    
    # Configure LLM mode
    CONFIG.llm.enabled = True
    CONFIG.llm.city = "Guangzhou"  # 修改为你想要的城市
    CONFIG.llm.num_days = 4
    CONFIG.llm.preferences = "cultural sites, museums, parks"
    CONFIG.llm.budget = "mid-range"
    CONFIG.llm.interests = ["museums", "parks", "food", "history"]
    CONFIG.llm.num_pois = None  # 自动计算：num_days * 6
    
    # Optional: adjust POI filter settings
    CONFIG.poi_filter.max_pois = 20  # 最多选择20个POI
    CONFIG.poi_filter.min_rating = 3.5  # 降低最低评分要求（LLM推荐的评分可能不同）
    
    print("=" * 60)
    print("Running experiments with LLM-based POI recommendations")
    print("=" * 60)
    print(f"City: {CONFIG.llm.city}")
    print(f"Days: {CONFIG.llm.num_days}")
    print(f"Provider: {CONFIG.llm.provider}")
    print(f"Model: {CONFIG.llm.model}")
    print("=" * 60)
    print()
    
    # Run experiments
    run_all_experiments()


if __name__ == "__main__":
    main()

