from fastapi import APIRouter

router = APIRouter(prefix="/api/api-data", tags=["API对接-行情数据"])


@router.get("/symbols")
async def get_symbols():
    """获取交易对列表"""
    return {"success": True, "data": [], "message": "模块开发中"}


@router.get("/kline")
async def get_kline(symbol: str = "BTC/USDT", timeframe: str = "1h"):
    """获取K线数据"""
    return {"success": True, "data": [], "message": "模块开发中"}


@router.get("/ticker")
async def get_ticker(symbol: str = "BTC/USDT"):
    """获取实时行情"""
    return {"success": True, "data": {}, "message": "模块开发中"}
