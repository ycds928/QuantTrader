from typing import Optional
from datetime import datetime

from .adapters.base import DataSourceAdapter
from .adapters.mock import MockAdapter
from .repository import (
    StockRepository,
    KLineRepository,
    RealtimeQuoteRepository,
    SectorRepository,
)
from .models import KLineDataModel, RealtimeQuoteModel


class StockService:
    """个股服务"""

    def __init__(self, data_source: DataSourceAdapter, stock_repo: StockRepository):
        self.data_source = data_source
        self.stock_repo = stock_repo

    async def get_stock_base_info(self, symbol: str) -> dict:
        """获取个股基础信息"""
        return await self.data_source.get_stock_base_info(symbol)

    async def list_stocks(self, market: Optional[str] = None) -> list[dict]:
        """获取股票列表"""
        return await self.data_source.list_stocks(market)

    async def sync_stocks(self, symbols: Optional[list[str]] = None) -> list[dict]:
        """批量同步股票基础信息"""
        stocks_data = await self.data_source.sync_stock_base_info(symbols)
        for stock_data in stocks_data:
            await self.stock_repo.upsert(stock_data)
        return stocks_data


class KLineService:
    """K线服务"""

    def __init__(self, data_source: DataSourceAdapter, kline_repo: KLineRepository):
        self.data_source = data_source
        self.kline_repo = kline_repo

    async def get_kline_data(
        self,
        symbol: str,
        timeframe: str = "1d",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        """获取K线数据"""
        return await self.data_source.get_kline_data(symbol, timeframe, start_date, end_date, limit)

    async def sync_kline_data(
        self,
        symbol: str,
        timeframe: str = "1d",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> list[dict]:
        """同步K线数据"""
        klines_data = await self.data_source.sync_kline_data(symbol, timeframe, start_date, end_date)
        klines = [KLineDataModel(**k) for k in klines_data]
        return await self.kline_repo.delete_and_insert(symbol, timeframe, klines)


class MarketDataService:
    """行情服务"""

    def __init__(self, data_source: DataSourceAdapter, quote_repo: RealtimeQuoteRepository):
        self.data_source = data_source
        self.quote_repo = quote_repo

    async def get_realtime_quote(self, symbol: str) -> dict:
        """获取实时行情"""
        return await self.data_source.get_realtime_quote(symbol)

    async def get_batch_realtime_quote(self, symbols: list[str]) -> list[dict]:
        """批量获取实时行情"""
        return await self.data_source.get_batch_realtime_quote(symbols)

    async def get_realtime_quote_cached(self, symbol: str) -> dict:
        """获取实时行情（优先从数据库读取）"""
        cached = await self.quote_repo.get_by_symbol(symbol)
        if cached:
            return {
                "symbol": cached.symbol,
                "name": cached.name,
                "last_price": cached.last_price,
                "change": cached.change,
                "change_pct": cached.change_pct,
                "open": cached.open,
                "high": cached.high,
                "low": cached.low,
                "volume": cached.volume,
                "turnover": cached.turnover,
                "amplitude": cached.amplitude,
                "market_cap": cached.market_cap,
                "float_market_cap": cached.float_market_cap,
                "pe_ratio": cached.pe_ratio,
                "pb_ratio": cached.pb_ratio,
                "timestamp": cached.timestamp,
            }
        return await self.get_realtime_quote(symbol)


class SectorService:
    """板块服务"""

    def __init__(self, data_source: DataSourceAdapter, sector_repo: SectorRepository):
        self.data_source = data_source
        self.sector_repo = sector_repo

    async def list_sectors(self, market: Optional[str] = None) -> list[dict]:
        """获取板块列表"""
        return await self.data_source.list_sectors(market)

    async def get_sector_stocks(self, sector_code: str) -> list[dict]:
        """获取板块成分股"""
        return await self.data_source.get_sector_stocks(sector_code)


def create_services(data_source: Optional[DataSourceAdapter] = None):
    """工厂函数：创建服务实例（依赖注入）"""
    if data_source is None:
        data_source = MockAdapter()
    return {
        "stock_service": StockService(data_source, None),  # repo稍后注入
        "kline_service": KLineService(data_source, None),
        "market_data_service": MarketDataService(data_source, None),
        "sector_service": SectorService(data_source, None),
    }