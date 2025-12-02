# PlanC Travel Planner

**An Automated Travel Planning System for POI Clustering and Route Optimization**

**自动化旅游规划系统：景点聚类与路线优化**

---

## 📋 Overview / 项目概述

This research system addresses the following question:

**Research Question / 研究问题：**

> Given a set of Points of Interest (POIs) with attributes such as location, rating, category, and estimated visit duration, how can we automatically cluster them into daily travel zones and generate optimized intra-day routes?

> 给定一组景点（POI），包含位置、评分、类别、预估游玩时长等属性，如何自动将其聚类为多日行程区域，并生成每天内部的优化路线？

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
│   └── ablation.py              # Experiment 4 implementation
├── data/                        # Data directory
│   ├── Gowalla_totalCheckins.txt   # Raw Gowalla check-in data
│   └── city_pois.csv           # Preprocessed OSM POI data
├── scripts/                     # Data download scripts
│   ├── download_gowalla.py     # Gowalla dataset downloader
│   ├── download_osm_pois.py    # OSM POI data downloader
│   └── download_data.py        # Main download script (all datasets)
├── notebooks/                   # Jupyter notebooks for analysis
├── requirements.txt             # Python dependencies
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
cd /Users/nicolewang/Documents/research/planCTravel/planC-Travel-Planner
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

---

## 📊 Data Preparation / 数据准备

### Option A: Automatic Download (Recommended) / 选项 A：自动下载（推荐）

We provide automated scripts to download both datasets. First, install additional dependencies:

我们提供了自动下载脚本。首先安装额外的依赖：

```bash
pip install -r requirements.txt
```

**Note:** If you plan to use OSMnx for OSM data download, also install it:
**注意：** 如果使用 OSMnx 下载 OSM 数据，请额外安装：

```bash
pip install osmnx
```

#### Download All Data / 下载所有数据

**Using city name (recommended) / 使用城市名称（推荐）：**

```bash
python scripts/download_data.py --city "Manhattan, New York, USA"
```

**Using bounding box / 使用边界框：**

```bash
python scripts/download_data.py --bbox 40.8 40.7 -73.9 -74.0
```

**Download only one dataset / 只下载一个数据集：**

```bash
# Only Gowalla
python scripts/download_data.py --skip-osm

# Only OSM POIs
python scripts/download_data.py --skip-gowalla --city "Paris, France"
```

#### Download Separately / 分别下载

**Download Gowalla data only / 只下载 Gowalla 数据：**

```bash
python scripts/download_gowalla.py
```

**Download OSM POIs only / 只下载 OSM POI 数据：**

```bash
# Using city name (requires osmnx)
python scripts/download_osm_pois.py --city "Manhattan, New York, USA" --method osmnx

# Using bounding box with Overpass API (no osmnx needed)
python scripts/download_osm_pois.py --bbox 40.8 40.7 -73.9 -74.0 --method overpass
```

**See help / 查看帮助：**

```bash
python scripts/download_data.py --help
python scripts/download_gowalla.py --help
python scripts/download_osm_pois.py --help
```

---

### Option B: Manual Preparation / 选项 B：手动准备

### 1. Gowalla Check-in Data / Gowalla 签到数据

**File:** `data/Gowalla_totalCheckins.txt`

**Expected Format / 期望格式：**

The file should contain tab-separated or space-separated values with the following columns:

- `user_id` — User identifier
- `check-in_time` — Timestamp (format: YYYY-MM-DD HH:MM:SS)
- `latitude` — Latitude
- `longitude` — Longitude
- `location_id` — Location identifier

**Example / 示例：**

```
0	2010-07-24T13:45:06Z	30.285648	-97.741760	145064
0	2010-07-24T13:44:58Z	30.275103	-97.740310	145063
```

**Note / 说明：** The actual format may vary. Update `data_loader.py` if your file has a different structure.

**Manual Download / 手动下载：**

You can download the Gowalla dataset from:
你可以从以下地址手动下载 Gowalla 数据集：

- **Stanford SNAP:** [https://snap.stanford.edu/data/loc-gowalla.html](https://snap.stanford.edu/data/loc-gowalla.html)
- Direct link: [https://snap.stanford.edu/data/loc-gowalla_totalCheckins.txt.gz](https://snap.stanford.edu/data/loc-gowalla_totalCheckins.txt.gz)

Download and extract the `.gz` file to `data/Gowalla_totalCheckins.txt`.

下载并解压 `.gz` 文件到 `data/Gowalla_totalCheckins.txt`。

### 2. OSM POI Data / OSM 景点数据

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
| `popularity` | float | Popularity score (optional, can be derived) |
| `name` | str | POI name |
| `opening_hours` | str | Opening hours (e.g., "Mo-Su 09:00-18:00") |

**Example / 示例 CSV:**

```csv
poi_id,lat,lon,category,rating,duration_min,popularity,name,opening_hours
1,40.7128,-74.0060,tourism=museum,4.5,120.0,0.85,Metropolitan Museum,Mo-Su 10:00-17:30
2,40.7589,-73.9851,amenity=restaurant,4.2,60.0,0.72,Central Park Cafe,Mo-Su 08:00-22:00
```

**Manual Collection / 手动收集：**

If you prefer to manually collect OSM data, you can use:

如果你更喜欢手动收集 OSM 数据，可以使用：

- **Overpass Turbo** — Interactive query builder: [https://overpass-turbo.eu/](https://overpass-turbo.eu/)
- **OSMnx Python library** — See example below
- **osm2pgsql** — Import OSM data into PostgreSQL

**Example OSM Query (Overpass API) / 示例查询：**

```xml
<osm-script>
  <query type="node">
    <bbox-query e="..." n="..." s="..." w="..."/>
    <has-kv k="tourism"/>
  </query>
  <print/>
</osm-script>
```

**Example Python script with OSMnx / 使用 OSMnx 的示例：**

```python
import osmnx as ox
import pandas as pd

# Download POIs in a city
tags = {'tourism': True, 'amenity': 'restaurant'}
gdf = ox.geometries_from_place('City Name', tags=tags)

# Process and export to CSV with required columns
# (You'll need to map OSM fields to the required schema)
gdf.to_csv('data/city_pois.csv')
```

**Note / 注意：** For easier data preparation, we recommend using the automatic download scripts described in Option A above.

为了更轻松地准备数据，我们建议使用上面选项 A 中描述的自动下载脚本。

---

## ⚙️ Configuration / 配置说明

Edit `planner/config.py` to customize:

修改 `planner/config.py` 以自定义配置：

### Data Paths / 数据路径

```python
CONFIG.data.gowalla_checkins = Path("data/Gowalla_totalCheckins.txt")
CONFIG.data.osm_poi = Path("data/city_pois.csv")
```

### Clustering Settings / 聚类设置

```python
CONFIG.clustering.methods = ["kmeans", "dbscan", "hac", "spectral"]
CONFIG.clustering.max_days = 7  # Maximum number of days
```

### Routing Settings / 路线规划设置

```python
CONFIG.routing.methods = ["random", "rating", "nn", "two_opt"]
CONFIG.routing.max_daily_hours = 10.0  # Maximum hours per day
CONFIG.routing.start_time = "09:00"
CONFIG.routing.end_time = "19:00"
```

### Ablation Settings / 消融实验设置

```python
CONFIG.ablation.consider_category = True
CONFIG.ablation.consider_popularity = True
CONFIG.ablation.enable_two_opt = True
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
with_popularity_and_2opt: length=38.56, time_eff=0.87
```

### Option 2: Run Individual Experiments / 运行单个实验

**Python script / Python 脚本：**

```python
from planner.experiments import (
    experiment_1_poi_clustering,
    experiment_2_daily_routes,
    experiment_3_behavior_alignment,
    experiment_4_ablation,
    assign_pois_to_days,
)
from planner.data_loader import load_osm_pois, load_gowalla_checkins
from planner.config import CONFIG

# Load data
pois = load_osm_pois()
gowalla = load_gowalla_checkins()

# Experiment 1: Clustering
cluster_results = experiment_1_poi_clustering(pois)
best_result = cluster_results["kmeans"]  # or select by best silhouette
print(f"Optimal number of days: {best_result.n_clusters}")

# Assign POIs to days
day_pois = assign_pois_to_days(pois, best_result.labels)

# Experiment 2: Daily routes
routes, metrics = experiment_2_daily_routes(
    day_pois, method="nn", use_two_opt=True
)
print(f"Day 1 route length: {metrics[1]['length_km']:.2f} km")

# Experiment 3: Behavior alignment (example)
planned_route = [1, 2, 3, 4, 5]
real_trajectory = [1, 3, 2, 4, 5]  # From Gowalla data
alignment = experiment_3_behavior_alignment(planned_route, real_trajectory)
print(f"Jaccard similarity: {alignment['jaccard']:.3f}")

# Experiment 4: Ablation
ablation_results = experiment_4_ablation(pois)
print(ablation_results)
```

### Option 3: Custom Experiment / 自定义实验

```python
from planner.clustering import select_best_clustering
from planner.routing import build_route
from planner.evaluation import evaluate_route

# Custom clustering
results = select_best_clustering(pois, max_days=5)

# Custom routing
order = build_route(day_pois[1], method="rating", use_two_opt=False)

# Evaluate
metrics = evaluate_route(day_pois[1], order)
print(f"Route length: {metrics.length_km:.2f} km")
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

### Adding New Evaluation Metrics / 添加新的评估指标

Edit `planner/evaluation.py`:

```python
def your_custom_metric(route, reference):
    # Your implementation
    score = ...
    return score
```

### Custom Data Loader / 自定义数据加载器

Edit `planner/data_loader.py` to support additional data formats.

---

## 📝 Code Structure Notes / 代码结构说明

- **Modular design / 模块化设计：** Each experiment and functionality is separated into its own module.
- **Type hints / 类型提示：** Functions use type hints for better code readability.
- **Docstrings / 文档字符串：** All modules and functions have docstrings (English and Chinese).
- **Configuration centralized / 配置集中化：** All hyperparameters are in `config.py`.
- **Easy to extend / 易于扩展：** Clear interfaces allow easy addition of new methods.

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

## ❓ Troubleshooting / 故障排除

### Issue: FileNotFoundError for data files

**Solution:** Ensure `Gowalla_totalCheckins.txt` and `city_pois.csv` are in the `data/` directory, or update paths in `config.py`.

### Issue: Import errors

**Solution:** Make sure you've installed all dependencies: `pip install -r requirements.txt`

### Issue: Memory errors with large datasets

**Solution:** Adjust `CONFIG.alignment.max_trajectories` to limit Gowalla data loading, or process data in batches.

---

**For questions or issues, please open an issue on the repository.**

**如有问题或建议，请在仓库中提交 issue。**
