# PlanC Travel Planner

Automated multi-day travel planning with clustering, routing, LLM POI recommendation, and behavioral alignment.  
支持自动分天、日内路线优化、LLM 推荐景点、真实轨迹对齐与消融分析。

---

## What's inside / 核心功能
- POI clustering → 自动推断旅行天数，支持 KMeans/DBSCAN/HAC/Spectral，指标包含 Silhouette/DB/CH/SCI。
- Daily routing → Random / Rating / Nearest Neighbor，可选 2-opt，支持日最小/最大游玩时长约束。
- LLM recommendations → 多提供商（OpenAI/Anthropic/Google/AiHubMix），结果缓存到 `data/llm_pois/{city}.csv`。
- Real-world behavior alignment → 自动加载真实 Gowalla 签到数据，空间匹配到 OSM POI，提取用户轨迹，与规划路线计算对齐指标（路线级：Jaccard/Overlap/DTW；POI 热度级：Top-K Overlap/Spearman/Coverage）。
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
CONFIG.llm.city = "beijing"  # 或 "shanghai", "chengdu"
CONFIG.llm.num_days = 3
CONFIG.llm.preferences = "museums, parks, food"
CONFIG.llm.budget = "mid-range"

run_all_experiments()
```
或直接运行：`python scripts/run_with_llm.py`

### 优化对齐度的示例配置
```python
from planner.config import CONFIG
from planner.experiments import run_all_experiments

# 基础配置
CONFIG.llm.enabled = True
CONFIG.llm.city = "shanghai"
CONFIG.llm.num_days = 3

# 优化 1: 增加 POI 数量和多样性
CONFIG.llm.num_pois = 60  # 大幅增加
CONFIG.llm.preferences = "attractions, museums, parks, restaurants, shopping"
CONFIG.llm.interests = ["museums", "parks", "food", "history", "shopping", "culture"]
CONFIG.poi_filter.max_pois = 100
CONFIG.poi_filter.min_rating = 3.0  # 降低评分要求

# 优化 2: 放宽 Gowalla 匹配条件
CONFIG.alignment.max_matching_distance_km = 1.0  # 增加匹配距离
CONFIG.alignment.min_checkins_per_user = 3  # 降低签到阈值

# 优化 3: 增加每日游玩时间
CONFIG.routing.max_daily_hours = 12.0

run_all_experiments()
```

Outputs: 控制台打印实验结果；生成 `results/evaluation_summary.csv`。

---

## Data prep / 数据准备
- OSM POIs → `data/city_pois.csv`  
  - 可用 `python scripts/download_data.py --city "Paris, France"` 自动下载/预处理，或自备同字段：`poi_id, lat, lon, category, rating, duration_min, popularity, name, opening_hours`。
  - 支持非交互式环境：如果文件已存在，脚本会自动使用现有文件（无需手动确认）
  - 使用 OSMnx 下载时可能出现 FutureWarning（关于 `geometries` 模块重命名为 `features`），不影响功能，可忽略
  - 大区域查询会自动分割为多个子查询，可能需要较长时间
- **Gowalla 轨迹** → `data/Gowalla_totalCheckins.txt`（`python scripts/download_gowalla.py` 或从 [Stanford SNAP](https://snap.stanford.edu/data/loc-gowalla.html) 下载）
  - Experiment 3 会自动按城市过滤、空间匹配到 POI、提取用户轨迹
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
- **Alignment**: `max_trajectories`, `max_matching_distance_km` (Gowalla 位置到 POI 的匹配距离阈值), `min_checkins_per_user` (用户轨迹最少签到数)
- **City bounding boxes**: `CITY_BBOXES` 定义了支持的城市边界框（beijing, shanghai, chengdu）

---

## Experiments / 实验流程
- **Exp1 聚类**：KMeans/DBSCAN/HAC/Spectral；特征含标准化后的 lat/lon、rating、duration_min、popularity；指标 Silhouette/DB/CH/SCI。
  - 默认自动选择最佳聚类数（在 2 到 `max_days` 之间）
  - LLM 模式下自动使用 `CONFIG.llm.num_days` 作为固定天数（确保与推荐的天数一致）
- **Exp2 日内路线**：Random/Rating/NN，可 2-opt；约束日最小/最大游玩时长；评估 route length、backtracking ratio、time efficiency。
- **Exp3 真实行为对齐**（已完全集成真实 Gowalla 数据）：
  1. 自动加载指定城市的 Gowalla 签到数据（按边界框过滤）
  2. 使用 Haversine 距离将 Gowalla 位置空间匹配到 OSM POI（可配置距离阈值）
  3. 提取用户签到序列为轨迹（按时间排序，过滤签到数少的用户，支持去重和时间间隔分割）
  4. 与规划路线计算对齐指标：
     - **Jaccard**: 交集/并集，衡量 POI 重叠度（0-1，越高越好）
     - **Overlap**: 交集/min(规划, 真实)，衡量小集合被包含程度（0-1，越高越好）
     - **DTW**: Dynamic Time Warping，衡量序列相似度（越小越好）
  5. 输出多个真实轨迹的平均对齐分数
- **Exp4 消融**：popularity on/off × 2-opt on/off（可扩展）；输出 route_length_km、time_efficiency。
- **Exp5 POI 热度对齐**（基于 Gowalla 数据）：
  1. **数据来源**：
     - **规划路线数据**：统计系统生成的旅行路线中每个 POI 的访问频率
     - **真实轨迹数据**：从 Gowalla 签到数据中提取真实用户轨迹，统计每个 POI 的访问频率
  2. **对比方式**：比较规划路线与真实轨迹的 POI 热度分布一致性
  3. **评估指标**：
     - **Top-K Overlap**: Top-K 热门 POI 的重叠度（0-1，越高越好）
     - **Spearman 相关系数**: 热度排名的相关性（-1 到 1，越接近 1 越好）
     - **Coverage at K**: 规划路线覆盖真实 Top-K POI 的比例（0-1，越高越好）
  4. **目标**：评估规划算法是否选择了真实用户最常访问的 POI
  5. **与 Exp3 的区别**：Exp3 关注路线顺序的相似性（Jaccard/Overlap/DTW），Exp5 关注 POI 访问频率的相似性（热度分布）

---

## Outputs / 结果
- 控制台：簇数、路线统计、对齐指标（路线级和 POI 热度级）、消融对比。
- 文件：
  - `results/evaluation_summary.csv`（或 json）：包含 POI 数、天数、总/均值路线长、时间效率、回溯率、访问时长、聚类方法及 silhouette、路线方法、2-opt 使用情况、对齐指标（Exp3: Jaccard/Overlap/DTW，Exp5: Top-K Overlap/Spearman/Coverage）、消融结果。
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
scripts/           download_data.py (主下载脚本), download_gowalla.py, 
                   download_osm_pois.py (OSM POI 下载), run_with_llm.py, 
                   run_with_osm.py, clean_city_pois.py, visualize_ablation.py
data/              city_pois.csv, Gowalla_totalCheckins.txt, llm_pois/
results/           evaluation_summary.csv (运行后生成)
env.example        环境变量模板
requirements.txt   依赖
```

---

## Troubleshooting / 常见问题
- **缺少数据**：确认 `data/city_pois.csv` 与 `data/Gowalla_totalCheckins.txt` 已就位或运行下载脚本。
- **OSM 下载问题**：
  - 非交互式环境：脚本已支持自动处理，如果文件已存在会自动使用现有文件
  - OSMnx FutureWarning：关于 `geometries` 模块的警告可忽略，不影响功能
  - 大区域查询慢：大城市的 OSM 查询会自动分割为多个子查询，可能需要 10-30 分钟，请耐心等待
  - 查询失败：可尝试使用 `--bbox` 参数指定更精确的边界框，或使用 `--osm-method overpass` 切换方法
- **LLM 报错无 Key**：在 `.env` 中填 `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `GOOGLE_API_KEY` / `AIHUBMIX_API_KEY`。
- **坐标偏差**：LLM 生成坐标可能有误，可改用 OSM 模式或人工校验。
- **大规模 POI**：2-opt 会自动限迭代或跳过以避免过慢。
- **Gowalla 匹配数少**：
  - 增加 `CONFIG.alignment.max_matching_distance_km`（默认 0.5 km，建议 1.0-1.5 km）
  - 增加 POI 数量：`CONFIG.llm.num_pois = 60` 或使用 OSM 数据
  - 扩展 POI 类型：添加餐厅、商店、咖啡馆等日常地点
- **Gowalla 轨迹数少**：
  - 减少 `CONFIG.alignment.min_checkins_per_user`（默认 5，建议 3）
  - 选择签到数据更多的城市（北京 5,228 > 上海 2,144 > 成都 59）
- **对齐度指标很低**（Jaccard < 0.1）：
  - 增加 POI 数量到 60+（见上方优化建议）
  - 使用 OSM 数据代替 LLM（更全面的 POI 覆盖）
  - 增加每日 POI 数量：`CONFIG.routing.max_daily_hours = 12.0`
  - 扩展 POI 类型，包含餐厅、商店等真实用户常去的地方
- **缺少 sklearn**：运行 `pip install scikit-learn` 或 `pip install -r requirements.txt`

---

---

## Gowalla Integration Details / Gowalla 集成详情

### 数据流程
```
Gowalla_totalCheckins.txt (6.4M 签到)
    ↓ 按城市边界框过滤
城市签到数据 (如北京: 5,228 条)
    ↓ 空间匹配 (Haversine 距离)
Location → POI 映射
    ↓ 按用户和时间排序
用户轨迹序列
    ↓ 与规划路线对比
    ├─ Experiment 3: 路线级对齐
    │  └─ 对齐指标 (Jaccard, Overlap, DTW)
    └─ Experiment 5: POI 热度对齐
       └─ 热度指标 (Top-K Overlap, Spearman, Coverage)
```

### 对齐度指标说明

- **Jaccard 相似度** (0-1，越高越好)
  - 公式：交集大小 / 并集大小
  - 衡量规划路线与真实轨迹的 POI 重叠程度
  - 0.1-0.3 为合理范围，> 0.2 说明有一定参考价值

- **Overlap 系数** (0-1，越高越好)
  - 公式：交集大小 / min(规划路线大小, 真实轨迹大小)
  - 衡量较小集合被较大集合包含的程度
  - 0.3-0.5 为不错的表现，> 0.4 说明规划的 POI 大部分被真实访问

- **DTW 距离** (越小越好)
  - Dynamic Time Warping，考虑顺序的序列相似度
  - < 10 说明序列相对相似，< 8 为很好的表现
  - 受序列长度和内容差异影响

**Experiment 5 - POI 热度对齐指标**：

**数据对比**：
- **规划路线热度**：统计所有规划路线中每个 POI 的出现次数，按频率排序
- **真实轨迹热度**：统计 Gowalla 真实用户轨迹中每个 POI 的访问次数，按频率排序
- **对比方法**：比较两者的 Top-K 重叠、排名相关性、覆盖率

**指标说明**：
- **Top-K Overlap** (0-1，越高越好)
  - 定义：`|top_k_planned ∩ top_k_real| / K`
  - 衡量规划路线是否包含真实用户最常访问的 POI
  - > 0.3 为不错的表现，> 0.5 说明规划很好地捕捉了热门 POI
- **Spearman 相关系数** (-1 到 1，越接近 1 越好)
  - 定义：POI 热度排名的秩相关系数
  - 衡量规划路线和真实轨迹的 POI 热度排序是否一致
  - > 0.3 为正相关，> 0.5 为强相关
- **Coverage at K** (0-1，越高越好)
  - 定义：`|top_k_real ∩ all_planned| / K`
  - 衡量规划路线覆盖真实 Top-K POI 的比例
  - > 0.4 为不错的表现，> 0.6 说明覆盖了大部分热门 POI

**典型表现**（路线级对齐）：
- 基础配置（15-30 POI）：Jaccard 0.05-0.10, Overlap 0.15-0.25, DTW 12-15
- 优化配置（60+ POI，多类型）：Jaccard 0.15-0.25, Overlap 0.30-0.45, DTW 8-12
- OSM 数据（200+ POI）：Jaccard 0.20-0.30, Overlap 0.40-0.55, DTW 7-10

### 核心功能实现

#### 1. 城市过滤加载 (`data_loader.py`)
```python
load_gowalla_checkins(city_bbox=(lat_min, lat_max, lon_min, lon_max))
```
- 分块读取大文件（500k 行/块）
- 按边界框过滤，减少内存使用

#### 2. 空间匹配 (`data_loader.py`)
```python
match_gowalla_to_pois(gowalla_df, pois_df, max_distance_km=0.5)
```
- 使用 Haversine 距离计算
- 为每个 Gowalla location 找最近的 POI
- 可配置距离阈值

#### 3. 轨迹提取 (`data_loader.py`)
```python
extract_user_trajectories(
    gowalla_df, 
    mapping, 
    min_checkins=5,
    remove_duplicates=True,  # 移除连续重复的 POI
    max_time_gap_hours=24    # 按时间间隔分割轨迹
)
```
- 提取用户签到序列，转换为 POI 索引列表
- 按时间排序，过滤签到数少的用户
- 支持移除连续重复 POI（去除噪声）
- 支持按时间间隔分割（超过阈值视为不同行程）

#### 4. 集成到 Experiment 3 和 5 (`experiments.py`)
```python
get_real_gowalla_trajectories(pois, city="beijing", max_trajectories=None)
experiment_5_poi_popularity_alignment(planned_routes, day_pois, real_trajectories, pois, k=10)
```
- 一站式获取真实轨迹
- 自动处理完整流程
- 详细的进度输出
- Experiment 5 复用 Experiment 3 的轨迹数据，计算 POI 热度对齐

### 对齐度优化建议

1. **增加 POI 数量和多样性**：
```python
CONFIG.llm.num_pois = 60  # 从默认 18 增加到 60
CONFIG.poi_filter.max_pois = 100  # 从 50 增加到 100
CONFIG.llm.preferences = "attractions, museums, parks, restaurants, shopping, local experiences"
CONFIG.llm.interests = ["museums", "parks", "food", "history", "shopping", "culture"]
CONFIG.poi_filter.preferred_categories = [
    "tourism=attraction", "tourism=museum", "leisure=park",
    "amenity=restaurant", "shop", "amenity=cafe"  # 添加更多类型
]
```
预期提升：Jaccard 0.07 → 0.15-0.25，Overlap 0.20 → 0.30-0.45

2. **使用 OSM 数据**：
```bash
# 下载全面的 OSM POI 数据
python scripts/download_data.py --city "Shanghai, China" --bbox 30.7 31.5 121.0 122.0

# 然后禁用 LLM，使用 OSM 数据
CONFIG.llm.enabled = False
CONFIG.poi_filter.max_pois = 200
```
预期提升：Jaccard 0.07 → 0.20-0.30，Overlap 0.20 → 0.40-0.55

3. **调整匹配参数**：
```python
CONFIG.alignment.max_matching_distance_km = 1.0  # 从 0.5 增加到 1.0
CONFIG.alignment.min_checkins_per_user = 3  # 从 5 降低到 3
CONFIG.alignment.max_trajectories = 50  # 限制数量以加快实验
```

4. **增加每日 POI 数量**：
```python
CONFIG.routing.max_daily_hours = 12.0  # 从 8.0 增加
CONFIG.poi_filter.max_visit_time_hours = 10.0  # 从 6.0 增加
```
---

## License / 许可证
MIT (见 `LICENSE`)
