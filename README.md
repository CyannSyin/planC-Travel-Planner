# PlanC Travel Planner — Product MVP

PlanC 将城市 POI 转换成可以直接消费的多日旅行计划。产品入口接收城市、天数、偏好和每日时间预算，返回按天组织、包含到达时间和交通估算的 JSON，并将完整请求与结果保存到 SQLite。

## AI Native 对话入口

`dev/product-ai-native` 分支提供自然语言、多轮重规划入口。LLM 负责理解并持续合并用户约束，原有地理聚类和路线算法作为确定性规划工具执行。

先在 `.env` 中配置 `OPENAI_API_KEY`（OpenAI 兼容代理也可以同时配置 `OPENAI_BASE_URL`），然后运行：

```bash
python scripts/travel_agent.py "去广州玩四天，喜欢历史和美食，每天不要超过六小时"
```

生成计划后可以继续输入：

```text
每天十点再出发
少安排一点博物馆，多去公园
改成三天，但保留轻松的节奏
```

Agent 会保留城市、预算、兴趣等上下文，合并新约束后重新调用规划引擎。使用 `/reset` 清空上下文，使用 `/quit` 退出。完整对话输出可以通过 `--json` 查看。

## 快速开始

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp env.example .env
```

使用已有的广州 LLM 缓存生成四日行程：

```bash
python scripts/plan_trip.py \
  --city guangzhou \
  --days 4 \
  --source llm \
  --max-pois 24 \
  --max-daily-hours 8 \
  --output results/guangzhou-plan.json
```

使用自己的 OSM 兼容 POI 文件：

```bash
python scripts/plan_trip.py \
  --city "Shanghai" \
  --days 3 \
  --source osm \
  --poi-file data/city_pois.csv
```

如果对应请求的 LLM 缓存不存在，需要在 `.env` 中配置模型提供商和 API Key。缓存键包含城市、天数、偏好、预算、兴趣和 POI 数量，避免错误复用另一位用户的推荐结果。也可以通过 `scripts/download_data.py` 准备 OSM 数据。

## 产品 IO

### 输入

CLI 与 `PlanRequest` 使用同一组字段：

| 字段 | 类型 | 必需 | 默认值 | 含义 |
|---|---:|:---:|---|---|
| `city` | string | 是 | — | 目标城市 |
| `num_days` / `--days` | integer | 是 | — | 旅行天数，1–14 |
| `source` | `llm` / `osm` | 否 | `llm` | POI 来源 |
| `preferences` | string | 否 | null | 自然语言偏好 |
| `budget` | string | 否 | null | 预算描述 |
| `interests` | string[] | 否 | `[]` | 兴趣标签 |
| `max_pois` | integer | 否 | `days × 6` | 最大候选 POI 数 |
| `min_rating` | number | 否 | `3.5` | 最低评分 |
| `max_daily_hours` | number | 否 | `8` | 每日交通加游玩的总时间上限 |
| `start_time` | `HH:MM` | 否 | `09:00` | 每日起始时间 |
| `walking_speed_kmh` | number | 否 | `4.0` | 步行速度，用于交通时间估算 |
| `poi_file` | path | OSM 时可选 | `data/city_pois.csv` | 自定义 POI CSV |

POI CSV 至少需要：

```text
poi_id,lat,lon,category,rating,duration_min
```

可选字段为 `name,popularity,opening_hours`。

Python 调用方式：

```python
from planner.models import PlanRequest
from planner.product import create_trip_plan
from planner.storage import PlanRepository

request = PlanRequest(
    city="guangzhou",
    num_days=4,
    source="llm",
    interests=["museum", "food", "park"],
    max_daily_hours=8,
)
plan = create_trip_plan(request, repository=PlanRepository("data/planner.db"))
result = plan.to_dict()
```

### 处理流程

```text
PlanRequest
  → 参数校验
  → LLM 缓存/API 或 OSM CSV
  → 字段标准化、坐标校验、去重、评分过滤
  → 地理 KMeans 分天
  → 每天从最高评分 POI 出发
  → Nearest Neighbor 生成初始路线
  → 2-opt 局部搜索缩短路线
  → 按 Haversine 距离估算步行时间
  → 在每日总时间预算内选择 POI 并生成时刻表
  → TripPlan JSON
  → SQLite 持久化
```

### 输出

标准输出和 `--output` 文件都是同一份 JSON：

```json
{
  "plan_id": "uuid",
  "city": "guangzhou",
  "num_days": 4,
  "source": "llm",
  "algorithm": {
    "day_partition": "geographic KMeans on local kilometer coordinates",
    "daily_route": "highest-rated start + nearest neighbor + 2-opt",
    "distance": "Haversine great-circle distance",
    "time_budget": "greedy inclusion of travel and visit time"
  },
  "days": [
    {
      "day": 1,
      "visits": [
        {
          "poi_id": "llm_guangzhou_1",
          "name": "Canton Tower",
          "arrival_time": "09:00",
          "departure_time": "11:00",
          "travel_from_previous_km": 0.0,
          "travel_from_previous_minutes": 0.0
        }
      ],
      "route_length_km": 4.2,
      "visit_minutes": 300,
      "travel_minutes": 63,
      "total_minutes": 363,
      "skipped_poi_ids": []
    }
  ],
  "total_pois": 18,
  "total_route_length_km": 21.4,
  "total_minutes": 1700,
  "created_at": "UTC ISO-8601"
}
```

实际 `visits` 还包含类别、经纬度、评分、开放时间和游玩时长。

失败时 CLI 向 stderr 返回：

```json
{"error": "错误原因"}
```

并以非零状态码退出。

## 算法

### 地理 KMeans 分天

经纬度先投影到以公里为单位的局部平面，再执行 NumPy 实现的 KMeans++。评分、热度和游玩时长不参与空间距离，避免“属性相似但相距很远”的 POI 被分到同一天。算法使用固定随机种子、20 次初始化和最多 100 次迭代，结果可复现。scikit-learn 仅供研究实验入口使用，不阻塞产品主流程。

### Nearest Neighbor + 2-opt

每天以评分最高的 POI 为起点，最近邻算法每次选择距离当前位置最近的未访问 POI。随后执行 2-opt，通过反转路线片段消除绕路。2-opt 只比较发生变化的边，不再为每个候选方案重复计算整条路线。

### 距离与时间预算

地点间距离使用 Haversine 大圆距离。交通时间为 `距离 / 步行速度`。系统按路线顺序贪心加入 POI，保证“交通时间 + 游玩时间”不超过每日上限；未能加入的 POI 返回在 `skipped_poi_ids`。

当前版本会把 `opening_hours` 返回给调用方，但尚未解析复杂营业时间规则，也没有接入道路网络和公共交通 API。

## 数据库

MVP 使用 Python 标准库内置的 SQLite，默认文件为 `data/planner.db`，不需要单独部署数据库服务。

表结构：

```sql
CREATE TABLE trip_plans (
    plan_id TEXT PRIMARY KEY,
    city TEXT NOT NULL,
    num_days INTEGER NOT NULL,
    source TEXT NOT NULL,
    request_json TEXT NOT NULL,
    result_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
```

选择“请求快照 + 结果快照”是为了让 MVP 可以直接回放历史计划，并避免产品模型仍在快速变化时频繁迁移多张关系表。`PlanRepository` 隔离了存储逻辑，后续可替换为 PostgreSQL。

## 研究评估工具

原有聚类比较、路线指标、Gowalla 行为对齐和 POI 热度对齐仍可通过以下入口运行：

```bash
python -m planner.experiments
```

产品主流程不依赖 Gowalla。消融实验及其配置、执行脚本、报告字段和可视化已经删除。

## 目录

```text
planner/
  models.py             产品输入输出模型
  product.py            产品规划流水线
  storage.py            SQLite 持久化
  data_loader.py        POI 与 Gowalla 数据加载
  clustering.py         地理分天和研究聚类算法
  routing.py            NN 与 2-opt 路线优化
  experiments.py        可选研究评估入口
scripts/
  plan_trip.py          产品 CLI
tests/
  test_product.py       产品端到端测试
```

## 验证

```bash
python -m unittest discover -s tests -v
```

## License

MIT，详见 [LICENSE](LICENSE)。
