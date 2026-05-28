from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from account_trading.models import TradingAccount
from account_trading.repository import AccountTradingRepository
from account_trading.router import engine_label
from account_trading.service import account_trading_service
from common.dependencies import get_db


router = APIRouter(prefix="/api/integration", tags=["上下游统一接入"])

OrderSide = Literal["buy", "sell"]
OrderScope = Literal["today", "history"]
AccountType = Literal["live", "paper", "backtest"]


class ApiResponse(BaseModel):
    success: bool
    data: Any = None
    message: str = ""


class AccountIdentity(BaseModel):
    user_id: str | None = Field(default=None, max_length=64, description="外部用户ID，对应 trading_account.meta_json.user_id")
    account_id: int | None = Field(default=None, gt=0, description="内部交易账户ID")
    account_code: str | None = Field(default=None, max_length=64, description="内部交易账户编码")


class RoutedOrderRequest(AccountIdentity):
    symbol: str = Field(..., min_length=6, max_length=12, description="证券代码")
    name: str | None = Field(default=None, max_length=128, description="证券名称")
    side: OrderSide
    price: Decimal = Field(..., gt=0, description="限价委托价格")
    quantity: int = Field(..., gt=0, description="委托股数")
    idempotency_key: str | None = Field(default=None, max_length=80, description="幂等键，实盘必填")
    remark: str | None = Field(default=None, max_length=200)
    wait_manual_captcha: bool = True
    manual_captcha_timeout: int = Field(default=180, ge=30, le=600)

    @field_validator("quantity")
    @classmethod
    def validate_a_share_lot(cls, value: int) -> int:
        if value % 100 != 0:
            raise ValueError("A 股委托数量必须是 100 股的整数倍。")
        return value


class RoutedSyncRequest(AccountIdentity):
    scope: OrderScope = "today"
    wait_manual_captcha: bool = True
    manual_captcha_timeout: int = Field(default=180, ge=30, le=600)


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


def account_payload(account: TradingAccount) -> dict[str, Any]:
    return {
        "account_id": account.id,
        "account_code": account.account_code,
        "account_name": account.account_name,
        "account_type": account.account_type,
        "engine": engine_label(account.account_type),
        "status": account.status,
        "broker_name": account.broker_name,
        "broker_account_no": account.broker_account_no,
        "shareholder_account": account.shareholder_account,
        "exchange": account.exchange,
        "meta_json": account.meta_json or {},
    }


async def resolve_account(db: AsyncSession, identity: AccountIdentity) -> TradingAccount:
    repo = AccountTradingRepository(db)
    if identity.account_id:
        account = await repo.get_account(identity.account_id)
        if account is None:
            raise LookupError("账户不存在")
        return _assert_available(account)

    if identity.account_code:
        result = await db.execute(select(TradingAccount).where(TradingAccount.account_code == identity.account_code))
        account = result.scalar_one_or_none()
        if account is None:
            raise LookupError("账户不存在")
        return _assert_available(account)

    if identity.user_id:
        result = await db.execute(
            select(TradingAccount)
            .where(TradingAccount.status != "archived")
            .order_by(TradingAccount.is_default.desc(), TradingAccount.id.desc())
        )
        user_id = str(identity.user_id)
        for account in result.scalars().all():
            meta = account.meta_json or {}
            if str(meta.get("user_id") or meta.get("external_user_id") or "") == user_id:
                return _assert_available(account)
        raise LookupError("未找到该用户绑定的交易账户")

    raise ValueError("必须提供 user_id、account_id 或 account_code 之一")


def _assert_available(account: TradingAccount) -> TradingAccount:
    if account.status == "archived":
        raise ValueError("账户已归档，不能用于上下游接入")
    return account


async def local_snapshot(repo: AccountTradingRepository, account: TradingAccount, scope: str = "today") -> dict[str, Any]:
    return {
        "account": account_payload(account),
        "balance": await repo.get_latest_balance(account),
        "positions": await repo.list_latest_positions(account),
        "orders": await repo.list_order_records(account, scope),
        "trades": await repo.list_trade_records(account, scope),
    }


@router.get("/capabilities", response_model=ApiResponse)
async def get_capabilities():
    data = {
        "account_identity": ["account_id", "account_code", "user_id(meta_json.user_id)"],
        "engines": {
            "live": {"engine": "desktop_live", "supports_order": True, "requires_desktop": True, "requires_idempotency_key": True},
            "paper": {"engine": "paper_trading", "supports_order": True, "requires_desktop": False, "requires_idempotency_key": False},
            "backtest": {"engine": "backtest_trading", "supports_order": False, "entry": "/api/replay/backtest/run"},
        },
        "shared_endpoints": [
            "GET /api/integration/accounts",
            "GET /api/integration/account/resolve",
            "GET /api/integration/account/snapshot",
            "POST /api/integration/account/sync",
            "POST /api/integration/order/route",
        ],
    }
    return ok(data, "统一接入能力已获取")


@router.get("/accounts", response_model=ApiResponse)
async def list_integration_accounts(
    user_id: str | None = Query(default=None, description="外部用户ID，对应 trading_account.meta_json.user_id/external_user_id"),
    account_type: AccountType | None = Query(default=None, description="账户类型：live 实盘，paper 模拟盘，backtest 回测盘"),
    include_archived: bool = Query(default=False, description="是否返回已归档账户，默认不返回"),
    db: AsyncSession = Depends(get_db),
):
    try:
        query = select(TradingAccount)
        if not include_archived:
            query = query.where(TradingAccount.status != "archived")
        if account_type:
            query = query.where(TradingAccount.account_type == account_type)
        query = query.order_by(TradingAccount.is_default.desc(), TradingAccount.account_type.asc(), TradingAccount.id.desc())
        result = await db.execute(query)
        rows = []
        for account in result.scalars().all():
            meta = account.meta_json or {}
            if user_id and str(meta.get("user_id") or meta.get("external_user_id") or "") != str(user_id):
                continue
            payload = account_payload(account)
            payload["identity_keys"] = {
                "account_id": account.id,
                "account_code": account.account_code,
                "user_id": meta.get("user_id") or meta.get("external_user_id"),
            }
            payload["is_default"] = bool(account.is_default)
            rows.append(payload)
        return ok({"items": rows, "total": len(rows)}, "统一接入账户列表已获取")
    except Exception as exc:
        raise_api_error(exc)


@router.get("/account/resolve", response_model=ApiResponse)
async def resolve_account_endpoint(
    user_id: str | None = Query(default=None),
    account_id: int | None = Query(default=None, gt=0),
    account_code: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    try:
        identity = AccountIdentity(user_id=user_id, account_id=account_id, account_code=account_code)
        account = await resolve_account(db, identity)
        return ok(account_payload(account), "账户和交易引擎已解析")
    except Exception as exc:
        raise_api_error(exc)


@router.get("/account/snapshot", response_model=ApiResponse)
async def get_account_snapshot(
    user_id: str | None = Query(default=None),
    account_id: int | None = Query(default=None, gt=0),
    account_code: str | None = Query(default=None),
    scope: OrderScope = "today",
    db: AsyncSession = Depends(get_db),
):
    try:
        identity = AccountIdentity(user_id=user_id, account_id=account_id, account_code=account_code)
        account = await resolve_account(db, identity)
        repo = AccountTradingRepository(db)
        return ok(await local_snapshot(repo, account, scope), "账户本地快照已获取")
    except Exception as exc:
        raise_api_error(exc)


@router.post("/account/sync", response_model=ApiResponse)
async def sync_account(payload: RoutedSyncRequest, db: AsyncSession = Depends(get_db)):
    try:
        account = await resolve_account(db, payload)
        repo = AccountTradingRepository(db)
        if account.account_type == "paper":
            match_result = await repo.match_pending_paper_orders(account)
            await repo.expire_today_unfilled_orders(account)
            refreshed = await repo.refresh_paper_market_value(account)
            data = await local_snapshot(repo, account, payload.scope)
            data["match_result"] = match_result
            data["balance"] = refreshed["balance"]
            data["positions"] = refreshed["positions"]
            return ok(data, "模拟账户已通过本地引擎同步")

        if account.account_type == "backtest":
            return ok(await local_snapshot(repo, account, payload.scope), "回测账户本地快照已获取")

        client_path = await repo.get_active_client_path(account)
        task = await repo.create_task(
            account,
            "sync",
            {"source": "integration_api", "scope": payload.scope, "wait_manual_captcha": payload.wait_manual_captcha},
        )
        data = await run_in_threadpool(
            account_trading_service.sync,
            client_path,
            payload.wait_manual_captcha,
            payload.manual_captcha_timeout,
        )
        await repo.save_balance(account, data.get("balance") or {})
        await repo.save_positions(account, data.get("positions") or [])
        await repo.save_orders(account, data.get("orders") or [])
        await repo.save_trades(account, data.get("trades") or [])
        await repo.finish_task(task, "success", data)
        return ok({"account": account_payload(account), **data}, "实盘账户已通过桌面引擎同步")
    except Exception as exc:
        raise_api_error(exc)


@router.post("/order/route", response_model=ApiResponse)
async def route_order(payload: RoutedOrderRequest, db: AsyncSession = Depends(get_db)):
    try:
        account = await resolve_account(db, payload)
        repo = AccountTradingRepository(db)

        if account.account_type == "paper":
            task = await repo.create_task(account, payload.side, {"source": "integration_api", **payload.model_dump(mode="json")})
            data = await repo.place_paper_order(
                account,
                side=payload.side,
                symbol=payload.symbol,
                name=payload.name,
                price=payload.price,
                quantity=payload.quantity,
                idempotency_key=payload.idempotency_key,
                remark=payload.remark,
            )
            await repo.finish_task(task, "success", data)
            return ok({"account": account_payload(account), "result": data}, "模拟订单已路由到 paper_trading 引擎")

        if account.account_type == "backtest":
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "回测账户不支持通过统一下单接口手工委托，请使用 /api/replay/backtest/run。",
                    "type": "backtest_engine_requires_run",
                    "account": account_payload(account),
                },
            )

        if not payload.idempotency_key:
            raise ValueError("实盘下单必须提供 idempotency_key，避免重复下单。")

        client_path = await repo.get_active_client_path(account)
        task = await repo.create_task(account, payload.side, {"source": "integration_api", **payload.model_dump(mode="json")})
        data = await run_in_threadpool(
            account_trading_service.place_order,
            side=payload.side,
            symbol=payload.symbol,
            price=payload.price,
            quantity=payload.quantity,
            client_path=client_path,
            wait_manual_captcha=payload.wait_manual_captcha,
            manual_captcha_timeout=payload.manual_captcha_timeout,
            idempotency_key=payload.idempotency_key,
            remark=payload.remark,
        )
        await repo.save_place_order_result(account, data)
        await repo.save_trades(account, data.get("matched_trades") or [])
        await repo.save_balance(account, data.get("balance_after") or {})
        await repo.finish_task(task, "success", data)
        return ok({"account": account_payload(account), "result": data}, "实盘订单已路由到 desktop_live 引擎")
    except Exception as exc:
        raise_api_error(exc)
