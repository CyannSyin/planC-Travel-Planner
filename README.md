# PlanC Travel Planner

**An Automated Travel Planning System for POI Clustering and Route Optimization**

**自动化旅游规划系统：景点聚类与路线优化**

---

## 📋 Overview / 项目概述

This research system addresses the following question:

**Research Question / 研究问题：**

> Given a set of Points of Interest (POIs) with attributes such as location, rating, category, and estimated visit duration, how can we automatically cluster them into daily travel zones and generate optimized intra-day routes?

> 给定一组景点（POI），包含位置、评分、类别、预估游玩时长等属性，如何自动将其聚类为多日行程区域，并生成每天内部的优化路线？

### Key Features / 核心功能

- **Multiple Data Sources / 多种数据源**：
  - OSM (OpenStreetMap) POI data / OSM 景点数据
  - **LLM-based POI recommendations / LLM 智能推荐** (NEW!)
  - Gowalla check-in trajectories / Gowalla 签到轨迹

- **Advanced Clustering / 高级聚类**：
  - K-means, DBSCAN, HAC, Spectral clustering
  - Automatic optimal day count determination

- **Route Optimization / 路线优化**：
  - Nearest Neighbor, Rating-based, 2-opt improvement
  - Daily time constraints (min/max visit hours)

- **Comprehensive Evaluation / 全面评估**：
  - Route efficiency metrics
  - Real-world behavior alignment
  - Ablation studies

---

## 🔬 Experiments / 实验设计

### Experiment 1 — POI Clustering / 景点聚类

**Goal / 目标：** Automatically determine the optimal number of days and cluster POIs into daily travel zones.

自动确定最优天数，并将 POI 聚类为每日行程区域。

- **Methods / 方法：**
  - K-means clustering
  - DBSCAN clustering
  - Hierarchical Agglomerative Clustering (HAC)
  - Spectral clustering

- **Metrics / 评估指标：**
  - Silhouette Score
  - Davies-Bouldin Index (DB Index)
  - Calinski-Harabasz Index (CH Index)
  - Spatial Cohesion Index (SCI) — custom metric (inter-cluster distance / intra-cluster distance)

- **Output / 输出：** Best clustering result → number of days

### Experiment 2 — Daily Route Optimization / 日内路线优化

**Goal / 目标：** Generate optimized routes for each day's POI cluster.

为每天的 POI 簇生成优化路线。

- **Methods / 方法：**
  - Random ordering
  - Rating-based (descending)
  - Nearest Neighbor (NN)
  - 2-opt improvement (can be applied to any base route)

- **Constraints / 约束条件：**
  - Maximum visit time per day / 每天最大游玩时间
  - **Minimum visit time per day / 每天最小游玩时间** (NEW! Ensures at least 4 hours per day)

- **Metrics / 评估指标：**
  - Route length (km)
  - Backtracking ratio
  - Time efficiency

### Experiment 3 — Real-world Behavior Alignment / 真实行为对齐

**Goal / 目标：** Compare planned routes with real-world travel behavior from Gowalla trajectories.

将规划路线与 Gowalla 真实轨迹进行对比。

- **Data / 数据：** Gowalla check-in trajectories

- **Metrics / 评估指标：**
  - Jaccard similarity
  - Overlap coefficient
  - Dynamic Time Warping (DTW) distance

- **Shows / 展示：** System alignment with real travel behavior

### Experiment 4 — Ablation Study / 消融实验

**Goal / 目标：** Analyze the effect of different factors on route quality.

分析不同因素对路线质量的影响。

- **Factors / 因子：**
  - Category influence
  - Popularity influence
  - 2-opt improvement effect

---

## 📁 Project Structure / 项目结构

```
planC-Travel-Planner/
├── planner/                      # Main Python package
│   ├── __init__.py              # Package initialization
│   ├── config.py                # Global configuration (paths, hyperparameters)
│   ├── data_loader.py           # Data loading utilities
│   │                             # - Gowalla_totalCheckins.txt loader
│   │                             # - OSM POI CSV loader
│   │                             # - LLM POI recommender integration
│   ├── llm_recommender.py       # LLM-based POI recommendation (NEW!)
│   ├── clustering.py            # Experiment 1 implementation
│   │                             # - K-means, DBSCAN, HAC, Spectral
│   │                             # - Silhouette, DB, CH, SCI metrics
│   ├── routing.py               # Experiment 2 implementation
│   │                             # - Random, Rating, NN, 2-opt methods
│   ├── evaluation.py            # Evaluation metrics
│   │                             # - Route metrics (length, backtracking, time)
│   │                             # - Alignment metrics (Jaccard, Overlap, DTW)
│   ├── experiments.py           # Experiment orchestration
│   │                             # - run_all_experiments() entry point
│   ├── ablation.py              # Experiment 4 implementation
│   └── results_evaluation.py    # Results evaluation and reporting
├── data/                        # Data directory
│   ├── Gowalla_totalCheckins.txt   # Raw Gowalla check-in data
│   ├── city_pois.csv           # Preprocessed OSM POI data
│   └── llm_pois/               # LLM-recommended POI cache (NEW!)
├── scripts/                     # Data download scripts
│   ├── download_gowalla.py     # Gowalla dataset downloader
│   ├── download_osm_pois.py    # OSM POI data downloader
│   ├── download_data.py        # Main download script (all datasets)
│   └── run_with_llm.py         # Example script for LLM mode (NEW!)
├── notebooks/                   # Jupyter notebooks for analysis
├── requirements.txt             # Python dependencies
├── env.example                  # Environment variables template (NEW!)
├── LICENSE                      # License file
└── README.md                    # This file
```

---

## 🚀 Setup / 环境准备

### Prerequisites / 前置要求

- Python 3.8+
- pip or conda

### Installation / 安装步骤

1. **Clone or navigate to the project directory:**

```bash
cd planC-Travel-Planner
```

2. **Create a virtual environment (recommended):**

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install dependencies:**

```bash
pip install -r requirements.txt
```

**Dependencies / 依赖包：**
- `numpy` — Numerical computations
- `pandas` — Data manipulation
- `scikit-learn` — Clustering algorithms
- `scipy` — Distance calculations, DTW
- `python-dotenv` — Environment variable management
- `openai` — OpenAI API client (for LLM recommendations)

**Optional dependencies / 可选依赖：**
- `anthropic` — Anthropic Claude API (for alternative LLM provider)
- `google-generativeai` — Google Gemini API (for alternative LLM provider)
- `osmnx` — OSM data download (optional, for OSM data collection)

---

## 📊 Data Preparation / 数据准备

### Option A: LLM-based POI Recommendations (NEW!) / 选项 A：基于 LLM 的 POI 推荐（新功能！）

The system now supports using Large Language Models (LLMs) to recommend POIs and estimate visit durations. This provides more personalized recommendations compared to OSM data.

系统现在支持使用大语言模型（LLM）来推荐POI和游玩时间，相比OSM数据提供更个性化的推荐。

#### Setup LLM Mode / 设置 LLM 模式

1. **Configure API keys:**

```bash
cp env.example .env
```

2. **Edit `.env` file with your API key:**

```bash
OPENAI_API_KEY=your_openai_api_key_here
LLM_PROVIDER=openai
LLM_MODEL=gpt-4
LLM_TEMPERATURE=0.7
```

**Supported LLM Providers / 支持的 LLM 提供商：**
- `openai` — OpenAI GPT models (default)
- `anthropic` — Anthropic Claude (requires `anthropic` package)
- `google` — Google Gemini (requires `google-generativeai` package)

3. **Use LLM mode in code:**

```python
from planner.config import CONFIG
from planner.experiments import run_all_experiments

# Enable LLM mode
CONFIG.llm.enabled = True
CONFIG.llm.city = "Chengdu"
CONFIG.llm.num_days = 3
CONFIG.llm.preferences = "cultural sites, museums, parks"
CONFIG.llm.budget = "mid-range"
CONFIG.llm.interests = ["museums", "parks", "food"]

# Run experiments
run_all_experiments()
```

4. **Or use the example script:**

```bash
python scripts/run_with_llm.py
```

**LLM Configuration Options / LLM 配置选项：**

- `enabled`: Enable LLM mode (default: False)
- `provider`: LLM provider (`"openai"`, `"anthropic"`, `"google"`)
- `model`: Model name (e.g., `"gpt-4"`, `"claude-3-opus-20240229"`, `"gemini-pro"`)
- `temperature`: Generation temperature (0.0-2.0, default: 0.7)
- `use_cache`: Use cached results (default: True)
- `city`: Target city name (required)
- `num_days`: Number of travel days (default: 3)
- `preferences`: User preferences description (optional)
- `budget`: Budget level (`"budget"`, `"mid-range"`, `"luxury"`) (optional)
- `interests`: List of interests (optional)
- `num_pois`: Target number of POIs (None = auto: num_days * 6)

**LLM Data Flow / LLM 数据流：**

1. LLM API call → Get POI recommendations in JSON format
2. Cache save → Results saved to `data/llm_pois/{city}.csv`
3. Data loading → Load from cache if available, otherwise call API
4. Standard processing → Filtering, clustering, routing, evaluation

**LLM vs OSM Comparison / LLM 与 OSM 对比：**

| Feature / 特性 | OSM Mode | LLM Mode |
|---------------|----------|----------|
| Data Source / 数据源 | OpenStreetMap | LLM Recommendations |
| Coordinate Accuracy / 坐标精度 | High / 高 | Medium / 中等 |
| Personalization / 个性化 | Low / 低 | High / 高 |
| Cost / 成本 | Free / 免费 | API fees / API费用 |
| Speed / 速度 | Fast (local file) / 快（本地文件） | Slow (API call) / 慢（API调用） |
| Data Volume / 数据量 | Large / 大 | Controllable / 可控制 |

---

### Option B: OSM Data (Traditional) / 选项 B：OSM 数据（传统方式）

#### Automatic Download (Recommended) / 自动下载（推荐）

We provide automated scripts to download OSM data:

我们提供了自动下载脚本：

```bash
# Download using city name
python scripts/download_data.py --city "Manhattan, New York, USA"

# Download using bounding box
python scripts/download_data.py --bbox 40.8 40.7 -73.9 -74.0

# Download only OSM POIs
python scripts/download_data.py --skip-gowalla --city "Paris, France"
```

#### Manual Preparation / 手动准备

**OSM POI Data Format / OSM POI 数据格式：**

**File:** `data/city_pois.csv`

**Required Columns / 必需列：**

| Column / 列名 | Type / 类型 | Description / 说明 |
|--------------|------------|-------------------|
| `poi_id` | int/str | Unique POI identifier |
| `lat` | float | Latitude |
| `lon` | float | Longitude |
| `category` | str | POI category (e.g., "tourism=museum", "amenity=restaurant") |
| `rating` | float | Rating (0.0-5.0) |
| `duration_min` | float | Estimated visit duration in minutes |
| `popularity` | float | Popularity score (optional) |
| `name` | str | POI name |
| `opening_hours` | str | Opening hours (optional) |

**Example CSV / 示例 CSV:**

```csv
poi_id,lat,lon,category,rating,duration_min,popularity,name,opening_hours
1,40.7128,-74.0060,tourism=museum,4.5,120.0,0.85,Metropolitan Museum,Mo-Su 10:00-17:30
2,40.7589,-73.9851,amenity=restaurant,4.2,60.0,0.72,Central Park Cafe,Mo-Su 08:00-22:00
```

---

### Option C: Gowalla Check-in Data / 选项 C：Gowalla 签到数据

**File:** `data/Gowalla_totalCheckins.txt`

**Expected Format / 期望格式：**

Tab-separated values with columns: `user_id`, `check-in_time`, `latitude`, `longitude`, `location_id`

**Download / 下载：**

```bash
python scripts/download_gowalla.py
```

Or manually from: [Stanford SNAP](https://snap.stanford.edu/data/loc-gowalla.html)

---

## ⚙️ Configuration / 配置说明

Edit `planner/config.py` to customize:

修改 `planner/config.py` 以自定义配置：

### Data Paths / 数据路径

```python
CONFIG.data.gowalla_checkins = Path("data/Gowalla_totalCheckins.txt")
CONFIG.data.osm_poi = Path("data/city_pois.csv")
CONFIG.data.llm_poi_cache = Path("data/llm_pois")  # LLM cache directory
```

### LLM Settings / LLM 设置

```python
CONFIG.llm.enabled = False  # Enable LLM mode
CONFIG.llm.city = "Chengdu"
CONFIG.llm.num_days = 3
CONFIG.llm.provider = "openai"
CONFIG.llm.model = "gpt-4"
CONFIG.llm.temperature = 0.7
CONFIG.llm.use_cache = True
```

### POI Filter Settings / POI 过滤设置

```python
CONFIG.poi_filter.min_rating = 4.0  # Minimum rating
CONFIG.poi_filter.max_pois = 10  # Maximum POIs to select
CONFIG.poi_filter.max_visit_time_hours = 6.0  # Max hours per day
CONFIG.poi_filter.min_visit_time_hours = 4.0  # Min hours per day (NEW!)
CONFIG.poi_filter.category_limit = 5  # Max POIs per category
```

### Clustering Settings / 聚类设置

```python
CONFIG.clustering.methods = ["kmeans", "dbscan", "hac", "spectral"]
CONFIG.clustering.max_days = 7  # Maximum number of days
```

### Routing Settings / 路线规划设置

```python
CONFIG.routing.methods = ["random", "rating", "nn", "two_opt"]
CONFIG.routing.max_daily_hours = 8.0  # Maximum hours per day
CONFIG.routing.start_time = "09:00"
CONFIG.routing.end_time = "19:00"
```

---

## 🏃 Running Experiments / 运行实验

### Option 1: Run All Experiments / 运行所有实验

**Command line / 命令行：**

```bash
python -m planner.experiments
```

**Expected Output / 预期输出：**

```
=== LLM POI Recommendation ===
City: Chengdu
Number of days: 3
Preferences: cultural sites, museums, parks
=== POI Filtering ===
Total POIs loaded: 18
POIs after filtering:
  - Min rating: 4.0
  - Max POIs: 10
  - Selected POIs: 9

=== Experiment 1: POI Clustering ===
kmeans: n_clusters=3, silhouette=0.452
dbscan: n_clusters=4, silhouette=0.381
hac: n_clusters=3, silhouette=0.468
spectral: n_clusters=4, silhouette=0.423

=== Experiment 2: Daily Route Optimization (NN + 2-opt) ===
Day 0: length=12.34 km, time_eff=0.82
Day 1: length=15.67 km, time_eff=0.79
Day 2: length=11.23 km, time_eff=0.85

=== Experiment 3: Real-world Behavior Alignment (toy) ===
Alignment metrics: {'jaccard': 0.65, 'overlap': 0.72, 'dtw': 0.15}

=== Experiment 4: Ablation ===
baseline: length=45.23, time_eff=0.75
with_popularity: length=42.11, time_eff=0.81
with_2opt: length=40.89, time_eff=0.84
```

### Option 2: Run with LLM Mode / 使用 LLM 模式运行

```bash
python scripts/run_with_llm.py
```

Or configure in code:

```python
from planner.config import CONFIG
from planner.experiments import run_all_experiments

CONFIG.llm.enabled = True
CONFIG.llm.city = "Beijing"
CONFIG.llm.num_days = 5
CONFIG.llm.interests = ["museums", "history", "food"]

run_all_experiments()
```

### Option 3: Run Individual Experiments / 运行单个实验

```python
from planner.experiments import (
    experiment_1_poi_clustering,
    experiment_2_daily_routes,
    assign_pois_to_days,
)
from planner.data_loader import load_pois  # Works with both OSM and LLM
from planner.config import CONFIG

# Load data (automatically uses LLM if enabled, otherwise OSM)
pois = load_pois()

# Experiment 1: Clustering
cluster_results = experiment_1_poi_clustering(pois)
best_result = cluster_results["kmeans"]

# Assign POIs to days
day_pois = assign_pois_to_days(
    pois, 
    best_result.labels,
    max_visit_time_hours=CONFIG.poi_filter.max_visit_time_hours,
    min_visit_time_hours=CONFIG.poi_filter.min_visit_time_hours
)

# Experiment 2: Daily routes
routes, metrics = experiment_2_daily_routes(
    day_pois, method="nn", use_two_opt=True
)
```

---

## 📈 Output & Results / 输出与结果

### Experiment 1 Output / 实验 1 输出

- **Clustering results per method:**
  - Number of clusters (days)
  - Silhouette score
  - DB Index
  - CH Index
  - SCI (Spatial Cohesion Index)
  - Cluster labels for each POI

### Experiment 2 Output / 实验 2 输出

- **Route for each day:**
  - Ordered list of POI indices
  - Route length (km)
  - Backtracking ratio
  - Time efficiency
  - **Daily visit time (with min/max constraints)**

### Experiment 3 Output / 实验 3 输出

- **Alignment metrics:**
  - Jaccard similarity (0-1, higher is better)
  - Overlap coefficient (0-1, higher is better)
  - DTW distance (0-1, lower is better)

### Experiment 4 Output / 实验 4 输出

- **Ablation results:**
  - Route length comparison
  - Time efficiency comparison
  - Effect of each factor (category, popularity, 2-opt)

### Evaluation Report / 评估报告

Results are automatically saved to `results/evaluation_summary.csv` with:
- Overall statistics
- Route statistics
- Time statistics
- Experiment details

---

## 🧮 Evaluation Guide / 实验结果评估指南

### Key Metrics / 核心评估指标

- **Route efficiency / 路线效率**
  - **Time efficiency**: visit time / (visit time + travel time), in [0, 1], higher is better.
  - **Backtracking ratio**: actual route length / baseline route length, ≈1.0 is ideal, <1.0 is better than baseline.

- **Clustering quality / 聚类质量**
  - **Silhouette score**: [-1, 1], higher is better; >0.5 is good, >0.7 is very good.

- **Behavior alignment / 与真实行为对齐**
  - **Jaccard similarity**, **Overlap coefficient**: [0, 1], higher is better.
  - **DTW distance**: ≥0, lower is better (sequence more similar).

### Daily Time Constraints / 每日时间约束

The system now enforces:
- **Maximum visit time**: Limits total visit time per day
- **Minimum visit time**: Ensures at least 4 hours of activities per day (configurable)

系统现在强制执行：
- **最大游玩时间**：限制每天的总游玩时间
- **最小游玩时间**：确保每天至少有4小时的活动（可配置）

---

## 🔧 Extension & Customization / 扩展与定制

### Adding New Clustering Methods / 添加新的聚类方法

Edit `planner/clustering.py`:

```python
def your_custom_clustering(pois: pd.DataFrame, n_clusters: int):
    # Your implementation
    labels = ...
    return labels
```

### Adding New Routing Methods / 添加新的路径规划方法

Edit `planner/routing.py`:

```python
def your_custom_route(pois: pd.DataFrame) -> List[int]:
    # Your implementation
    order = ...
    return order
```

### Custom Data Loader / 自定义数据加载器

Edit `planner/data_loader.py` to support additional data formats or sources.

---

## ❓ Troubleshooting / 故障排除

### Issue: FileNotFoundError for data files

**Solution:** Ensure data files are in the `data/` directory, or update paths in `config.py`.

### Issue: LLM API key not found

```
ValueError: API key not found for provider 'openai'
```

**Solution:** 
1. Copy `env.example` to `.env`
2. Add your API key: `OPENAI_API_KEY=your_key_here`
3. Ensure `.env` file is in the project root

### Issue: LLM JSON parsing error

```
ValueError: Failed to parse JSON from LLM response
```

**Solution:**
- Check if the LLM model supports JSON output
- Try lowering temperature value (e.g., 0.3) for more stable output
- Check API response completeness

### Issue: Invalid coordinates from LLM

```
ValueError: Invalid coordinates in LLM response
```

**Solution:**
- Use geocoding API to correct coordinates
- Manually edit cache file: `data/llm_pois/{city}.csv`
- Re-request recommendations

### Issue: Import errors

**Solution:** Make sure you've installed all dependencies: `pip install -r requirements.txt`

### Issue: Memory errors with large datasets

**Solution:** Adjust `CONFIG.alignment.max_trajectories` to limit Gowalla data loading, or process data in batches.

---

## 📝 Code Structure Notes / 代码结构说明

- **Modular design / 模块化设计：** Each experiment and functionality is separated into its own module.
- **Type hints / 类型提示：** Functions use type hints for better code readability.
- **Docstrings / 文档字符串：** All modules and functions have docstrings (English and Chinese).
- **Configuration centralized / 配置集中化：** All hyperparameters are in `config.py`.
- **Easy to extend / 易于扩展：** Clear interfaces allow easy addition of new methods.
- **Multiple data sources / 多种数据源：** Supports both OSM and LLM-based POI recommendations.

---

## 🤝 Contributing / 贡献

This is a research codebase. Feel free to:

- Report issues
- Suggest improvements
- Extend with new methods

---

## 📄 License / 许可

See `LICENSE` file for details.

---

## 📚 References / 参考文献

- Gowalla Dataset: [Stanford Large Network Dataset Collection](https://snap.stanford.edu/data/loc-gowalla.html)
- OpenStreetMap: [https://www.openstreetmap.org/](https://www.openstreetmap.org/)
- Scikit-learn Clustering: [https://scikit-learn.org/stable/modules/clustering.html](https://scikit-learn.org/stable/modules/clustering.html)

---

**For questions or issues, please open an issue on the repository.**

**如有问题或建议，请在仓库中提交 issue。**
