from fastapi import APIRouter

router = APIRouter(prefix="/api/replay", tags=["历史回放"])


@router.post("/start")
async def start_replay():
    """启动回放"""
    return {"success": True, "data": {}, "message": "模块开发中"}


@router.get("/session/{session_id}")
async def get_replay_session(session_id: int):
    """获取回放会话"""
    return {"success": True, "data": {}, "message": "模块开发中"}


@router.get("/trades/{session_id}")
async def get_replay_trades(session_id: int):
    """获取回放交易记录"""
    return {"success": True, "data": [], "message": "模块开发中"}
