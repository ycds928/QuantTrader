from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class StockBaseInfo(BaseModel):
    """个股基础信息"""
    id: Optional[int] = None
    symbol: str
    name: str
    market: str
    sector: Optional[str] = None
    IPO_date: Optional[str] = None
    total_shares: Optional[float] = None
    float_shares: Optional[float] = None
    status: str = "active"
    created_at: datetime
    updated_at: datetime


class KLineData(BaseModel):
    """K线数据"""
    id: Optional[int] = None
    symbol: str
    timeframe: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    turnover: Optional[float] = None


class RealTimeQuote(BaseModel):
    """实时行情"""
    id: Optional[int] = None
    symbol: str
    name: str
    last_price: float
    change: float
    change_pct: float
    open: float
    high: float
    low: float
    volume: float
    turnover: Optional[float] = None
    amplitude: Optional[float] = None
    market_cap: Optional[float] = None
    float_market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    timestamp: datetime


class SectorInfo(BaseModel):
    """板块信息"""
    id: Optional[int] = None
    sector_code: str
    sector_name: str
    market: str
    stock_count: int = 0
    description: Optional[str] = None


class StockListItem(BaseModel):
    """股票列表项（简化）"""
    symbol: str
    name: str
    market: str
    sector: Optional[str] = None


# ========== 请求模型 ==========

class KLineQuery(BaseModel):
    """K线查询参数"""
    symbol: str = Field(..., description="股票代码")
    timeframe: str = Field(default="1d", description="时间周期: 1m/5m/15m/30m/1h/1d/1w")
    start_date: Optional[str] = Field(None, description="开始日期 YYYY-MM-DD")
    end_date: Optional[str] = Field(None, description="结束日期 YYYY-MM-DD")
    limit: int = Field(default=100, ge=1, le=1000, description="返回条数")


class BatchStockQuery(BaseModel):
    """批量股票查询"""
    symbols: list[str] = Field(..., min_length=1, max_length=100, description="股票代码列表")


class StockSyncRequest(BaseModel):
    """股票同步请求"""
    symbols: Optional[list[str]] = Field(None, description="指定股票代码，为空则同步所有")


class KLineSyncRequest(BaseModel):
    """K线同步请求"""
    symbol: str
    timeframe: str = "1d"
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class SectorStocksQuery(BaseModel):
    """板块成分股查询"""
    sector_code: str


class StockSearchQuery(BaseModel):
    """股票搜索查询"""
    keyword: str = Field(..., min_length=1, max_length=50, description="搜索关键词（股票代码或名称）")
    market: Optional[str] = Field(None, description="市场类型 A/HK/US")
    limit: int = Field(default=50, ge=1, le=200, description="返回条数")