from typing import Protocol, runtime_checkable
from datetime import datetime
from typing import Optional


@runtime_checkable
class DataSourceAdapter(Protocol):
    """数据源适配器接口"""

    async def get_stock_base_info(self, symbol: str) -> dict:
        """获取个股基础信息"""
        ...

    async def list_stocks(self, market: Optional[str] = None) -> list[dict]:
        """获取股票列表"""
        ...

    async def get_kline_data(
        self,
        symbol: str,
        timeframe: str = "1d",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        """获取K线数据"""
        ...

    async def get_realtime_quote(self, symbol: str) -> dict:
        """获取实时行情"""
        ...

    async def get_batch_realtime_quote(self, symbols: list[str]) -> list[dict]:
        """批量获取实时行情"""
        ...

    async def list_sectors(self, market: Optional[str] = None) -> list[dict]:
        """获取板块列表"""
        ...

    async def get_sector_stocks(self, sector_code: str) -> list[dict]:
        """获取板块成分股"""
        ...

    async def sync_stock_base_info(self, symbols: Optional[list[str]] = None) -> list[dict]:
        """同步个股基础信息"""
        ...

    async def sync_kline_data(
        self,
        symbol: str,
        timeframe: str = "1d",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> list[dict]:
        """同步K线数据"""
        ...