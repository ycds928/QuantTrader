from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from common.config import get_settings
from common.middleware import setup_cors
from api_data.router import router as api_data_router
from account_trading.router import router as account_router
from strategy_engine.router import router as strategy_router
from strategy_execution.router import router as execution_router
from review_analysis.router import router as review_router
from history_replay.router import router as replay_router
from integration_api.router import router as integration_router

settings = get_settings()

app = FastAPI(
    title="QuantFlow API",
    description="个人量化交易平台 API",
    version="0.1.0",
)

# CORS
setup_cors(app)

# 注册各模块路由
app.include_router(api_data_router)
app.include_router(account_router)
app.include_router(strategy_router)
app.include_router(execution_router)
app.include_router(review_router)
app.include_router(replay_router)
app.include_router(integration_router)


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.API_PORT,
        reload=True,
    )
