from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, field_validator, model_validator
from starlette.concurrency import run_in_threadpool

from .adapters.ths_desktop import CaptchaRequiredError, TradingClientNotReadyError
from .service import account_trading_service


router = APIRouter(prefix="/api/account", tags=["账户与交易"])


OrderSide = Literal["buy", "sell"]
AccountMode = Literal["live", "paper"]
OrderScope = Literal["today", "history"]


class ApiResponse(BaseModel):
    success: bool
    data: Any = None
    message: str = ""


class OrderRequest(BaseModel):
    symbol: str = Field(..., min_length=6, max_length=12, description="证券代码")
    side: OrderSide
    price: Decimal = Field(..., gt=0, description="限价委托价格")
    quantity: int = Field(..., gt=0, description="委托股数")
    mode: AccountMode = "live"
    idempotency_key: str | None = Field(default=None, max_length=80)
    remark: str | None = Field(default=None, max_length=200)
    wait_manual_captcha: bool = True
    manual_captcha_timeout: int = Field(default=180, ge=30, le=600)

    @field_validator("quantity")
    @classmethod
    def validate_a_share_lot(cls, value: int) -> int:
        if value % 100 != 0:
            raise ValueError("A 股委托数量必须是 100 股的整数倍。")
        return value

    @model_validator(mode="after")
    def validate_live_idempotency(self) -> "OrderRequest":
        if self.mode == "live" and not self.idempotency_key:
            raise ValueError("实盘下单必须提供 idempotency_key，避免重复下单。")
        return self


class CancelRequest(BaseModel):
    wait_manual_captcha: bool = True
    manual_captcha_timeout: int = Field(default=180, ge=30, le=600)


class SyncRequest(BaseModel):
    wait_manual_captcha: bool = True
    manual_captcha_timeout: int = Field(default=180, ge=30, le=600)


def ok(data: Any, message: str = "ok") -> ApiResponse:
    return ApiResponse(success=True, data=data, message=message)


def raise_api_error(exc: Exception) -> None:
    if isinstance(exc, CaptchaRequiredError):
        raise HTTPException(
            status_code=409,
            detail={
                "message": "检测到验证码弹窗，请在同花顺中人工处理后重试，或启用等待人工验证码。",
                "captcha_path": str(exc.screenshot),
            },
        ) from exc
    if isinstance(exc, TradingClientNotReadyError):
        raise HTTPException(
            status_code=409,
            detail={
                "message": str(exc),
                "type": "trading_client_not_ready",
            },
        ) from exc
    raise HTTPException(status_code=500, detail={"message": str(exc), "type": type(exc).__name__}) from exc


@router.get("/automation/status", response_model=ApiResponse)
async def automation_status():
    try:
        data = await run_in_threadpool(account_trading_service.status)
        return ok(data, "同花顺连接状态已获取")
    except Exception as exc:
        raise_api_error(exc)


@router.get("/automation/logs", response_model=ApiResponse)
async def automation_logs(limit: int = Query(default=50, ge=1, le=200)):
    return ok(account_trading_service.logs(limit), "自动化日志已获取")


@router.get("/balance", response_model=ApiResponse)
async def get_balance(
    wait_manual_captcha: bool = False,
    manual_captcha_timeout: int = Query(default=120, ge=30, le=600),
):
    try:
        data = await run_in_threadpool(
            account_trading_service.balance,
            None,
            wait_manual_captcha,
            manual_captcha_timeout,
        )
        return ok(data, "账户余额已同步")
    except Exception as exc:
        raise_api_error(exc)


@router.get("/positions", response_model=ApiResponse)
async def get_positions(
    wait_manual_captcha: bool = False,
    manual_captcha_timeout: int = Query(default=120, ge=30, le=600),
):
    try:
        data = await run_in_threadpool(
            account_trading_service.positions,
            None,
            wait_manual_captcha,
            manual_captcha_timeout,
        )
        return ok(data, "持仓列表已同步")
    except Exception as exc:
        raise_api_error(exc)


@router.get("/orders", response_model=ApiResponse)
async def get_orders(
    scope: OrderScope = "today",
    wait_manual_captcha: bool = False,
    manual_captcha_timeout: int = Query(default=120, ge=30, le=600),
):
    try:
        data = await run_in_threadpool(
            account_trading_service.orders,
            scope,
            None,
            wait_manual_captcha,
            manual_captcha_timeout,
        )
        return ok(data, "委托列表已同步")
    except Exception as exc:
        raise_api_error(exc)


@router.get("/trades", response_model=ApiResponse)
async def get_trades(
    scope: OrderScope = "today",
    wait_manual_captcha: bool = False,
    manual_captcha_timeout: int = Query(default=120, ge=30, le=600),
):
    try:
        data = await run_in_threadpool(
            account_trading_service.trades,
            scope,
            None,
            wait_manual_captcha,
            manual_captcha_timeout,
        )
        return ok(data, "成交列表已同步")
    except Exception as exc:
        raise_api_error(exc)


@router.post("/order", response_model=ApiResponse)
async def place_order(payload: OrderRequest):
    if payload.mode != "live":
        raise HTTPException(status_code=400, detail={"message": "当前桌面适配器只实现 live 实盘模式。"})
    try:
        data = await run_in_threadpool(
            account_trading_service.place_order,
            side=payload.side,
            symbol=payload.symbol,
            price=payload.price,
            quantity=payload.quantity,
            wait_manual_captcha=payload.wait_manual_captcha,
            manual_captcha_timeout=payload.manual_captcha_timeout,
            idempotency_key=payload.idempotency_key,
            remark=payload.remark,
        )
        return ok(data, "委托流程已执行，请以返回的合同编号、当日委托或成交回报为准")
    except Exception as exc:
        raise_api_error(exc)


@router.post("/order/{entrust_no}/cancel", response_model=ApiResponse)
async def cancel_order(entrust_no: str, payload: CancelRequest | None = None):
    payload = payload or CancelRequest()
    try:
        data = await run_in_threadpool(
            account_trading_service.cancel_order,
            entrust_no,
            None,
            payload.wait_manual_captcha,
            payload.manual_captcha_timeout,
        )
        return ok(data, "撤单流程已执行，请以当日委托状态为准")
    except Exception as exc:
        raise_api_error(exc)


@router.post("/sync", response_model=ApiResponse)
async def sync_account(payload: SyncRequest | None = None):
    payload = payload or SyncRequest()
    try:
        data = await run_in_threadpool(
            account_trading_service.sync,
            None,
            payload.wait_manual_captcha,
            payload.manual_captcha_timeout,
        )
        return ok(data, "账户数据已同步")
    except Exception as exc:
        raise_api_error(exc)
