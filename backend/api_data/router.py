from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Any

from common.database import get_db
from common.dependencies import get_data_source
from .adapters.base import DataSourceAdapter
from .adapters.mock import MockAdapter
from .schemas import (
    StockBaseInfo,
    KLineData,
    RealTimeQuote,
    SectorInfo,
    StockListItem,
    KLineQuery,
    BatchStockQuery,
    StockSyncRequest,
    KLineSyncRequest,
    SectorStocksQuery,
    StockSearchQuery,
)
from .service import StockService, KLineService, MarketDataService, SectorService
from .repository import (
    StockRepository,
    KLineRepository,
    RealtimeQuoteRepository,
    SectorRepository,
)

router = APIRouter(prefix="/api/api-data", tags=["API对接-行情数据"])


def get_stock_service(
    db: AsyncSession = Depends(get_db),
    data_source: DataSourceAdapter = Depends(get_data_source),
) -> StockService:
    return StockService(data_source, StockRepository(db))


def get_kline_service(
    db: AsyncSession = Depends(get_db),
    data_source: DataSourceAdapter = Depends(get_data_source),
) -> KLineService:
    return KLineService(data_source, KLineRepository(db))


def get_market_data_service(
    db: AsyncSession = Depends(get_db),
    data_source: DataSourceAdapter = Depends(get_data_source),
) -> MarketDataService:
    return MarketDataService(data_source, RealtimeQuoteRepository(db))


def get_sector_service(
    db: AsyncSession = Depends(get_db),
    data_source: DataSourceAdapter = Depends(get_data_source),
) -> SectorService:
    return SectorService(data_source, SectorRepository(db))


def success_response(data: Any, message: str = "操作成功") -> dict:
    """统一响应格式"""
    return {"success": True, "data": data, "message": message}


def error_response(message: str, status_code: int = 400) -> None:
    """统一错误响应"""
    raise HTTPException(status_code=status_code, detail={"success": False, "message": message})


# ========== 个股接口 ==========


@router.get("/stock/{symbol}/base")
async def get_stock_base_info(symbol: str, service: StockService = Depends(get_stock_service)):
    """获取个股基础信息"""
    data = await service.get_stock_base_info(symbol)
    return success_response(data, "获取成功")


@router.post("/stock/sync")
async def sync_stocks(request: StockSyncRequest, service: StockService = Depends(get_stock_service)):
    """批量同步个股信息"""
    data = await service.sync_stocks(request.symbols)
    return success_response(data, "同步成功")


@router.get("/stock/list")
async def get_stock_list(
    market: Optional[str] = Query(None, description="市场类型 A/HK/US"),
    service: StockService = Depends(get_stock_service),
):
    """获取所有个股列表"""
    data = await service.list_stocks(market)
    return success_response(data, "获取成功")


@router.get("/stock/search")
async def search_stocks(
    keyword: str = Query(..., min_length=1, max_length=50, description="搜索关键词（股票代码或名称）"),
    market: Optional[str] = Query(None, description="市场类型 A/HK/US"),
    limit: int = Query(50, ge=1, le=200, description="返回条数"),
    service: StockService = Depends(get_stock_service),
):
    """根据股票名称或代码模糊搜索"""
    data = await service.search_stocks(keyword, market, limit)
    return success_response(data, "搜索成功")


# ========== K线接口 ==========


@router.get("/kline/{symbol}")
async def get_kline(
    symbol: str,
    timeframe: str = Query("1d", description="时间周期: 1m/5m/15m/30m/1h/1d/1w"),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    limit: int = Query(100, ge=1, le=1000, description="返回条数"),
    service: KLineService = Depends(get_kline_service),
):
    """获取K线数据"""
    data = await service.get_kline_data(symbol, timeframe, start_date, end_date, limit)
    return success_response(data, "获取成功")


@router.post("/kline/{symbol}/sync")
async def sync_kline(
    symbol: str,
    request: KLineSyncRequest,
    service: KLineService = Depends(get_kline_service),
):
    """同步K线数据"""
    data = await service.sync_kline_data(symbol, request.timeframe, request.start_date, request.end_date)
    return success_response(data, "同步成功")


# ========== 实时行情接口 ==========


@router.get("/realtime/{symbol}")
async def get_realtime_quote(symbol: str, service: MarketDataService = Depends(get_market_data_service)):
    """获取实时行情"""
    data = await service.get_realtime_quote(symbol)
    return success_response(data, "获取成功")


@router.post("/realtime/batch")
async def get_batch_realtime_quote(request: BatchStockQuery, service: MarketDataService = Depends(get_market_data_service)):
    """批量获取实时行情"""
    data = await service.get_batch_realtime_quote(request.symbols)
    return success_response(data, "获取成功")


# ========== 板块接口 ==========


@router.get("/sector")
async def get_sector_list(
    market: Optional[str] = Query(None, description="市场类型"),
    service: SectorService = Depends(get_sector_service),
):
    """获取板块列表"""
    data = await service.list_sectors(market)
    return success_response(data, "获取成功")


@router.get("/sector/{sector_code}/stocks")
async def get_sector_stocks(sector_code: str, service: SectorService = Depends(get_sector_service)):
    """获取板块成分股"""
    data = await service.get_sector_stocks(sector_code)
    return success_response(data, "获取成功")