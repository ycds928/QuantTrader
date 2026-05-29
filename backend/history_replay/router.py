from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from account_trading.backtest_engine import BacktestBar, BacktestContext, BacktestOrderRequest, BacktestTradingEngine
from account_trading.backtest_engine.schemas import FeeRule, SlippageRule
from account_trading.models import BacktestRun, BacktestTrade
from common.dependencies import get_db


router = APIRouter(prefix="/api/replay", tags=["历史回放"])


class ApiResponse(BaseModel):
    success: bool
    data: Any = None
    message: str = ""


class FeeRulePayload(BaseModel):
    commission_rate: Decimal = Decimal("0.00025")
    min_commission: Decimal = Decimal("5")
    stamp_tax_rate_sell: Decimal = Decimal("0.0005")
    transfer_fee_rate: Decimal = Decimal("0")


class SlippageRulePayload(BaseModel):
    type: Literal["none", "fixed_tick", "percent"] = "none"
    value: Decimal = Decimal("0")


class BacktestBarPayload(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=32)
    trade_date: date
    timestamp: datetime
    open: Decimal = Field(..., gt=0)
    high: Decimal = Field(..., gt=0)
    low: Decimal = Field(..., gt=0)
    close: Decimal = Field(..., gt=0)
    volume: int = Field(..., ge=0)
    amount: Decimal | None = None
    name: str | None = Field(default=None, max_length=128)
    exchange: str | None = Field(default=None, max_length=16)
    limit_up: Decimal | None = None
    limit_down: Decimal | None = None
    paused: bool = False

    @model_validator(mode="after")
    def validate_ohlc(self) -> "BacktestBarPayload":
        if self.high < self.low:
            raise ValueError("K 线 high 不能小于 low")
        if not (self.low <= self.open <= self.high and self.low <= self.close <= self.high):
            raise ValueError("K 线 open/close 必须落在 low 与 high 之间")
        return self


class BacktestOrderPayload(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=32)
    side: Literal["buy", "sell"]
    quantity: int = Field(..., gt=0)
    signal_time: datetime
    price: Decimal | None = Field(default=None, gt=0)
    order_type: Literal["market", "limit"] = "limit"
    signal_id: str | None = Field(default=None, max_length=64)
    remark: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def validate_limit_price(self) -> "BacktestOrderPayload":
        if self.order_type == "limit" and self.price is None:
            raise ValueError("限价单必须提供 price")
        if self.quantity % 100 != 0:
            raise ValueError("A 股回测委托数量必须是 100 股的整数倍")
        return self


class BacktestRunRequest(BaseModel):
    account_id: int = Field(..., gt=0)
    strategy_id: str = Field(default="manual_backtest", min_length=1, max_length=64)
    version_id: str | None = Field(default=None, max_length=64)
    run_id: str | None = Field(default=None, max_length=64)
    start_date: date
    end_date: date
    initial_cash: Decimal = Field(..., gt=0)
    benchmark_symbol: str | None = Field(default=None, max_length=32)
    frequency: str = Field(default="daily", max_length=16)
    fee_rule: FeeRulePayload = Field(default_factory=FeeRulePayload)
    slippage_rule: SlippageRulePayload = Field(default_factory=SlippageRulePayload)
    volume_limit_ratio: Decimal = Field(default=Decimal("0.1"), gt=0, le=1)
    bars: list[BacktestBarPayload] = Field(..., min_length=1)
    orders: list[BacktestOrderPayload] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_dates(self) -> "BacktestRunRequest":
        if self.start_date > self.end_date:
            raise ValueError("回测开始日期不能晚于结束日期")
        for bar in self.bars:
            if bar.trade_date < self.start_date or bar.trade_date > self.end_date:
                raise ValueError("K 线日期必须在回测区间内")
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


@router.post("/backtest/run", response_model=ApiResponse)
async def run_backtest(payload: BacktestRunRequest, db: AsyncSession = Depends(get_db)):
    """运行第一版回测交易闭环：K 线撮合、订单成交、资金持仓落库。"""
    try:
        context = BacktestContext(
            account_id=payload.account_id,
            run_id=payload.run_id or f"BTRUN-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:6].upper()}",
            strategy_id=payload.strategy_id,
            version_id=payload.version_id,
            start_date=payload.start_date,
            end_date=payload.end_date,
            initial_cash=payload.initial_cash,
            benchmark_symbol=payload.benchmark_symbol,
            frequency=payload.frequency,
            fee_rule=FeeRule(**payload.fee_rule.model_dump()),
            slippage_rule=SlippageRule(**payload.slippage_rule.model_dump()),
            volume_limit_ratio=payload.volume_limit_ratio,
        )
        bars = [BacktestBar(**item.model_dump()) for item in payload.bars]
        orders = [BacktestOrderRequest(**item.model_dump()) for item in payload.orders]
        data = await BacktestTradingEngine(db).run(context, bars, orders)
        return ok(data, "回测交易闭环已完成")
    except Exception as exc:
        raise_api_error(exc)


@router.post("/start", response_model=ApiResponse)
async def start_replay(payload: BacktestRunRequest, db: AsyncSession = Depends(get_db)):
    """兼容历史回放启动入口，当前直接运行第一版回测。"""
    return await run_backtest(payload, db)


@router.get("/session/{run_id}", response_model=ApiResponse)
async def get_replay_session(run_id: str, db: AsyncSession = Depends(get_db)):
    """获取回测运行批次。"""
    result = await db.execute(select(BacktestRun).where(BacktestRun.run_id == run_id))
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail={"message": "回测运行批次不存在", "type": "not_found"})
    return ok(
        {
            "id": row.id,
            "run_id": row.run_id,
            "account_id": row.account_id,
            "strategy_id": row.strategy_id,
            "version_id": row.version_id,
            "start_date": row.start_date.isoformat(),
            "end_date": row.end_date.isoformat(),
            "initial_cash": str(row.initial_cash),
            "benchmark_symbol": row.benchmark_symbol,
            "frequency": row.frequency,
            "params": row.params_json or {},
            "status": row.status,
            "created_at": row.created_at.isoformat(sep=" ", timespec="seconds") if row.created_at else "",
            "updated_at": row.updated_at.isoformat(sep=" ", timespec="seconds") if row.updated_at else "",
        },
        "回测运行批次已获取",
    )


@router.get("/trades/{run_id}", response_model=ApiResponse)
async def get_replay_trades(run_id: str, db: AsyncSession = Depends(get_db)):
    """获取回测成交记录。"""
    result = await db.execute(
        select(BacktestTrade)
        .where(BacktestTrade.run_id == run_id)
        .order_by(BacktestTrade.traded_at.asc(), BacktestTrade.id.asc())
    )
    rows = result.scalars().all()
    return ok(
        [
            {
                "trade_id": row.trade_id,
                "broker_trade_id": row.broker_trade_no,
                "order_id": row.broker_order_no or str(row.order_id or ""),
                "symbol": row.symbol,
                "name": row.name or "",
                "side": row.side,
                "price": str(row.price),
                "quantity": int(row.quantity or 0),
                "amount": str(row.amount),
                "commission": str(row.commission or "0"),
                "stamp_tax": str(row.stamp_tax or "0"),
                "transfer_fee": str(row.transfer_fee or "0"),
                "traded_at": row.traded_at.isoformat(sep=" ", timespec="seconds") if row.traded_at else "",
            }
            for row in rows
        ],
        "回测成交记录已获取",
    )
