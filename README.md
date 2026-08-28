# PlanC Travel Planner — Product MVP

PlanC 将自然语言旅行需求转换为按天组织的行程计划，包含地点、到达时间、游玩时长和步行交通估算。LLM 负责理解并持续合并用户约束，地理聚类与路线算法负责生成确定性的日程，完整请求和结果保存到 SQLite。

## 当前可用入口

| 入口 | 启动位置 | 当前能力 |
|---|---|---|
| AI 对话 CLI | 仓库根目录 | 已连接 OpenAI API 和 Python 规划器，支持真正的多轮重规划 |
| Web 应用 | `web/` + 仓库根目录 | 已连接 Python API、OpenAI 意图解析、规划器和 SQLite，支持真实生成与多轮重规划 |
| 参数化 CLI | 仓库根目录 | 直接传入城市、天数、兴趣等结构化参数并输出 JSON |

配置好 `.env` 并同时启动 API 与 Web 服务后，可以直接在浏览器中生成和持续调整真实行程。Web 前端不再使用静态 mock 数据；页面中的日期、地点、路线、地图标记、调整消息和 JSON 导出都来自后端返回的结构化行程。

## 前后端连接概览

浏览器只调用 Python API，不直接接触 OpenAI API Key。后端负责意图解析、约束合并、路线规划和 SQLite 持久化；前端负责展示行程和把用户的首轮需求、后续调整发送给后端。

```text
Browser / Vinext web app
  -> POST /api/chat
  -> FastAPI planner.api
  -> TravelAgent + OpenAIIntentInterpreter
  -> create_trip_plan
  -> SQLite data/planner.db
```

当前 HTTP API：

| 方法 | 路径 | 用途 |
|---|---|---|
| `GET` | `/health` | 健康检查，返回 API 是否可用 |
| `POST` | `/api/chat` | 发送首轮需求或后续调整，返回 `session_id` 和规划结果 |
| `POST` | `/api/reset` | 清空指定浏览器会话的多轮上下文 |

`POST /api/chat` 请求体：

```json
{
  "message": "去广州玩四天，喜欢历史和美食，每天不要超过六小时",
  "session_id": null
}
```

后续调整时继续带上同一个 `session_id`：

```json
{
  "message": "每天十点再出发",
  "session_id": "上一轮返回的 session_id"
}
```

响应体中的 `turn.plan` 就是前端页面展示和导出的完整行程。

## 环境要求

- Python 3.10 或更高版本
- Node.js 22.13 或更高版本（仅运行 Web 前端时需要）
- pnpm（仅运行 Web 前端时需要）
- 一个可用的 OpenAI API Key，或 OpenAI 兼容服务的 API Key 和 Base URL

## 从零启动 AI 对话

以下命令都在仓库根目录执行。

### 1. 安装 Python 依赖

macOS / Linux：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Windows PowerShell：

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### 2. 配置 `.env`

首次配置时复制示例文件；如果已经有 `.env`，不要再次复制覆盖：

```bash
cp env.example .env
```

把占位符替换为真实配置：

```dotenv
LLM_PROVIDER=openai
OPENAI_API_KEY=你的真实_API_Key
OPENAI_BASE_URL=
LLM_MODEL=gpt-4o-mini
AGENT_MODEL=gpt-4o-mini
```

`AGENT_MODEL` 必须是当前 API 项目有权使用、并支持 Responses API Structured Outputs 的模型。若不设置，程序依次使用 `LLM_MODEL` 和代码中的默认模型。OpenAI SDK 从环境变量读取 API Key，Key 不要提交到 Git、写进前端代码或分享给他人。可在 [OpenAI API Keys](https://platform.openai.com/api-keys) 创建或管理密钥。

如果使用通用 OpenAI 兼容代理，还需按服务商说明配置。`OPENAI_BASE_URL`
会同时作用于 AI 对话 CLI 和参数化规划入口：

```dotenv
LLM_PROVIDER=openai
OPENAI_API_KEY=代理服务提供的_Key
OPENAI_BASE_URL=https://代理服务地址/v1
LLM_MODEL=代理支持的模型名
AGENT_MODEL=代理支持的模型名
```

AIHubMix 也可以使用独立变量，避免与已有的 OpenAI Key 混淆：

```dotenv
LLM_PROVIDER=aihubmix
AIHUBMIX_API_KEY=AIHubMix_Key
OPENAI_BASE_URL=https://aihubmix.com/v1
LLM_MODEL=AIHubMix_支持的模型名
AGENT_MODEL=AIHubMix_支持且兼容_Responses_API_的模型名
```

`LLM_PROVIDER=aihubmix` 时 `OPENAI_BASE_URL` 是必填项，程序会在缺失时
立即报错，防止把代理 Key 发送给 OpenAI 官方端点。

修改 `.env` 后需要停止并重新启动程序。仅有 ChatGPT 账号或订阅不等同于已经配置了可用的 API Key。

### 3. 启动可交互的旅行规划师

直接进入多轮对话：

```bash
python scripts/travel_agent.py
```

也可以带上第一条需求启动：

```bash
python scripts/travel_agent.py "去广州玩四天，喜欢历史和美食，每天不要超过六小时"
```

生成计划后可继续输入调整要求，Agent 会保留当前城市、天数、预算、兴趣和节奏等约束并重新规划：

```text
每天十点再出发
少安排一点博物馆，多去公园
改成三天，但保留轻松的节奏
```

- `/reset`：清空当前对话中的旅行约束
- `/quit`：退出
- `--json`：打印完整的结构化结果
- 生成的行程 JSON：默认保存到 `results/`
- 规划结果数据库：默认保存到 `data/planner.db`

## 本地联调 Web 前端

Web 页面通过 Python API 调用同一个 TravelAgent 和规划器。本地联调需要两个终端：一个跑后端 API，一个跑前端开发服务器。

终端 1，在仓库根目录启动后端：

```bash
source .venv/bin/activate
uvicorn planner.api:app --reload --host 127.0.0.1 --port 8000
```

可以先检查 API 是否正常：

```bash
curl http://127.0.0.1:8000/health
```

终端 2，启动前端：

```bash
cd web
pnpm install
pnpm dev
```

启动成功后，在浏览器打开终端输出的 Local 地址（Vinext 通常为 `http://localhost:3000`）。

前端默认连接 `http://localhost:8000`；需要使用其他 API 地址时，复制 `web/.env.example` 到 `web/.env.local` 并修改：

```dotenv
NEXT_PUBLIC_API_URL=https://你的-api-域名
```

当前页面可以进行以下本地交互：

- 切换行程日期和选中地点
- 点击地图标记
- 输入或点击建议消息并触发真实重规划
- 返回“新行程”输入页
- 导出完整行程 JSON
- 在窄屏设备上使用响应式布局

浏览器只接触 API 地址，不会获得 OpenAI API Key。多轮会话目前保存在 API 进程内存中，生成的完整计划会继续写入 `data/planner.db`。重启 API 会清空对话上下文，但不会删除已保存的计划。

若前端与 API 使用不同域名，把正式前端源站加入根目录 `.env` 的 `FRONTEND_ORIGINS`（多个地址用逗号分隔），否则浏览器会因为 CORS 拒绝请求。

Sites 只能托管 Web 前端；正式环境还需要将 Python API 部署到支持 Python 的服务，并把其 HTTPS 地址配置为 `NEXT_PUBLIC_API_URL`。不要把 OpenAI API Key 写入 `web/.env.local`，因为 `NEXT_PUBLIC_*` 变量会进入浏览器端 bundle。

生产构建检查：

```bash
cd web
pnpm build
pnpm start
```

## 参数化 CLI

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
  api.py                Web HTTP API、CORS 与多轮会话管理
  agent.py              自然语言意图解析和多轮对话状态
  models.py             产品输入输出模型
  product.py            产品规划流水线
  storage.py            SQLite 持久化
  data_loader.py        POI 与 Gowalla 数据加载
  clustering.py         地理分天和研究聚类算法
  routing.py            NN 与 2-opt 路线优化
  experiments.py        可选研究评估入口
scripts/
  plan_trip.py          产品 CLI
  travel_agent.py       AI 多轮对话 CLI
web/
  app/page.tsx          真实 API 驱动的 Web 应用
tests/
  test_api.py           API 会话复用与重置测试
  test_agent.py         对话状态和重规划测试
  test_product.py       产品端到端测试
```

## 验证

```bash
python -m unittest discover -s tests -v
```

## License

MIT，详见 [LICENSE](LICENSE)。
