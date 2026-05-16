# 个人量化交易平台 — 设计方案

## 概述

前后端分离的个人量化交易平台 Web 应用。后端 Python FastAPI 提供 REST API + WebSocket 实时推送，前端 Vite + React SPA 实现传统后台管理界面，集成 lightweight-charts（K线）与 ECharts（收益/统计图表）。数据库 MySQL 8.0，.env 管理配置。项目按 6 大模块划分独立文件夹，支持多人 Git 协作，公共部分专人维护。

## 技术方案

| 维度 | 选择 | 理由 |
|------|------|------|
| 前端框架 | Vite + React 19 + TypeScript | SPA 场景，HMR 快，轻量 |
| UI 组件 | shadcn/ui (Radix) + Tailwind CSS 4 | 后台管理风格，组件丰富 |
| K线图表 | lightweight-charts (TradingView) | 金融图表专业度最高 |
| 通用图表 | ECharts | 收益曲线/饼图/热力图等覆盖全 |
| 状态管理 | Zustand | 轻量，适合模块独立开发 |
| 路由 | React Router v7 | SPA 标准路由 |
| 后端框架 | FastAPI | 异步高性能，原生 WebSocket，自动 OpenAPI 文档 |
| ORM | SQLAlchemy 2.0 (async) | Python 主流 ORM，支持异步 MySQL |
| 数据库 | MySQL 8.0 | 用户指定 |
| 配置管理 | pydantic-settings + .env | 类型安全的环境变量读取 |
| 实时通信 | FastAPI WebSocket | 行情推送、策略状态、风控告警 |
| 进程管理 | uvicorn | ASGI 服务器，支持热重载 |

## 前端样式体系

### 设计方向

以 **TradingView 深色风格** 为基调，K线/图表区直接沿用 lightweight-charts/ECharts 的暗色主题；非图表区域（侧栏、表单、表格、卡片等）通过 shadcn/ui 暗色主题 + 定制 Design Token 统一视觉语言，确保整体一致。

### 核心样式 Token

| Token | 值 | 用途 |
|-------|-----|------|
| 背景层级 | `#0a0a0f` → `#12121a` → `#1a1a2e` → `#242438` | 页面底 → 容器 → 卡片 → 悬浮层，4级深度 |
| 主色调 | `#3b82f6`（蓝） | 按钮/链接/选中态/聚焦环 |
| 涨色 | `#ef4444`（红） | 中国惯例：红涨 |
| 跌色 | `#22c55e`（绿） | 中国惯例：绿跌 |
| 告警色 | `#f59e0b`（橙）/ `#ef4444`（红） | warning / critical |
| 文字层级 | `#e5e7eb` → `#9ca3af` → `#6b7280` | 主文字 → 次文字 → 禁用/提示 |
| 边框 | `rgba(255,255,255,0.08)` | 卡片边框、分割线 |
| 数字字体 | JetBrains Mono | 所有价格、数量、百分比、PnL 数值 |
| UI 字体 | Inter | 标签、按钮、导航等常规文字 |

### 非图表组件样式规范

| 组件 | 样式要点 |
|------|---------|
| **侧栏** | 深底色 `#0a0a0f`，图标 + 文字导航，当前项左侧蓝色竖条 + 浅底高亮，可折叠 |
| **顶部栏** | 深底色，右侧全局搜索 + 通知铃铛 + 连接状态指示灯 |
| **卡片** | 圆角 `rounded-lg`，`#1a1a2e` 底 + `rgba(255,255,255,0.08)` 边框，轻微 `shadow-lg` |
| **表格** | 紧凑行高 `h-10`，斑马纹 `#12121a` / `#16162a`，悬停行 `#242438`，数字右对齐 + Mono 字体 |
| **表单** | 输入框深底 `#12121a` + 蓝色聚焦环，标签小号灰色，分组用卡片 + 标题 |
| **按钮** | 主按钮蓝底白字，次要按钮透明 + 边框，危险操作红色，悬停加深 |
| **状态标签** | 圆角药丸形，running=蓝底、stopped=灰底、error=红底、profit=红字、loss=绿字 |
| **数字显示** | 涨跌数字后跟涨跌幅百分比，正数红色 + 前缀 `+`，负数绿色 + 前缀 `-` |
| **K线图区** | lightweight-charts 暗色主题，十字光标白色半透明，MA 线用标准配色 |
| **ECharts 图** | 统一暗色背景，收益曲线蓝色面积图，热力图红绿渐变，饼图冷色系 |

### shadcn/ui 定制策略

1. 使用 `theme.sh` 脚本初始化为暗色主题（`--default-dark`）
2. 选择 `tech-purple` 或 `neutral` 色系作为基底（避免 AI 蓝紫渐变）
3. 初始化后手动覆盖 `globals.css`：将上述 Token 写入 CSS 变量
4. 额外注册自定义 utility：`text-up`（涨色）、`text-down`（跌色）、`font-mono-num`（数字字体）
5. 所有 shadcn 组件默认暗色适配，无需额外处理

## 目录结构

```
quant-trading/
├── frontend/                              # 前端应用
│   ├── public/
│   ├── src/
│   │   ├── common/                        # 【公共模块 - 专人维护】
│   │   │   ├── components/                # 布局组件 (AppLayout, Sidebar, Header, PageContainer)
│   │   │   ├── hooks/                     # 公共 Hooks (useWebSocket, useAuth, useTheme)
│   │   │   ├── utils/                     # 工具函数 (request, format, storage)
│   │   │   ├── types/                     # 全局类型定义
│   │   │   ├── styles/                    # 全局样式 + Tailwind 配置
│   │   │   └── router/                    # 路由注册中心 (汇总各模块路由)
│   │   ├── api-data/                      # 模块1: API对接展示信息和数据
│   │   │   ├── pages/
│   │   │   ├── components/
│   │   │   ├── hooks/
│   │   │   ├── api/
│   │   │   └── types/
│   │   ├── account-trading/               # 模块2: 帐户与交易对接
│   │   │   ├── pages/
│   │   │   ├── components/
│   │   │   ├── hooks/
│   │   │   ├── api/
│   │   │   └── types/
│   │   ├── strategy-engine/               # 模块3: 策略引擎与策略管理
│   │   │   ├── pages/
│   │   │   ├── components/
│   │   │   ├── hooks/
│   │   │   ├── api/
│   │   │   └── types/
│   │   ├── strategy-execution/            # 模块4: 策略执行与实时风控
│   │   │   ├── pages/
│   │   │   ├── components/
│   │   │   ├── hooks/
│   │   │   ├── api/
│   │   │   └── types/
│   │   ├── review-analysis/              # 模块5: 复盘分析与策略优化
│   │   │   ├── pages/
│   │   │   ├── components/
│   │   │   ├── hooks/
│   │   │   ├── api/
│   │   │   └── types/
│   │   ├── history-replay/                # 模块6: 历史回放策略模拟
│   │   │   ├── pages/
│   │   │   ├── components/
│   │   │   ├── hooks/
│   │   │   ├── api/
│   │   │   └── types/
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── index.html
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   └── package.json
├── backend/                               # 后端应用
│   ├── common/                            # 【公共模块 - 专人维护】
│   │   ├── database.py                    # 数据库连接与会话管理
│   │   ├── config.py                      # pydantic-settings 读取 .env
│   │   ├── dependencies.py                # FastAPI 依赖注入 (db_session, etc.)
│   │   ├── middleware/                     # CORS, 日志, 错误处理
│   │   ├── utils/                         # 工具函数 (时间, 加密, 序列化)
│   │   └── base_model.py                  # SQLAlchemy Base, 公共字段 Mixin
│   ├── api_data/                          # 模块1: API对接展示信息和数据
│   │   ├── router.py
│   │   ├── service.py
│   │   ├── model.py
│   │   └── schema.py
│   ├── account_trading/                   # 模块2: 帐户与交易对接
│   │   ├── router.py
│   │   ├── service.py
│   │   ├── model.py
│   │   └── schema.py
│   ├── strategy_engine/                   # 模块3: 策略引擎与策略管理
│   │   ├── router.py
│   │   ├── service.py
│   │   ├── model.py
│   │   └── schema.py
│   ├── strategy_execution/                # 模块4: 策略执行与实时风控
│   │   ├── router.py
│   │   ├── service.py
│   │   ├── model.py
│   │   └── schema.py
│   ├── review_analysis/                   # 模块5: 复盘分析与策略优化
│   │   ├── router.py
│   │   ├── service.py
│   │   ├── model.py
│   │   └── schema.py
│   ├── history_replay/                    # 模块6: 历史回放策略模拟
│   │   ├── router.py
│   │   ├── service.py
│   │   ├── model.py
│   │   └── schema.py
│   ├── main.py                            # FastAPI 入口, 注册路由和中间件
│   ├── requirements.txt
│   └── alembic/                           # 数据库迁移
│       └── ...
├── .env                                   # 环境变量 (不入库)
├── .env.example                           # 环境变量模板 (入库)
├── .coze                                  # 部署配置
└── README.md
```

## 功能模块

### 公共模块 (common/) — 专人维护

**前端 common/**：AppLayout（左侧 Sidebar + 顶部 Header + 内容区）、路由注册中心（各模块导出路由数组，common 统一注册）、公共组件（KlineChart 封装、ECharts 封装、DataTable、StatusBadge）、useWebSocket Hook、API 请求封装（axios 实例 + 拦截器）、全局类型。

**后端 common/**：FastAPI 应用工厂、数据库连接池（async SQLAlchemy）、pydantic-settings 配置类、公共依赖注入、CORS/日志中间件、SQLAlchemy Base + 时间戳 Mixin、分页/响应封装。

### 模块1: api-data — API对接展示信息和数据

**职责**：对接交易所 API，拉取行情/深度/资金费率等数据，持久化并提供查询接口；前端展示实时行情、K线图、深度图。

**后端关键逻辑**：
- 交易所 API 适配层（Binance/OKX 等），统一数据格式
- 定时任务拉取 K线/Ticker 数据
- WebSocket 推送实时 Ticker
- 历史数据查询（分页、时间范围过滤）

**数据表**：
```sql
-- 交易对
symbol (id, exchange, name, base_currency, quote_currency, status, created_at)

-- K线数据
kline (id, symbol_id, timeframe, open_time, open, high, low, close, volume, created_at)

-- Ticker
ticker (id, symbol_id, last_price, bid, ask, volume_24h, change_24h, updated_at)

-- API配置
api_config (id, exchange, api_key_encrypted, api_secret_encrypted, passphrase_encrypted, is_valid, updated_at)
```

### 模块2: account-trading — 帐户与交易对接

**职责**：管理交易所账户连接，执行下单/撤单，同步持仓和余额。

**后端关键逻辑**：
- 账户余额同步（定时/手动）
- 下单/撤单/批量下单接口
- 持仓同步与聚合
- 订单状态 WebSocket 推送

**数据表**：
```sql
-- 账户
account (id, exchange, name, api_key_encrypted, api_secret_encrypted, passphrase_encrypted, balance_json, status, created_at)

-- 订单
order (id, account_id, symbol, side, type, price, quantity, filled_quantity, status, exchange_order_id, strategy_id, created_at, updated_at)

-- 持仓
position (id, account_id, symbol, side, quantity, entry_price, unrealized_pnl, leverage, updated_at)
```

### 模块3: strategy-engine — 策略引擎与策略管理

**职责**：策略的创建、编辑、参数配置、版本管理、启停控制。

**后端关键逻辑**：
- 策略 CRUD（代码存储、参数 schema 定义）
- 策略版本管理（git-like diff 存储）
- 策略参数校验（pydantic schema 驱动）
- 策略启停状态机

**数据表**：
```sql
-- 策略
strategy (id, name, description, code, parameters_json, version, status[draft/active/stopped], created_at, updated_at)

-- 策略版本
strategy_version (id, strategy_id, version, code, parameters_json, changelog, created_at)

-- 策略关联交易对
strategy_symbol (id, strategy_id, symbol_id)
```

### 模块4: strategy-execution — 策略执行与实时风控

**职责**：策略运行时管理、实时风控规则执行、告警通知。

**后端关键逻辑**：
- 策略执行引擎（加载策略代码，驱动信号产生）
- 实时风控：最大回撤、单笔止损、持仓上限、频率限制
- 风控告警 WebSocket 推送
- 执行日志记录

**数据表**：
```sql
-- 策略执行实例
execution (id, strategy_id, account_id, started_at, stopped_at, status[running/stopped/error], pnl, error_message)

-- 风控规则
risk_rule (id, name, rule_type[max_drawdown/stop_loss/position_limit/frequency], threshold_json, enabled, created_at)

-- 风控告警
risk_alert (id, execution_id, rule_id, level[warning/critical], message, triggered_at, acknowledged)

-- 执行日志
execution_log (id, execution_id, timestamp, level, message, data_json)
```

### 模块5: review-analysis — 复盘分析与策略优化

**职责**：交易复盘、绩效分析、可视化报告、优化建议。

**后端关键逻辑**：
- 收益曲线计算（累计/年化/夏普/最大回撤）
- 交易统计（胜率/盈亏比/持仓时间分布）
- 策略对比分析
- 按日/周/月聚合

**数据表**：
```sql
-- 复盘报告
review_report (id, strategy_id, period_start, period_end, total_pnl, win_rate, sharpe_ratio, max_drawdown, trade_count, created_at)

-- 交易记录（从 order 聚合）
trade_record (id, strategy_id, symbol, side, entry_price, exit_price, quantity, pnl, pnl_pct, entry_time, exit_time, duration_seconds)

-- 优化建议
optimization_suggestion (id, strategy_id, report_id, category, description, data_json, created_at)
```

### 模块6: history-replay — 历史回放策略模拟

**职责**：用历史数据回放策略运行，模拟交易结果，对比回测。

**后端关键逻辑**：
- 历史数据回放引擎（按时间步进推送 K线）
- 模拟撮合（虚拟下单/成交）
- 回放速度控制（1x/5x/10x/max）
- 回放结果对比

**数据表**：
```sql
-- 回放会话
replay_session (id, strategy_id, symbol_id, timeframe, start_time, end_time, speed, status[pending/running/completed/failed], initial_capital, final_capital, created_at)

-- 回放交易
replay_trade (id, session_id, symbol, side, price, quantity, pnl, timestamp)

-- 回放快照（关键节点状态）
replay_snapshot (id, session_id, timestamp, capital, position_json, equity_curve_json)
```

## .env 配置项

```env
# MySQL
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=quant_user
MYSQL_PASSWORD=
MYSQL_DATABASE=quant_trading

# 服务
API_PORT=5000
API_CORS_ORIGINS=http://localhost:5000

# 交易所 API（按需填）
BINANCE_API_KEY=
BINANCE_API_SECRET=
OKX_API_KEY=
OKX_API_SECRET=
OKX_PASSPHRASE=

# 安全
ENCRYPTION_KEY=
```

## 是否有原型设计

是

## 实施步骤

1. **原型设计** — 加载 design-canvas 技能，完成全部页面的原型 HTML 设计，涵盖 Dashboard、6 大模块的典型页面、公共布局。完成后提示用户验收确认。涉及文件：原型 HTML 页面集。

2. **项目骨架搭建** — 创建前端 Vite + React + TypeScript 项目和后端 FastAPI 项目结构；建立 .coze 自定义配置（Python + Node 双栈）；创建 .env/.env.example；初始化 Git。涉及文件：frontend/package.json、backend/requirements.txt、.coze。

3. **公共模块实现** — 前端：AppLayout（Sidebar + Header + Content）、路由注册中心、KlineChart/EChartsChart 封装、API 请求层、useWebSocket Hook。后端：FastAPI 应用工厂、数据库连接、配置类、Base Model、中间件、统一响应格式。涉及文件：frontend/src/common/、backend/common/、backend/main.py。

4. **模块1 + 模块2 实现** — API对接展示（行情列表、K线图页面、深度图、API配置管理）+ 帐户交易对接（账户管理、下单、持仓、订单列表）。涉及文件：frontend/src/api-data/、frontend/src/account-trading/、backend/api_data/、backend/account_trading/。

5. **模块3 + 模块4 实现** — 策略引擎（策略列表、策略编辑器、参数配置、版本管理）+ 策略执行与风控（执行仪表盘、实时风控监控、告警面板）。涉及文件：frontend/src/strategy-engine/、frontend/src/strategy-execution/、backend/strategy_engine/、backend/strategy_execution/。

6. **模块5 + 模块6 实现** — 复盘分析（绩效面板、收益曲线、交易复盘、优化建议）+ 历史回放（回放配置、回放控制台、结果对比）。涉及文件：frontend/src/review-analysis/、frontend/src/history-replay/、backend/review_analysis/、backend/history_replay/。

7. **数据库与集成测试** — 创建 Alembic 迁移脚本，初始化数据库表结构；前端 Vite 代理配置打通前后端联调；接口冒烟测试。涉及文件：backend/alembic/、frontend/vite.config.ts。

8. **验收与交付** — 全链路测试、日志健康检查、AGENTS.md 生成、最终交付。涉及文件：AGENTS.md。

## 页面规格

##### @nav(web-topbar)
> type: topbar
> platform: web

- @page(/) 首页
- @page(/api-data) 行情数据
- @page(/account) 账户交易
- @page(/strategies) 策略管理
- @page(/execution) 执行监控
- @page(/review) 复盘分析
- @page(/replay) 历史回放

##### @page(/) 首页仪表盘

**核心职责**：全局概览，关键指标一目了然。
**访问路径**：导航直达。
**布局**：顶部 4 个指标卡（总资产/当日盈亏/运行策略数/活跃告警数）→ 中部左侧资产曲线（ECharts）+ 右侧持仓分布（饼图）→ 底部最近交易记录表 + 告警列表。
**列表项字段**（交易记录）：交易对 / 方向 / 价格 / 数量 / 盈亏 / 时间
**列表项字段**（告警列表）：级别 / 策略 / 规则 / 消息 / 时间

**交互说明**

| 元素 | 动作 | 响应 | 传参 | 备注 |
|------|------|------|------|------|
| Logo | 点击 | 跳转 @page(/) | — | — |
| 指标卡"运行策略数" | 点击 | 跳转 @page(/execution) | — | — |
| 指标卡"活跃告警" | 点击 | 跳转 @page(/execution) 滚动到告警区 | — | — |
| 交易记录行 | 点击 | 跳转 @page(/account) | — | — |
| 告警行 | 点击 | 跳转 @page(/execution) | — | — |

##### @page(/api-data) 行情数据

**核心职责**：展示实时行情列表，进入交易对详情。
**访问路径**：导航直达。
**布局**：顶部搜索栏 + 交易所筛选下拉 → 主内容区自选行情表格（实时价格闪烁更新）→ 右侧收藏的交易对快捷卡片。
**列表项字段**：交易对 / 最新价 / 24h涨跌 / 24h成交量 / 24h最高 / 24h最低 / 操作

**交互说明**

| 元素 | 动作 | 响应 | 传参 | 备注 |
|------|------|------|------|------|
| 搜索框 | 输入 | 实时过滤行情列表 | — | 防抖 300ms |
| 交易所筛选 | 选择 | 过滤对应交易所行情 | — | — |
| 行情行 | 点击 | 跳转 @page(/symbol-detail)?symbol_id | symbol_id | — |
| 收藏按钮 | 点击 | 切换收藏状态 | — | — |
| Logo | 点击 | 跳转 @page(/) | — | — |

##### @page(/symbol-detail) 交易对详情

**核心职责**：K线图 + 深度图 + 实时 Ticker，核心行情查看页面。
**访问路径**：从 @page(/api-data) 行点击进入。
**布局**：顶部交易对名称 + 实时价格 + 涨跌幅 → 主区域左侧 K线图（lightweight-charts，支持 1m/5m/15m/1h/4h/1d 切换 + 十字光标 + 技术指标叠加）→ 右侧上方深度图（ECharts）→ 右侧下方最近成交列表。
**列表项字段**（成交列表）：时间 / 方向 / 价格 / 数量

**交互说明**

| 元素 | 动作 | 响应 | 传参 | 备注 |
|------|------|------|------|------|
| 周期切换 | 点击 | 切换K线周期，重新加载数据 | — | 1m/5m/15m/1h/4h/1d |
| K线图 | 拖拽/缩放 | 平移/缩放时间轴 | — | — |
| 返回按钮 | 点击 | 返回 @page(/api-data) | — | — |
| Logo | 点击 | 跳转 @page(/) | — | — |

##### @page(/account) 账户管理

**核心职责**：管理交易所账户、查看余额、下单交易。
**访问路径**：导航直达。
**布局**：顶部账户切换 Tab → 余额概览卡片（总资产/可用/冻结）→ 中部下单面板（市价/限价/止损 Tab + 表单）→ 底部持仓列表 + 当前挂单列表。
**列表项字段**（持仓）：交易对 / 方向 / 数量 / 开仓价 / 未实现盈亏 / 杠杆 / 操作
**列表项字段**（挂单）：交易对 / 方向 / 类型 / 价格 / 数量 / 状态 / 操作

**交互说明**

| 元素 | 动作 | 响应 | 传参 | 备注 |
|------|------|------|------|------|
| 账户 Tab | 点击 | 切换账户，刷新余额和持仓 | — | — |
| 下单表单 | 提交 | 调用下单 API，成功后刷新持仓和挂单 | — | 表单校验必填项 |
| 持仓-平仓按钮 | 点击 | 弹出 @modal(confirm-close-position) | — | — |
| 挂单-撤单按钮 | 点击 | 弹出 @modal(confirm-cancel-order) | — | — |
| Logo | 点击 | 跳转 @page(/) | — | — |

**弹窗 confirm-close-position**：
- 标题："确认平仓"
- 内容：展示交易对、方向、数量
- 操作：确认（调用平仓 API）、取消

**弹窗 confirm-cancel-order**：
- 标题："确认撤单"
- 内容：展示交易对、价格、数量
- 操作：确认（调用撤单 API）、取消

##### @page(/strategies) 策略列表

**核心职责**：管理所有策略，查看状态，进入编辑。
**访问路径**：导航直达。
**布局**：顶部"新建策略"按钮 + 筛选（状态/交易对）→ 策略卡片网格（名称/状态标签/关联交易对/创建时间/最后运行时间/操作按钮）。
**列表项字段**：策略名称 / 状态 / 关联交易对 / 创建时间 / 操作

**交互说明**

| 元素 | 动作 | 响应 | 传参 | 备注 |
|------|------|------|------|------|
| 新建策略 | 点击 | 跳转 @page(/strategy-editor) | — | — |
| 策略卡片 | 点击 | 跳转 @page(/strategy-editor)?strategy_id | strategy_id | — |
| 启动/停止按钮 | 点击 | 切换策略运行状态 | — | 调用 API |
| 删除按钮 | 点击 | 弹出 @modal(confirm-delete-strategy) | — | — |
| 状态筛选 | 选择 | 过滤策略列表 | — | — |
| Logo | 点击 | 跳转 @page(/) | — | — |

**弹窗 confirm-delete-strategy**：
- 标题："确认删除策略"
- 内容：展示策略名称
- 操作：确认（删除并刷新列表）、取消

##### @page(/strategy-editor) 策略编辑器

**核心职责**：编写策略代码、配置参数、管理版本。
**访问路径**：从 @page(/strategies) 新建或点击进入。
**布局**：顶部策略名称（可编辑）+ 保存/另存版本按钮 → 左侧代码编辑器（Monaco Editor）→ 右侧参数配置面板（动态表单，根据 parameters_json schema 生成）→ 底部版本历史列表。
**列表项字段**（版本历史）：版本号 / 修改说明 / 时间 / 操作

**交互说明**

| 元素 | 动作 | 响应 | 传参 | 备注 |
|------|------|------|------|------|
| 保存按钮 | 点击 | 保存当前代码和参数 | — | — |
| 另存版本 | 点击 | 弹出 @modal(save-version) | — | — |
| 代码编辑器 | 编辑 | 实时保存到本地状态 | — | — |
| 参数表单 | 修改 | 实时校验参数类型和范围 | — | — |
| 版本行-回滚按钮 | 点击 | 弹出 @modal(confirm-rollback) | — | 回滚到该版本 |
| 返回按钮 | 点击 | 有未保存改动时弹出 @modal(discard-confirm)，否则返回 @page(/strategies) | — | — |
| Logo | 点击 | 跳转 @page(/) | — | — |

**弹窗 save-version**：
- 标题："保存为新版本"
- 内容：修改说明输入框
- 操作：确认（保存新版本）、取消

**弹窗 confirm-rollback**：
- 标题："确认回滚"
- 内容：展示目标版本号
- 操作：确认（回滚代码和参数）、取消

**弹窗 discard-confirm**：
- 标题："未保存的修改"
- 内容："是否放弃未保存的修改？"
- 操作：放弃（不保存直接返回）、取消

##### @page(/execution) 执行监控

**核心职责**：监控运行中策略的实时状态和风控告警。
**访问路径**：导航直达。
**布局**：顶部运行策略概览（卡片：策略名/运行时长/实时盈亏/状态）→ 中部风控规则状态栏（每条规则状态指示灯）→ 底部实时告警列表 + 执行日志流。
**列表项字段**（告警）：级别 / 策略 / 规则 / 消息 / 时间 / 操作
**列表项字段**（日志）：时间 / 级别 / 策略 / 消息
**状态**：
- 空态：无运行策略时显示"暂无运行中的策略"
- 加载态：骨架屏

**交互说明**

| 元素 | 动作 | 响应 | 传参 | 备注 |
|------|------|------|------|------|
| 策略卡片-停止按钮 | 点击 | 弹出 @modal(confirm-stop-strategy) | — | — |
| 告警-确认按钮 | 点击 | 标记告警已确认 | — | — |
| 日志-筛选 | 选择 | 按级别/策略过滤日志 | — | — |
| 风控规则-开关 | 点击 | 启用/禁用风控规则 | — | — |
| Logo | 点击 | 跳转 @page(/) | — | — |

**弹窗 confirm-stop-strategy**：
- 标题："确认停止策略"
- 内容：展示策略名称、运行时长、当前盈亏
- 操作：确认（停止策略）、取消

##### @page(/review) 复盘分析

**核心职责**：策略绩效分析、交易复盘、收益可视化。
**访问路径**：导航直达。
**布局**：顶部策略选择 + 时间范围选择器 → 指标卡片行（累计收益/年化收益/夏普比率/最大回撤/胜率/盈亏比）→ 左侧收益曲线（ECharts 面积图，支持叠加策略对比）→ 右侧月度收益热力图 → 底部交易复盘表格 + 优化建议卡片。
**列表项字段**（交易复盘）：交易对 / 方向 / 开仓价 / 平仓价 / 盈亏 / 持仓时间 / 操作

**交互说明**

| 元素 | 动作 | 响应 | 传参 | 备注 |
|------|------|------|------|------|
| 策略选择 | 选择 | 刷新所有图表和指标 | — | 支持多选对比 |
| 时间范围 | 选择 | 刷新数据和图表 | — | 近7天/30天/90天/自定义 |
| 收益曲线-对比开关 | 点击 | 叠加/移除对比策略曲线 | — | — |
| 优化建议-采纳按钮 | 点击 | 标记建议已采纳 | — | — |
| Logo | 点击 | 跳转 @page(/) | — | — |

##### @page(/replay) 历史回放

**核心职责**：用历史数据模拟策略运行，对比回测结果。
**访问路径**：导航直达。
**布局**：左侧配置面板（策略选择/交易对/时间范围/初始资金/回放速度）→ 右侧主区域：K线回放图（lightweight-charts，标记买卖点）→ 下方回放控制条（播放/暂停/步进/速度切换/进度条）→ 底部回放统计（模拟收益/交易次数/胜率）。
**状态**：
- 初始态：显示配置面板，主区域提示"配置参数后开始回放"
- 运行态：K线图逐步推进，买卖点标记实时出现
- 完成态：显示完整统计结果

**交互说明**

| 元素 | 动作 | 响应 | 传参 | 备注 |
|------|------|------|------|------|
| 开始回放按钮 | 点击 | 校验配置，启动回放 | — | — |
| 播放/暂停 | 点击 | 切换回放运行/暂停 | — | — |
| 步进按钮 | 点击 | 推进一根K线 | — | — |
| 速度选择 | 选择 | 切换回放速度 | — | 1x/5x/10x/max |
| 进度条 | 拖拽 | 跳转到指定时间点 | — | — |
| 重置按钮 | 点击 | 清除回放结果，回到配置态 | — | — |
| Logo | 点击 | 跳转 @page(/) | — | — |
