from fastapi import APIRouter

router = APIRouter(prefix="/api/strategy", tags=["策略引擎"])


@router.get("/list")
async def get_strategies():
    """获取策略列表"""
    return {"success": True, "data": [], "message": "模块开发中"}


@router.post("/create")
async def create_strategy():
    """创建策略"""
    return {"success": True, "data": {}, "message": "模块开发中"}


@router.get("/{strategy_id}")
async def get_strategy(strategy_id: int):
    """获取策略详情"""
    return {"success": True, "data": {}, "message": "模块开发中"}
