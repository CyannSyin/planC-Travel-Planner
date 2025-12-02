# 实验结果评估指南 / Experiment Results Evaluation Guide

## 📊 评估功能说明

### 1. 自动生成评估报告

运行实验后，系统会自动生成评估报告，包括：

- **总体统计**：POI 总数、天数、每天平均 POI 数
- **路线统计**：总路线长度、平均路线长度、时间效率、回溯比例
- **时间统计**：总浏览时长、每天平均浏览时长
- **实验详情**：聚类方法、路径规划方法、优化选项
- **对齐指标**：与真实行为的相似度（Jaccard、Overlap、DTW）
- **消融实验结果**：不同设置的对比

### 2. 如何查看评估结果

运行实验：
```bash
python -m planner.experiments
```

评估报告会在实验结束时自动显示。报告也会保存到：
- `results/evaluation_summary.csv` - CSV 格式

### 3. 评估指标说明

#### 路线效率指标
- **时间效率 (Time Efficiency)**：浏览时间 / (浏览时间 + 交通时间)
  - 范围：0-1，越高越好（接近 1 表示大部分时间在浏览，而不是在路上）
  
- **回溯比例 (Backtracking Ratio)**：实际路线长度 / 基线路线长度
  - 范围：≥0，接近 1.0 最好
  - < 1.0 表示比基线路线更短（更好）
  - > 1.0 表示有额外绕路

#### 聚类质量指标
- **Silhouette Score**：聚类质量指标
  - 范围：-1 到 1，越高越好
  - > 0.5：好的聚类
  - > 0.7：非常好的聚类

#### 对齐指标
- **Jaccard Similarity**：集合相似度
  - 范围：0-1，越高越好（表示与真实轨迹越相似）
  
- **Overlap Coefficient**：重叠系数
  - 范围：0-1，越高越好
  
- **DTW Distance**：动态时间规整距离
  - 范围：≥0，越低越好（表示路径顺序越相似）

---

## 🧹 数据清洗功能

### Unknown POI 名称处理

系统会自动处理名称为 "Unknown" 的 POI：

1. **自动生成名称**：根据类别生成有意义的名称
   - 例如：`tourism=museum` → "博物馆 (museum)"
   - `leisure=park` → "公园 (park)"

2. **过滤选项**：可以在配置中设置是否过滤 Unknown 名称的 POI
   ```python
   CONFIG.poi_filter.filter_unknown_names = True  # 过滤掉 Unknown
   ```

### 配置数据清洗

在 `planner/config.py` 中：
```python
@dataclass
class POIFilterConfig:
    filter_unknown_names: bool = True  # 是否过滤 Unknown 名称的 POI
```

---

## ⏰ 最大浏览时长限制

### 功能说明

可以设置每天的最大浏览时长，系统会自动：
1. 在分配 POI 到每天时应用时长限制
2. 按评分排序，优先选择高评分 POI
3. 确保每天的浏览时长不超过限制

### 配置方法

在 `planner/config.py` 中：

```python
@dataclass
class POIFilterConfig:
    max_visit_time_hours: Optional[float] = 8.0  # 每天最大浏览时长（小时）
```

或者在 `RoutingConfig` 中：

```python
@dataclass
class RoutingConfig:
    max_visit_time_hours: float = 8.0  # 每天最大浏览时长
```

### 示例

```python
# 设置为 8 小时/天
CONFIG.poi_filter.max_visit_time_hours = 8.0

# 设置为 6 小时/天
CONFIG.routing.max_visit_time_hours = 6.0

# 不限制（设置为 None）
CONFIG.poi_filter.max_visit_time_hours = None
```

---

## 📈 评估结果示例

运行实验后，你会看到类似以下输出：

```
=== EXPERIMENT RESULTS EVALUATION / 实验结果评估 ===

📊 Overall Statistics / 总体统计:
  Total POIs: 100
  Number of days: 5
  Average POIs per day: 20.0

🗺️  Route Statistics / 路线统计:
  Total route length: 514.87 km
  Average route length per day: 102.97 km
  Average time efficiency: 0.60
  Average backtracking ratio: 0.90
    (Lower is better, <1.0 means better than baseline)

⏰ Time Statistics / 时间统计:
  Total visit time: 94.0 hours
  Average visit time per day: 18.8 hours

🔬 Experiment Details / 实验详情:
  Clustering method: kmeans
  Clustering silhouette score: 0.334
  Routing method: nn
  Used 2-opt optimization: True
```

---

## 🔧 自定义评估

### 保存评估报告

评估报告会自动保存到 `results/evaluation_summary.csv`。你也可以在代码中手动保存：

```python
from planner.results_evaluation import evaluate_experiment_results, save_evaluation_report

summary = evaluate_experiment_results(...)
save_evaluation_report(summary, Path("my_results.csv"), format="csv")
```

### 导出 JSON 格式

```python
save_evaluation_report(summary, Path("results/evaluation_summary.json"), format="json")
```

---

## 💡 最佳实践

1. **合理设置时长限制**
   - 一般建议：6-8 小时/天
   - 包括交通时间的话，可设为 10 小时/天

2. **过滤 Unknown POI**
   - 建议开启 `filter_unknown_names = True`
   - 确保所有 POI 都有有意义的名称

3. **评估指标解读**
   - 时间效率 > 0.7：很好
   - 回溯比例 < 1.1：路线合理
   - Silhouette > 0.5：聚类质量好

4. **多次实验对比**
   - 保存多次实验的结果
   - 对比不同配置的效果
   - 选择最优配置

---

## 📝 配置示例

完整的配置示例（`planner/config.py`）：

```python
# 修改 POI 过滤配置
CONFIG.poi_filter.min_rating = 4.0
CONFIG.poi_filter.max_pois = 100
CONFIG.poi_filter.max_visit_time_hours = 8.0  # 8小时/天
CONFIG.poi_filter.filter_unknown_names = True

# 修改路径规划配置
CONFIG.routing.max_daily_hours = 10.0  # 包括交通时间
CONFIG.routing.max_visit_time_hours = 8.0  # 纯浏览时间
```

---

更多信息请参考主 README.md。

