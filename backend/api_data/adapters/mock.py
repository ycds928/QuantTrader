from datetime import datetime, timedelta
from typing import Optional
import random

from .base import DataSourceAdapter


# Mock 数据
MOCK_STOCKS = [
    {"symbol": "000001", "name": "平安银行", "market": "A", "sector": "银行"},
    {"symbol": "000002", "name": "万科A", "market": "A", "sector": "房地产"},
    {"symbol": "600000", "name": "浦发银行", "market": "A", "sector": "银行"},
    {"symbol": "600036", "name": "招商银行", "market": "A", "sector": "银行"},
    {"symbol": "600519", "name": "贵州茅台", "market": "A", "sector": "白酒"},
    {"symbol": "600886", "name": "国电电力", "market": "A", "sector": "电力"},
    {"symbol": "601318", "name": "中国平安", "market": "A", "sector": "保险"},
    {"symbol": "000858", "name": "五粮液", "market": "A", "sector": "白酒"},
    {"symbol": "002594", "name": "比亚迪", "market": "A", "sector": "汽车"},
    {"symbol": "300750", "name": "宁德时代", "market": "A", "sector": "新能源"},
]

MOCK_SECTORS = [
    {"sector_code": "BK0001", "sector_name": "银行", "market": "A", "stock_count": 42, "description": "银行业板块"},
    {"sector_code": "BK0002", "sector_name": "白酒", "market": "A", "stock_count": 18, "description": "白酒行业板块"},
    {"sector_code": "BK0003", "sector_name": "房地产", "market": "A", "stock_count": 65, "description": "房地产行业板块"},
    {"sector_code": "BK0004", "sector_name": "电力", "market": "A", "stock_count": 56, "description": "电力行业板块"},
    {"sector_code": "BK0005", "sector_name": "汽车", "market": "A", "stock_count": 78, "description": "汽车行业板块"},
    {"sector_code": "BK0006", "sector_name": "新能源", "market": "A", "stock_count": 93, "description": "新能源行业板块"},
]


def generate_mock_kline(symbol: str, timeframe: str, days: int = 100) -> list[dict]:
    """生成模拟K线数据"""
    klines = []
    base_price = random.uniform(10, 200)
    now = datetime.now()

    for i in range(days):
        date = now - timedelta(days=days - i - 1)
        if timeframe == "1d":
            date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif timeframe == "1h":
            date = date.replace(minute=0, second=0, microsecond=0)

        change = random.uniform(-0.03, 0.03)
        open_price = base_price * (1 + random.uniform(-0.02, 0.02))
        close_price = open_price * (1 + change)
        high_price = max(open_price, close_price) * (1 + random.uniform(0, 0.02))
        low_price = min(open_price, close_price) * (1 - random.uniform(0, 0.02))
        volume = random.uniform(1000000, 10000000)

        klines.append({
            "symbol": symbol,
            "timeframe": timeframe,
            "timestamp": date,
            "open": round(open_price, 2),
            "high": round(high_price, 2),
            "low": round(low_price, 2),
            "close": round(close_price, 2),
            "volume": round(volume, 2),
            "turnover": round(volume * close_price, 2),
        })
        base_price = close_price

    return klines


def generate_mock_realtime_quote(symbol: str, name: str) -> dict:
    """生成模拟实时行情"""
    base_price = random.uniform(10, 200)
    change = random.uniform(-10, 10)
    change_pct = (change / base_price) * 100

    return {
        "symbol": symbol,
        "name": name,
        "last_price": round(base_price, 2),
        "change": round(change, 2),
        "change_pct": round(change_pct, 2),
        "open": round(base_price * random.uniform(0.98, 1.02), 2),
        "high": round(base_price * random.uniform(1.0, 1.05), 2),
        "low": round(base_price * random.uniform(0.95, 1.0), 2),
        "volume": round(random.uniform(10000000, 100000000), 2),
        "turnover": round(random.uniform(100000000, 1000000000), 2),
        "amplitude": round(random.uniform(1, 10), 2),
        "market_cap": round(base_price * random.uniform(1000000000, 10000000000), 2),
        "float_market_cap": round(base_price * random.uniform(500000000, 5000000000), 2),
        "pe_ratio": round(random.uniform(5, 50), 2),
        "pb_ratio": round(random.uniform(0.5, 5), 2),
        "timestamp": datetime.now(),
    }


class MockAdapter(DataSourceAdapter):
    """Mock数据适配器（内存测试数据）"""

    async def get_stock_base_info(self, symbol: str) -> dict:
        for stock in MOCK_STOCKS:
            if stock["symbol"] == symbol:
                return {**stock, "IPO_date": "2010-01-01", "total_shares": 1000000, "float_shares": 800000, "status": "active"}
        return MOCK_STOCKS[0].copy()

    async def list_stocks(self, market: Optional[str] = None) -> list[dict]:
        if market:
            return [s for s in MOCK_STOCKS if s["market"] == market]
        return MOCK_STOCKS.copy()

    async def get_kline_data(
        self,
        symbol: str,
        timeframe: str = "1d",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        return generate_mock_kline(symbol, timeframe, limit)

    async def get_realtime_quote(self, symbol: str) -> dict:
        stock = MOCK_STOCKS[0]
        for s in MOCK_STOCKS:
            if s["symbol"] == symbol:
                stock = s
                break
        return generate_mock_realtime_quote(stock["symbol"], stock["name"])

    async def get_batch_realtime_quote(self, symbols: list[str]) -> list[dict]:
        quotes = []
        for symbol in symbols:
            quotes.append(await self.get_realtime_quote(symbol))
        return quotes

    async def list_sectors(self, market: Optional[str] = None) -> list[dict]:
        if market:
            return [s for s in MOCK_SECTORS if s["market"] == market]
        return MOCK_SECTORS.copy()

    async def get_sector_stocks(self, sector_code: str) -> list[dict]:
        sector = None
        for s in MOCK_SECTORS:
            if s["sector_code"] == sector_code:
                sector = s
                break
        if not sector:
            return [s for s in MOCK_STOCKS if s["sector"] == "银行"]
        sector_name = sector["sector_name"]
        return [s for s in MOCK_STOCKS if s["sector"] == sector_name]

    async def sync_stock_base_info(self, symbols: Optional[list[str]] = None) -> list[dict]:
        if symbols:
            return [s for s in MOCK_STOCKS if s["symbol"] in symbols]
        return MOCK_STOCKS.copy()

    async def sync_kline_data(
        self,
        symbol: str,
        timeframe: str = "1d",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> list[dict]:
        return generate_mock_kline(symbol, timeframe, 100)