from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from typing import Optional

from common.database import async_session
from .models import (
    StockBaseInfoModel,
    KLineDataModel,
    RealtimeQuoteModel,
    SectorInfoModel,
)


class StockRepository:
    """个股Repository"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_symbol(self, symbol: str) -> Optional[StockBaseInfoModel]:
        result = await self.session.execute(
            select(StockBaseInfoModel).where(StockBaseInfoModel.symbol == symbol)
        )
        return result.scalar_one_or_none()

    async def get_all(self, market: Optional[str] = None, limit: int = 100, offset: int = 0) -> list[StockBaseInfoModel]:
        query = select(StockBaseInfoModel).where(StockBaseInfoModel.status == "active")
        if market:
            query = query.where(StockBaseInfoModel.market == market)
        query = query.limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create(self, stock: StockBaseInfoModel) -> StockBaseInfoModel:
        self.session.add(stock)
        await self.session.flush()
        return stock

    async def upsert(self, stock_data: dict) -> StockBaseInfoModel:
        existing = await self.get_by_symbol(stock_data["symbol"])
        if existing:
            for key, value in stock_data.items():
                setattr(existing, key, value)
            await self.session.flush()
            return existing
        else:
            new_stock = StockBaseInfoModel(**stock_data)
            self.session.add(new_stock)
            await self.session.flush()
            return new_stock

    async def batch_upsert(self, stocks_data: list[dict]) -> list[StockBaseInfoModel]:
        results = []
        for stock_data in stocks_data:
            results.append(await self.upsert(stock_data))
        return results

    async def search_by_name(
        self,
        keyword: str,
        market: Optional[str] = None,
        limit: int = 50
    ) -> list[StockBaseInfoModel]:
        """根据股票名称或代码模糊搜索"""
        query = select(StockBaseInfoModel).where(
            and_(
                StockBaseInfoModel.status == "active",
                or_(
                    StockBaseInfoModel.symbol.like(f"%{keyword}%"),
                    StockBaseInfoModel.name.like(f"%{keyword}%")
                )
            )
        )
        if market:
            query = query.where(StockBaseInfoModel.market == market)
        query = query.limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())


class KLineRepository:
    """K线Repository"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_kline(
        self,
        symbol: str,
        timeframe: str = "1d",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[KLineDataModel]:
        query = select(KLineDataModel).where(
            and_(
                KLineDataModel.symbol == symbol,
                KLineDataModel.timeframe == timeframe,
            )
        )
        if start_date:
            query = query.where(KLineDataModel.timestamp >= start_date)
        if end_date:
            query = query.where(KLineDataModel.timestamp <= end_date)
        query = query.order_by(KLineDataModel.timestamp.desc()).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create(self, kline: KLineDataModel) -> KLineDataModel:
        self.session.add(kline)
        await self.session.flush()
        return kline

    async def batch_create(self, klines: list[KLineDataModel]) -> list[KLineDataModel]:
        for kline in klines:
            self.session.add(kline)
        await self.session.flush()
        return klines

    async def delete_and_insert(self, symbol: str, timeframe: str, klines: list[KLineDataModel]) -> list[KLineDataModel]:
        """删除旧数据，插入新数据"""
        await self.session.execute(
            KLineDataModel.__table__.delete().where(
                and_(
                    KLineDataModel.symbol == symbol,
                    KLineDataModel.timeframe == timeframe,
                )
            )
        )
        for kline in klines:
            self.session.add(kline)
        await self.session.flush()
        return klines


class RealtimeQuoteRepository:
    """实时行情Repository"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_symbol(self, symbol: str) -> Optional[RealtimeQuoteModel]:
        result = await self.session.execute(
            select(RealtimeQuoteModel).where(RealtimeQuoteModel.symbol == symbol)
        )
        return result.scalar_one_or_none()

    async def get_by_symbols(self, symbols: list[str]) -> list[RealtimeQuoteModel]:
        if not symbols:
            return []
        result = await self.session.execute(
            select(RealtimeQuoteModel).where(RealtimeQuoteModel.symbol.in_(symbols))
        )
        return list(result.scalars().all())

    async def upsert(self, quote_data: dict) -> RealtimeQuoteModel:
        existing = await self.get_by_symbol(quote_data["symbol"])
        if existing:
            for key, value in quote_data.items():
                setattr(existing, key, value)
            await self.session.flush()
            return existing
        else:
            new_quote = RealtimeQuoteModel(**quote_data)
            self.session.add(new_quote)
            await self.session.flush()
            return new_quote


class SectorRepository:
    """板块Repository"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all(self, market: Optional[str] = None) -> list[SectorInfoModel]:
        query = select(SectorInfoModel)
        if market:
            query = query.where(SectorInfoModel.market == market)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_code(self, sector_code: str) -> Optional[SectorInfoModel]:
        result = await self.session.execute(
            select(SectorInfoModel).where(SectorInfoModel.sector_code == sector_code)
        )
        return result.scalar_one_or_none()

    async def upsert(self, sector_data: dict) -> SectorInfoModel:
        existing = await self.get_by_code(sector_data["sector_code"])
        if existing:
            for key, value in sector_data.items():
                setattr(existing, key, value)
            await self.session.flush()
            return existing
        else:
            new_sector = SectorInfoModel(**sector_data)
            self.session.add(new_sector)
            await self.session.flush()
            return new_sector