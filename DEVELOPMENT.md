# DEVELOPMENT.md — QuantFlow 开发指南

## 架构概览

```
浏览器 → Vite Dev Server (:5000) → /api/* 代理 → FastAPI (:8000) → MySQL 8.0
                              → /ws/* 代理 → FastAPI WebSocket
```

- **前端**：单页应用（SPA），Vite 开发服务器代理 API 请求到后端
- **后端**：FastAPI 提供 REST API + WebSocket，SQLAlchemy 异步 ORM 操作 MySQL
- **生产环境**：前端构建为静态文件，由 FastAPI 托管

## 技术栈

| 层 | 技术 | 版本 |
|---|------|------|
| 前端框架 | Vite + React + TypeScript | React 19 / TS 6 / Vite 8 |
| 样式 | Tailwind CSS 4 + Design Token | 深色主题，CSS 变量体系 |
| 状态管理 | Zustand | 5.x |
| 路由 | React Router v7 | lazy load 各模块 |
| K线图表 | lightweight-charts | 5.x（TradingView 开源） |
| 通用图表 | ECharts + echarts-for-react | 6.x |
| HTTP | axios | 拦截器统一响应格式 |
| 图标 | Lucide React | — |
| 后端框架 | FastAPI + uvicorn | 0.115 / 0.32 |
| ORM | SQLAlchemy 2.0 (async) + aiomysql | — |
| 配置 | pydantic-settings + .env | — |
| 数据库 | MySQL 8.0 | utf8mb4 |
| 迁移 | Alembic | 1.14 |

## 前端开发

### 目录结构规范

每个模块的目录结构相同，以 `strategy-engine` 为例：

```
src/strategy-engine/
├── pages/          # 页面组件（与路由一一对应）
│   └── Strategies.tsx
├── components/     # 模块私有组件
├── hooks/          # 模块私有 Hook
├── api/            # API 请求函数
│   └── strategy.ts     # export function getStrategyList() { return request.get(...) }
└── types/          # 模块私有类型
    └── strategy.ts     # interface Strategy { ... }
```

### 公共模块（`src/common/`）

**由专人维护，其他模块开发者不得修改。** 如需公共能力，提 Issue 或联系维护者。

| 文件 | 说明 |
|------|------|
| `components/AppLayout.tsx` | 侧边栏 + 顶栏布局，所有页面套用 |
| `router/routes.ts` | 路由注册中心，新增页面在此 lazy import |
| `utils/request.ts` | axios 实例，baseURL `/api`，响应拦截器自动解包 `response.data` |
| `utils/cn.ts` | `clsx` + `tailwind-merge` 合并 class |
| `utils/format.ts` | 数字/价格/百分比/日期格式化函数 |
| `hooks/useWebSocket.ts` | WebSocket Hook，自动重连 |
| `types/api.ts` | `ApiResponse<T>` / `PaginatedResponse<T>` / 分页排序参数 |

### 新增页面流程

1. 在自己模块的 `pages/` 下创建页面组件
2. 在 `src/common/router/routes.ts` 注册路由（lazy import）
3. 在 `src/App.tsx` 的 `<Routes>` 中添加 `<Route>`
4. 如需侧边栏导航入口，联系公共模块维护者修改 `AppLayout.tsx`

### API 请求

```typescript
import request from '@/common/utils/request'
import type { ApiResponse } from '@/common/types'

// GET
const res = await request.get<ApiResponse<Symbol[]>>('/api-data/symbols')

// POST
const res = await request.post<ApiResponse<Order>>('/account/order', {
  symbol: 'BTC/USDT', side: 'buy', amount: 0.01
})
```

`request` 拦截器已自动解包，`res` 直接就是 `ApiResponse<T>` 结构。

### 图表使用

**K线图**（lightweight-charts）：
```typescript
import { createChart } from 'lightweight-charts'
// 在 useEffect 中初始化，详见 lightweight-charts 文档
```

**通用图表**（ECharts）：
```typescript
import ReactECharts from 'echarts-for-react'
<ReactECharts option={{ ... }} style={{ height: 300 }} />
```

### 样式系统

所有样式通过 `src/index.css` 的 `@theme` 定义 CSS 变量，组件中使用语义化 class：

| 场景 | class | 说明 |
|------|-------|------|
| 页面背景 | `bg-background` | 最深层 #0a0a0f |
| 卡片/容器 | `bg-surface-container-high` | 卡片底色 #1a1a2e |
| 输入框/表格行 | `bg-surface-container` | 中层 #16162a |
| 文字主色 | `text-on-surface` | #e5e7eb |
| 文字次色 | `text-on-surface-variant` | #9ca3af |
| 涨（红） | `text-up` | #ef4444 |
| 跌（绿） | `text-down` | #22c55e |
| 数字等宽 | `font-mono-num` | JetBrains Mono + tabular-nums |
| 卡片阴影 | `shadow-card` | 深色主题适配 |
| 浮层阴影 | `shadow-float` | 弹窗/下拉 |

**禁止硬编码颜色**。如需新色值，先在 `@theme` 中定义变量。

## 后端开发

### 目录结构规范

每个模块目录结构相同，以 `strategy_engine` 为例：

```
backend/strategy_engine/
├── __init__.py
├── router.py       # APIRouter，定义路由
├── models.py       # SQLAlchemy Model（新建）
├── schemas.py      # Pydantic 请求/响应 Schema（新建）
├── service.py      # 业务逻辑层（新建）
└── dependencies.py # 模块级依赖注入（可选）
```

### 公共模块（`common/`）

| 文件 | 说明 |
|------|------|
| `config.py` | `Settings` 类，从 .env 读取配置，`get_settings()` 缓存单例 |
| `database.py` | `Base` / `TimestampMixin` / `engine` / `async_session` / `get_db()` |
| `dependencies.py` | 公共依赖注入函数 |
| `middleware/cors.py` | CORS 中间件配置 |

### 新增接口流程

1. 在自己模块的 `router.py` 中添加路由函数
2. 如需数据库，创建 `models.py`（继承 `Base` + `TimestampMixin`）
3. 创建 `schemas.py`（Pydantic BaseModel，请求/响应分离）
4. 创建 `service.py`（业务逻辑，注入 `get_db` 依赖）
5. 路由已通过 `main.py` 的 `include_router` 自动注册

### 统一响应格式

所有接口必须返回统一格式：

```python
# 成功
return {"success": True, "data": result, "message": "操作成功"}

# 失败（HTTP 异常）
raise HTTPException(status_code=400, detail={"success": False, "message": "参数错误"})
```

前端 `ApiResponse<T>` 对应此结构。

### 数据库操作

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from common.database import get_db, Base, TimestampMixin

class Strategy(Base, TimestampMixin):
    __tablename__ = "strategies"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)

@router.get("/list")
async def list_strategies(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Strategy))
    return {"success": True, "data": result.scalars().all()}
```

### 配置读取

所有配置通过 `common/config.py` 的 `Settings` 类读取 `.env`：

```python
from common.config import get_settings

settings = get_settings()
db_url = settings.DATABASE_URL
```

新增配置项：在 `Settings` 类中添加字段并设默认值，同时在 `.env.example` 中补上说明。

### API 路由前缀约定

| 模块 | 前缀 | 示例 |
|------|------|------|
| 行情数据 | `/api/api-data` | `/api/api-data/symbols` |
| 帐户交易 | `/api/account` | `/api/account/balance` |
| 策略引擎 | `/api/strategy` | `/api/strategy/list` |
| 执行风控 | `/api/execution` | `/api/execution/status` |
| 复盘分析 | `/api/review` | `/api/review/report` |
| 历史回放 | `/api/replay` | `/api/replay/start` |

### 数据库迁移

```bash
cd backend

# 生成迁移文件
alembic revision --autogenerate -m "add strategies table"

# 执行迁移
alembic upgrade head

# 回滚
alembic downgrade -1
```

## 协作规范

### 模块所有权

| 模块 | 前端目录 | 后端目录 | 负责人 |
|------|----------|----------|--------|
| 公共 | `src/common/` | `common/` | 专人维护 |
| 行情数据 | `src/api-data/` | `api_data/` | 开发者 A |
| 帐户交易 | `src/account-trading/` | `account_trading/` | 开发者 B |
| 策略引擎 | `src/strategy-engine/` | `strategy_engine/` | 开发者 C |
| 执行风控 | `src/strategy-execution/` | `strategy_execution/` | 开发者 D |
| 复盘分析 | `src/review-analysis/` | `review_analysis/` | 开发者 E |
| 历史回放 | `src/history-replay/` | `history_replay/` | 开发者 F |

### Git 协作规则

1. **只修改自己模块的文件**，禁止修改其他模块目录
2. **公共模块需提 PR**，由专人 Review 后合并
3. 功能开发在 feature 分支，完成后提 PR 到 main
4. 提交信息遵循 Conventional Commits：`feat(strategy): 添加策略创建接口`
5. 路由注册（`routes.ts` / `main.py`）如需修改，在 PR 中说明
