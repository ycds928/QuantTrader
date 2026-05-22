from __future__ import annotations

import os
import threading
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from .adapters.ths_desktop import CaptchaRequiredError, ThsDesktopAdapter


OrderSide = Literal["buy", "sell"]
OrderScope = Literal["today", "history"]


DEFAULT_THS_CLIENT_PATH = r"E:\同花顺软件\同花顺\xiadan.exe"


@dataclass
class AutomationLog:
    id: str
    operation: str
    status: str
    message: str
    created_at: str
    detail: dict[str, Any] = field(default_factory=dict)


class AccountTradingService:
    """Application service for the account trading module.

    The desktop trading client is a single local UI resource, so all adapter
    calls are serialized through one process lock.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._logs: list[AutomationLog] = []

    def status(self, client_path: str | None = None) -> dict[str, Any]:
        return self._run("status", client_path, lambda adapter: adapter.status())

    def balance(
        self,
        client_path: str | None = None,
        wait_manual_captcha: bool = False,
        manual_captcha_timeout: int = 120,
    ) -> dict[str, Any]:
        return self._run(
            "balance",
            client_path,
            lambda adapter: self._normalize_balance(adapter.get_balance()),
            wait_manual_captcha=wait_manual_captcha,
            manual_captcha_timeout=manual_captcha_timeout,
        )

    def positions(
        self,
        client_path: str | None = None,
        wait_manual_captcha: bool = False,
        manual_captcha_timeout: int = 120,
    ) -> list[dict[str, Any]]:
        return self._run(
            "positions",
            client_path,
            lambda adapter: [self._normalize_position(row) for row in adapter.get_positions()],
            wait_manual_captcha=wait_manual_captcha,
            manual_captcha_timeout=manual_captcha_timeout,
        )

    def orders(
        self,
        scope: OrderScope = "today",
        client_path: str | None = None,
        wait_manual_captcha: bool = False,
        manual_captcha_timeout: int = 120,
    ) -> list[dict[str, Any]]:
        def work(adapter: ThsDesktopAdapter) -> list[dict[str, Any]]:
            rows = adapter.get_today_orders() if scope == "today" else adapter.get_history_orders()
            return [
                order
                for row in rows
                if self._row_has_value(row)
                for order in [self._normalize_order(row)]
                if order["broker_order_id"] or order["symbol"] or order["quantity"]
            ]

        return self._run(
            f"{scope}_orders",
            client_path,
            work,
            wait_manual_captcha=wait_manual_captcha,
            manual_captcha_timeout=manual_captcha_timeout,
        )

    def trades(
        self,
        scope: OrderScope = "today",
        client_path: str | None = None,
        wait_manual_captcha: bool = False,
        manual_captcha_timeout: int = 120,
    ) -> list[dict[str, Any]]:
        def work(adapter: ThsDesktopAdapter) -> list[dict[str, Any]]:
            rows = adapter.get_today_trades() if scope == "today" else adapter.get_history_trades()
            return [
                trade
                for row in rows
                if self._row_has_value(row)
                for trade in [self._normalize_trade(row)]
                if trade["broker_trade_id"] or trade["symbol"] or trade["quantity"]
            ]

        return self._run(
            f"{scope}_trades",
            client_path,
            work,
            wait_manual_captcha=wait_manual_captcha,
            manual_captcha_timeout=manual_captcha_timeout,
        )

    def place_order(
        self,
        *,
        side: OrderSide,
        symbol: str,
        price: Decimal,
        quantity: int,
        client_path: str | None = None,
        wait_manual_captcha: bool = True,
        manual_captcha_timeout: int = 180,
        idempotency_key: str | None = None,
        remark: str | None = None,
    ) -> dict[str, Any]:
        operation = f"{side}_order"

        def work(adapter: ThsDesktopAdapter) -> dict[str, Any]:
            result = adapter.buy(symbol, price, quantity) if side == "buy" else adapter.sell(symbol, price, quantity)
            result["request"] = {
                "symbol": symbol,
                "side": side,
                "price": str(price),
                "quantity": quantity,
                "idempotency_key": idempotency_key,
                "remark": remark,
            }
            return result

        return self._run(
            operation,
            client_path,
            work,
            wait_manual_captcha=wait_manual_captcha,
            manual_captcha_timeout=manual_captcha_timeout,
        )

    def cancel_order(
        self,
        entrust_no: str,
        client_path: str | None = None,
        wait_manual_captcha: bool = True,
        manual_captcha_timeout: int = 180,
    ) -> dict[str, Any]:
        return self._run(
            "cancel_order",
            client_path,
            lambda adapter: adapter.cancel_order(entrust_no),
            wait_manual_captcha=wait_manual_captcha,
            manual_captcha_timeout=manual_captcha_timeout,
        )

    def sync(
        self,
        client_path: str | None = None,
        wait_manual_captcha: bool = True,
        manual_captcha_timeout: int = 180,
    ) -> dict[str, Any]:
        def work(adapter: ThsDesktopAdapter) -> dict[str, Any]:
            return {
                "balance": self._normalize_balance(adapter.get_balance()),
                "positions": [self._normalize_position(row) for row in adapter.get_positions()],
                "orders": [
                    order
                    for row in adapter.get_today_orders()
                    if self._row_has_value(row)
                    for order in [self._normalize_order(row)]
                    if order["broker_order_id"] or order["symbol"] or order["quantity"]
                ],
                "trades": [
                    trade
                    for row in adapter.get_today_trades()
                    if self._row_has_value(row)
                    for trade in [self._normalize_trade(row)]
                    if trade["broker_trade_id"] or trade["symbol"] or trade["quantity"]
                ],
            }

        return self._run(
            "sync",
            client_path,
            work,
            wait_manual_captcha=wait_manual_captcha,
            manual_captcha_timeout=manual_captcha_timeout,
        )

    def logs(self, limit: int = 50) -> list[dict[str, Any]]:
        return [log.__dict__ for log in self._logs[-limit:]][::-1]

    def _run(
        self,
        operation: str,
        client_path: str | None,
        work: Any,
        *,
        wait_manual_captcha: bool = False,
        manual_captcha_timeout: int = 120,
    ) -> Any:
        if not self._lock.acquire(blocking=False):
            raise RuntimeError("同花顺自动化正在执行其他任务，请稍后再试。")

        try:
            adapter = ThsDesktopAdapter(
                self._resolve_client_path(client_path),
                wait_manual_captcha=wait_manual_captcha,
                manual_captcha_timeout=manual_captcha_timeout,
            )
            adapter.connect()
            result = work(adapter)
            self._append_log(operation, "success", "操作完成", {"result": result})
            return result
        except CaptchaRequiredError as exc:
            detail = {"captcha_path": str(exc.screenshot)}
            self._append_log(operation, "captcha_required", str(exc), detail)
            raise
        except Exception as exc:
            self._append_log(operation, "failed", str(exc), {"error_type": type(exc).__name__})
            raise
        finally:
            self._lock.release()

    def _resolve_client_path(self, client_path: str | None) -> Path:
        path = client_path or os.getenv("THS_CLIENT_PATH") or DEFAULT_THS_CLIENT_PATH
        return Path(path)

    def _append_log(
        self,
        operation: str,
        status: str,
        message: str,
        detail: dict[str, Any] | None = None,
    ) -> None:
        self._logs.append(
            AutomationLog(
                id=uuid4().hex,
                operation=operation,
                status=status,
                message=message,
                created_at=datetime.now().isoformat(timespec="seconds"),
                detail=detail or {},
            )
        )
        if len(self._logs) > 200:
            self._logs = self._logs[-200:]

    def _normalize_balance(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "account_id": "ths-local",
            "mode": "live",
            "total_asset": self._decimal_text(row.get("总资产")),
            "available_cash": self._decimal_text(row.get("可用金额")),
            "withdrawable_cash": self._decimal_text(row.get("可取金额")),
            "market_value": self._decimal_text(row.get("股票市值")),
            "cash_balance": self._decimal_text(row.get("资金余额")),
            "frozen_cash": self._decimal_text(
                Decimal(str(row.get("资金余额", 0) or 0)) - Decimal(str(row.get("可用金额", 0) or 0))
            ),
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            "raw": row,
        }

    def _normalize_position(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "position_id": self._first(row, "证券代码", "position_id"),
            "symbol": self._first(row, "证券代码", "代码"),
            "name": self._first(row, "证券名称", "名称"),
            "quantity": self._int(row, "股票余额", "持仓数量", "当前持仓"),
            "available_quantity": self._int(row, "可用余额", "可卖数量"),
            "cost_price": self._decimal_text(self._first(row, "成本价", "成本价格")),
            "last_price": self._decimal_text(self._first(row, "市价", "最新价")),
            "market_value": self._decimal_text(self._first(row, "市值", "股票市值")),
            "unrealized_pnl": self._decimal_text(self._first(row, "浮动盈亏", "盈亏")),
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            "raw": row,
        }

    def _normalize_order(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "order_id": self._first(row, "合同编号", "委托编号", "申请编号"),
            "broker_order_id": self._first(row, "合同编号", "委托编号", "申请编号"),
            "symbol": self._first(row, "证券代码", "代码"),
            "name": self._first(row, "证券名称", "名称"),
            "side": self._normalize_side(self._first(row, "买卖标志", "操作", "委托类别")),
            "price": self._decimal_text(self._first(row, "委托价格", "价格")),
            "quantity": self._int(row, "委托数量", "数量"),
            "filled_quantity": self._int(row, "成交数量", "已成交数量"),
            "avg_fill_price": self._decimal_text(self._first(row, "成交均价", "成交价格")),
            "status": self._first(row, "委托状态", "状态"),
            "submitted_at": self._first(row, "委托时间", "申报时间", "操作日期"),
            "raw": row,
        }

    def _normalize_trade(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "trade_id": self._first(row, "成交编号", "合同编号", "委托编号"),
            "broker_trade_id": self._first(row, "成交编号", "合同编号"),
            "order_id": self._first(row, "合同编号", "委托编号"),
            "symbol": self._first(row, "证券代码", "代码"),
            "name": self._first(row, "证券名称", "名称"),
            "side": self._normalize_side(self._first(row, "买卖标志", "操作", "委托类别")),
            "price": self._decimal_text(self._first(row, "成交价格", "成交均价", "价格")),
            "quantity": self._int(row, "成交数量", "数量"),
            "amount": self._decimal_text(self._first(row, "成交金额", "发生金额")),
            "commission": self._decimal_text(self._first(row, "佣金")),
            "stamp_tax": self._decimal_text(self._first(row, "印花税")),
            "traded_at": self._first(row, "成交时间", "发生时间", "操作日期"),
            "source": "live",
            "raw": row,
        }

    def _first(self, row: dict[str, Any], *keys: str) -> Any:
        for key in keys:
            value = row.get(key)
            if value not in (None, ""):
                return value
        return ""

    def _int(self, row: dict[str, Any], *keys: str) -> int:
        value = self._first(row, *keys)
        try:
            return int(float(value or 0))
        except (TypeError, ValueError):
            return 0

    def _decimal_text(self, value: Any) -> str:
        try:
            return f"{Decimal(str(value or 0)):.2f}"
        except Exception:
            return "0.00"

    def _normalize_side(self, value: Any) -> str:
        text = str(value or "")
        if "买" in text:
            return "buy"
        if "卖" in text:
            return "sell"
        return text

    def _row_has_value(self, row: dict[str, Any]) -> bool:
        return any(str(value).strip() not in ("", "0", "0.0", "0.00") for value in row.values())


account_trading_service = AccountTradingService()
