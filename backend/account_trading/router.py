from fastapi import APIRouter

router = APIRouter(prefix="/api/account", tags=["账户与交易"])


@router.get("/balance")
async def get_balance():
    """获取账户余额"""
    return {"success": True, "data": {}, "message": "模块开发中"}


@router.get("/positions")
async def get_positions():
    """获取持仓列表"""
    return {"success": True, "data": [], "message": "模块开发中"}


@router.get("/orders")
async def get_orders():
    """获取订单列表"""
    return {"success": True, "data": [], "message": "模块开发中"}


@router.post("/order")
async def place_order():
    """下单"""
    return {"success": True, "data": {}, "message": "模块开发中"}
