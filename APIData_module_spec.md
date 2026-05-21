# 数据API模块技术文档

## 1. 模块概述

### 1.1 核心职责
- 从外部数据源获取数据，保存到MySQL数据库
- 从MySQL数据库调取数据供业务使用
- 对外部数据源封装抽象层，支持灵活切换数据源

### 1.2 技术栈
- **Web框架**: Python FastAPI
- **ORM**: SQLAlchemy 2.0
- **数据库**: MySQL 8.0

---

## 2. 架构设计

```
外部数据源 → DataSource Adapter（适配器抽象层）
                      ↓
              DataService（业务服务层）
                      ↓
              SQLAlchemy → MySQL（数据持久化）
                      ↓
              API Routes → 业务调用
```

### 2.1 分层说明
| 层级 | 职责 |
|-----|------|
| `DataSource Adapter` | 封装外部数据源获取逻辑，统一接口 |
| `DataService` | 业务逻辑处理，数据转换 |
| `Repository` | 数据库读写操作 |
| `API Routes` | FastAPI接口暴露 |

---

## 3. 数据库表结构

### 3.1 stock_base_info（个股基础信息表）
```sql
CREATE TABLE stock_base_info (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL UNIQUE COMMENT '股票代码',
    name VARCHAR(100) COMMENT '股票名称',
    industry VARCHAR(100) COMMENT '所属行业',
    listing_date DATE COMMENT '上市日期',
    is_st TINYINT DEFAULT 0 COMMENT '是否ST',
    total_share DECIMAL(20,2) COMMENT '总股本',
    float_share DECIMAL(20,2) COMMENT '流通股本',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_symbol (symbol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 3.2 kline_data（K线数据表）
```sql
CREATE TABLE kline_data (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL COMMENT '股票代码',
    trade_date DATE NOT NULL COMMENT '交易日期',
    open DECIMAL(10,3) COMMENT '开盘价',
    high DECIMAL(10,3) COMMENT '最高价',
    low DECIMAL(10,3) COMMENT '最低价',
    close DECIMAL(10,3) COMMENT '收盘价',
    volume BIGINT COMMENT '成交量',
    amount DECIMAL(20,3) COMMENT '成交额',
    adjust_type VARCHAR(10) DEFAULT 'qfq' COMMENT '复权类型 qfq/hfq',
    data_source VARCHAR(50) COMMENT '数据来源标识',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_symbol_date (symbol, trade_date, adjust_type),
    INDEX idx_symbol (symbol),
    INDEX idx_trade_date (trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 3.3 realtime_quote（实时行情表）
```sql
CREATE TABLE realtime_quote (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL UNIQUE COMMENT '股票代码',
    name VARCHAR(100) COMMENT '股票名称',
    last_price DECIMAL(10,3) COMMENT '最新价',
    open_price DECIMAL(10,3) COMMENT '开盘价',
    high_price DECIMAL(10,3) COMMENT '最高价',
    low_price DECIMAL(10,3) COMMENT '最低价',
    volume BIGINT COMMENT '成交量',
    amount DECIMAL(20,3) COMMENT '成交额',
    update_time TIMESTAMP COMMENT '更新时间',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 3.4 sector_info（板块信息表）
```sql
CREATE TABLE sector_info (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    sector_code VARCHAR(50) NOT NULL UNIQUE COMMENT '板块代码',
    sector_name VARCHAR(100) COMMENT '板块名称',
    sector_type VARCHAR(20) COMMENT '板块类型 industry/concept/index',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

## 4. 数据模型（Python Pydantic Models）

### 4.1 基础数据模型
```python
class StockBaseInfo(BaseModel):
    symbol: str
    name: str | None = None
    industry: str | None = None
    listing_date: date | None = None
    is_st: bool = False
    total_share: float | None = None
    float_share: float | None = None

class KLineData(BaseModel):
    symbol: str
    trade_date: date
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: float | None = None
    adjust_type: str = "qfq"
    data_source: str | None = None

class RealTimeQuote(BaseModel):
    symbol: str
    name: str | None = None
    last_price: float
    open_price: float
    high_price: float
    low_price: float
    volume: int
    amount: float | None = None
    update_time: datetime

class SectorInfo(BaseModel):
    sector_code: str
    sector_name: str
    sector_type: str  # industry/concept/index
```

### 4.2 请求/响应模型
```python
class KLineQuery(BaseModel):
    symbol: str
    start_date: date
    end_date: date
    adjust_type: str = "qfq"

class BatchStockQuery(BaseModel):
    symbol_list: list[str]

class ApiResponse(BaseModel):
    success: bool
    message: str
    data: Any = None
```

---

## 5. 数据源适配器（DataSource Adapter）

### 5.1 抽象接口
```python
class DataSourceAdapter(Protocol):
    """数据源适配器抽象接口"""

    def get_stock_base_info(self, symbol: str) -> StockBaseInfo: ...

    def batch_get_stock_base_info(self, symbol_list: list[str]) -> list[StockBaseInfo]: ...

    def get_kline_data(self, symbol: str, start_date: date, end_date: date, adjust_type: str) -> list[KLineData]: ...

    def get_realtime_quote(self, symbol: str) -> RealTimeQuote: ...

    def batch_get_realtime_quote(self, symbol_list: list[str]) -> list[RealTimeQuote]: ...

    def get_stock_list(self) -> list[StockBaseInfo]: ...

    def get_sector_list(self, sector_type: str | None = None) -> list[SectorInfo]: ...

    def get_sector_stocks(self, sector_code: str) -> list[str]: ...
```

### 5.2 数据源实现
| 适配器 | 说明 |
|-------|------|
| `AkshareAdapter` | akshare数据源封装 |
| `BaostockAdapter` | baostock数据源封装 |
| `CustomBrokerAdapter` | 自定义券商API封装 |

---

## 6. 服务层（DataService）

### 6.1 StockService
```python
class StockService:
    """个股数据服务"""

    def __init__(self, data_source: DataSourceAdapter, repository: StockRepository):
        self.data_source = data_source
        self.repository = repository

    def get_stock_base_info(self, symbol: str, use_cache: bool = True) -> StockBaseInfo:
        """获取个股基础信息"""
        ...

    def sync_stock_base_to_db(self, symbol: str) -> bool:
        """同步个股基础信息到数据库"""
        ...

    def batch_sync_stock_base_to_db(self, symbol_list: list[str]) -> int:
        """批量同步"""
        ...

    def get_stock_base_from_db(self, symbol: str) -> StockBaseInfo | None:
        """从数据库获取个股基础信息"""
        ...
```

### 6.2 KLineService
```python
class KLineService:
    """K线数据服务"""

    def __init__(self, data_source: DataSourceAdapter, repository: KLineRepository):
        self.data_source = data_source
        self.repository = repository

    def get_kline_data(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        adjust_type: str = "qfq",
        prefer_cache: bool = True
    ) -> list[KLineData]:
        """获取K线数据（优先数据库，辅以数据源）"""
        ...

    def sync_kline_to_db(self, symbol: str, kline_list: list[KLineData]) -> int:
        """同步K线数据到数据库"""
        ...

    def get_kline_from_db(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        adjust_type: str = "qfq"
    ) -> list[KLineData]:
        """从数据库获取K线数据"""
        ...
```

### 6.3 MarketDataService
```python
class MarketDataService:
    """行情数据服务"""

    def __init__(self, data_source: DataSourceAdapter, repository: RealtimeQuoteRepository):
        self.data_source = data_source
        self.repository = repository

    def get_realtime_quote(self, symbol: str, use_cache: bool = True) -> RealTimeQuote:
        """获取实时行情"""
        ...

    def batch_get_realtime_quote(self, symbol_list: list[str]) -> list[RealTimeQuote]:
        """批量获取实时行情（直接查数据源，不过缓存）"""
        ...

    def sync_realtime_to_db(self, symbol: str) -> bool:
        """同步实时行情到数据库"""
        ...
```

### 6.4 SectorService
```python
class SectorService:
    """板块数据服务"""

    def get_all_sectors(self, sector_type: str | None = None) -> list[SectorInfo]:
        """获取所有板块"""
        ...

    def sync_sectors_to_db(self) -> int:
        """同步板块数据到数据库"""
        ...

    def get_sector_stocks(self, sector_code: str) -> list[str]:
        """获取板块成分股"""
        ...
```

---

## 7. 仓库层（Repository）

```python
class StockRepository:
    """个股信息仓库"""

    def save(self, stock_info: StockBaseInfo) -> bool: ...
    def batch_save(self, stock_list: list[StockBaseInfo]) -> int: ...
    def get_by_symbol(self, symbol: str) -> StockBaseInfo | None: ...
    def get_all(self) -> list[StockBaseInfo]: ...
    def exists(self, symbol: str) -> bool: ...

class KLineRepository:
    """K线数据仓库"""

    def save(self, kline: KLineData) -> bool: ...
    def batch_save(self, kline_list: list[KLineData]) -> int: ...
    def query(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        adjust_type: str = "qfq"
    ) -> list[KLineData]: ...
    def get_latest_date(self, symbol: str, adjust_type: str = "qfq") -> date | None: ...

class RealtimeQuoteRepository:
    """实时行情仓库"""

    def save(self, quote: RealTimeQuote) -> bool: ...
    def batch_save(self, quote_list: list[RealTimeQuote]) -> int: ...
    def get_by_symbol(self, symbol: str) -> RealTimeQuote | None: ...

class SectorRepository:
    """板块仓库"""

    def save(self, sector: SectorInfo) -> bool: ...
    def batch_save(self, sector_list: list[SectorInfo]) -> int: ...
    def get_by_type(self, sector_type: str) -> list[SectorInfo]: ...
    def get_by_code(self, sector_code: str) -> SectorInfo | None: ...
```

---

## 8. API接口（FastAPI Routes）

### 8.1 个股数据接口
```
GET  /api/v1/stock/{symbol}/base
     → 获取个股基础信息（优先缓存）

POST /api/v1/stock/sync
     body: {"symbol_list": ["000001", "000002"]}
     → 批量同步个股信息到数据库

GET  /api/v1/stock/list
     → 获取所有个股列表
```

### 8.2 K线数据接口
```
GET  /api/v1/kline/{symbol}
     params: start_date, end_date, adjust_type
     → 获取K线数据（优先数据库）

POST /api/v1/kline/{symbol}/sync
     body: {"kline_list": [...]}
     → 同步K线数据到数据库
```

### 8.3 实时行情接口
```
GET  /api/v1/realtime/{symbol}
     → 获取实时行情

POST /api/v1/realtime/batch
     body: {"symbol_list": [...]}
     → 批量获取实时行情
```

### 8.4 板块数据接口
```
GET  /api/v1/sector
     params: sector_type
     → 获取板块列表

GET  /api/v1/sector/{sector_code}/stocks
     → 获取板块成分股
```

---

## 9. 项目目录结构
```
project/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI入口
│   ├── config.py            # 配置
│   ├── database.py          # 数据库连接
│   ├── models/
│   │   ├── __init__.py
│   │   ├── stock.py        # SQLAlchemy模型
│   │   ├── kline.py
│   │   ├── realtime.py
│   │   └── sector.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── stock.py        # Pydantic模型
│   │   ├── kline.py
│   │   ├── realtime.py
│   │   └── common.py
│   ├── repository/
│   │   ├── __init__.py
│   │   ├── stock_repo.py
│   │   ├── kline_repo.py
│   │   ├── realtime_repo.py
│   │   └── sector_repo.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── stock_service.py
│   │   ├── kline_service.py
│   │   ├── market_service.py
│   │   └── sector_service.py
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── base.py         # 适配器基类
│   │   ├── akshare_adapter.py
│   │   └── baostock_adapter.py
│   └── routes/
│       ├── __init__.py
│       ├── stock.py
│       ├── kline.py
│       ├── realtime.py
│       └── sector.py
├── tests/
│   └── ...
├── requirements.txt
└── README.md
```

---

## 10. 使用示例

### 10.1 配置数据源
```python
# 选择使用哪个数据源
data_source = AkshareAdapter()
# 或
data_source = BaostockAdapter()

# 初始化服务
stock_service = StockService(data_source, StockRepository())
```

### 10.2 获取数据（自动处理缓存）
```python
# 优先从数据库获取，无则从数据源获取
stock_info = stock_service.get_stock_base_info("000001")

# 强制从数据源获取并更新缓存
stock_info = stock_service.get_stock_base_info("000001", use_cache=False)
```

### 10.3 同步数据到数据库
```python
# 单个同步
stock_service.sync_stock_base_to_db("000001")

# 批量同步
stock_service.batch_sync_stock_base_to_db(["000001", "000002"])
```

---

## 11. 核心设计原则

1. **数据源可切换**: 通过适配器模式封装外部数据源，可灵活替换
2. **缓存优先**: 优先从MySQL获取，已存在则直接返回
3. **统一接口**: 各数据源适配器实现统一接口，业务代码无需感知数据源差异
4. **批量操作支持**: 批量获取、批量写入数据库
5. **数据模型统一**: SQLAlchemy模型与Pydantic模型分离，数据库结构与API响应解耦