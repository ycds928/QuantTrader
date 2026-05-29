# 模拟交易引擎实时行情接口需求文档

## 目标

为 QuantFlow 模拟交易引擎提供足够真实的实时行情、盘口、涨跌停、交易状态、成交量和费用配置输入，使模拟账户可以完成：

- 限价单撮合
- 涨跌停校验
- 停牌/休市校验
- 盘口价成交
- 部分成交
- 成交量约束
- 滑点模拟
- 手续费、印花税、过户费计算
- 持仓市值刷新
- 资金快照持续持久化

当前系统会把模拟交易结果持久化到：

- `paper_order`
- `paper_trade`
- `paper_position_snapshot`
- `paper_balance_snapshot`
- `paper_order_status_log`

## 接口约定

### 基础要求

- 协议：HTTP JSON 或 WebSocket JSON 均可，HTTP 为最低必需。
- 编码：UTF-8。
- 时间：ISO 8601，建议带毫秒和时区，例如 `2026-05-25T09:31:12.123+08:00`。
- 数值：价格、金额、比例字段建议使用字符串，避免浮点精度问题。
- 股票代码：必须提供交易所或统一代码格式，避免 `600519` 与其他市场代码冲突。
- 行情延迟：必须返回行情时间 `timestamp`，并说明实时、准实时或延迟分钟数。
- 停牌、集合竞价、午休、收盘等状态必须明确返回，不允许只返回空行情。

## 必需接口

### 1. 单证券实时行情

`GET /quote/latest?symbol=600519&exchange=SH`

用途：

- 模拟下单撮合
- 涨跌停校验
- 交易状态校验
- 持仓市值刷新

响应示例：

```json
{
  "success": true,
  "data": {
    "symbol": "600519",
    "exchange": "SH",
    "name": "贵州茅台",
    "timestamp": "2026-05-25T10:12:03.456+08:00",
    "trading_status": "trading",
    "last_price": "1688.88",
    "pre_close": "1660.00",
    "open_price": "1668.00",
    "high_price": "1699.00",
    "low_price": "1658.00",
    "limit_up": "1826.00",
    "limit_down": "1494.00",
    "volume": 1234567,
    "turnover": "2087654321.00",
    "bid_price_1": "1688.80",
    "bid_volume_1": 1200,
    "ask_price_1": "1688.90",
    "ask_volume_1": 800
  },
  "message": "ok"
}
```

必需字段：

| 字段 | 类型 | 必需 | 说明 |
|---|---:|---:|---|
| `symbol` | string | 是 | 证券代码 |
| `exchange` | string | 是 | `SH` / `SZ` / `BJ` |
| `timestamp` | string | 是 | 行情时间 |
| `trading_status` | string | 是 | 交易状态 |
| `last_price` | string | 是 | 最新价 |
| `limit_up` | string | 是 | 当日涨停价 |
| `limit_down` | string | 是 | 当日跌停价 |
| `volume` | integer | 是 | 当日累计成交量，单位股 |

推荐字段：

| 字段 | 类型 | 说明 |
|---|---:|---|
| `name` | string | 证券名称 |
| `pre_close` | string | 昨收价 |
| `open_price` | string | 开盘价 |
| `high_price` | string | 当日最高价 |
| `low_price` | string | 当日最低价 |
| `turnover` | string | 当日成交额 |
| `bid_price_1` / `ask_price_1` | string | 买一/卖一价 |
| `bid_volume_1` / `ask_volume_1` | integer | 买一/卖一量，单位股 |

`trading_status` 枚举：

| 值 | 说明 | 模拟撮合行为 |
|---|---|---|
| `trading` | 连续竞价 | 允许撮合 |
| `auction` | 集合竞价 | 可配置是否允许撮合，默认不成交 |
| `halted` | 停牌 | 拒单 |
| `suspended` | 临停/停牌 | 拒单 |
| `lunch_break` | 午休 | 保持待成交 |
| `closed` | 收盘 | 保持待成交或拒单 |
| `unknown` | 未知 | 可配置，默认谨慎处理 |

### 2. 批量实时行情

`GET /quote/batch?symbols=SH.600519,SZ.000001,SZ.301183`

用途：

- 定时刷新模拟账户持仓市值
- 更新 `paper_position_snapshot`
- 更新 `paper_balance_snapshot`

响应示例：

```json
{
  "success": true,
  "data": [
    {
      "symbol": "600519",
      "exchange": "SH",
      "timestamp": "2026-05-25T10:12:03.456+08:00",
      "trading_status": "trading",
      "last_price": "1688.88",
      "limit_up": "1826.00",
      "limit_down": "1494.00",
      "volume": 1234567
    }
  ],
  "message": "ok"
}
```

要求：

- 单次至少支持 100 个证券。
- 返回顺序可以不同，但必须有 `symbol` + `exchange`。
- 某个证券失败时，不应导致整批失败；建议在单项中返回 `error_code` / `error_message`。

### 3. 五档盘口

`GET /quote/orderbook?symbol=600519&exchange=SH&levels=5`

用途：

- 更真实地按卖一/买一或多档盘口撮合
- 支持部分成交
- 支持成交量约束

响应示例：

```json
{
  "success": true,
  "data": {
    "symbol": "600519",
    "exchange": "SH",
    "timestamp": "2026-05-25T10:12:03.456+08:00",
    "bids": [
      { "price": "1688.80", "volume": 1200 },
      { "price": "1688.70", "volume": 1600 }
    ],
    "asks": [
      { "price": "1688.90", "volume": 800 },
      { "price": "1689.00", "volume": 2300 }
    ]
  },
  "message": "ok"
}
```

要求：

- `bids` 按价格从高到低排序。
- `asks` 按价格从低到高排序。
- `volume` 单位为股。
- 如果只提供一档盘口，也必须明确说明。

## 推荐接口

### 4. 交易日历

`GET /quote/trading-calendar?date=2026-05-25&exchange=SH`

用途：

- 判断是否交易日
- 判断开盘、午休、收盘
- 避免模拟引擎在非交易时间错误成交

响应字段：

| 字段 | 类型 | 说明 |
|---|---:|---|
| `is_trading_day` | boolean | 是否交易日 |
| `sessions` | array | 交易时段 |
| `timezone` | string | 时区，A 股为 `Asia/Shanghai` |

### 5. 涨跌停与证券状态

`GET /quote/security-status?symbol=600519&exchange=SH`

用途：

- 获取涨跌停价
- 获取 ST、新股、北交所等不同涨跌幅规则
- 获取停牌、退市整理、风险警示状态

推荐字段：

| 字段 | 类型 | 说明 |
|---|---:|---|
| `limit_up` | string | 涨停价 |
| `limit_down` | string | 跌停价 |
| `price_tick` | string | 最小价格变动单位，通常 `0.01` |
| `lot_size` | integer | 最小交易单位，A 股通常买入 100 |
| `sell_lot_size` | integer | 卖出单位，A 股可零股卖出时需说明 |
| `is_st` | boolean | 是否 ST |
| `is_halted` | boolean | 是否停牌 |

## 模拟引擎撮合规则

### 限价买入

- 使用卖一价作为优先参考价。
- 如果没有盘口，使用最新价。
- 应用买入滑点后得到模拟成交价。
- 如果模拟成交价高于委托价，订单保持 `submitted`。
- 如果超过涨停价，订单 `rejected`。
- 如果资金不足，订单 `rejected`。

### 限价卖出

- 使用买一价作为优先参考价。
- 如果没有盘口，使用最新价。
- 应用卖出滑点后得到模拟成交价。
- 如果模拟成交价低于委托价，订单保持 `submitted`。
- 如果低于跌停价，订单 `rejected`。
- 如果可卖持仓不足，订单 `rejected`。

### 部分成交

部分成交由以下约束共同决定：

- 委托数量
- 盘口可成交量
- 当日成交量比例上限

当前建议默认配置：

```json
{
  "volume_limit_ratio": "0.05"
}
```

即单笔模拟成交最多不超过当日累计成交量的 5%。如果行情方提供盘口，则还受盘口量限制。

### 费用规则

默认建议：

```json
{
  "commission_rate": "0.00025",
  "min_commission": "5",
  "stamp_tax_rate_sell": "0.0005",
  "transfer_fee_rate": "0"
}
```

费用计算：

- 买入费用 = 佣金 + 过户费
- 卖出费用 = 佣金 + 印花税 + 过户费
- 买入现金扣减 = 成交金额 + 费用
- 卖出现金增加 = 成交金额 - 费用

### 滑点规则

推荐配置：

```json
{
  "type": "fixed_tick",
  "value": "0.01"
}
```

枚举：

| 类型 | 说明 |
|---|---|
| `none` | 不应用滑点 |
| `fixed_tick` | 固定价格跳动 |
| `percent` | 按成交参考价比例 |

## 对接验收标准

行情提供方需要满足：

- 行情时间准确，不能返回陈旧行情且无标识。
- 单票行情接口 P95 延迟建议小于 300ms。
- 批量行情接口 P95 延迟建议小于 1000ms。
- 涨跌停价必须与交易所规则一致。
- 停牌/休市状态必须明确。
- 盘口量单位必须说明，默认按股。
- 价格必须是精确字符串。
- 异常响应必须包含稳定 `error_code`。

异常响应示例：

```json
{
  "success": false,
  "error_code": "QUOTE_NOT_FOUND",
  "message": "未找到证券实时行情",
  "data": null
}
```

## 后续系统接入点

当前代码中的接入抽象：

- `backend/account_trading/paper_engine/schemas.py`
- `backend/account_trading/paper_engine/market_data.py`
- `backend/account_trading/paper_engine/engine.py`

后续只需要新增一个真实行情 Provider，实现：

```python
class MarketDataProvider:
    async def get_quote(self, symbol: str) -> RealtimeQuote:
        ...

    async def get_quotes(self, symbols: list[str]) -> dict[str, RealtimeQuote]:
        ...
```

然后替换 `PaperTradingEngine(market_data=...)` 的默认 Provider 即可。
