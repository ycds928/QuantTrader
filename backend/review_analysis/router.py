from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from common.dependencies import get_db

from .repository import ReviewAnalysisRepository


router = APIRouter(prefix="/api/review", tags=["复盘分析"])


class ApiResponse(BaseModel):
    success: bool
    data: Any = None
    message: str = ""


class GenerateReviewRequest(BaseModel):
    account_id: int = Field(..., gt=0, description="复盘账户 ID")
    start_date: date | None = Field(default=None, description="复盘开始日期")
    end_date: date | None = Field(default=None, description="复盘结束日期")
    title: str | None = Field(default=None, max_length=128, description="复盘标题")
    strategy_id: str | None = Field(default=None, max_length=64, description="策略 ID")
    version_id: str | None = Field(default=None, max_length=64, description="策略版本 ID")
    benchmark_symbol: str | None = Field(default=None, max_length=32, description="基准代码")
    run_id: str | None = Field(default=None, max_length=64, description="回测运行批次 ID")

    @model_validator(mode="after")
    def validate_dates(self) -> "GenerateReviewRequest":
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("复盘开始日期不能晚于结束日期")
        return self


def ok(data: Any, message: str = "ok") -> ApiResponse:
    return ApiResponse(success=True, data=data, message=message)


def raise_api_error(exc: Exception) -> None:
    if isinstance(exc, HTTPException):
        raise exc
    if isinstance(exc, LookupError):
        raise HTTPException(status_code=404, detail={"message": str(exc), "type": "not_found"}) from exc
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=400, detail={"message": str(exc), "type": "invalid_request"}) from exc
    raise HTTPException(status_code=500, detail={"message": str(exc), "type": type(exc).__name__}) from exc


@router.get("/accounts", response_model=ApiResponse)
async def list_review_accounts(db: AsyncSession = Depends(get_db)):
    """获取可复盘账户列表。"""
    repo = ReviewAnalysisRepository(db)
    return ok(await repo.list_accounts(), "复盘账户列表已获取")


@router.get("/sessions", response_model=ApiResponse)
async def list_review_sessions(
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """获取复盘会话列表。"""
    repo = ReviewAnalysisRepository(db)
    return ok(await repo.list_sessions(limit), "复盘会话列表已获取")


@router.post("/sessions/generate", response_model=ApiResponse)
async def generate_review_session(payload: GenerateReviewRequest, db: AsyncSession = Depends(get_db)):
    """从账户成交、资金快照生成一轮复盘。"""
    try:
        repo = ReviewAnalysisRepository(db)
        data = await repo.generate_session(**payload.model_dump())
        return ok(data, "复盘已生成")
    except Exception as exc:
        raise_api_error(exc)


@router.delete("/sessions/{session_id}", response_model=ApiResponse)
async def delete_review_session(session_id: int, db: AsyncSession = Depends(get_db)):
    """删除复盘会话及其派生数据。"""
    try:
        repo = ReviewAnalysisRepository(db)
        return ok(await repo.delete_session(session_id), "复盘会话已删除")
    except Exception as exc:
        raise_api_error(exc)


@router.get("/report", response_model=ApiResponse)
async def get_review_report(
    session_id: int = Query(..., gt=0),
    db: AsyncSession = Depends(get_db),
):
    """获取指定复盘报告。"""
    try:
        repo = ReviewAnalysisRepository(db)
        return ok(await repo.get_report(session_id), "复盘报告已获取")
    except Exception as exc:
        raise_api_error(exc)


@router.get("/trades", response_model=ApiResponse)
async def get_trade_records(
    session_id: int = Query(..., gt=0),
    limit: int = Query(default=200, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """获取复盘交易记录。"""
    try:
        repo = ReviewAnalysisRepository(db)
        return ok(await repo.list_trade_items(session_id, limit), "复盘交易记录已获取")
    except Exception as exc:
        raise_api_error(exc)


@router.get("/suggestions", response_model=ApiResponse)
async def get_optimization_suggestions(
    session_id: int = Query(..., gt=0),
    db: AsyncSession = Depends(get_db),
):
    """获取策略优化建议。"""
    try:
        repo = ReviewAnalysisRepository(db)
        return ok(await repo.list_suggestions(session_id), "优化建议已获取")
    except Exception as exc:
        raise_api_error(exc)


@router.get("/equity-curve", response_model=ApiResponse)
async def get_equity_curve(
    session_id: int = Query(..., gt=0),
    db: AsyncSession = Depends(get_db),
):
    """获取复盘净值曲线。"""
    try:
        repo = ReviewAnalysisRepository(db)
        return ok(await repo.list_equity_curve(session_id), "净值曲线已获取")
    except Exception as exc:
        raise_api_error(exc)


@router.get("/drawdown-curve", response_model=ApiResponse)
async def get_drawdown_curve(
    session_id: int = Query(..., gt=0),
    db: AsyncSession = Depends(get_db),
):
    """获取复盘回撤曲线。"""
    try:
        repo = ReviewAnalysisRepository(db)
        return ok(await repo.list_drawdown_curve(session_id), "回撤曲线已获取")
    except Exception as exc:
        raise_api_error(exc)
