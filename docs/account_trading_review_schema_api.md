# 账户与交易 + 复盘分析 永久存储与 API 说明

## 0. 最终审核版建表结论

> 本节是给团队审核的最终结果。后续章节作为字段说明、API 说明和设计依据。  
> 对外 API 保持统一，数据库持久化必须按 `live` 实盘、`paper` 模拟盘、`backtest` 回测三类物理隔离。  
> 文档禁止记录数据库连接串、密码、真实客户号、验证码图片路径等敏感信息。

### 0.1 最终建表总名单

第一批必须创建，这一批用于跑通账户管理、交易持久化、实盘自动化追踪的最小闭环：

| 优先级 | 表名 | 类型 | 账户类型 | 主要用途 | 上游来源 | 下游消费者 |
|---:|---|---|---|---|---|---|
| P0 | `trading_account` | 公共主档 | live/paper/backtest | 统一保存账户主档、账户类型、展示名、状态 | 用户配置、同花顺识别、回测配置 | 账户页面、下单接口、复盘筛选 |
| P0 | `account_binding` | 公共绑定 | live/paper/backtest | 保存账户与同花顺客户端、模拟适配器、回测引擎的绑定关系 | 用户配置、桌面自动化识别 | 自动连接、账户识别、状态检查 |
| P0 | `account_runtime_status` | 公共状态 | live/paper/backtest | 保存账户当前连接状态、同步状态、最后错误、最近心跳 | 交易适配器、模拟撮合器、回测引擎 | 前端状态栏、监控告警 |
| P0 | `account_operation_task` | 公共任务 | live/paper/backtest | 保存一次同步、查询、下单、撤单、回测运行等完整业务任务 | Web 请求、策略信号、定时任务 | 操作日志、问题定位、审计 |
| P0 | `account_operation_step` | 公共步骤 | live/paper/backtest | 保存任务内每一步操作，例如连接客户端、切换菜单、填代码、点买入、读取委托结果 | 桌面自动化适配器、模拟撮合器、回测引擎 | 实盘自动化排错、操作审计 |
| P0 | `live_balance_snapshot` | 实盘事实 | live | 保存实盘资金快照 | 同花顺资金股票页面 | 账户首页、风控、复盘 |
| P0 | `live_position_snapshot` | 实盘事实 | live | 保存实盘持仓快照 | 同花顺资金股票页面 | 账户首页、风控、复盘 |
| P0 | `live_order` | 实盘事实 | live | 保存实盘委托、合同编号、撤单状态 | 同花顺当日委托/历史委托、Web 下单 | 订单列表、撤单、复盘 |
| P0 | `live_trade` | 实盘事实 | live | 保存实盘成交明细 | 同花顺当日成交/历史成交 | 成交列表、复盘、绩效计算 |
| P0 | `live_order_status_log` | 实盘状态流 | live | 保存实盘订单状态变化轨迹 | 下单、同步委托、撤单、成交回查 | 订单追踪、审计、复盘解释 |
| P0 | `paper_balance_snapshot` | 模拟事实 | paper | 保存模拟盘资金快照 | 本地模拟撮合、上游实时行情 | 账户首页、策略执行、复盘 |
| P0 | `paper_position_snapshot` | 模拟事实 | paper | 保存模拟盘持仓快照 | 本地模拟撮合、上游实时行情 | 账户首页、策略执行、复盘 |
| P0 | `paper_order` | 模拟事实 | paper | 保存模拟盘委托 | Web 手工下单、策略信号、本地撮合 | 订单列表、撤单、复盘 |
| P0 | `paper_trade` | 模拟事实 | paper | 保存模拟盘成交 | 本地撮合引擎 | 成交列表、复盘、绩效计算 |
| P0 | `paper_order_status_log` | 模拟状态流 | paper | 保存模拟订单状态变化 | 本地撮合、撤单、行情触发 | 订单追踪、复盘解释 |
| P0 | `backtest_run` | 回测批次 | backtest | 保存一次回测的策略、参数、区间、初始资金、状态 | 回测启动请求、策略模块 | 回测结果页、复盘入口 |
| P0 | `backtest_balance_snapshot` | 回测事实 | backtest | 保存回测资金曲线基础快照 | 回测引擎 | 净值曲线、复盘指标 |
| P0 | `backtest_position_snapshot` | 回测事实 | backtest | 保存回测持仓快照 | 回测引擎 | 持仓分析、复盘 |
| P0 | `backtest_order` | 回测事实 | backtest | 保存回测委托 | 回测撮合引擎、历史行情 | 回测明细、复盘 |
| P0 | `backtest_trade` | 回测事实 | backtest | 保存回测成交 | 回测撮合引擎、历史行情 | 回测明细、复盘、指标 |
| P0 | `backtest_order_status_log` | 回测状态流 | backtest | 保存回测订单状态变化 | 回测撮合引擎 | 回测追踪、复盘解释 |

第二批建议创建，这一批用于补齐资金流水、模拟批次、复盘指标和图表：

| 优先级 | 表名 | 类型 | 账户类型 | 主要用途 | 上游来源 | 下游消费者 |
|---:|---|---|---|---|---|---|
| P1 | `live_cash_flow` | 实盘流水 | live | 保存实盘现金流水、费用、税费、冻结解冻 | 同花顺、成交计算 | 对账、复盘、收益归因 |
| P1 | `paper_cash_flow` | 模拟流水 | paper | 保存模拟盘现金流水和费用 | 本地模拟撮合 | 对账、复盘、收益归因 |
| P1 | `backtest_cash_flow` | 回测流水 | backtest | 保存回测现金流水和费用 | 回测引擎 | 对账、复盘、收益归因 |
| P1 | `paper_simulation_run` | 模拟批次 | paper | 保存一次模拟运行的参数、资金、行情源、撮合规则 | 模拟盘启动配置 | 模拟盘结果复盘、策略对比 |
| P1 | `review_session` | 复盘主表 | live/paper/backtest | 保存一次复盘分析任务 | 用户发起、回测结束、定时任务 | 复盘页面、报告导出 |
| P1 | `review_metric_snapshot` | 复盘指标 | live/paper/backtest | 保存收益率、最大回撤、胜率、盈亏比等指标 | 复盘计算引擎 | 复盘报告、策略对比 |
| P1 | `review_trade_item` | 复盘明细 | live/paper/backtest | 保存复盘后的交易明细、盈亏、持仓周期、标签 | 订单表、成交表、行情表 | 交易归因、问题定位 |
| P1 | `review_equity_curve` | 复盘曲线 | live/paper/backtest | 保存净值曲线、总资产曲线、收益曲线 | 资金快照、持仓估值、成交 | 图表展示、指标计算 |
| P1 | `review_drawdown_curve` | 复盘曲线 | live/paper/backtest | 保存回撤曲线和峰值回撤区间 | 净值曲线计算 | 风险分析、复盘报告 |
| P1 | `review_suggestion` | 复盘建议 | live/paper/backtest | 保存策略优化、风控、仓位、进出场建议 | 复盘分析引擎 | 复盘页面、团队确认 |

第三批可选增强，后续根据团队排期决定：

| 优先级 | 表名 | 类型 | 账户类型 | 主要用途 |
|---:|---|---|---|---|
| P2 | `account_sync_log` | 同步日志 | live/paper/backtest | 保存同步摘要日志。若 `account_operation_task` 已覆盖，可降级为视图或不建。 |
| P2 | `market_data_ref_log` | 行情引用 | paper/backtest | 保存模拟和回测使用过的行情批次、K 线版本、数据源版本。 |
| P2 | `risk_check_log` | 风控日志 | live/paper/backtest | 保存下单前后的风控检查结果。 |
| P2 | `trade_reconcile_record` | 对账记录 | live/paper | 保存本地订单成交与交易端读取结果的对账差异。 |
| P2 | `review_tag` | 复盘标签 | live/paper/backtest | 保存用户给交易或复盘会话打的标签。 |
| P2 | `review_note` | 复盘笔记 | live/paper/backtest | 保存人工复盘笔记、结论和团队确认意见。 |

### 0.2 三类账户持久化边界

实盘 `live_*`：

- 只保存真实交易端或真实交易动作形成的数据。
- 数据来源包括同花顺桌面自动化读取资金、持仓、委托、成交，以及 Web 触发的买入、卖出、撤单操作。
- 不能用模拟撮合结果覆盖实盘订单状态。
- 不能直接假定下单成功，必须以交易端委托记录或合同编号为准。
- 验证码只作为运行时交互状态处理，不保存验证码截图文件路径。

模拟盘 `paper_*`：

- 不操作同花顺软件。
- 数据来源是上游实时行情、本地模拟撮合、Web 手工下单、策略信号。
- 允许重置或删除模拟批次，但不能影响实盘表。
- 必须记录委托、成交、资金、持仓和订单状态流转，保证复盘口径与实盘一致。

回测 `backtest_*`：

- 数据来源是上游历史行情、策略信号和回测撮合引擎。
- 所有回测事实表必须带 `run_id`，通过 `backtest_run.run_id` 隔离每一次回测任务。
- 回测数据量大，后续清理、归档、重算都应以 `run_id` 为单位。
- 回测结果不能写入 `paper_*` 或 `live_*`。

### 0.3 关键新增表说明

旧版设计已有 `live_*`、`paper_*`、`backtest_*` 三套交易表族，方向正确，但还不足以满足当前“所有交易记录持久化、三类账户独立、实盘自动化可追溯”的要求。最终必须补充以下表：

1. `account_runtime_status`：记录账户当前可用性、连接状态、最近同步状态、最后错误、最近心跳。
2. `account_operation_task`：记录一次完整业务动作，例如同步、查询余额、下单、撤单、回测运行。
3. `account_operation_step`：记录自动化或撮合过程中的每一步，实盘下单尤其需要它定位问题。
4. `live_order_status_log`、`paper_order_status_log`、`backtest_order_status_log`：记录订单状态变化历史，不能只在订单主表保留最终状态。
5. `paper_simulation_run`：模拟盘如果需要按批次复盘、重置或对比，应单独建表。
6. `review_equity_curve`、`review_drawdown_curve`：复盘图表和风险指标需要曲线型结果表。

### 0.4 上下游接口关系

账户交易模块需要上游市场数据提供：`symbol`、`name`、`exchange`、`trade_date`、`latest_price`、`prev_close`、`limit_up`、`limit_down`、`is_halted`、`bar_time`、`open`、`high`、`low`、`close`、`volume`、`amount`。

| 下游模块 | 读取表 | 读取目的 |
|---|---|---|
| 前端账户页面 | `trading_account`、三类 `*_balance_snapshot`、`*_position_snapshot`、`*_order`、`*_trade` | 展示账户、资金、持仓、委托、成交 |
| 策略执行模块 | `trading_account`、`account_runtime_status`、三类订单和持仓表 | 判断账户可用性、仓位、委托状态 |
| 风控模块 | 三类资金、持仓、订单、成交表、`risk_check_log` | 下单前检查、盘中风险监控 |
| 复盘模块 | 三类订单、成交、资金、持仓表、`review_*` | 计算收益、回撤、胜率、盈亏比、交易归因 |
| 历史回放模块 | `backtest_run`、`backtest_*`、`review_*` | 回放历史交易过程和复盘结果 |

### 0.5 最终审核判断

当前数据库设计应按本节的 P0、P1、P2 三档推进。P0 是本阶段必须落地的表，否则无法满足“交易记录全部持久化、账户状态可监控、实盘自动化过程可追踪”的要求。P1 是复盘和资金对账真正可用所需的表。P2 是后续工程化增强项，可以在基础交易闭环稳定后继续补。

> 适用模块：`backend/account_trading`、`backend/review_analysis`  
> 目标：把实盘 / 模拟 / 回测三类账户统一进一套永久存储模型，并抽出可供上下游复用的公共 API 与数据结构。

## 1. 设计目标

1. 统一账户口径：`live` 实盘、`paper` 模拟、`backtest` 回测。
2. 统一交易口径：委托、成交、资金、持仓、现金流水、自动化日志。
3. 统一复盘口径：复盘会话、绩效指标、交易归因、建议结果。
4. 兼容当前实现：同花顺桌面自动化、Web API、策略执行模块、行情模块。

## 1.1 项目数据库连接约定

根据项目 `README.md`、`DEVELOPMENT.md` 与 `backend/common/config.py`，当前项目使用：

- 数据库：MySQL 8.0
- ORM：SQLAlchemy 2.0 async
- 驱动：`aiomysql`
- 配置来源：项目根目录 `.env`
- 配置类：`backend/common/config.py::Settings`

`.env` 配置项：

```env
MYSQL_HOST=<your-mysql-host>
MYSQL_PORT=<your-mysql-port>
MYSQL_USER=<your-mysql-user>
MYSQL_PASSWORD=<your-mysql-password>
MYSQL_DATABASE=<your-mysql-database>
```

后端实际连接串由 `Settings.DATABASE_URL` 自动拼接：

```python
mysql+aiomysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}
```

默认示例：

```text
mysql+aiomysql://<user>:<password>@<host>:<port>/<database>
```

> 真实数据库连接信息只应保留在本机 `.env`，不要写入文档、示例文件或提交历史。

数据库初始化建议：

```sql
CREATE DATABASE IF NOT EXISTS quant_trading
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;
```

## 2. 模块边界

### 2.1 账户与交易对接

职责：

- 账户连接与识别
- 资金、持仓、委托、成交同步
- 买入、卖出、撤单
- 自动化状态、日志、验证码运行时处理
- 账户持久化与快照写入

不负责：

- 复杂绩效分析
- 策略表达式求值
- 行情采集

### 2.2 复盘分析与策略优化

职责：

- 消费账户成交、委托、持仓、资金快照
- 汇总绩效指标
- 生成复盘报告
- 给策略优化模块提供建议

不负责：

- 真实下单
- 实时风控
- 行情采集

## 3. 共享枚举与公共字段

### 3.1 账户类型

```text
account_type = live | paper | backtest
```

说明：

- `live`：实盘账户
- `paper`：模拟账户
- `backtest`：回测账户

### 3.2 交易方向

```text
side = buy | sell
```

### 3.3 订单状态

```text
order_status = draft | submitted | partial_filled | filled | canceled | rejected | failed
```

### 3.4 数据来源

```text
source = live | paper | backtest | replay | manual
```

### 3.5 核心公共字段

| 字段 | 说明 |
|---|---|
| `account_id` | 系统内部账户 ID |
| `broker_account_no` | 券商资金账号或模拟盘账号 |
| `shareholder_account` | 股东账号 |
| `symbol` | 证券代码，建议统一为 `600519.SH` 格式 |
| `name` | 证券名称 |
| `strategy_id` | 策略 ID |
| `version_id` | 策略版本 ID |
| `run_id` | 策略运行批次 ID |
| `signal_id` | 策略信号 ID |
| `entrust_no` | 券商合同编号 |
| `trade_id` | 系统成交 ID |
| `trade_date` | 交易日期 |
| `created_at` / `updated_at` | 记录创建与更新时间 |

### 3.6 枚举注释字典

> 下面这些枚举值需要在 SQL、ORM、接口文档三处保持一致。

| 枚举名 | 值 | 注释 |
|---|---|---|
| `account_type` | `live` | 实盘账户，真实资金交易。 |
| `account_type` | `paper` | 模拟账户，虚拟资金交易。 |
| `account_type` | `backtest` | 回测账户，历史数据驱动的模拟交易。 |
| `binding_type` | `desktop` | 通过桌面客户端自动化连接。 |
| `binding_type` | `ths` | 同花顺适配器绑定。 |
| `binding_type` | `webapi` | 券商柜台 API 绑定。 |
| `binding_type` | `mock` | 本地模拟适配器绑定。 |
| `source` | `live` | 来自实盘。 |
| `source` | `paper` | 来自模拟盘。 |
| `source` | `backtest` | 来自回测。 |
| `source` | `replay` | 来自历史回放。 |
| `source` | `manual` | 来自人工录入。 |
| `order_status` | `draft` | 草稿，尚未提交。 |
| `order_status` | `submitted` | 已提交到交易端。 |
| `order_status` | `partial_filled` | 部分成交。 |
| `order_status` | `filled` | 全部成交。 |
| `order_status` | `canceled` | 已撤单。 |
| `order_status` | `rejected` | 已拒单。 |
| `order_status` | `failed` | 处理失败。 |
| `flow_type` | `deposit` | 入金。 |
| `flow_type` | `withdraw` | 出金。 |
| `flow_type` | `freeze` | 冻结资金。 |
| `flow_type` | `unfreeze` | 解冻资金。 |
| `flow_type` | `trade_fee` | 交易手续费。 |
| `flow_type` | `tax` | 印花税或税费。 |
| `flow_type` | `trade_cash` | 成交扣款或回款。 |
| `review_session.status` | `draft` | 复盘会话创建但未计算。 |
| `review_session.status` | `running` | 正在计算。 |
| `review_session.status` | `done` | 已完成。 |
| `review_session.status` | `failed` | 计算失败。 |
| `review_suggestion.severity` | `low` | 低优先级建议。 |
| `review_suggestion.severity` | `medium` | 中优先级建议。 |
| `review_suggestion.severity` | `high` | 高优先级建议。 |
| `review_suggestion.suggestion_type` | `risk` | 风控类建议。 |
| `review_suggestion.suggestion_type` | `position` | 仓位类建议。 |
| `review_suggestion.suggestion_type` | `entry` | 进场类建议。 |
| `review_suggestion.suggestion_type` | `exit` | 离场类建议。 |
| `review_suggestion.suggestion_type` | `parameter` | 参数优化类建议。 |

## 4. 永久表结构（逻辑草案）

> 说明：本节先给出统一字段模板，**最终落库建议按账户类型分族存储**，见第 11 节。  
> 也就是说，对外 API 仍然统一，但物理表建议拆成 `live_*`、`paper_*`、`backtest_*` 三套。

> 建议使用 MySQL 8.0，所有金额字段统一 `DECIMAL(20,4)`，数量字段统一 `BIGINT` 或 `INT`，时间字段统一 `DATETIME(3)`。

### 4.1 `trading_account` 账户主表

用途：保存所有账户主档信息，覆盖实盘、模拟、回测三类账户。

```sql
CREATE TABLE trading_account (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    account_code VARCHAR(64) NOT NULL UNIQUE COMMENT '系统账户编码',
    account_name VARCHAR(128) NOT NULL COMMENT '账户显示名',
    account_type VARCHAR(16) NOT NULL COMMENT 'live/paper/backtest',
    broker_name VARCHAR(64) DEFAULT NULL COMMENT '券商或平台名称',
    broker_account_no VARCHAR(64) DEFAULT NULL COMMENT '资金账号',
    shareholder_account VARCHAR(64) DEFAULT NULL COMMENT '股东账号',
    exchange VARCHAR(16) DEFAULT NULL COMMENT '交易市场，如 SZ/SH/BJ',
    status VARCHAR(16) NOT NULL DEFAULT 'active' COMMENT 'active/inactive/archived',
    is_default TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否默认账户',
    meta_json JSON DEFAULT NULL COMMENT '扩展信息',
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
    INDEX idx_account_type (account_type),
    INDEX idx_broker_account_no (broker_account_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 4.2 `account_binding` 账户绑定表

用途：记录账户与同花顺/其他客户端的绑定关系，支持一个账户多终端或多连接方式。

```sql
CREATE TABLE account_binding (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    account_id BIGINT NOT NULL COMMENT '关联 trading_account.id',
    binding_type VARCHAR(32) NOT NULL COMMENT 'desktop/ths/webapi/mock',
    client_path VARCHAR(255) DEFAULT NULL COMMENT '桌面客户端路径',
    client_identity VARCHAR(128) DEFAULT NULL COMMENT '客户端唯一标识',
    login_account_name VARCHAR(128) DEFAULT NULL COMMENT '界面展示的登录名称',
    login_account_mask VARCHAR(64) DEFAULT NULL COMMENT '脱敏账号',
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    last_connected_at DATETIME(3) DEFAULT NULL,
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
    UNIQUE KEY uk_account_binding (account_id, binding_type, client_identity),
    INDEX idx_account_id (account_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 4.3 `account_balance_snapshot` 资金快照表

用途：保存资金余额、可用资金、冻结资金、总资产等快照。

```sql
CREATE TABLE account_balance_snapshot (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    account_id BIGINT NOT NULL,
    trade_date DATE NOT NULL,
    snapshot_time DATETIME(3) NOT NULL,
    total_asset DECIMAL(20,4) NOT NULL DEFAULT 0,
    cash_balance DECIMAL(20,4) NOT NULL DEFAULT 0,
    available_cash DECIMAL(20,4) NOT NULL DEFAULT 0,
    withdrawable_cash DECIMAL(20,4) NOT NULL DEFAULT 0,
    frozen_cash DECIMAL(20,4) NOT NULL DEFAULT 0,
    market_value DECIMAL(20,4) NOT NULL DEFAULT 0,
    realized_pnl DECIMAL(20,4) DEFAULT NULL,
    unrealized_pnl DECIMAL(20,4) DEFAULT NULL,
    source VARCHAR(16) NOT NULL COMMENT 'live/paper/backtest/replay/manual',
    raw_json JSON DEFAULT NULL,
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    INDEX idx_account_date (account_id, trade_date),
    INDEX idx_snapshot_time (snapshot_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 4.4 `account_position_snapshot` 持仓快照表

用途：记录账户当前持仓及估值信息。

```sql
CREATE TABLE account_position_snapshot (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    account_id BIGINT NOT NULL,
    trade_date DATE NOT NULL,
    snapshot_time DATETIME(3) NOT NULL,
    symbol VARCHAR(32) NOT NULL,
    name VARCHAR(128) DEFAULT NULL,
    exchange VARCHAR(16) DEFAULT NULL,
    quantity BIGINT NOT NULL DEFAULT 0,
    available_quantity BIGINT NOT NULL DEFAULT 0,
    frozen_quantity BIGINT NOT NULL DEFAULT 0,
    cost_price DECIMAL(20,4) DEFAULT NULL,
    last_price DECIMAL(20,4) DEFAULT NULL,
    market_value DECIMAL(20,4) DEFAULT NULL,
    unrealized_pnl DECIMAL(20,4) DEFAULT NULL,
    pnl_ratio DECIMAL(20,6) DEFAULT NULL,
    source VARCHAR(16) NOT NULL,
    raw_json JSON DEFAULT NULL,
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    UNIQUE KEY uk_position (account_id, trade_date, symbol),
    INDEX idx_account_date (account_id, trade_date),
    INDEX idx_symbol (symbol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 4.5 `account_order` 委托表

用途：记录所有买卖委托、状态变化、合同编号、撤单信息。

```sql
CREATE TABLE account_order (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    account_id BIGINT NOT NULL,
    strategy_id VARCHAR(64) DEFAULT NULL,
    version_id VARCHAR(64) DEFAULT NULL,
    run_id VARCHAR(64) DEFAULT NULL,
    signal_id VARCHAR(64) DEFAULT NULL,
    idempotency_key VARCHAR(80) DEFAULT NULL,
    order_no VARCHAR(64) DEFAULT NULL COMMENT '系统订单号',
    broker_order_no VARCHAR(64) DEFAULT NULL COMMENT '券商合同编号',
    trade_date DATE NOT NULL,
    symbol VARCHAR(32) NOT NULL,
    name VARCHAR(128) DEFAULT NULL,
    side VARCHAR(8) NOT NULL COMMENT 'buy/sell',
    order_type VARCHAR(16) NOT NULL DEFAULT 'limit',
    price DECIMAL(20,4) NOT NULL,
    quantity BIGINT NOT NULL,
    filled_quantity BIGINT NOT NULL DEFAULT 0,
    canceled_quantity BIGINT NOT NULL DEFAULT 0,
    avg_fill_price DECIMAL(20,4) DEFAULT NULL,
    status VARCHAR(24) NOT NULL,
    remark VARCHAR(255) DEFAULT NULL,
    source VARCHAR(16) NOT NULL,
    submitted_at DATETIME(3) DEFAULT NULL,
    accepted_at DATETIME(3) DEFAULT NULL,
    canceled_at DATETIME(3) DEFAULT NULL,
    rejected_at DATETIME(3) DEFAULT NULL,
    raw_json JSON DEFAULT NULL,
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
    UNIQUE KEY uk_order_no (order_no),
    UNIQUE KEY uk_broker_order_no (broker_order_no),
    INDEX idx_account_date (account_id, trade_date),
    INDEX idx_strategy (strategy_id, version_id),
    INDEX idx_status (status),
    INDEX idx_symbol (symbol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 4.6 `account_trade` 成交表

用途：记录成交明细，与委托一对多。

```sql
CREATE TABLE account_trade (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    account_id BIGINT NOT NULL,
    order_id BIGINT DEFAULT NULL COMMENT '关联 account_order.id',
    strategy_id VARCHAR(64) DEFAULT NULL,
    version_id VARCHAR(64) DEFAULT NULL,
    run_id VARCHAR(64) DEFAULT NULL,
    signal_id VARCHAR(64) DEFAULT NULL,
    trade_id VARCHAR(64) DEFAULT NULL,
    broker_trade_no VARCHAR(64) DEFAULT NULL,
    broker_order_no VARCHAR(64) DEFAULT NULL,
    trade_date DATE NOT NULL,
    traded_at DATETIME(3) NOT NULL,
    symbol VARCHAR(32) NOT NULL,
    name VARCHAR(128) DEFAULT NULL,
    side VARCHAR(8) NOT NULL,
    price DECIMAL(20,4) NOT NULL,
    quantity BIGINT NOT NULL,
    amount DECIMAL(20,4) NOT NULL,
    commission DECIMAL(20,4) DEFAULT NULL,
    stamp_tax DECIMAL(20,4) DEFAULT NULL,
    transfer_fee DECIMAL(20,4) DEFAULT NULL,
    source VARCHAR(16) NOT NULL,
    raw_json JSON DEFAULT NULL,
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    UNIQUE KEY uk_trade_id (trade_id),
    INDEX idx_account_date (account_id, trade_date),
    INDEX idx_order_id (order_id),
    INDEX idx_symbol (symbol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 4.7 `account_cash_flow` 现金流水表

用途：记录入金、出金、冻结、解冻、手续费、税费、成交扣款等现金流。

```sql
CREATE TABLE account_cash_flow (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    account_id BIGINT NOT NULL,
    trade_date DATE NOT NULL,
    flow_type VARCHAR(32) NOT NULL COMMENT 'deposit/withdraw/freeze/unfreeze/trade_fee/tax/trade_cash',
    ref_type VARCHAR(32) DEFAULT NULL COMMENT 'order/trade/manual',
    ref_id VARCHAR(64) DEFAULT NULL,
    amount DECIMAL(20,4) NOT NULL,
    balance_after DECIMAL(20,4) DEFAULT NULL,
    remark VARCHAR(255) DEFAULT NULL,
    source VARCHAR(16) NOT NULL,
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    INDEX idx_account_date (account_id, trade_date),
    INDEX idx_ref (ref_type, ref_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 4.8 `account_sync_log` 自动化同步日志表

用途：记录连接、同步、验证码、失败原因。

```sql
CREATE TABLE account_sync_log (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    account_id BIGINT DEFAULT NULL,
    operation VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL,
    message VARCHAR(255) NOT NULL,
    detail_json JSON DEFAULT NULL,
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    INDEX idx_operation_time (operation, created_at),
    INDEX idx_account_time (account_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 4.9 `review_session` 复盘会话表

用途：每次复盘/回测/模拟盘分析的顶层会话。

```sql
CREATE TABLE review_session (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    session_code VARCHAR(64) NOT NULL UNIQUE,
    account_id BIGINT DEFAULT NULL,
    strategy_id VARCHAR(64) DEFAULT NULL,
    version_id VARCHAR(64) DEFAULT NULL,
    account_type VARCHAR(16) NOT NULL,
    source VARCHAR(16) NOT NULL COMMENT 'live/paper/backtest/replay',
    start_date DATE DEFAULT NULL,
    end_date DATE DEFAULT NULL,
    benchmark_symbol VARCHAR(32) DEFAULT NULL,
    title VARCHAR(128) DEFAULT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'draft',
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
    INDEX idx_strategy (strategy_id, version_id),
    INDEX idx_account (account_id),
    INDEX idx_source (source)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 4.10 `review_metric_snapshot` 绩效指标表

用途：保存某次复盘会话的指标结果。

```sql
CREATE TABLE review_metric_snapshot (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    session_id BIGINT NOT NULL,
    metric_key VARCHAR(64) NOT NULL,
    metric_value DECIMAL(20,8) DEFAULT NULL,
    metric_text VARCHAR(255) DEFAULT NULL,
    metric_unit VARCHAR(32) DEFAULT NULL,
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    UNIQUE KEY uk_session_metric (session_id, metric_key),
    INDEX idx_session (session_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 4.11 `review_trade_item` 复盘交易明细表

用途：从成交和委托抽象出来的复盘交易明细，方便分析。

```sql
CREATE TABLE review_trade_item (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    session_id BIGINT NOT NULL,
    account_id BIGINT NOT NULL,
    order_id BIGINT DEFAULT NULL,
    trade_id BIGINT DEFAULT NULL,
    symbol VARCHAR(32) NOT NULL,
    name VARCHAR(128) DEFAULT NULL,
    side VARCHAR(8) NOT NULL,
    price DECIMAL(20,4) NOT NULL,
    quantity BIGINT NOT NULL,
    amount DECIMAL(20,4) NOT NULL,
    pnl DECIMAL(20,4) DEFAULT NULL,
    pnl_ratio DECIMAL(20,8) DEFAULT NULL,
    holding_period_minutes INT DEFAULT NULL,
    signal_tag VARCHAR(64) DEFAULT NULL,
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    INDEX idx_session (session_id),
    INDEX idx_account (account_id),
    INDEX idx_symbol (symbol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 4.12 `review_suggestion` 优化建议表

用途：保存复盘分析输出的建议。

```sql
CREATE TABLE review_suggestion (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    session_id BIGINT NOT NULL,
    suggestion_type VARCHAR(64) NOT NULL,
    severity VARCHAR(16) NOT NULL DEFAULT 'medium',
    title VARCHAR(128) NOT NULL,
    content TEXT NOT NULL,
    evidence_json JSON DEFAULT NULL,
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    INDEX idx_session (session_id),
    INDEX idx_type (suggestion_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

## 5. 核心关系

```text
trading_account
  ├─ account_binding
  ├─ account_balance_snapshot
  ├─ account_position_snapshot
  ├─ account_order
  │    └─ account_trade
  ├─ account_cash_flow
  ├─ account_sync_log
  └─ review_session
       ├─ review_metric_snapshot
       ├─ review_trade_item
       └─ review_suggestion
```

## 6. 对外 API 说明

### 6.1 账户与交易 API

#### `GET /api/account/automation/status`

返回：

- `connected`
- `ready`
- `window_title`
- `window_class`
- `window_rect`
- `account`

`account` 结构：

```json
{
  "account_name": "模拟炒股-UI**39",
  "account_type": "paper",
  "account_type_label": "模拟盘",
  "market": "深圳Ａ股",
  "shareholder_account": "001****9089",
  "capital_account": "116453076"
}
```

#### `GET /api/account/balance`

返回账户资金快照，字段建议直接落库到 `account_balance_snapshot`。

#### `GET /api/account/positions`

返回持仓快照列表，字段建议直接落库到 `account_position_snapshot`。

#### `GET /api/account/orders?scope=today|history`

返回委托列表，字段建议直接落库到 `account_order`。

#### `GET /api/account/trades?scope=today|history`

返回成交列表，字段建议直接落库到 `account_trade`。

#### `POST /api/account/order`

请求体：

```json
{
  "symbol": "301183.SZ",
  "side": "buy",
  "price": 240.70,
  "quantity": 100,
  "mode": "live",
  "idempotency_key": "uuid",
  "remark": "manual"
}
```

说明：

- `mode=live` 时必须传 `idempotency_key`
- `quantity` 必须是 100 股整数倍
- 成功后应先写 `account_order`，再根据成交回写 `account_trade`

#### `POST /api/account/order/{entrust_no}/cancel`

撤单接口。建议写入 `account_order.status=canceled` 并补充 `canceled_at`。

#### `POST /api/account/sync`

同步资金、持仓、委托、成交。建议作为定时任务或页面手动触发。

### 6.2 复盘分析 API

建议接口：

#### `GET /api/review/sessions`

列出复盘会话。

#### `GET /api/review/session/{id}`

获取复盘会话详情，包括账户、策略、时间区间和指标摘要。

#### `GET /api/review/session/{id}/metrics`

获取指标列表，如：

- 总收益率
- 年化收益率
- 夏普比率
- 最大回撤
- 胜率
- 盈亏比
- 平均持有时间
- 交易次数

#### `GET /api/review/session/{id}/trades`

获取复盘交易明细。

#### `GET /api/review/session/{id}/suggestions`

获取优化建议列表。

#### `POST /api/review/session/recompute`

重新计算某个会话的复盘指标与建议。

## 7. 上游 / 下游数据口径

### 7.1 上游市场数据需要提供

账户与复盘模块依赖行情模块提供：

- `symbol`
- `name`
- `latest_price`
- `prev_close`
- `trade_date`
- `ts`
- `status` / `halted`

### 7.2 下游复盘模块需要消费

账户与交易模块必须能输出：

- `account_balance_snapshot`
- `account_position_snapshot`
- `account_order`
- `account_trade`
- `account_cash_flow`
- `account_sync_log`

复盘模块再把这些数据聚合成：

- `review_session`
- `review_metric_snapshot`
- `review_trade_item`
- `review_suggestion`

## 8. 建议的落地顺序

1. 先落 `trading_account`、`account_order`、`account_trade`、`account_balance_snapshot`、`account_position_snapshot`
2. 再补 `account_cash_flow` 和 `account_sync_log`
3. 最后落 `review_session`、`review_metric_snapshot`、`review_trade_item`、`review_suggestion`
4. 前端先消费 `/api/account/automation/status`、`/api/account/balance`、`/api/account/positions`
5. 再接入 `/api/review/*`

## 9. 当前实现与建议差异

当前项目已实现：

- 同花顺桌面适配器
- Web 余额/持仓/委托/成交同步
- 下单/撤单 API
- 账户类型识别
- 自动化日志

建议继续补齐：

- 持久化 Repository 层
- 账户主档 CRUD
- 复盘分析引擎
- 指标计算任务
- 账户快照定时同步任务

## 10. 字段注释字典

> 这一节是给上下游和数据库建模使用的字段级说明。SQL 里的 `COMMENT` 用于数据库层面，下面的字典用于接口、ORM、前端展示和跨模块沟通。

### 10.1 `trading_account`

| 字段 | 类型 | 是否必填 | 来源 | 注释与用途 |
|---|---|---:|---|---|
| `id` | `BIGINT` | 是 | 数据库自增 | 账户主键，供所有账户相关表作为 `account_id` 引用。 |
| `account_code` | `VARCHAR(64)` | 是 | 系统生成 | 系统内账户编码，建议格式：`LIVE_THS_001`、`PAPER_THS_001`、`BT_202605_001`。 |
| `account_name` | `VARCHAR(128)` | 是 | 同花顺界面 / 用户录入 | 前端展示名称，例如 `模拟炒股-UI**39`。 |
| `account_type` | `VARCHAR(16)` | 是 | 用户选择 / 自动识别 | 账户类型：`live` 实盘、`paper` 模拟、`backtest` 回测。 |
| `broker_name` | `VARCHAR(64)` | 否 | 用户录入 / 自动识别 | 券商或交易平台名称，例如 `同花顺模拟炒股`、`华泰证券`。 |
| `broker_account_no` | `VARCHAR(64)` | 否 | 同花顺界面 | 资金账号。实盘建议脱敏展示，数据库是否存明文由安全策略决定。 |
| `shareholder_account` | `VARCHAR(64)` | 否 | 同花顺界面 | 股东账号，如 `001****9089`。 |
| `exchange` | `VARCHAR(16)` | 否 | 同花顺界面 / 行情模块 | 市场或交易所，建议内部标准化为 `SH`、`SZ`、`BJ`。 |
| `status` | `VARCHAR(16)` | 是 | 系统维护 | 账户状态：`active`、`inactive`、`archived`。 |
| `is_default` | `TINYINT(1)` | 是 | 用户设置 | 是否为默认交易账户。前端下单未选择账户时可使用默认账户。 |
| `meta_json` | `JSON` | 否 | 系统扩展 | 存放额外信息，例如客户端窗口标题、自动化能力、账户标签。 |
| `created_at` | `DATETIME(3)` | 是 | 数据库 | 创建时间。 |
| `updated_at` | `DATETIME(3)` | 是 | 数据库 | 最近更新时间。 |

### 10.2 `account_binding`

| 字段 | 类型 | 是否必填 | 来源 | 注释与用途 |
|---|---|---:|---|---|
| `id` | `BIGINT` | 是 | 数据库自增 | 账户绑定记录主键。 |
| `account_id` | `BIGINT` | 是 | `trading_account.id` | 绑定所属账户。 |
| `binding_type` | `VARCHAR(32)` | 是 | 系统 | 绑定类型：`desktop` 桌面自动化、`ths` 同花顺、`webapi` 券商 API、`mock` 模拟适配器。 |
| `client_path` | `VARCHAR(255)` | 否 | 配置 / 用户录入 | 桌面客户端路径，例如 `E:\同花顺软件\同花顺\xiadan.exe`。 |
| `client_identity` | `VARCHAR(128)` | 否 | 自动识别 | 客户端唯一标识，可用窗口类名、进程路径、账号组合生成。 |
| `login_account_name` | `VARCHAR(128)` | 否 | 同花顺界面 | 登录账号展示名，例如 `模拟炒股-UI**39`。 |
| `login_account_mask` | `VARCHAR(64)` | 否 | 同花顺界面 | 脱敏账号，例如 `UI**39`。 |
| `is_active` | `TINYINT(1)` | 是 | 系统 | 当前绑定是否启用。 |
| `last_connected_at` | `DATETIME(3)` | 否 | 自动化适配器 | 最近一次成功连接交易客户端的时间。 |
| `created_at` | `DATETIME(3)` | 是 | 数据库 | 创建时间。 |
| `updated_at` | `DATETIME(3)` | 是 | 数据库 | 最近更新时间。 |

### 10.3 `account_balance_snapshot`

| 字段 | 类型 | 是否必填 | 来源 | 注释与用途 |
|---|---|---:|---|---|
| `id` | `BIGINT` | 是 | 数据库自增 | 资金快照主键。 |
| `account_id` | `BIGINT` | 是 | `trading_account.id` | 快照所属账户。 |
| `trade_date` | `DATE` | 是 | 交易日历 / 系统时间 | 交易日期，用于日级统计和复盘。 |
| `snapshot_time` | `DATETIME(3)` | 是 | 系统时间 | 快照采集时间，支持日内多次同步。 |
| `total_asset` | `DECIMAL(20,4)` | 是 | 同花顺资金页 / 回测引擎 | 总资产，现金 + 持仓市值。 |
| `cash_balance` | `DECIMAL(20,4)` | 是 | 同花顺资金页 | 资金余额。 |
| `available_cash` | `DECIMAL(20,4)` | 是 | 同花顺资金页 | 可用资金，可用于新委托。 |
| `withdrawable_cash` | `DECIMAL(20,4)` | 是 | 同花顺资金页 | 可取资金。 |
| `frozen_cash` | `DECIMAL(20,4)` | 是 | 同花顺资金页 / 系统计算 | 冻结资金，通常来自未成交买单。 |
| `market_value` | `DECIMAL(20,4)` | 是 | 同花顺资金页 / 行情估值 | 持仓市值。 |
| `realized_pnl` | `DECIMAL(20,4)` | 否 | 复盘计算 | 已实现盈亏，用于绩效分析。 |
| `unrealized_pnl` | `DECIMAL(20,4)` | 否 | 持仓估值 / 复盘计算 | 未实现盈亏。 |
| `source` | `VARCHAR(16)` | 是 | 系统 | 数据来源：`live`、`paper`、`backtest`、`replay`、`manual`。 |
| `raw_json` | `JSON` | 否 | 自动化适配器 | 原始抓取数据，用于问题追溯。 |
| `created_at` | `DATETIME(3)` | 是 | 数据库 | 入库时间。 |

### 10.4 `account_position_snapshot`

| 字段 | 类型 | 是否必填 | 来源 | 注释与用途 |
|---|---|---:|---|---|
| `id` | `BIGINT` | 是 | 数据库自增 | 持仓快照主键。 |
| `account_id` | `BIGINT` | 是 | `trading_account.id` | 所属账户。 |
| `trade_date` | `DATE` | 是 | 交易日历 / 系统时间 | 交易日期。 |
| `snapshot_time` | `DATETIME(3)` | 是 | 系统时间 | 快照采集时间。 |
| `symbol` | `VARCHAR(32)` | 是 | 同花顺持仓表 / 行情模块 | 证券代码。建议内部统一成 `301183.SZ`。 |
| `name` | `VARCHAR(128)` | 否 | 同花顺持仓表 / `stock_base_info` | 证券名称。 |
| `exchange` | `VARCHAR(16)` | 否 | 行情模块 / 代码规则 | 交易所代码：`SH`、`SZ`、`BJ`。 |
| `quantity` | `BIGINT` | 是 | 同花顺持仓表 | 当前持仓股数。 |
| `available_quantity` | `BIGINT` | 是 | 同花顺持仓表 | 可卖数量，A 股 T+1 下可能小于持仓。 |
| `frozen_quantity` | `BIGINT` | 是 | 同花顺持仓表 | 冻结数量。 |
| `cost_price` | `DECIMAL(20,4)` | 否 | 同花顺持仓表 | 成本价。 |
| `last_price` | `DECIMAL(20,4)` | 否 | 同花顺持仓表 / `realtime_quote` | 最新价。 |
| `market_value` | `DECIMAL(20,4)` | 否 | 同花顺持仓表 / 系统计算 | 市值。 |
| `unrealized_pnl` | `DECIMAL(20,4)` | 否 | 同花顺持仓表 / 系统计算 | 浮动盈亏。 |
| `pnl_ratio` | `DECIMAL(20,6)` | 否 | 同花顺持仓表 / 系统计算 | 浮盈比例。 |
| `source` | `VARCHAR(16)` | 是 | 系统 | 数据来源。 |
| `raw_json` | `JSON` | 否 | 自动化适配器 | 原始持仓行数据。 |
| `created_at` | `DATETIME(3)` | 是 | 数据库 | 入库时间。 |

### 10.5 `account_order`

| 字段 | 类型 | 是否必填 | 来源 | 注释与用途 |
|---|---|---:|---|---|
| `id` | `BIGINT` | 是 | 数据库自增 | 委托主键。 |
| `account_id` | `BIGINT` | 是 | `trading_account.id` | 委托所属账户。 |
| `strategy_id` | `VARCHAR(64)` | 否 | 策略执行模块 | 策略 ID，人工下单可为空。 |
| `version_id` | `VARCHAR(64)` | 否 | 策略执行模块 | 策略版本 ID。 |
| `run_id` | `VARCHAR(64)` | 否 | 策略执行模块 / 回测引擎 | 策略运行批次。 |
| `signal_id` | `VARCHAR(64)` | 否 | 策略执行模块 | 触发该委托的信号 ID。 |
| `idempotency_key` | `VARCHAR(80)` | 否 | 前端 / 策略执行模块 | 幂等键，实盘下单必填，用于防重复提交。 |
| `order_no` | `VARCHAR(64)` | 否 | 系统生成 | 系统订单号。 |
| `broker_order_no` | `VARCHAR(64)` | 否 | 同花顺委托回报 | 券商合同编号，用于撤单和对账。 |
| `trade_date` | `DATE` | 是 | 交易日历 / 系统时间 | 委托交易日。 |
| `symbol` | `VARCHAR(32)` | 是 | 前端 / 策略执行模块 | 证券代码。 |
| `name` | `VARCHAR(128)` | 否 | 行情模块 / 委托表 | 证券名称。 |
| `side` | `VARCHAR(8)` | 是 | 前端 / 策略执行模块 | 买卖方向：`buy`、`sell`。 |
| `order_type` | `VARCHAR(16)` | 是 | 前端 / 策略执行模块 | 委托类型，当前先用 `limit`。 |
| `price` | `DECIMAL(20,4)` | 是 | 前端 / 策略执行模块 | 委托价格。 |
| `quantity` | `BIGINT` | 是 | 前端 / 策略执行模块 | 委托数量。 |
| `filled_quantity` | `BIGINT` | 是 | 成交回报 | 已成交数量。 |
| `canceled_quantity` | `BIGINT` | 是 | 撤单回报 | 已撤数量。 |
| `avg_fill_price` | `DECIMAL(20,4)` | 否 | 成交回报 / 系统计算 | 成交均价。 |
| `status` | `VARCHAR(24)` | 是 | 系统 / 券商回报 | 状态：`submitted`、`partial_filled`、`filled`、`canceled`、`rejected`、`failed`。 |
| `remark` | `VARCHAR(255)` | 否 | 前端 / 策略执行模块 | 人工备注或策略说明。 |
| `source` | `VARCHAR(16)` | 是 | 系统 | 数据来源。 |
| `submitted_at` | `DATETIME(3)` | 否 | 系统 | 提交时间。 |
| `accepted_at` | `DATETIME(3)` | 否 | 券商回报 | 被交易端接受时间。 |
| `canceled_at` | `DATETIME(3)` | 否 | 撤单回报 | 撤单时间。 |
| `rejected_at` | `DATETIME(3)` | 否 | 券商回报 | 拒单时间。 |
| `raw_json` | `JSON` | 否 | 自动化适配器 | 原始委托数据。 |
| `created_at` | `DATETIME(3)` | 是 | 数据库 | 创建时间。 |
| `updated_at` | `DATETIME(3)` | 是 | 数据库 | 更新时间。 |

### 10.6 `account_trade`

| 字段 | 类型 | 是否必填 | 来源 | 注释与用途 |
|---|---|---:|---|---|
| `id` | `BIGINT` | 是 | 数据库自增 | 成交主键。 |
| `account_id` | `BIGINT` | 是 | `trading_account.id` | 成交所属账户。 |
| `order_id` | `BIGINT` | 否 | `account_order.id` | 关联系统委托。历史导入时可能暂时为空。 |
| `strategy_id` | `VARCHAR(64)` | 否 | 订单继承 | 策略 ID。 |
| `version_id` | `VARCHAR(64)` | 否 | 订单继承 | 策略版本 ID。 |
| `run_id` | `VARCHAR(64)` | 否 | 订单继承 | 运行批次。 |
| `signal_id` | `VARCHAR(64)` | 否 | 订单继承 | 信号 ID。 |
| `trade_id` | `VARCHAR(64)` | 否 | 系统 / 券商 | 系统成交 ID 或券商成交编号。 |
| `broker_trade_no` | `VARCHAR(64)` | 否 | 同花顺成交表 | 券商成交编号。 |
| `broker_order_no` | `VARCHAR(64)` | 否 | 同花顺成交表 | 券商合同编号。 |
| `trade_date` | `DATE` | 是 | 成交时间 | 成交交易日。 |
| `traded_at` | `DATETIME(3)` | 是 | 成交回报 | 成交时间。 |
| `symbol` | `VARCHAR(32)` | 是 | 成交回报 | 证券代码。 |
| `name` | `VARCHAR(128)` | 否 | 成交回报 / 行情模块 | 证券名称。 |
| `side` | `VARCHAR(8)` | 是 | 成交回报 | 买卖方向。 |
| `price` | `DECIMAL(20,4)` | 是 | 成交回报 | 成交价格。 |
| `quantity` | `BIGINT` | 是 | 成交回报 | 成交数量。 |
| `amount` | `DECIMAL(20,4)` | 是 | 成交回报 / 系统计算 | 成交金额，通常为 `price * quantity`。 |
| `commission` | `DECIMAL(20,4)` | 否 | 券商回报 / 估算 | 佣金。 |
| `stamp_tax` | `DECIMAL(20,4)` | 否 | 券商回报 / 估算 | 印花税，通常卖出产生。 |
| `transfer_fee` | `DECIMAL(20,4)` | 否 | 券商回报 / 估算 | 过户费。 |
| `source` | `VARCHAR(16)` | 是 | 系统 | 数据来源。 |
| `raw_json` | `JSON` | 否 | 自动化适配器 | 原始成交数据。 |
| `created_at` | `DATETIME(3)` | 是 | 数据库 | 入库时间。 |

### 10.7 `account_cash_flow`

| 字段 | 类型 | 是否必填 | 来源 | 注释与用途 |
|---|---|---:|---|---|
| `id` | `BIGINT` | 是 | 数据库自增 | 现金流水主键。 |
| `account_id` | `BIGINT` | 是 | `trading_account.id` | 所属账户。 |
| `trade_date` | `DATE` | 是 | 系统 / 交易日历 | 发生日期。 |
| `flow_type` | `VARCHAR(32)` | 是 | 系统 | 流水类型：`deposit`、`withdraw`、`freeze`、`unfreeze`、`trade_fee`、`tax`、`trade_cash`。 |
| `ref_type` | `VARCHAR(32)` | 否 | 系统 | 关联对象类型：`order`、`trade`、`manual`。 |
| `ref_id` | `VARCHAR(64)` | 否 | 系统 | 关联对象 ID 或编号。 |
| `amount` | `DECIMAL(20,4)` | 是 | 系统计算 / 券商流水 | 流水金额，收入为正，支出为负。 |
| `balance_after` | `DECIMAL(20,4)` | 否 | 券商流水 / 系统计算 | 流水发生后的资金余额。 |
| `remark` | `VARCHAR(255)` | 否 | 系统 / 用户 | 备注。 |
| `source` | `VARCHAR(16)` | 是 | 系统 | 数据来源。 |
| `created_at` | `DATETIME(3)` | 是 | 数据库 | 入库时间。 |

### 10.8 `account_sync_log`

| 字段 | 类型 | 是否必填 | 来源 | 注释与用途 |
|---|---|---:|---|---|
| `id` | `BIGINT` | 是 | 数据库自增 | 日志主键。 |
| `account_id` | `BIGINT` | 否 | 系统 | 关联账户，连接失败且无法识别账户时可为空。 |
| `operation` | `VARCHAR(32)` | 是 | 后端 service | 操作名：`status`、`balance`、`positions`、`orders`、`trades`、`sync`、`buy_order`、`sell_order`、`cancel_order`。 |
| `status` | `VARCHAR(32)` | 是 | 后端 service | 结果：`success`、`failed`、`captcha_required`、`client_not_ready`。 |
| `message` | `VARCHAR(255)` | 是 | 后端 service | 简短错误或成功说明。 |
| `detail_json` | `JSON` | 否 | 后端 service | 结构化上下文，例如请求参数、异常类型、返回结果摘要。 |
| `created_at` | `DATETIME(3)` | 是 | 数据库 | 日志时间。 |

### 10.9 `review_session`

| 字段 | 类型 | 是否必填 | 来源 | 注释与用途 |
|---|---|---:|---|---|
| `id` | `BIGINT` | 是 | 数据库自增 | 复盘会话主键。 |
| `session_code` | `VARCHAR(64)` | 是 | 系统生成 | 复盘会话编码，例如 `RV_20260522_001`。 |
| `account_id` | `BIGINT` | 否 | 用户选择 / 系统 | 关联账户。单策略回测也可只关联 `strategy_id`。 |
| `strategy_id` | `VARCHAR(64)` | 否 | 策略模块 | 策略 ID。 |
| `version_id` | `VARCHAR(64)` | 否 | 策略模块 | 策略版本。 |
| `account_type` | `VARCHAR(16)` | 是 | 账户 / 回测引擎 | 复盘对象类型：`live`、`paper`、`backtest`。 |
| `source` | `VARCHAR(16)` | 是 | 系统 | 数据来源：`live`、`paper`、`backtest`、`replay`。 |
| `start_date` | `DATE` | 否 | 用户选择 | 复盘开始日期。 |
| `end_date` | `DATE` | 否 | 用户选择 | 复盘结束日期。 |
| `benchmark_symbol` | `VARCHAR(32)` | 否 | 用户选择 / 默认配置 | 基准指数，如 `000300.SH`。 |
| `title` | `VARCHAR(128)` | 否 | 用户输入 / 系统生成 | 复盘标题。 |
| `status` | `VARCHAR(16)` | 是 | 系统 | 状态：`draft`、`running`、`done`、`failed`。 |
| `created_at` | `DATETIME(3)` | 是 | 数据库 | 创建时间。 |
| `updated_at` | `DATETIME(3)` | 是 | 数据库 | 更新时间。 |

### 10.10 `review_metric_snapshot`

| 字段 | 类型 | 是否必填 | 来源 | 注释与用途 |
|---|---|---:|---|---|
| `id` | `BIGINT` | 是 | 数据库自增 | 指标记录主键。 |
| `session_id` | `BIGINT` | 是 | `review_session.id` | 所属复盘会话。 |
| `metric_key` | `VARCHAR(64)` | 是 | 复盘计算 | 指标编码，如 `total_return`、`max_drawdown`、`sharpe_ratio`。 |
| `metric_value` | `DECIMAL(20,8)` | 否 | 复盘计算 | 数值型指标值。 |
| `metric_text` | `VARCHAR(255)` | 否 | 复盘计算 | 非数值或展示型指标。 |
| `metric_unit` | `VARCHAR(32)` | 否 | 复盘计算 | 单位，如 `%`、`CNY`、`count`。 |
| `created_at` | `DATETIME(3)` | 是 | 数据库 | 生成时间。 |

### 10.11 `review_trade_item`

| 字段 | 类型 | 是否必填 | 来源 | 注释与用途 |
|---|---|---:|---|---|
| `id` | `BIGINT` | 是 | 数据库自增 | 复盘交易明细主键。 |
| `session_id` | `BIGINT` | 是 | `review_session.id` | 所属复盘会话。 |
| `account_id` | `BIGINT` | 是 | `trading_account.id` | 所属账户。 |
| `order_id` | `BIGINT` | 否 | `account_order.id` | 关联委托。 |
| `trade_id` | `BIGINT` | 否 | `account_trade.id` | 关联成交。 |
| `symbol` | `VARCHAR(32)` | 是 | 成交表 / 回测引擎 | 证券代码。 |
| `name` | `VARCHAR(128)` | 否 | 成交表 / 行情模块 | 证券名称。 |
| `side` | `VARCHAR(8)` | 是 | 成交表 | 买卖方向。 |
| `price` | `DECIMAL(20,4)` | 是 | 成交表 | 复盘使用成交价。 |
| `quantity` | `BIGINT` | 是 | 成交表 | 成交数量。 |
| `amount` | `DECIMAL(20,4)` | 是 | 成交表 | 成交金额。 |
| `pnl` | `DECIMAL(20,4)` | 否 | 复盘计算 | 该笔交易或交易对的盈亏。 |
| `pnl_ratio` | `DECIMAL(20,8)` | 否 | 复盘计算 | 盈亏比例。 |
| `holding_period_minutes` | `INT` | 否 | 复盘计算 | 持仓时长。 |
| `signal_tag` | `VARCHAR(64)` | 否 | 策略模块 / 复盘标注 | 交易标签，例如 `breakout`、`stop_loss`。 |
| `created_at` | `DATETIME(3)` | 是 | 数据库 | 生成时间。 |

### 10.12 `review_suggestion`

| 字段 | 类型 | 是否必填 | 来源 | 注释与用途 |
|---|---|---:|---|---|
| `id` | `BIGINT` | 是 | 数据库自增 | 建议主键。 |
| `session_id` | `BIGINT` | 是 | `review_session.id` | 所属复盘会话。 |
| `suggestion_type` | `VARCHAR(64)` | 是 | 复盘分析 | 建议类型：`risk`、`position`、`entry`、`exit`、`parameter`。 |
| `severity` | `VARCHAR(16)` | 是 | 复盘分析 | 严重程度：`low`、`medium`、`high`。 |
| `title` | `VARCHAR(128)` | 是 | 复盘分析 | 建议标题。 |
| `content` | `TEXT` | 是 | 复盘分析 | 建议正文。 |
| `evidence_json` | `JSON` | 否 | 复盘分析 | 支撑证据，例如相关交易、指标、图表区间。 |
| `created_at` | `DATETIME(3)` | 是 | 数据库 | 生成时间。 |

## 11. 最终物理表拆分方案

> 本节是推荐落库方案，优先级高于第 4 节的逻辑草案。第 4 节用于说明统一字段模板；实际建库时建议按本节进行物理隔离。

### 11.1 存储原则

对外接口统一，但持久化必须按账户类型隔离：

| 账户类型 | API 口径 | 物理表族 | 说明 |
|---|---|---|---|
| 实盘 | `account_type=live` | `live_*` | 真实资金交易数据，必须最严格保护。 |
| 模拟盘 | `account_type=paper` | `paper_*` | 模拟交易数据，可以重置和清理。 |
| 回测 | `account_type=backtest` | `backtest_*` | 回测批次数据，数据量大，可按批次删除。 |

这样设计的原因：

1. 实盘数据不能被模拟盘或回测数据污染。
2. 回测数据量通常远大于实盘数据，混表会拖慢实盘查询。
3. 模拟盘和回测经常需要清理，实盘数据一般只追加不删除。
4. 复盘时可以明确选择 `live/paper/backtest` 数据源。

### 11.2 表族清单

公共主档表：

| 表名 | 用途 | 是否按账户类型拆分 |
|---|---|---|
| `trading_account` | 账户主档，保存实盘、模拟、回测账户的基础信息。 | 不拆分 |
| `account_binding` | 账户与同花顺、券商 API、模拟适配器的绑定关系。 | 不拆分 |
| `account_sync_log` | 自动化连接、同步、验证码、错误日志。 | 不拆分，但必须带 `account_id` 和 `operation` |

交易数据表族：

| 逻辑表 | 实盘表 | 模拟盘表 | 回测表 |
|---|---|---|---|
| 资金快照 | `live_balance_snapshot` | `paper_balance_snapshot` | `backtest_balance_snapshot` |
| 持仓快照 | `live_position_snapshot` | `paper_position_snapshot` | `backtest_position_snapshot` |
| 委托 | `live_order` | `paper_order` | `backtest_order` |
| 成交 | `live_trade` | `paper_trade` | `backtest_trade` |
| 现金流水 | `live_cash_flow` | `paper_cash_flow` | `backtest_cash_flow` |
| 回测批次 | 不适用 | 不适用 | `backtest_run` |

复盘数据表：

| 表名 | 说明 |
|---|---|
| `review_session` | 复盘会话，必须带 `source=live/paper/backtest`。 |
| `review_metric_snapshot` | 指标结果，关联 `review_session`。 |
| `review_trade_item` | 复盘明细，来源可以是 live/paper/backtest。 |
| `review_suggestion` | 优化建议，关联 `review_session`。 |

### 11.3 最终建表字段注释要求

所有 SQL 字段必须具备 `COMMENT`。如果字段出现在第 10 节字段注释字典中，SQL `COMMENT` 必须与第 10 节含义一致。

下面给出核心交易表族的完整 COMMENT 模板。`paper_*` 表与 `live_*` 表字段一致；`backtest_*` 表额外带 `run_id`。

#### `live_balance_snapshot` 实盘资金快照表

```sql
CREATE TABLE live_balance_snapshot (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    account_id BIGINT NOT NULL COMMENT '实盘账户ID，关联 trading_account.id，且 account_type=live',
    trade_date DATE NOT NULL COMMENT '交易日期，按中国A股交易日历',
    snapshot_time DATETIME(3) NOT NULL COMMENT '快照采集时间，精确到毫秒',
    total_asset DECIMAL(20,4) NOT NULL DEFAULT 0 COMMENT '总资产=现金余额+持仓市值',
    cash_balance DECIMAL(20,4) NOT NULL DEFAULT 0 COMMENT '资金余额，从交易端资金页读取',
    available_cash DECIMAL(20,4) NOT NULL DEFAULT 0 COMMENT '可用资金，可用于新委托',
    withdrawable_cash DECIMAL(20,4) NOT NULL DEFAULT 0 COMMENT '可取资金',
    frozen_cash DECIMAL(20,4) NOT NULL DEFAULT 0 COMMENT '冻结资金，通常来自未成交买单',
    market_value DECIMAL(20,4) NOT NULL DEFAULT 0 COMMENT '股票持仓市值',
    realized_pnl DECIMAL(20,4) DEFAULT NULL COMMENT '已实现盈亏，由成交和费用计算',
    unrealized_pnl DECIMAL(20,4) DEFAULT NULL COMMENT '未实现盈亏，由持仓市值和成本计算',
    raw_json JSON DEFAULT NULL COMMENT '交易端原始资金数据，用于排查和对账',
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '入库时间',
    INDEX idx_live_balance_account_date (account_id, trade_date),
    INDEX idx_live_balance_snapshot_time (snapshot_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='实盘资金快照表';
```

#### `live_position_snapshot` 实盘持仓快照表

```sql
CREATE TABLE live_position_snapshot (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    account_id BIGINT NOT NULL COMMENT '实盘账户ID，关联 trading_account.id，且 account_type=live',
    trade_date DATE NOT NULL COMMENT '交易日期',
    snapshot_time DATETIME(3) NOT NULL COMMENT '快照采集时间',
    symbol VARCHAR(32) NOT NULL COMMENT '证券代码，建议统一为 301183.SZ 格式',
    name VARCHAR(128) DEFAULT NULL COMMENT '证券名称',
    exchange VARCHAR(16) DEFAULT NULL COMMENT '交易所代码：SH/SZ/BJ',
    quantity BIGINT NOT NULL DEFAULT 0 COMMENT '当前持仓数量',
    available_quantity BIGINT NOT NULL DEFAULT 0 COMMENT '可卖数量，A股T+1下可能小于持仓数量',
    frozen_quantity BIGINT NOT NULL DEFAULT 0 COMMENT '冻结数量',
    cost_price DECIMAL(20,4) DEFAULT NULL COMMENT '成本价',
    last_price DECIMAL(20,4) DEFAULT NULL COMMENT '最新价，来自交易端或行情模块',
    market_value DECIMAL(20,4) DEFAULT NULL COMMENT '持仓市值',
    unrealized_pnl DECIMAL(20,4) DEFAULT NULL COMMENT '浮动盈亏',
    pnl_ratio DECIMAL(20,6) DEFAULT NULL COMMENT '浮盈比例',
    raw_json JSON DEFAULT NULL COMMENT '交易端原始持仓行数据',
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '入库时间',
    UNIQUE KEY uk_live_position (account_id, trade_date, symbol),
    INDEX idx_live_position_symbol (symbol),
    INDEX idx_live_position_time (snapshot_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='实盘持仓快照表';
```

#### `live_order` 实盘委托表

```sql
CREATE TABLE live_order (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    account_id BIGINT NOT NULL COMMENT '实盘账户ID，关联 trading_account.id，且 account_type=live',
    strategy_id VARCHAR(64) DEFAULT NULL COMMENT '策略ID，人工委托为空',
    version_id VARCHAR(64) DEFAULT NULL COMMENT '策略版本ID',
    run_id VARCHAR(64) DEFAULT NULL COMMENT '策略运行批次ID',
    signal_id VARCHAR(64) DEFAULT NULL COMMENT '策略信号ID',
    idempotency_key VARCHAR(80) DEFAULT NULL COMMENT '幂等键，实盘下单必填，用于防止重复提交',
    order_no VARCHAR(64) DEFAULT NULL COMMENT '系统订单号',
    broker_order_no VARCHAR(64) DEFAULT NULL COMMENT '券商合同编号，用于撤单和对账',
    trade_date DATE NOT NULL COMMENT '委托交易日',
    symbol VARCHAR(32) NOT NULL COMMENT '证券代码',
    name VARCHAR(128) DEFAULT NULL COMMENT '证券名称',
    side VARCHAR(8) NOT NULL COMMENT '买卖方向：buy/sell',
    order_type VARCHAR(16) NOT NULL DEFAULT 'limit' COMMENT '委托类型，当前主要为 limit 限价单',
    price DECIMAL(20,4) NOT NULL COMMENT '委托价格',
    quantity BIGINT NOT NULL COMMENT '委托数量',
    filled_quantity BIGINT NOT NULL DEFAULT 0 COMMENT '已成交数量',
    canceled_quantity BIGINT NOT NULL DEFAULT 0 COMMENT '已撤数量',
    avg_fill_price DECIMAL(20,4) DEFAULT NULL COMMENT '成交均价',
    status VARCHAR(24) NOT NULL COMMENT '订单状态：submitted/partial_filled/filled/canceled/rejected/failed',
    remark VARCHAR(255) DEFAULT NULL COMMENT '人工备注或策略说明',
    submitted_at DATETIME(3) DEFAULT NULL COMMENT '提交时间',
    accepted_at DATETIME(3) DEFAULT NULL COMMENT '交易端接受时间',
    canceled_at DATETIME(3) DEFAULT NULL COMMENT '撤单时间',
    rejected_at DATETIME(3) DEFAULT NULL COMMENT '拒单时间',
    raw_json JSON DEFAULT NULL COMMENT '交易端原始委托数据',
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '创建时间',
    updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3) COMMENT '更新时间',
    UNIQUE KEY uk_live_order_no (order_no),
    UNIQUE KEY uk_live_broker_order_no (broker_order_no),
    INDEX idx_live_order_account_date (account_id, trade_date),
    INDEX idx_live_order_strategy (strategy_id, version_id),
    INDEX idx_live_order_status (status),
    INDEX idx_live_order_symbol (symbol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='实盘委托表';
```

#### `live_trade` 实盘成交表

```sql
CREATE TABLE live_trade (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    account_id BIGINT NOT NULL COMMENT '实盘账户ID，关联 trading_account.id，且 account_type=live',
    order_id BIGINT DEFAULT NULL COMMENT '关联 live_order.id',
    strategy_id VARCHAR(64) DEFAULT NULL COMMENT '策略ID，由订单继承',
    version_id VARCHAR(64) DEFAULT NULL COMMENT '策略版本ID，由订单继承',
    run_id VARCHAR(64) DEFAULT NULL COMMENT '策略运行批次ID，由订单继承',
    signal_id VARCHAR(64) DEFAULT NULL COMMENT '策略信号ID，由订单继承',
    trade_id VARCHAR(64) DEFAULT NULL COMMENT '系统成交ID',
    broker_trade_no VARCHAR(64) DEFAULT NULL COMMENT '券商成交编号',
    broker_order_no VARCHAR(64) DEFAULT NULL COMMENT '券商合同编号',
    trade_date DATE NOT NULL COMMENT '成交交易日',
    traded_at DATETIME(3) NOT NULL COMMENT '成交时间',
    symbol VARCHAR(32) NOT NULL COMMENT '证券代码',
    name VARCHAR(128) DEFAULT NULL COMMENT '证券名称',
    side VARCHAR(8) NOT NULL COMMENT '买卖方向：buy/sell',
    price DECIMAL(20,4) NOT NULL COMMENT '成交价格',
    quantity BIGINT NOT NULL COMMENT '成交数量',
    amount DECIMAL(20,4) NOT NULL COMMENT '成交金额',
    commission DECIMAL(20,4) DEFAULT NULL COMMENT '佣金',
    stamp_tax DECIMAL(20,4) DEFAULT NULL COMMENT '印花税',
    transfer_fee DECIMAL(20,4) DEFAULT NULL COMMENT '过户费',
    raw_json JSON DEFAULT NULL COMMENT '交易端原始成交数据',
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '入库时间',
    UNIQUE KEY uk_live_trade_id (trade_id),
    INDEX idx_live_trade_account_date (account_id, trade_date),
    INDEX idx_live_trade_order_id (order_id),
    INDEX idx_live_trade_symbol (symbol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='实盘成交表';
```

#### `live_cash_flow` 实盘现金流水表

```sql
CREATE TABLE live_cash_flow (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    account_id BIGINT NOT NULL COMMENT '实盘账户ID，关联 trading_account.id，且 account_type=live',
    trade_date DATE NOT NULL COMMENT '发生日期',
    flow_type VARCHAR(32) NOT NULL COMMENT '流水类型：deposit/withdraw/freeze/unfreeze/trade_fee/tax/trade_cash',
    ref_type VARCHAR(32) DEFAULT NULL COMMENT '关联对象类型：order/trade/manual',
    ref_id VARCHAR(64) DEFAULT NULL COMMENT '关联对象ID或编号',
    amount DECIMAL(20,4) NOT NULL COMMENT '流水金额，收入为正，支出为负',
    balance_after DECIMAL(20,4) DEFAULT NULL COMMENT '流水发生后的资金余额',
    remark VARCHAR(255) DEFAULT NULL COMMENT '备注',
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '入库时间',
    INDEX idx_live_cash_account_date (account_id, trade_date),
    INDEX idx_live_cash_ref (ref_type, ref_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='实盘现金流水表';
```

### 11.4 模拟盘和回测表的字段注释规则

模拟盘表 `paper_*`：字段与 `live_*` 保持一致，所有字段 COMMENT 也保持一致，只把“实盘账户”改为“模拟盘账户”。

回测表 `backtest_*`：字段与 `live_*` 的核心交易字段保持一致，但必须额外保留：

| 字段 | 类型 | 注释 |
|---|---|---|
| `run_id` | `VARCHAR(64)` | 回测运行批次ID，用于隔离不同回测任务。 |
| `strategy_id` | `VARCHAR(64)` | 策略ID。 |
| `version_id` | `VARCHAR(64)` | 策略版本ID。 |
| `signal_id` | `VARCHAR(64)` | 触发委托或成交的策略信号ID。 |

`backtest_run` 必须作为回测主表：

```sql
CREATE TABLE backtest_run (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    run_id VARCHAR(64) NOT NULL UNIQUE COMMENT '回测运行批次ID',
    account_id BIGINT DEFAULT NULL COMMENT '回测账户ID，关联 trading_account.id，且 account_type=backtest',
    strategy_id VARCHAR(64) NOT NULL COMMENT '策略ID',
    version_id VARCHAR(64) DEFAULT NULL COMMENT '策略版本ID',
    start_date DATE NOT NULL COMMENT '回测开始日期',
    end_date DATE NOT NULL COMMENT '回测结束日期',
    initial_cash DECIMAL(20,4) NOT NULL COMMENT '初始资金',
    benchmark_symbol VARCHAR(32) DEFAULT NULL COMMENT '基准指数代码',
    frequency VARCHAR(16) DEFAULT NULL COMMENT '回测频率，如 daily/1m/5m',
    params_json JSON DEFAULT NULL COMMENT '本次回测使用的策略参数',
    status VARCHAR(16) NOT NULL DEFAULT 'created' COMMENT '状态：created/running/done/failed',
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '创建时间',
    updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3) COMMENT '更新时间',
    INDEX idx_backtest_strategy (strategy_id, version_id),
    INDEX idx_backtest_date (start_date, end_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='回测运行批次表';
```

### 11.5 API 到物理表的映射

| API | 参数 | 写入/读取表 |
|---|---|---|
| `GET /api/account/balance` | `account_type=live` | `live_balance_snapshot` |
| `GET /api/account/balance` | `account_type=paper` | `paper_balance_snapshot` |
| `GET /api/account/balance` | `account_type=backtest` | `backtest_balance_snapshot` |
| `GET /api/account/orders` | `account_type=live` | `live_order` |
| `GET /api/account/orders` | `account_type=paper` | `paper_order` |
| `GET /api/account/orders` | `account_type=backtest` | `backtest_order` |
| `GET /api/account/trades` | `account_type=live` | `live_trade` |
| `GET /api/account/trades` | `account_type=paper` | `paper_trade` |
| `GET /api/account/trades` | `account_type=backtest` | `backtest_trade` |

### 11.6 满足性检查

| 需求 | 是否满足 | 说明 |
|---|---|---|
| 实盘交易数据独立 | 是 | 使用 `live_*` 表族。 |
| 模拟盘交易数据独立 | 是 | 使用 `paper_*` 表族。 |
| 回测交易数据独立 | 是 | 使用 `backtest_*` 表族，并通过 `run_id` 隔离回测批次。 |
| 对外接口一致 | 是 | API 通过 `account_type` 路由到不同表族。 |
| 便于复盘分析 | 是 | `review_session.source` 指向 `live/paper/backtest`，再读取对应表族。 |
| 便于清理回测数据 | 是 | 按 `backtest_run.run_id` 删除回测相关记录。 |
| 防止实盘污染 | 是 | 实盘数据不与模拟盘、回测数据共表。 |
