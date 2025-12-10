# PlanC Travel Planner

Automated multi-day travel planning with clustering, routing, LLM POI recommendation, and behavioral alignment.  
支持自动分天、日内路线优化、LLM 推荐景点、真实轨迹对齐与消融分析。

---

## What’s inside / 核心功能
- POI clustering → 自动推断旅行天数，支持 KMeans/DBSCAN/HAC/Spectral，指标包含 Silhouette/DB/CH/SCI。
- Daily routing → Random / Rating / Nearest Neighbor，可选 2-opt，支持日最小/最大游玩时长约束。
- LLM recommendations → 多提供商（OpenAI/Anthropic/Google/AiHubMix），结果缓存到 `data/llm_pois/{city}.csv`。
- Behavior alignment → 与 Gowalla 轨迹做 Jaccard / Overlap / DTW 对比。
- Ablation → 开关 popularity、2-opt 等因子，量化路线质量影响。

---

## Quickstart / 快速开始
```bash
git clone <repo>
cd planC-Travel-Planner
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp env.example .env   # 若启用 LLM，请填入对应 API Key
```

### Run with OSM data (no LLM) / 仅 OSM
```bash
# 准备 OSM POI CSV 与 Gowalla 数据（见下方数据准备）
python -m planner.experiments
```

### Run with LLM POIs / 使用 LLM 推荐
```python
from planner.config import CONFIG
from planner.experiments import run_all_experiments

CONFIG.llm.enabled = True
CONFIG.llm.city = "Chengdu"
CONFIG.llm.num_days = 3
CONFIG.llm.preferences = "museums, parks, food"
CONFIG.llm.budget = "mid-range"

run_all_experiments()
```
或直接运行：`python scripts/run_with_llm.py`

Outputs: 控制台打印实验结果；生成 `results/evaluation_summary.csv`。

---

## Data prep / 数据准备
- OSM POIs → `data/city_pois.csv`  
  - 可用 `python scripts/download_data.py --city "Paris, France"` 自动下载/预处理，或自备同字段：`poi_id, lat, lon, category, rating, duration_min, popularity, name, opening_hours`。
- Gowalla 轨迹 → `data/Gowalla_totalCheckins.txt`（`python scripts/download_gowalla.py` 或 SNAP 下载）。
- LLM 缓存 → 自动写入 `data/llm_pois/{city}.csv`（需 `.env` 中提供对应 API Key）。

---

## Key configuration / 主要配置（`planner/config.py`）
- Data paths: `CONFIG.data.*`
- POI 过滤：`min_rating`, `max_pois`, `category_limit`, `preferred_categories`, `max_visit_time_hours`, `min_visit_time_hours`, `filter_unknown_names`
- Clustering: `methods` (默认 `["kmeans","dbscan","hac","spectral"]`), `max_days`, `fixed_days`
  - **重要**：当 LLM 模式启用时，`CONFIG.llm.num_days` 会自动作为聚类实验的固定天数使用
  - 也可手动设置 `CONFIG.clustering.fixed_days` 来固定天数（优先级高于自动检测）
- Routing: `methods` (`["random","rating","nn","two_opt"]`), `max_daily_hours`, `start_time`, `end_time`
- LLM: `provider`(openai/anthropic/google/aihubmix), `model`, `temperature`, `city`, `num_days`, `preferences`, `budget`, `interests`, `num_pois`, `use_cache`
- Ablation: `consider_category`, `consider_popularity`, `enable_two_opt`
- Alignment: `max_trajectories`

---

## Experiments / 实验流程
- Exp1 聚类：KMeans/DBSCAN/HAC/Spectral；特征含标准化后的 lat/lon、rating、duration_min、popularity；指标 Silhouette/DB/CH/SCI。
  - 默认自动选择最佳聚类数（在 2 到 `max_days` 之间）
  - LLM 模式下自动使用 `CONFIG.llm.num_days` 作为固定天数（确保与推荐的天数一致）
- Exp2 日内路线：Random/Rating/NN，可 2-opt；约束日最小/最大游玩时长；评估 route length、backtracking ratio、time efficiency。
- Exp3 真实行为对齐：对 planned route 与 Gowalla 轨迹计算 Jaccard、Overlap、DTW（示例使用合成映射）。
- Exp4 消融：popularity on/off × 2-opt on/off（可扩展）；输出 route_length_km、time_efficiency。

---

## Outputs / 结果
- 控制台：簇数、路线统计、对齐指标、消融对比。
- 文件：
  - `results/evaluation_summary.csv`（或 json）：包含 POI 数、天数、总/均值路线长、时间效率、回溯率、访问时长、聚类方法及 silhouette、路线方法、2-opt 使用情况、对齐指标、消融结果。
  - `results/ablation_visualization.png`：消融实验对比柱状图（路线长度与时间效率）
  - `results/ablation_heatmap_length.png`：路线长度热力图
  - `results/ablation_heatmap_efficiency.png`：时间效率热力图
  - `results/ablation_comparison_table.png`：消融实验对比表格
- 单独运行可视化：`python scripts/visualize_ablation.py --input results/evaluation_summary.csv --show`

---

## Repo map / 目录
```
planner/           核心逻辑：config, data_loader, clustering, routing,
                   evaluation, experiments, ablation, results_evaluation, 
                   llm_recommender, visualization
scripts/           download_data.py, download_gowalla.py, run_with_llm.py, 
                   clean_city_pois.py, visualize_ablation.py
data/              city_pois.csv, Gowalla_totalCheckins.txt, llm_pois/
results/           evaluation_summary.csv (运行后生成)
env.example        环境变量模板
requirements.txt   依赖
```

---

## Troubleshooting / 常见问题
- 缺少数据：确认 `data/city_pois.csv` 与 `data/Gowalla_totalCheckins.txt` 已就位或运行下载脚本。
- LLM 报错无 Key：在 `.env` 中填 `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `GOOGLE_API_KEY` / `AIHUBMIX_API_KEY`。
- 坐标偏差：LLM 生成坐标可能有误，可改用 OSM 模式或人工校验。
- 大规模 POI：2-opt 会自动限迭代或跳过以避免过慢。

---

## License / 许可证
MIT (见 `LICENSE`)
