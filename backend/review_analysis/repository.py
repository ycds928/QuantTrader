from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import uuid4

from sqlalchemy import case, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from account_trading.models import (
    BacktestBalanceSnapshot,
    BacktestTrade,
    LiveBalanceSnapshot,
    LiveTrade,
    PaperBalanceSnapshot,
    PaperTrade,
    TradingAccount,
)

from .models import (
    ReviewDrawdownCurve,
    ReviewEquityCurve,
    ReviewMetricSnapshot,
    ReviewSession,
    ReviewSuggestion,
    ReviewTradeItem,
)


@dataclass
class TradeAnalysis:
    row: LiveTrade | PaperTrade | BacktestTrade
    pnl: Decimal | None
    pnl_ratio: Decimal | None
    holding_minutes: int | None


def _today() -> date:
    return date.today()


def _decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value or "0").replace(",", ""))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _date_text(value: date | None) -> str | None:
    return value.isoformat() if value else None


def _datetime_text(value: datetime | None) -> str | None:
    return value.isoformat(sep=" ", timespec="seconds") if value else None


def _float(value: Decimal | int | float | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


class ReviewAnalysisRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_accounts(self) -> list[dict[str, Any]]:
        result = await self.db.execute(
            select(TradingAccount)
            .where(TradingAccount.status != "archived")
            .order_by(TradingAccount.is_default.desc(), TradingAccount.id.desc())
        )
        return [self._serialize_account(row) for row in result.scalars().all()]

    async def list_sessions(self, limit: int = 20) -> list[dict[str, Any]]:
        result = await self.db.execute(select(ReviewSession).order_by(ReviewSession.id.desc()).limit(limit))
        sessions = result.scalars().all()
        if not sessions:
            return []
        account_ids = [row.account_id for row in sessions if row.account_id]
        accounts: dict[int, TradingAccount] = {}
        if account_ids:
            account_result = await self.db.execute(select(TradingAccount).where(TradingAccount.id.in_(account_ids)))
            accounts = {row.id: row for row in account_result.scalars().all()}
        return [self._serialize_session(row, accounts.get(row.account_id or 0)) for row in sessions]

    async def generate_session(
        self,
        *,
        account_id: int,
        start_date: date | None,
        end_date: date | None,
        title: str | None = None,
        strategy_id: str | None = None,
        version_id: str | None = None,
        benchmark_symbol: str | None = None,
        run_id: str | None = None,
    ) -> dict[str, Any]:
        account = await self._get_account(account_id)
        if account.status == "archived":
            raise ValueError("已归档账户不能生成复盘")

        trade_cls = self._trade_cls(account.account_type)
        balance_cls = self._balance_cls(account.account_type)
        end_date = end_date or _today()
        start_date = start_date or end_date - timedelta(days=30)
        if start_date > end_date:
            raise ValueError("复盘开始日期不能晚于结束日期")

        trades = await self._load_trades(
            trade_cls,
            account_id=account.id,
            start_date=start_date,
            end_date=end_date,
            strategy_id=strategy_id,
            version_id=version_id,
            run_id=run_id,
        )
        cost_basis_trades = await self._load_trades(
            trade_cls,
            account_id=account.id,
            start_date=date(1970, 1, 1),
            end_date=end_date,
            strategy_id=strategy_id,
            version_id=version_id,
            run_id=run_id,
        )
        balances = await self._load_balances(balance_cls, account_id=account.id, start_date=start_date, end_date=end_date, run_id=run_id)
        trade_analyses = [
            item
            for item in self._analyze_trades(cost_basis_trades)
            if item.row.trade_date >= start_date and item.row.trade_date <= end_date
        ]
        equity_points = self._build_equity_points(balances, account, cost_basis_trades, start_date, end_date)
        metrics = self._build_metrics(trade_analyses, equity_points)
        suggestions = self._build_suggestions(metrics, trade_analyses, equity_points)

        session = ReviewSession(
            session_code=f"REV-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:6].upper()}",
            account_id=account.id,
            strategy_id=strategy_id,
            version_id=version_id,
            account_type=account.account_type,
            source=account.account_type,
            start_date=start_date,
            end_date=end_date,
            benchmark_symbol=benchmark_symbol,
            title=title or f"{account.account_name} {start_date.isoformat()} 至 {end_date.isoformat()} 复盘",
            status="done",
            params_json={
                "account_id": account.id,
                "run_id": run_id,
                "strategy_id": strategy_id,
                "version_id": version_id,
            },
            summary_json={
                "metrics": _json_safe(metrics),
                "trade_count": len(trade_analyses),
                "equity_points": len(equity_points),
                "suggestions": len(suggestions),
            },
        )
        self.db.add(session)
        await self.db.flush()

        await self._save_metrics(session.id, metrics)
        await self._save_trade_items(session.id, account, trade_analyses)
        await self._save_curves(session.id, equity_points)
        await self._save_suggestions(session.id, suggestions)
        await self.db.flush()
        return await self.get_report(session.id)

    async def get_report(self, session_id: int | None = None) -> dict[str, Any]:
        if session_id is None:
            raise ValueError("查询复盘报告必须提供 session_id，避免多账户场景串读。")
        session = await self._get_session(session_id)
        account = await self._get_account(session.account_id) if session.account_id else None
        metrics = await self._load_metric_payload(session.id)
        equity = await self.list_equity_curve(session.id)
        drawdown = await self.list_drawdown_curve(session.id)
        suggestions = await self.list_suggestions(session.id)
        trades = await self.list_trade_items(session.id, limit=10)
        return {
            "session": self._serialize_session(session, account),
            "metrics": metrics,
            "equity_curve": equity,
            "drawdown_curve": drawdown,
            "suggestions": suggestions,
            "recent_trades": trades,
        }

    async def list_trade_items(self, session_id: int | None = None, limit: int = 200) -> list[dict[str, Any]]:
        if session_id is None:
            raise ValueError("查询复盘交易明细必须提供 session_id。")
        session = await self._get_session(session_id)
        result = await self.db.execute(
            select(ReviewTradeItem)
            .where(ReviewTradeItem.session_id == session.id)
            .order_by(ReviewTradeItem.traded_at.desc(), ReviewTradeItem.id.desc())
            .limit(limit)
        )
        return [self._serialize_trade_item(row) for row in result.scalars().all()]

    async def list_suggestions(self, session_id: int | None = None) -> list[dict[str, Any]]:
        if session_id is None:
            raise ValueError("查询复盘建议必须提供 session_id。")
        session = await self._get_session(session_id)
        severity_rank = case(
            (ReviewSuggestion.severity == "high", 3),
            (ReviewSuggestion.severity == "medium", 2),
            (ReviewSuggestion.severity == "low", 1),
            else_=0,
        )
        result = await self.db.execute(
            select(ReviewSuggestion)
            .where(ReviewSuggestion.session_id == session.id)
            .order_by(severity_rank.desc(), ReviewSuggestion.id.asc())
        )
        return [self._serialize_suggestion(row) for row in result.scalars().all()]

    async def list_equity_curve(self, session_id: int | None = None) -> list[dict[str, Any]]:
        if session_id is None:
            raise ValueError("查询复盘净值曲线必须提供 session_id。")
        session = await self._get_session(session_id)
        result = await self.db.execute(
            select(ReviewEquityCurve)
            .where(ReviewEquityCurve.session_id == session.id)
            .order_by(ReviewEquityCurve.curve_date.asc(), ReviewEquityCurve.curve_time.asc(), ReviewEquityCurve.id.asc())
        )
        return [self._serialize_equity(row) for row in result.scalars().all()]

    async def list_drawdown_curve(self, session_id: int | None = None) -> list[dict[str, Any]]:
        if session_id is None:
            raise ValueError("查询复盘回撤曲线必须提供 session_id。")
        session = await self._get_session(session_id)
        result = await self.db.execute(
            select(ReviewDrawdownCurve)
            .where(ReviewDrawdownCurve.session_id == session.id)
            .order_by(ReviewDrawdownCurve.curve_date.asc(), ReviewDrawdownCurve.curve_time.asc(), ReviewDrawdownCurve.id.asc())
        )
        return [self._serialize_drawdown(row) for row in result.scalars().all()]

    async def delete_session(self, session_id: int) -> dict[str, Any]:
        session = await self._get_session(session_id)
        for model in (ReviewSuggestion, ReviewDrawdownCurve, ReviewEquityCurve, ReviewTradeItem, ReviewMetricSnapshot):
            await self.db.execute(delete(model).where(model.session_id == session.id))
        await self.db.delete(session)
        await self.db.flush()
        return {"session_id": session_id, "deleted": True}

    async def _get_account(self, account_id: int | None) -> TradingAccount:
        if not account_id:
            raise ValueError("必须选择账户")
        result = await self.db.execute(select(TradingAccount).where(TradingAccount.id == account_id))
        account = result.scalar_one_or_none()
        if account is None:
            raise LookupError("账户不存在")
        return account

    async def _get_session(self, session_id: int | None = None) -> ReviewSession:
        query = select(ReviewSession)
        if session_id:
            query = query.where(ReviewSession.id == session_id)
        query = query.order_by(ReviewSession.id.desc()).limit(1)
        result = await self.db.execute(query)
        session = result.scalar_one_or_none()
        if session is None:
            raise LookupError("暂无复盘会话，请先生成复盘")
        return session

    def _trade_cls(self, account_type: str) -> type[LiveTrade] | type[PaperTrade] | type[BacktestTrade]:
        if account_type == "live":
            return LiveTrade
        if account_type == "paper":
            return PaperTrade
        if account_type == "backtest":
            return BacktestTrade
        raise ValueError("不支持的账户类型")

    def _balance_cls(self, account_type: str) -> type[LiveBalanceSnapshot] | type[PaperBalanceSnapshot] | type[BacktestBalanceSnapshot]:
        if account_type == "live":
            return LiveBalanceSnapshot
        if account_type == "paper":
            return PaperBalanceSnapshot
        if account_type == "backtest":
            return BacktestBalanceSnapshot
        raise ValueError("不支持的账户类型")

    async def _load_trades(
        self,
        trade_cls: type[LiveTrade] | type[PaperTrade] | type[BacktestTrade],
        *,
        account_id: int,
        start_date: date,
        end_date: date,
        strategy_id: str | None,
        version_id: str | None,
        run_id: str | None,
    ) -> list[LiveTrade | PaperTrade | BacktestTrade]:
        query = select(trade_cls).where(
            trade_cls.account_id == account_id,
            trade_cls.trade_date >= start_date,
            trade_cls.trade_date <= end_date,
        )
        if strategy_id:
            query = query.where(trade_cls.strategy_id == strategy_id)
        if version_id:
            query = query.where(trade_cls.version_id == version_id)
        if run_id and hasattr(trade_cls, "run_id"):
            query = query.where(trade_cls.run_id == run_id)
        query = query.order_by(trade_cls.traded_at.asc(), trade_cls.id.asc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def _load_balances(
        self,
        balance_cls: type[LiveBalanceSnapshot] | type[PaperBalanceSnapshot] | type[BacktestBalanceSnapshot],
        *,
        account_id: int,
        start_date: date,
        end_date: date,
        run_id: str | None,
    ) -> list[LiveBalanceSnapshot | PaperBalanceSnapshot | BacktestBalanceSnapshot]:
        query = select(balance_cls).where(
            balance_cls.account_id == account_id,
            balance_cls.trade_date >= start_date,
            balance_cls.trade_date <= end_date,
        )
        if run_id and hasattr(balance_cls, "run_id"):
            query = query.where(balance_cls.run_id == run_id)
        query = query.order_by(balance_cls.snapshot_time.asc(), balance_cls.id.asc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    def _analyze_trades(self, trades: list[LiveTrade | PaperTrade | BacktestTrade]) -> list[TradeAnalysis]:
        lots: dict[str, deque[tuple[int, Decimal, datetime]]] = defaultdict(deque)
        analyses: list[TradeAnalysis] = []
        for row in trades:
            side = str(row.side or "").lower()
            quantity = int(row.quantity or 0)
            amount = _decimal(row.amount)
            fee = _decimal(row.commission) + _decimal(row.stamp_tax) + _decimal(getattr(row, "transfer_fee", None))
            pnl: Decimal | None = None
            pnl_ratio: Decimal | None = None
            holding_minutes: int | None = None

            if side == "buy" and quantity > 0:
                lots[row.symbol].append((quantity, amount + fee, row.traded_at))
            elif side == "sell" and quantity > 0:
                remaining = quantity
                cost = Decimal("0")
                first_buy_at: datetime | None = None
                while remaining > 0 and lots[row.symbol]:
                    lot_quantity, lot_cost, lot_at = lots[row.symbol][0]
                    used_quantity = min(remaining, lot_quantity)
                    used_cost = lot_cost * Decimal(used_quantity) / Decimal(lot_quantity)
                    cost += used_cost
                    if first_buy_at is None:
                        first_buy_at = lot_at
                    remaining -= used_quantity
                    lot_quantity -= used_quantity
                    lot_cost -= used_cost
                    if lot_quantity <= 0:
                        lots[row.symbol].popleft()
                    else:
                        lots[row.symbol][0] = (lot_quantity, lot_cost, lot_at)
                if cost > 0:
                    pnl = amount - fee - cost
                    pnl_ratio = pnl / cost
                if first_buy_at:
                    holding_minutes = max(0, int((row.traded_at - first_buy_at).total_seconds() // 60))
            analyses.append(TradeAnalysis(row=row, pnl=pnl, pnl_ratio=pnl_ratio, holding_minutes=holding_minutes))
        return analyses

    def _build_equity_points(
        self,
        balances: list[LiveBalanceSnapshot | PaperBalanceSnapshot | BacktestBalanceSnapshot],
        account: TradingAccount,
        trades: list[LiveTrade | PaperTrade | BacktestTrade],
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        if balances:
            first_asset = max(_decimal(balances[0].total_asset), Decimal("0.0001"))
            return [
                {
                    "date": row.trade_date,
                    "time": row.snapshot_time,
                    "total_asset": _decimal(row.total_asset),
                    "cash_balance": _decimal(row.cash_balance),
                    "market_value": _decimal(row.market_value),
                    "equity": _decimal(row.total_asset) / first_asset,
                    "cumulative_return": (_decimal(row.total_asset) / first_asset) - Decimal("1"),
                }
                for row in balances
            ]

        initial_cash = _decimal((account.meta_json or {}).get("initial_cash")) or Decimal("1000000")
        cash = initial_cash
        positions: dict[str, tuple[int, Decimal]] = {}

        def apply_trade(row: LiveTrade | PaperTrade | BacktestTrade) -> None:
            nonlocal cash
            amount = _decimal(row.amount)
            fee = _decimal(row.commission) + _decimal(row.stamp_tax) + _decimal(getattr(row, "transfer_fee", None))
            price = _decimal(row.price)
            quantity = int(row.quantity or 0)
            current_quantity, current_price = positions.get(row.symbol, (0, price))
            if str(row.side).lower() == "sell":
                cash += amount - fee
                positions[row.symbol] = (max(0, current_quantity - quantity), price or current_price)
            else:
                cash -= amount + fee
                positions[row.symbol] = (current_quantity + quantity, price or current_price)

        def current_market_value() -> Decimal:
            return sum(Decimal(quantity) * price for quantity, price in positions.values() if quantity > 0)

        for row in trades:
            if row.trade_date < start_date:
                apply_trade(row)

        start_market_value = current_market_value()
        start_asset = max(cash + start_market_value, Decimal("0.0001"))
        points = [
            {
                "date": start_date,
                "time": datetime.combine(start_date, datetime.min.time()),
                "total_asset": cash + start_market_value,
                "cash_balance": cash,
                "market_value": start_market_value,
                "equity": Decimal("1"),
                "cumulative_return": Decimal("0"),
            }
        ]
        for row in trades:
            if row.trade_date < start_date:
                continue
            apply_trade(row)
            market_value = current_market_value()
            total_asset = cash + market_value
            equity = total_asset / start_asset if start_asset > 0 else Decimal("1")
            points.append(
                {
                    "date": row.trade_date,
                    "time": row.traded_at,
                    "total_asset": total_asset,
                    "cash_balance": cash,
                    "market_value": market_value,
                    "equity": equity,
                    "cumulative_return": equity - Decimal("1"),
                }
            )
        if points[-1]["date"] != end_date:
            points.append({**points[-1], "date": end_date, "time": datetime.combine(end_date, datetime.min.time())})
        return points

    def _build_metrics(self, analyses: list[TradeAnalysis], equity_points: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        trades = [item.row for item in analyses]
        sell_pnls = [item.pnl for item in analyses if item.pnl is not None]
        wins = [value for value in sell_pnls if value and value > 0]
        losses = [value for value in sell_pnls if value and value < 0]
        total_turnover = sum(_decimal(row.amount) for row in trades)
        total_fee = sum(_decimal(row.commission) + _decimal(row.stamp_tax) + _decimal(getattr(row, "transfer_fee", None)) for row in trades)
        realized_pnl = sum(sell_pnls, Decimal("0"))
        buy_count = len([row for row in trades if str(row.side).lower() == "buy"])
        sell_count = len([row for row in trades if str(row.side).lower() == "sell"])
        final_return = equity_points[-1]["cumulative_return"] if equity_points else Decimal("0")
        max_drawdown = self._max_drawdown(equity_points)
        profit_factor = sum(wins, Decimal("0")) / abs(sum(losses, Decimal("0"))) if losses else None
        avg_holding = [item.holding_minutes for item in analyses if item.holding_minutes is not None]

        return {
            "total_return": {"value": final_return, "unit": "%", "group": "performance", "text": f"{final_return * 100:.2f}%"},
            "realized_pnl": {"value": realized_pnl, "unit": "CNY", "group": "performance", "text": f"{realized_pnl:.2f}"},
            "max_drawdown": {"value": max_drawdown, "unit": "%", "group": "risk", "text": f"{max_drawdown * 100:.2f}%"},
            "trade_count": {"value": Decimal(len(trades)), "unit": "笔", "group": "trade", "text": str(len(trades))},
            "buy_count": {"value": Decimal(buy_count), "unit": "笔", "group": "trade", "text": str(buy_count)},
            "sell_count": {"value": Decimal(sell_count), "unit": "笔", "group": "trade", "text": str(sell_count)},
            "win_rate": {
                "value": Decimal(len(wins)) / Decimal(len(sell_pnls)) if sell_pnls else Decimal("0"),
                "unit": "%",
                "group": "trade",
                "text": f"{(Decimal(len(wins)) / Decimal(len(sell_pnls)) * 100) if sell_pnls else Decimal('0'):.2f}%",
            },
            "profit_factor": {
                "value": profit_factor,
                "unit": "倍",
                "group": "trade",
                "text": f"{profit_factor:.2f}" if profit_factor is not None else "-",
            },
            "turnover": {"value": total_turnover, "unit": "CNY", "group": "trade", "text": f"{total_turnover:.2f}"},
            "fee_total": {"value": total_fee, "unit": "CNY", "group": "cost", "text": f"{total_fee:.2f}"},
            "fee_ratio": {
                "value": total_fee / total_turnover if total_turnover > 0 else Decimal("0"),
                "unit": "%",
                "group": "cost",
                "text": f"{(total_fee / total_turnover * 100) if total_turnover > 0 else Decimal('0'):.3f}%",
            },
            "avg_holding_minutes": {
                "value": Decimal(sum(avg_holding)) / Decimal(len(avg_holding)) if avg_holding else Decimal("0"),
                "unit": "分钟",
                "group": "trade",
                "text": f"{(Decimal(sum(avg_holding)) / Decimal(len(avg_holding))) if avg_holding else Decimal('0'):.0f}",
            },
        }

    def _max_drawdown(self, points: list[dict[str, Any]]) -> Decimal:
        peak = Decimal("0")
        max_drawdown = Decimal("0")
        for point in points:
            equity = _decimal(point["equity"])
            peak = max(peak, equity)
            if peak > 0:
                max_drawdown = min(max_drawdown, equity / peak - Decimal("1"))
        return max_drawdown

    def _build_suggestions(
        self,
        metrics: dict[str, dict[str, Any]],
        analyses: list[TradeAnalysis],
        equity_points: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        suggestions: list[dict[str, Any]] = []
        trade_count = int(metrics["trade_count"]["value"])
        max_drawdown = _decimal(metrics["max_drawdown"]["value"])
        win_rate = _decimal(metrics["win_rate"]["value"])
        fee_ratio = _decimal(metrics["fee_ratio"]["value"])
        realized_pnl = _decimal(metrics["realized_pnl"]["value"])

        if trade_count == 0:
            suggestions.append(
                {
                    "type": "data",
                    "severity": "medium",
                    "title": "复盘区间内暂无成交",
                    "content": "当前复盘没有匹配到成交记录，建议先同步账户成交或缩小/调整复盘日期范围。",
                    "evidence": {"trade_count": trade_count},
                }
            )
            return suggestions
        if max_drawdown <= Decimal("-0.10"):
            suggestions.append(
                {
                    "type": "risk",
                    "severity": "high",
                    "title": "最大回撤偏高",
                    "content": "本轮复盘最大回撤超过 10%，建议降低单票仓位上限，增加止损或组合级别熔断规则。",
                    "evidence": {"max_drawdown": str(max_drawdown)},
                }
            )
        if win_rate < Decimal("0.40") and trade_count >= 5:
            suggestions.append(
                {
                    "type": "entry",
                    "severity": "medium",
                    "title": "胜率低于 40%",
                    "content": "交易胜率偏低，建议复查入场条件、过滤弱趋势信号，并单独统计买入后 1 日/3 日表现。",
                    "evidence": {"win_rate": str(win_rate), "trade_count": trade_count},
                }
            )
        if fee_ratio > Decimal("0.003"):
            suggestions.append(
                {
                    "type": "cost",
                    "severity": "medium",
                    "title": "交易成本占比偏高",
                    "content": "手续费、税费相对成交额偏高，建议减少低确定性高频交易，或在策略参数中加入最小预期收益过滤。",
                    "evidence": {"fee_ratio": str(fee_ratio)},
                }
            )
        if realized_pnl < 0:
            loss_symbols: dict[str, Decimal] = defaultdict(Decimal)
            for item in analyses:
                if item.pnl is not None and item.pnl < 0:
                    loss_symbols[item.row.symbol] += item.pnl
            worst = sorted(loss_symbols.items(), key=lambda row: row[1])[:3]
            suggestions.append(
                {
                    "type": "exit",
                    "severity": "medium",
                    "title": "已实现盈亏为负",
                    "content": "当前区间交易结果为亏损，建议优先复查亏损最大的标的和卖出纪律，确认是否存在补仓摊薄或止损滞后。",
                    "evidence": {"realized_pnl": str(realized_pnl), "worst_symbols": [{"symbol": k, "pnl": str(v)} for k, v in worst]},
                }
            )
        if equity_points and len(equity_points) < 3:
            suggestions.append(
                {
                    "type": "data",
                    "severity": "low",
                    "title": "资金快照数量不足",
                    "content": "净值曲线点位较少，建议在交易日结束后同步资金快照，便于计算更稳定的收益和回撤。",
                    "evidence": {"equity_points": len(equity_points)},
                }
            )
        if not suggestions:
            suggestions.append(
                {
                    "type": "position",
                    "severity": "low",
                    "title": "交易表现稳定",
                    "content": "本轮复盘暂未发现明显风险项，建议继续沉淀样本，并按策略、标的、时间段拆分比较表现。",
                    "evidence": {"trade_count": trade_count},
                }
            )
        return suggestions

    async def _save_metrics(self, session_id: int, metrics: dict[str, dict[str, Any]]) -> None:
        for key, item in metrics.items():
            self.db.add(
                ReviewMetricSnapshot(
                    session_id=session_id,
                    metric_key=key,
                    metric_value=_float(item.get("value")),
                    metric_text=item.get("text"),
                    metric_unit=item.get("unit"),
                    group_key=item.get("group"),
                    detail_json={"raw_value": str(item.get("value")) if item.get("value") is not None else None},
                )
            )

    async def _save_trade_items(self, session_id: int, account: TradingAccount, analyses: list[TradeAnalysis]) -> None:
        for item in analyses:
            row = item.row
            self.db.add(
                ReviewTradeItem(
                    session_id=session_id,
                    account_id=account.id,
                    order_id=row.order_id,
                    trade_id=row.trade_id,
                    source=account.account_type,
                    strategy_id=getattr(row, "strategy_id", None),
                    version_id=getattr(row, "version_id", None),
                    run_id=getattr(row, "run_id", None),
                    signal_id=getattr(row, "signal_id", None),
                    trade_date=row.trade_date,
                    traded_at=row.traded_at,
                    symbol=row.symbol,
                    name=row.name,
                    side=row.side,
                    price=_decimal(row.price),
                    quantity=int(row.quantity or 0),
                    amount=_decimal(row.amount),
                    pnl=_float(item.pnl),
                    pnl_ratio=_float(item.pnl_ratio),
                    holding_period_minutes=item.holding_minutes,
                    signal_tag=None,
                    detail_json={
                        "commission": str(_decimal(row.commission)),
                        "stamp_tax": str(_decimal(row.stamp_tax)),
                        "transfer_fee": str(_decimal(getattr(row, "transfer_fee", None))),
                        "broker_trade_no": row.broker_trade_no,
                        "broker_order_no": row.broker_order_no,
                    },
                )
            )

    async def _save_curves(self, session_id: int, points: list[dict[str, Any]]) -> None:
        peak = Decimal("0")
        peak_date: date | None = None
        used_points: set[tuple[date, datetime | None]] = set()
        for point in points:
            curve_date = point["date"]
            curve_time = point["time"]
            while (curve_date, curve_time) in used_points:
                curve_time = (curve_time or datetime.combine(curve_date, datetime.min.time())) + timedelta(seconds=1)
            used_points.add((curve_date, curve_time))
            equity = _decimal(point["equity"])
            if equity >= peak:
                peak = equity
                peak_date = curve_date
            drawdown = equity / peak - Decimal("1") if peak > 0 else Decimal("0")
            drawdown_amount = _decimal(point["total_asset"]) * drawdown
            self.db.add(
                ReviewEquityCurve(
                    session_id=session_id,
                    curve_date=curve_date,
                    curve_time=curve_time,
                    equity=equity,
                    total_asset=point["total_asset"],
                    cash_balance=point["cash_balance"],
                    market_value=point["market_value"],
                    cumulative_return=point["cumulative_return"],
                    benchmark_value=None,
                    detail_json=None,
                )
            )
            self.db.add(
                ReviewDrawdownCurve(
                    session_id=session_id,
                    curve_date=curve_date,
                    curve_time=curve_time,
                    equity=equity,
                    peak_equity=peak,
                    drawdown=drawdown,
                    drawdown_amount=drawdown_amount,
                    peak_date=peak_date,
                    detail_json=None,
                )
            )

    async def _save_suggestions(self, session_id: int, suggestions: list[dict[str, Any]]) -> None:
        for item in suggestions:
            self.db.add(
                ReviewSuggestion(
                    session_id=session_id,
                    suggestion_type=item["type"],
                    severity=item["severity"],
                    title=item["title"],
                    content=item["content"],
                    evidence_json=item.get("evidence"),
                    status="open",
                    owner=None,
                )
            )

    async def _load_metric_payload(self, session_id: int) -> dict[str, Any]:
        result = await self.db.execute(select(ReviewMetricSnapshot).where(ReviewMetricSnapshot.session_id == session_id))
        return {row.metric_key: self._serialize_metric(row) for row in result.scalars().all()}

    def _serialize_account(self, row: TradingAccount) -> dict[str, Any]:
        return {
            "id": row.id,
            "account_code": row.account_code,
            "account_name": row.account_name,
            "account_type": row.account_type,
            "broker_name": row.broker_name,
            "status": row.status,
            "is_default": bool(row.is_default),
        }

    def _serialize_session(self, row: ReviewSession, account: TradingAccount | None = None) -> dict[str, Any]:
        return {
            "id": row.id,
            "session_code": row.session_code,
            "title": row.title,
            "account_id": row.account_id,
            "account_name": account.account_name if account else "",
            "account_type": row.account_type,
            "source": row.source,
            "strategy_id": row.strategy_id,
            "version_id": row.version_id,
            "start_date": _date_text(row.start_date),
            "end_date": _date_text(row.end_date),
            "benchmark_symbol": row.benchmark_symbol,
            "status": row.status,
            "summary": row.summary_json or {},
            "created_at": _datetime_text(row.created_at),
            "updated_at": _datetime_text(row.updated_at),
        }

    def _serialize_metric(self, row: ReviewMetricSnapshot) -> dict[str, Any]:
        return {
            "key": row.metric_key,
            "value": str(row.metric_value) if row.metric_value is not None else None,
            "text": row.metric_text,
            "unit": row.metric_unit,
            "group": row.group_key,
            "detail": row.detail_json or {},
        }

    def _serialize_trade_item(self, row: ReviewTradeItem) -> dict[str, Any]:
        return {
            "id": row.id,
            "trade_id": row.trade_id,
            "order_id": row.order_id,
            "source": row.source,
            "strategy_id": row.strategy_id,
            "version_id": row.version_id,
            "run_id": row.run_id,
            "signal_id": row.signal_id,
            "trade_date": _date_text(row.trade_date),
            "traded_at": _datetime_text(row.traded_at),
            "symbol": row.symbol,
            "name": row.name or "",
            "side": row.side,
            "price": str(row.price),
            "quantity": int(row.quantity or 0),
            "amount": str(row.amount),
            "pnl": str(row.pnl) if row.pnl is not None else None,
            "pnl_ratio": str(row.pnl_ratio) if row.pnl_ratio is not None else None,
            "holding_period_minutes": row.holding_period_minutes,
            "signal_tag": row.signal_tag,
            "detail": row.detail_json or {},
        }

    def _serialize_suggestion(self, row: ReviewSuggestion) -> dict[str, Any]:
        return {
            "id": row.id,
            "type": row.suggestion_type,
            "severity": row.severity,
            "title": row.title,
            "content": row.content,
            "evidence": row.evidence_json or {},
            "status": row.status,
            "owner": row.owner,
            "created_at": _datetime_text(row.created_at),
        }

    def _serialize_equity(self, row: ReviewEquityCurve) -> dict[str, Any]:
        return {
            "date": _date_text(row.curve_date),
            "time": _datetime_text(row.curve_time),
            "equity": str(row.equity),
            "total_asset": str(row.total_asset or "0"),
            "cash_balance": str(row.cash_balance or "0"),
            "market_value": str(row.market_value or "0"),
            "cumulative_return": str(row.cumulative_return or "0"),
            "benchmark_value": str(row.benchmark_value) if row.benchmark_value is not None else None,
        }

    def _serialize_drawdown(self, row: ReviewDrawdownCurve) -> dict[str, Any]:
        return {
            "date": _date_text(row.curve_date),
            "time": _datetime_text(row.curve_time),
            "equity": str(row.equity),
            "peak_equity": str(row.peak_equity),
            "drawdown": str(row.drawdown),
            "drawdown_amount": str(row.drawdown_amount or "0"),
            "peak_date": _date_text(row.peak_date),
        }
