from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from account_trading.models import (
    BacktestBalanceSnapshot,
    BacktestCashFlow,
    BacktestOrder,
    BacktestOrderStatusLog,
    BacktestPositionSnapshot,
    BacktestRun,
    BacktestTrade,
    TradingAccount,
)

from .fees import BacktestFeeCalculator
from .matcher import BacktestMatcher
from .schemas import BacktestBar, BacktestContext, BacktestOrderRequest, MatchResult
from .slippage import BacktestSlippageCalculator


@dataclass
class PositionState:
    quantity: int = 0
    cost_price: Decimal = Decimal("0")
    last_price: Decimal = Decimal("0")
    name: str | None = None
    exchange: str | None = None


class BacktestTradingEngine:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def run(
        self,
        context: BacktestContext,
        bars: list[BacktestBar],
        orders: list[BacktestOrderRequest],
    ) -> dict[str, Any]:
        account = await self._get_backtest_account(context.account_id)
        if not bars:
            raise ValueError("回测至少需要一根历史 K 线")

        ordered_bars = sorted(bars, key=lambda item: (item.timestamp, item.symbol))
        pending_orders = sorted(orders, key=lambda item: item.signal_time)
        cash = context.initial_cash
        positions: dict[str, PositionState] = defaultdict(PositionState)
        matcher = BacktestMatcher(
            fee_calculator=BacktestFeeCalculator(context.fee_rule),
            slippage_calculator=BacktestSlippageCalculator(context.slippage_rule),
            volume_limit_ratio=context.volume_limit_ratio,
        )

        run_row = BacktestRun(
            run_id=context.run_id,
            account_id=account.id,
            strategy_id=context.strategy_id,
            version_id=context.version_id,
            start_date=context.start_date,
            end_date=context.end_date,
            initial_cash=context.initial_cash,
            benchmark_symbol=context.benchmark_symbol,
            frequency=context.frequency,
            params_json={
                "fee_rule": self._fee_rule_payload(context),
                "slippage_rule": self._slippage_rule_payload(context),
                "volume_limit_ratio": str(context.volume_limit_ratio),
                "order_count": len(orders),
                "bar_count": len(bars),
            },
            status="running",
        )
        self.db.add(run_row)
        await self.db.flush()
        await self._save_balance_snapshot(context, ordered_bars[0].timestamp, cash, positions, {"event": "backtest_start"})

        order_rows: list[BacktestOrder] = []
        trade_rows: list[BacktestTrade] = []
        rejected_count = 0
        filled_count = 0
        partial_count = 0

        for bar in ordered_bars:
            position = positions[bar.symbol]
            position.last_price = bar.close
            position.name = bar.name or position.name
            position.exchange = bar.exchange or position.exchange

            eligible = [
                request
                for request in pending_orders
                if request.symbol == bar.symbol and request.signal_time < bar.timestamp
            ]
            for request in eligible:
                pending_orders.remove(request)
                order_row = await self._create_order(context, request, bar)
                order_rows.append(order_row)
                decision = matcher.match(
                    request,
                    bar,
                    available_cash=cash,
                    available_quantity=positions[request.symbol].quantity,
                )
                if decision.is_filled:
                    cash = await self._apply_fill(context, request, bar, order_row, decision, cash, positions)
                    trade_rows.append(await self._latest_trade(order_row))
                    if decision.status == "partial_filled":
                        partial_count += 1
                    else:
                        filled_count += 1
                else:
                    if decision.status == "rejected":
                        rejected_count += 1
                    await self._mark_order_unfilled(order_row, decision, bar)
                await self._save_balance_snapshot(context, bar.timestamp, cash, positions, {"event": "after_order", "order_no": order_row.order_no})

            await self._save_position_snapshots(context, bar.timestamp, positions)
            await self._save_balance_snapshot(context, bar.timestamp, cash, positions, {"event": "bar_close", "symbol": bar.symbol})

        for request in pending_orders:
            synthetic_bar = ordered_bars[-1]
            order_row = await self._create_order(context, request, synthetic_bar, status="expired")
            order_rows.append(order_row)
            await self._append_status_log(
                context,
                order_row,
                None,
                "expired",
                "expired",
                {"signal_time": request.signal_time.isoformat(sep=" ", timespec="seconds")},
                "回测结束前没有下一根可撮合 K 线，订单过期",
            )

        market_value = self._market_value(positions)
        run_row.status = "done"
        await self.db.flush()
        return {
            "run": self._serialize_run(run_row),
            "summary": {
                "initial_cash": str(context.initial_cash),
                "cash_balance": str(cash),
                "market_value": str(market_value),
                "total_asset": str(cash + market_value),
                "orders": len(order_rows),
                "trades": len([row for row in trade_rows if row is not None]),
                "filled": filled_count,
                "partial_filled": partial_count,
                "rejected": rejected_count,
                "expired": len(pending_orders),
            },
            "orders": [self._serialize_order(row) for row in order_rows],
            "trades": [self._serialize_trade(row) for row in trade_rows if row is not None],
            "balance": await self._latest_balance(context),
            "positions": await self._latest_positions(context),
        }

    async def _get_backtest_account(self, account_id: int) -> TradingAccount:
        result = await self.db.execute(select(TradingAccount).where(TradingAccount.id == account_id))
        account = result.scalar_one_or_none()
        if account is None:
            raise LookupError("回测账户不存在")
        if account.account_type != "backtest":
            raise ValueError("回测交易引擎只能用于回测账户")
        if account.status == "archived":
            raise ValueError("已归档账户不能运行回测")
        return account

    async def _create_order(
        self,
        context: BacktestContext,
        request: BacktestOrderRequest,
        bar: BacktestBar,
        status: str = "submitted",
    ) -> BacktestOrder:
        now = bar.timestamp
        order_no = f"BTORD-{now.strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:8]}"
        broker_order_no = f"BTMOCK-{uuid4().hex[:12].upper()}"
        price = request.price if request.price is not None else bar.open
        order = BacktestOrder(
            account_id=context.account_id,
            run_id=context.run_id,
            strategy_id=context.strategy_id,
            version_id=context.version_id,
            signal_id=request.signal_id,
            idempotency_key=None,
            order_no=order_no,
            broker_order_no=broker_order_no,
            trade_date=bar.trade_date,
            symbol=request.symbol,
            name=bar.name,
            side=request.side,
            order_type=request.order_type,
            price=price,
            quantity=request.quantity,
            filled_quantity=0,
            canceled_quantity=0,
            avg_fill_price=None,
            status=status,
            remark=request.remark,
            source="backtest",
            submitted_at=now,
            accepted_at=now if status == "submitted" else None,
            rejected_at=now if status == "rejected" else None,
            raw_json={
                "signal_time": request.signal_time.isoformat(sep=" ", timespec="seconds"),
                "bar_time": bar.timestamp.isoformat(sep=" ", timespec="seconds"),
            },
        )
        self.db.add(order)
        await self.db.flush()
        await self._append_status_log(context, order, None, status, "submit", order.raw_json, "回测订单已创建")
        return order

    async def _apply_fill(
        self,
        context: BacktestContext,
        request: BacktestOrderRequest,
        bar: BacktestBar,
        order: BacktestOrder,
        decision: MatchResult,
        cash: Decimal,
        positions: dict[str, PositionState],
    ) -> Decimal:
        position = positions[request.symbol]
        order.status = decision.status
        order.filled_quantity = decision.fill_quantity
        order.avg_fill_price = decision.fill_price
        order.accepted_at = bar.timestamp

        trade_id = f"BTTRD-{bar.timestamp.strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:8]}"
        trade = BacktestTrade(
            account_id=context.account_id,
            order_id=order.id,
            run_id=context.run_id,
            strategy_id=context.strategy_id,
            version_id=context.version_id,
            signal_id=request.signal_id,
            trade_id=trade_id,
            broker_trade_no=trade_id,
            broker_order_no=order.broker_order_no,
            trade_date=bar.trade_date,
            traded_at=bar.timestamp,
            symbol=request.symbol,
            name=bar.name,
            side=request.side,
            price=decision.fill_price,
            quantity=decision.fill_quantity,
            amount=decision.amount,
            commission=decision.commission,
            stamp_tax=decision.stamp_tax,
            transfer_fee=decision.transfer_fee,
            raw_json={"reason": decision.reason, "bar": self._bar_payload(bar)},
        )
        self.db.add(trade)

        if request.side == "buy":
            old_quantity = position.quantity
            new_quantity = old_quantity + decision.fill_quantity
            old_cost = position.cost_price * Decimal(old_quantity)
            position.quantity = new_quantity
            position.cost_price = ((old_cost + decision.amount + decision.total_fee) / Decimal(new_quantity)).quantize(Decimal("0.0001"))
            cash = cash - decision.amount - decision.total_fee
            await self._save_cash_flow(context, bar, "trade_cash", "trade", trade_id, -decision.amount, cash, "买入成交")
            await self._save_cash_flow(context, bar, "trade_fee", "trade", trade_id, -decision.total_fee, cash, "买入费用")
        else:
            position.quantity -= decision.fill_quantity
            cash = cash + decision.amount - decision.total_fee
            if position.quantity <= 0:
                position.quantity = 0
                position.cost_price = Decimal("0")
            await self._save_cash_flow(context, bar, "trade_cash", "trade", trade_id, decision.amount, cash, "卖出成交")
            await self._save_cash_flow(context, bar, "trade_fee", "trade", trade_id, -decision.total_fee, cash, "卖出费用")

        position.last_price = bar.close
        position.name = bar.name or position.name
        position.exchange = bar.exchange or position.exchange
        await self._append_status_log(context, order, "submitted", decision.status, "fill", {"match": self._decision_payload(decision)}, decision.reason)
        await self.db.flush()
        return cash

    async def _mark_order_unfilled(self, order: BacktestOrder, decision: MatchResult, bar: BacktestBar) -> None:
        from_status = order.status
        order.status = decision.status
        if decision.status == "rejected":
            order.rejected_at = bar.timestamp
        await self._append_status_log(
            BacktestContext(
                account_id=order.account_id,
                run_id=order.run_id,
                strategy_id=order.strategy_id or "",
                version_id=order.version_id,
                start_date=order.trade_date,
                end_date=order.trade_date,
                initial_cash=Decimal("0"),
            ),
            order,
            from_status,
            decision.status,
            decision.status,
            {"match": self._decision_payload(decision)},
            decision.reason,
        )
        await self.db.flush()

    async def _append_status_log(
        self,
        context: BacktestContext,
        order: BacktestOrder,
        from_status: str | None,
        to_status: str,
        event_type: str,
        detail: dict[str, Any] | None,
        message: str | None,
    ) -> None:
        self.db.add(
            BacktestOrderStatusLog(
                account_id=context.account_id,
                order_id=order.id,
                run_id=context.run_id,
                broker_order_no=order.broker_order_no,
                from_status=from_status,
                to_status=to_status,
                event_type=event_type,
                event_source="backtest_engine",
                event_time=order.submitted_at or datetime.now(),
                detail_json=detail,
                message=message,
            )
        )

    async def _save_cash_flow(
        self,
        context: BacktestContext,
        bar: BacktestBar,
        flow_type: str,
        ref_type: str,
        ref_id: str,
        amount: Decimal,
        balance_after: Decimal,
        remark: str,
    ) -> None:
        self.db.add(
            BacktestCashFlow(
                account_id=context.account_id,
                run_id=context.run_id,
                trade_date=bar.trade_date,
                flow_type=flow_type,
                ref_type=ref_type,
                ref_id=ref_id,
                amount=amount,
                balance_after=balance_after,
                remark=remark,
                raw_json={"bar_time": bar.timestamp.isoformat(sep=" ", timespec="seconds")},
            )
        )

    async def _save_position_snapshots(
        self,
        context: BacktestContext,
        timestamp: datetime,
        positions: dict[str, PositionState],
    ) -> None:
        for symbol, position in positions.items():
            if position.quantity <= 0:
                continue
            await self._upsert_position_snapshot(context, timestamp, symbol, position)

    async def _upsert_position_snapshot(
        self,
        context: BacktestContext,
        timestamp: datetime,
        symbol: str,
        position: PositionState,
    ) -> None:
        market_value = position.last_price * Decimal(position.quantity)
        unrealized_pnl = (position.last_price - position.cost_price) * Decimal(position.quantity)
        result = await self.db.execute(
            select(BacktestPositionSnapshot).where(
                BacktestPositionSnapshot.account_id == context.account_id,
                BacktestPositionSnapshot.run_id == context.run_id,
                BacktestPositionSnapshot.trade_date == timestamp.date(),
                BacktestPositionSnapshot.symbol == symbol,
            )
        )
        row = result.scalar_one_or_none()
        payload = {
            "snapshot_time": timestamp,
            "quantity": position.quantity,
            "available_quantity": position.quantity,
            "frozen_quantity": 0,
            "cost_price": position.cost_price,
            "last_price": position.last_price,
            "market_value": market_value,
            "unrealized_pnl": unrealized_pnl,
            "pnl_ratio": ((position.last_price - position.cost_price) / position.cost_price) if position.cost_price > 0 else None,
            "raw_json": {"engine": "backtest_engine"},
        }
        if row is None:
            self.db.add(
                BacktestPositionSnapshot(
                    account_id=context.account_id,
                    run_id=context.run_id,
                    trade_date=timestamp.date(),
                    symbol=symbol,
                    name=position.name,
                    exchange=position.exchange,
                    source="backtest",
                    **payload,
                )
            )
            return
        for key, value in payload.items():
            setattr(row, key, value)
        row.name = position.name
        row.exchange = position.exchange

    async def _save_balance_snapshot(
        self,
        context: BacktestContext,
        timestamp: datetime,
        cash: Decimal,
        positions: dict[str, PositionState],
        raw: dict[str, Any],
    ) -> None:
        market_value = self._market_value(positions)
        self.db.add(
            BacktestBalanceSnapshot(
                account_id=context.account_id,
                run_id=context.run_id,
                trade_date=timestamp.date(),
                snapshot_time=timestamp,
                total_asset=cash + market_value,
                cash_balance=cash,
                available_cash=cash,
                withdrawable_cash=cash,
                frozen_cash=Decimal("0"),
                market_value=market_value,
                realized_pnl=None,
                unrealized_pnl=None,
                source="backtest",
                raw_json=raw,
            )
        )

    async def _latest_trade(self, order: BacktestOrder) -> BacktestTrade | None:
        result = await self.db.execute(select(BacktestTrade).where(BacktestTrade.order_id == order.id).order_by(BacktestTrade.id.desc()).limit(1))
        return result.scalar_one_or_none()

    async def _latest_balance(self, context: BacktestContext) -> dict[str, Any]:
        result = await self.db.execute(
            select(BacktestBalanceSnapshot)
            .where(BacktestBalanceSnapshot.account_id == context.account_id, BacktestBalanceSnapshot.run_id == context.run_id)
            .order_by(BacktestBalanceSnapshot.snapshot_time.desc(), BacktestBalanceSnapshot.id.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return self._serialize_balance(row) if row else {}

    async def _latest_positions(self, context: BacktestContext) -> list[dict[str, Any]]:
        result = await self.db.execute(
            select(BacktestPositionSnapshot)
            .where(BacktestPositionSnapshot.account_id == context.account_id, BacktestPositionSnapshot.run_id == context.run_id)
            .order_by(BacktestPositionSnapshot.snapshot_time.desc(), BacktestPositionSnapshot.id.desc())
        )
        latest: dict[str, BacktestPositionSnapshot] = {}
        for row in result.scalars().all():
            if row.symbol not in latest:
                latest[row.symbol] = row
        return [self._serialize_position(row) for row in latest.values() if int(row.quantity or 0) > 0]

    def _market_value(self, positions: dict[str, PositionState]) -> Decimal:
        return sum((item.last_price * Decimal(item.quantity) for item in positions.values() if item.quantity > 0), Decimal("0")).quantize(Decimal("0.0001"))

    def _fee_rule_payload(self, context: BacktestContext) -> dict[str, str]:
        return {
            "commission_rate": str(context.fee_rule.commission_rate),
            "min_commission": str(context.fee_rule.min_commission),
            "stamp_tax_rate_sell": str(context.fee_rule.stamp_tax_rate_sell),
            "transfer_fee_rate": str(context.fee_rule.transfer_fee_rate),
        }

    def _slippage_rule_payload(self, context: BacktestContext) -> dict[str, str]:
        return {"type": context.slippage_rule.type, "value": str(context.slippage_rule.value)}

    def _bar_payload(self, bar: BacktestBar) -> dict[str, Any]:
        return {
            "symbol": bar.symbol,
            "timestamp": bar.timestamp.isoformat(sep=" ", timespec="seconds"),
            "open": str(bar.open),
            "high": str(bar.high),
            "low": str(bar.low),
            "close": str(bar.close),
            "volume": bar.volume,
        }

    def _decision_payload(self, decision: MatchResult) -> dict[str, Any]:
        return {
            "status": decision.status,
            "fill_price": str(decision.fill_price),
            "fill_quantity": decision.fill_quantity,
            "amount": str(decision.amount),
            "commission": str(decision.commission),
            "stamp_tax": str(decision.stamp_tax),
            "transfer_fee": str(decision.transfer_fee),
            "total_fee": str(decision.total_fee),
            "reason": decision.reason,
        }

    def _serialize_run(self, row: BacktestRun) -> dict[str, Any]:
        return {
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
            "status": row.status,
        }

    def _serialize_order(self, row: BacktestOrder) -> dict[str, Any]:
        return {
            "order_id": row.order_no,
            "broker_order_id": row.broker_order_no,
            "symbol": row.symbol,
            "name": row.name or "",
            "side": row.side,
            "price": str(row.price),
            "quantity": int(row.quantity or 0),
            "filled_quantity": int(row.filled_quantity or 0),
            "avg_fill_price": str(row.avg_fill_price or "0"),
            "status": row.status,
            "submitted_at": row.submitted_at.isoformat(sep=" ", timespec="seconds") if row.submitted_at else "",
        }

    def _serialize_trade(self, row: BacktestTrade) -> dict[str, Any]:
        return {
            "trade_id": row.trade_id,
            "broker_trade_id": row.broker_trade_no,
            "order_id": row.broker_order_no or str(row.order_id or ""),
            "symbol": row.symbol,
            "name": row.name or "",
            "side": row.side,
            "price": str(row.price),
            "quantity": int(row.quantity or 0),
            "amount": str(row.amount),
            "traded_at": row.traded_at.isoformat(sep=" ", timespec="seconds") if row.traded_at else "",
        }

    def _serialize_balance(self, row: BacktestBalanceSnapshot) -> dict[str, Any]:
        return {
            "account_id": str(row.account_id),
            "run_id": row.run_id,
            "mode": row.source,
            "total_asset": str(row.total_asset),
            "available_cash": str(row.available_cash),
            "withdrawable_cash": str(row.withdrawable_cash),
            "market_value": str(row.market_value),
            "cash_balance": str(row.cash_balance),
            "frozen_cash": str(row.frozen_cash),
            "updated_at": row.snapshot_time.isoformat(sep=" ", timespec="seconds") if row.snapshot_time else "",
        }

    def _serialize_position(self, row: BacktestPositionSnapshot) -> dict[str, Any]:
        return {
            "position_id": f"{row.account_id}:{row.run_id}:{row.symbol}",
            "symbol": row.symbol,
            "name": row.name or "",
            "quantity": int(row.quantity or 0),
            "available_quantity": int(row.available_quantity or 0),
            "cost_price": str(row.cost_price or "0"),
            "last_price": str(row.last_price or "0"),
            "market_value": str(row.market_value or "0"),
            "unrealized_pnl": str(row.unrealized_pnl or "0"),
        }
