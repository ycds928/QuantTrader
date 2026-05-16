# AGENTS.md — QuantFlow 个人量化交易平台

## 项目概览

前后端分离的个人量化交易 Web 平台。前端 Vite + React 19 + TypeScript SPA，后端 Python FastAPI + SQLAlchemy + MySQL 8.0。深色 TradingView 风格，中国惯例红涨绿跌。

## 技术栈

| 层 | 技术 |
|---|---|
| 前端框架 | Vite + React 19 + TypeScript 5 |
| UI/样式 | Tailwind CSS 4（深色主题 Token） + Lucide Icons |
| 状态管理 | Zustand |
| 路由 | React Router v7 |
| 图表 | lightweight-charts（K线）+ ECharts（通用） |
| HTTP 客户端 | axios |
| 后端框架 | FastAPI + uvicorn |
| ORM | SQLAlchemy 2.0 (async) + aiomysql |
| 配置 | pydantic-settings + .env |
| 数据库 | MySQL 8.0 |

## 项目结构

```
frontend/src/
├── common/              # 公共模块（专人维护）
│   ├── components/      # AppLayout, 通用组件
│   ├── hooks/           # useWebSocket 等
│   ├── utils/           # cn, request, format
│   ├── types/           # 全局类型
│   ├── styles/          # 全局样式
│   └── router/          # 路由注册
├── api-data/            # 模块1: API对接展示信息和数据
├── account-trading/     # 模块2: 帐户与交易对接
├── strategy-engine/     # 模块3: 策略引擎与策略管理
├── strategy-execution/  # 模块4: 策略执行与实时风控
├── review-analysis/     # 模块5: 复盘分析与策略优化
└── history-replay/      # 模块6: 历史回放策略模拟

backend/
├── common/              # 公共模块（专人维护）
│   ├── config.py        # pydantic-settings 配置
│   ├── database.py      # 数据库连接/会话
│   ├── dependencies.py  # 依赖注入
│   └── middleware/      # CORS 等
├── api_data/            # 模块1
├── account_trading/     # 模块2
├── strategy_engine/     # 模块3
├── strategy_execution/  # 模块4
├── review_analysis/     # 模块5
└── history_replay/      # 模块6
```

## 构建与运行

```bash
# 开发环境（前后端同时启动，端口 5000）
# .coze 配置会自动调用 .cozeproj/dev-start.sh

# 前端单独
cd frontend && pnpm dev --host 0.0.0.0 --port 5000

# 后端单独
cd backend && uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## 代码规范

- **前端**：TypeScript strict，路径别名 `@/` → `src/`，ESLint + Prettier
- **后端**：Python 3.12+，async/await 优先，类型注解必须
- **样式**：只使用 `globals.css` 中的 CSS 变量（`bg-surface-container-high`、`text-up`/`text-down`），禁止硬编码颜色
- **数字显示**：价格/数量/百分比使用 `font-mono-num` class（JetBrains Mono）
- **涨跌色**：中国惯例 `text-up`（红 #ef4444）/ `text-down`（绿 #22c55e）

## 模块协作规范

- 每个模块有独立文件夹，只修改自己文件夹中的文件
- 公共模块（`common/`）由专人维护，其他人不得修改
- API 前缀约定：`/api/{module_name}/...`
- 各模块路由在 `backend/main.py` 统一注册
- 各模块前端路由在 `frontend/src/common/router/routes.ts` 统一注册

## API 接口清单

| 路径 | 方法 | 模块 | 说明 |
|------|------|------|------|
| /api/health | GET | 公共 | 健康检查 |
| /api/api-data/symbols | GET | 模块1 | 交易对列表 |
| /api/api-data/kline | GET | 模块1 | K线数据 |
| /api/api-data/ticker | GET | 模块1 | 实时行情 |
| /api/account/balance | GET | 模块2 | 账户余额 |
| /api/account/positions | GET | 模块2 | 持仓列表 |
| /api/account/orders | GET | 模块2 | 订单列表 |
| /api/account/order | POST | 模块2 | 下单 |
| /api/strategy/list | GET | 模块3 | 策略列表 |
| /api/strategy/create | POST | 模块3 | 创建策略 |
| /api/strategy/{id} | GET | 模块3 | 策略详情 |
| /api/execution/status | GET | 模块4 | 执行状态 |
| /api/execution/risk-alerts | GET | 模块4 | 风控告警 |
| /api/execution/logs | GET | 模块4 | 执行日志 |
| /api/review/report | GET | 模块5 | 复盘报告 |
| /api/review/trades | GET | 模块5 | 交易记录 |
| /api/review/suggestions | GET | 模块5 | 优化建议 |
| /api/replay/start | POST | 模块6 | 启动回放 |
| /api/replay/session/{id} | GET | 模块6 | 回放会话 |
| /api/replay/trades/{id} | GET | 模块6 | 回放交易 |
