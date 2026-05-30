# 数据API模块技术文档

## 1. 模块概述

### 1.1 核心职责
- 从外部数据源获取数据，保存到MySQL数据库
- 从MySQL数据库调取数据供业务使用
- 对外部数据源封装抽象层，支持灵活切换数据源

### 1.2 技术栈
- **Web框架**: Python FastAPI + uvicorn (0.115 / 0.32)
- **ORM**: SQLAlchemy 2.0 (async) + aiomysql
- **数据库**: MySQL 8.0 (utf8mb4)
- **配置**: pydantic-settings + .env

---

## 2. 架构设计

```
外部数据源 → DataSource Adapter（适配器抽象层）
                      ↓
              DataService（业务服务层）
                      ↓
              SQLAlchemy (async) → MySQL（数据持久化）
                      ↓
              API Routes → 业务调用
```

### 2.1 分层说明
| 层级 | 职责 |
|-----|------|
| `DataSource Adapter` | 封装外部数据源获取逻辑，统一接口 |
| `DataService` | 业务逻辑处理，数据转换 |
| `Repository` | 异步数据库读写操作 |
| `API Routes` | FastAPI Router 接口暴露 |

---

## 3. 目录结构

符合 DEVELOPMENT.md 规范的后端模块结构：

```
backend/api_data/
├── __init__.py
├── router.py       # APIRouter，定义路由
├── models.py       # SQLAlchemy Model
├── schemas.py      # Pydantic 请求/响应 Schema
├── service.py      # 业务逻辑层
└── dependencies.py # 模块级依赖注入（可选）
```

前端对应模块：

```
frontend/src/api-data/
├── pages/          # 页面组件
├── components/     # 模块私有组件
├── hooks/          # 模块私有 Hook
├── api/            # API 请求函数
└── types/          # 模块私有类型
```

---

## 4. 数据库表结构

### 4.1 stock_base_info（个股基础信息表）
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

### 4.2 kline_data（K线数据表）
```sql
CREATE TABLE kline_data (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL COMMENT '股票代码',
    timeframe VARCHAR(10) NOT NULL COMMENT '时间周期 1m/5m/15m/30m/1h/1d/1w',
    timestamp TIMESTAMP NOT NULL COMMENT 'K线时间戳',
    open FLOAT NOT NULL COMMENT '开盘价',
    high FLOAT NOT NULL COMMENT '最高价',
    low FLOAT NOT NULL COMMENT '最低价',
    close FLOAT NOT NULL COMMENT '收盘价',
    volume FLOAT NOT NULL COMMENT '成交量',
    turnover FLOAT COMMENT '成交额',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_symbol_timeframe_timestamp (symbol, timeframe, timestamp),
    INDEX idx_symbol_timeframe (symbol, timeframe),
    INDEX idx_timestamp (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**支持的级别（timeframe）**：
- `1m` - 1分钟
- `5m` - 5分钟
- `15m` - 15分钟
- `30m` - 30分钟
- `1h` - 1小时
- `1d` - 日线
- `1w` - 周线

### 4.3 realtime_quote（实时行情表）
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

### 4.4 sector_info（板块信息表）
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

## 5. 数据模型（Python Pydantic Models）

### 5.1 基础数据模型
```python
from datetime import date, datetime
from typing import Any
from pydantic import BaseModel

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
    timeframe: str  # 1m/5m/15m/30m/1h/1d/1w
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    turnover: float | None = None

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

### 5.2 请求/响应模型
```python
class KLineQuery(BaseModel):
    symbol: str
    timeframe: str = "1d"  # 1m/5m/15m/30m/1h/1d/1w
    start_date: date | None = None
    end_date: date | None = None
    limit: int = 100

class BatchStockQuery(BaseModel):
    symbol_list: list[str]

class StockSearchQuery(BaseModel):
    keyword: str  # 搜索关键词（股票代码或名称）
    market: str | None = None  # 市场类型 A/HK/US
    limit: int = 50  # 返回条数，最大200

class ApiResponse(BaseModel):
    success: bool
    message: str
    data: Any = None

class PaginatedResponse(BaseModel):
    success: bool
    message: str
    data: Any = None
    total: int = 0
    page: int = 1
    page_size: int = 20
```

---

## 6. 数据源适配器（DataSource Adapter）

### 6.1 抽象接口
```python
from datetime import date
from typing import Protocol

class DataSourceAdapter(Protocol):
    """数据源适配器抽象接口"""

    def get_stock_base_info(self, symbol: str) -> StockBaseInfo: ...

    def batch_get_stock_base_info(self, symbol_list: list[str]) -> list[StockBaseInfo]: ...

    def get_kline_data(self, symbol: str, timeframe: str, start_date: date | None, end_date: date | None, limit: int) -> list[KLineData]: ...

    def get_realtime_quote(self, symbol: str) -> RealTimeQuote: ...

    def batch_get_realtime_quote(self, symbol_list: list[str]) -> list[RealTimeQuote]: ...

    def get_stock_list(self) -> list[StockBaseInfo]: ...

    def get_sector_list(self, sector_type: str | None = None) -> list[SectorInfo]: ...

    def get_sector_stocks(self, sector_code: str) -> list[str]: ...
```

### 6.2 数据源实现
| 适配器 | 说明 |
|-------|------|
| `AkshareAdapter` | akshare数据源封装 |
| `BaostockAdapter` | baostock数据源封装 |
| `CustomBrokerAdapter` | 自定义券商API封装 |

---

## 7. 服务层（DataService）

### 7.1 StockService
```python
class StockService:
    """个股数据服务"""

    def __init__(self, data_source: DataSourceAdapter, repository: StockRepository):
        self.data_source = data_source
        self.repository = repository

    def get_stock_base_info(self, symbol: str, use_cache: bool = True) -> StockBaseInfo:
        """获取个股基础信息"""
        ...

    def list_stocks(self, market: str | None = None) -> list[StockBaseInfo]:
        """获取股票列表"""
        ...

    def search_stocks(self, keyword: str, market: str | None = None, limit: int = 50) -> list[StockBaseInfo]:
        """根据股票名称或代码模糊搜索"""
        ...

    def sync_stocks(self, symbols: list[str] | None = None) -> list[StockBaseInfo]:
        """同步股票信息到数据库"""
        ...
```

### 7.2 KLineService
```python
class KLineService:
    """K线数据服务"""

    def __init__(self, data_source: DataSourceAdapter, repository: KLineRepository):
        self.data_source = data_source
        self.repository = repository

    def get_kline_data(
        self,
        symbol: str,
        timeframe: str = "1d",
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 100
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

### 7.3 MarketDataService
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

### 7.4 SectorService
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

## 8. 仓库层（Repository）

```python
class StockRepository:
    """个股信息仓库"""

    async def get_by_symbol(self, symbol: str) -> StockBaseInfo | None: ...
    async def get_all(self, market: str | None = None, limit: int = 100, offset: int = 0) -> list[StockBaseInfo]: ...
    async def search_by_name(self, keyword: str, market: str | None = None, limit: int = 50) -> list[StockBaseInfo]: ...
    async def upsert(self, stock_data: dict) -> StockBaseInfo: ...
    async def batch_upsert(self, stocks_data: list[dict]) -> list[StockBaseInfo]: ...

class KLineRepository:
    """K线数据仓库"""

    async def save(self, kline: KLineData) -> bool: ...
    async def batch_save(self, kline_list: list[KLineData]) -> int: ...
    async def query(
        self,
        symbol: str,
        timeframe: str = "1d",
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 100
    ) -> list[KLineData]: ...
    async def get_latest_date(self, symbol: str, timeframe: str = "1d") -> date | None: ...

class RealtimeQuoteRepository:
    """实时行情仓库"""

    async def save(self, quote: RealTimeQuote) -> bool: ...
    async def batch_save(self, quote_list: list[RealTimeQuote]) -> int: ...
    async def get_by_symbol(self, symbol: str) -> RealtimeQuote | None: ...

class SectorRepository:
    """板块仓库"""

    async def save(self, sector: SectorInfo) -> bool: ...
    async def batch_save(self, sector_list: list[SectorInfo]) -> int: ...
    async def get_by_type(self, sector_type: str) -> list[SectorInfo]: ...
    async def get_by_code(self, sector_code: str) -> SectorInfo | None: ...
```

---

## 9. API接口（FastAPI Routes）

**基础路径**: `/api/api-data`

### 9.1 个股数据接口
```
GET  /api/api-data/stock/{symbol}/base
     → 获取个股基础信息（优先缓存）

POST /api/api-data/stock/sync
     body: {"symbol_list": ["000001", "000002"]}
     → 批量同步个股信息到数据库

GET  /api/api-data/stock/list
     params: market
     → 获取所有个股列表

GET  /api/api-data/stock/search
     params: keyword, market, limit
     → 根据股票名称或代码模糊搜索
     keyword: 搜索关键词（支持股票代码和名称模糊匹配）
```

### 9.2 K线数据接口
```
GET  /api/api-data/kline/{symbol}
     params: timeframe, start_date, end_date, limit
     → 获取K线数据（优先数据库）
     timeframe: 1m/5m/15m/30m/1h/1d/1w

POST /api/api-data/kline/{symbol}/sync
     body: {"timeframe": "1d", "start_date": "...", "end_date": "..."}
     → 同步K线数据到数据库
```

### 9.3 实时行情接口
```
GET  /api/api-data/realtime/{symbol}
     → 获取实时行情

POST /api/api-data/realtime/batch
     body: {"symbol_list": [...]}
     → 批量获取实时行情
```

### 9.4 板块数据接口
```
GET  /api/api-data/sector
     params: sector_type
     → 获取板块列表

GET  /api/api-data/sector/{sector_code}/stocks
     → 获取板块成分股
```

---

## 10. 统一响应格式

所有接口必须返回统一格式：

```python
# 成功
return {"success": True, "data": result, "message": "操作成功"}

# 失败（HTTP 异常）
raise HTTPException(status_code=400, detail={"success": False, "message": "参数错误"})
```

前端 `ApiResponse<T>` 对应此结构。

---

## 11. 数据库异步操作示例

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from common.database import get_db, Base, TimestampMixin

class StockBaseInfoModel(Base, TimestampMixin):
    __tablename__ = "stock_base_info"
    id = Column(BigInteger, primary_key=True)
    symbol = Column(String(10), nullable=False, unique=True)
    name = Column(String(100))

@router.get("/list")
async def list_stocks(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(StockBaseInfoModel))
    stocks = result.scalars().all()
    return {
        "success": True,
        "data": [{"symbol": s.symbol, "name": s.name} for s in stocks],
        "message": "查询成功"
    }
```

---

## 12. 使用示例

### 12.1 配置数据源
```python
# 选择使用哪个数据源
data_source = AkshareAdapter()
# 或
data_source = BaostockAdapter()

# 初始化服务
stock_service = StockService(data_source, StockRepository())
```

### 12.2 获取数据（自动处理缓存）
```python
# 获取个股基础信息
stock_info = await stock_service.get_stock_base_info("000001")

# 获取K线数据（支持多种级别）
klines_1d = await kline_service.get_kline_data("000001", timeframe="1d", limit=100)
klines_1h = await kline_service.get_kline_data("000001", timeframe="1h", limit=100)
klines_5m = await kline_service.get_kline_data("000001", timeframe="5m", limit=100)

# 获取实时行情
quote = await market_service.get_realtime_quote("000001")
```

### 12.3 同步数据到数据库
```python
# 单个同步
await stock_service.sync_stock_base_to_db("000001")

# 批量同步
await stock_service.batch_sync_stock_base_to_db(["000001", "000002"])
```

---

## 13. 核心设计原则

1. **数据源可切换**: 通过适配器模式封装外部数据源，可灵活替换
2. **缓存优先**: 优先从MySQL获取，已存在则直接返回
3. **统一接口**: 各数据源适配器实现统一接口，业务代码无需感知数据源差异
4. **批量操作支持**: 批量获取、批量写入数据库
5. **数据模型统一**: SQLAlchemy模型与Pydantic模型分离，数据库结构与API响应解耦
6. **异步优先**: 使用 SQLAlchemy 2.0 async 模式，配合 `await` 异步操作
7. **级别支持**: K线数据支持多个时间周期（1m/5m/15m/30m/1h/1d/1w），通过 (symbol, timeframe, timestamp) 唯一索引区分

---

## 14. 开发状态 (2026-05-21)

### Phase 1: 已完成 ✅
- [x] `backend/api_data/models.py` - SQLAlchemy 模型
  - StockBaseInfoModel, KLineDataModel, RealtimeQuoteModel, SectorInfoModel
  - 继承 Base + TimestampMixin
- [x] `backend/api_data/schemas.py` - Pydantic 模型
  - StockBaseInfo, KLineData, RealTimeQuote, SectorInfo
  - 请求模型: KLineQuery, BatchStockQuery, StockSyncRequest, KLineSyncRequest
- [x] `backend/api_data/repository.py` - Repository 层
  - StockRepository, KLineRepository, RealtimeQuoteRepository, SectorRepository
  - 所有方法为 async def
- [x] `backend/api_data/adapters/base.py` - DataSourceAdapter Protocol
- [x] `backend/api_data/adapters/mock.py` - MockAdapter (内存测试数据)
- [x] `backend/api_data/adapters/__init__.py`
- [x] `backend/api_data/service.py` - Service 层
  - StockService, KLineService, MarketDataService, SectorService
  - 依赖注入 data_source + repository
- [x] `backend/api_data/router.py` - API 接口已实现
- [x] `backend/common/dependencies.py` - get_data_source() 依赖注入
- [x] `frontend/src/api-data/types/index.ts` - TypeScript 类型
- [x] `frontend/src/api-data/api/index.ts` - API 请求函数
- [x] `frontend/src/api-data/pages/ApiData.tsx` - 股票搜索和列表
- [x] `frontend/src/api-data/pages/SymbolDetail.tsx` - 股票详情+K线图表
- [x] `frontend/src/api-data/pages/Dashboard.tsx` - 市场概览

### Phase 2: 已完成 ✅
- [x] 创建 `AkshareAdapter` 实现真实的 akshare 数据调用
- [x] 数据库表创建脚本 (`backend/api_data/init_db.py`)
- [ ] 创建 `BaostockAdapter` 实现真实的 baostock 数据调用（可选）
- [ ] 数据同步调度机制

### 当前数据源
- **使用**: AkshareAdapter (真实市场数据)
- **位置**: `backend/api_data/adapters/akshare.py`
- **切换方式**: 修改 `backend/common/dependencies.py` 中的 `get_data_source()`
- **注意**: K线数据接口可能不稳定（有重试机制）

### 当前数据库
- **配置**: MySQL (阿里云 RDS)
- **连接信息**: 见 `backend/.env`
- **表结构**: `backend/api_data/init_db.py`

### API 端点测试结果
```
✅ GET /api/api-data/stock/list          → 5519只真实股票
⚠️  GET /api/api-data/kline/000001       → K线接口不稳定（网络问题）
✅ GET /api/api-data/realtime/000001     → 实时行情正常
⚠️  GET /api/api-data/sector              → 板块接口不稳定（网络问题）
```

### 待其他模块调用的接口
其他模块可通过以下方式获取股票数据：
```python
# 方式1: 直接调用 API
GET http://localhost:8000/api/api-data/stock/list
GET http://localhost:8000/api/api-data/kline/{symbol}?timeframe=1d
GET http://localhost:8000/api/api-data/realtime/{symbol}
GET http://localhost:8000/api/api-data/sector

# K线级别参数
timeframe: 1m/5m/15m/30m/1h/1d/1w

# 方式2: 导入 api_data 模块（需等 Phase 2）
from api_data.service import StockService, KLineService
```

### 下一步工作
1. ~~实现 AkshareAdapter 替换 MockAdapter~~ ✅ 已完成
2. ~~解决 MySQL 数据库连接问题~~ ✅ 已完成
3. ~~创建数据库表初始化脚本~~ ✅ 已完成
4. 实现定时数据同步
5. 解决 K线/板块接口网络不稳定问题（可能需要代理或备选数据源）

---

## 15. 代码风格合规性

### 检查结果 (2026-05-21)

| 检查项 | 状态 | 说明 |
|-------|------|------|
| 后端命名 (snake_case) | ✅ | models.py, repository.py, adapters/ |
| 前端命名 (kebab-case) | ✅ | api-data/pages/, api-data/types/ |
| 类型注解 | ✅ | 后端函数标注类型，前端 interface/type 定义 |
| 路径别名 (@/) | ✅ | 使用 `@/` 而不是相对路径 |
| 导入顺序 | ✅ | 标准库 → 第三方 → 本地 |
| async/await | ✅ | Repository 层全部使用 async |
| CSS 变量 class | ✅ | 使用 bg-surface-container-high 等 class |

### 已知偏差

| 问题 | 说明 | 处理方式 |
|------|------|---------|
| 前端组件默认导出 | CODE_STYLE.md 第73行要求禁止默认导出，但 lazy() 动态导入需要默认导出 | 保持与其他模块一致，后续统一修改 |
| 提交信息格式 | 应使用 `feat(api-data): ...` 格式 | 本次已按计划执行 |

### 相关文件
- `frontend/src/api-data/pages/ApiData.tsx`
- `frontend/src/api-data/pages/SymbolDetail.tsx`
- `frontend/src/api-data/pages/Dashboard.tsx`
- `frontend/src/common/router/routes.ts`
- `backend/api_data/adapters/akshare.py` (Phase 2 新增)
- `backend/api_data/init_db.py` (Phase 2 新增)
- `backend/common/dependencies.py` (Phase 2 更新)
