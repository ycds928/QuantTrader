from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Literal


OrderSide = Literal["buy", "sell"]
OrderType = Literal["market", "limit"]
MatchStatus = Literal["filled", "partial_filled", "submitted", "rejected", "expired"]
SlippageType = Literal["none", "fixed_tick", "percent"]


@dataclass(frozen=True)
class FeeRule:
    commission_rate: Decimal = Decimal("0.00025")
    min_commission: Decimal = Decimal("5")
    stamp_tax_rate_sell: Decimal = Decimal("0.0005")
    transfer_fee_rate: Decimal = Decimal("0")


@dataclass(frozen=True)
class SlippageRule:
    type: SlippageType = "none"
    value: Decimal = Decimal("0")


@dataclass(frozen=True)
class BacktestContext:
    account_id: int
    run_id: str
    strategy_id: str
    start_date: date
    end_date: date
    initial_cash: Decimal
    version_id: str | None = None
    benchmark_symbol: str | None = None
    frequency: str = "daily"
    fee_rule: FeeRule = FeeRule()
    slippage_rule: SlippageRule = SlippageRule()
    volume_limit_ratio: Decimal = Decimal("0.1")


@dataclass(frozen=True)
class BacktestBar:
    symbol: str
    trade_date: date
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    amount: Decimal | None = None
    name: str | None = None
    exchange: str | None = None
    limit_up: Decimal | None = None
    limit_down: Decimal | None = None
    paused: bool = False


@dataclass(frozen=True)
class BacktestOrderRequest:
    symbol: str
    side: OrderSide
    quantity: int
    signal_time: datetime
    price: Decimal | None = None
    order_type: OrderType = "limit"
    signal_id: str | None = None
    remark: str | None = None


@dataclass(frozen=True)
class MatchResult:
    status: MatchStatus
    fill_price: Decimal
    fill_quantity: int
    amount: Decimal
    commission: Decimal
    stamp_tax: Decimal
    transfer_fee: Decimal
    total_fee: Decimal
    reason: str

    @property
    def is_filled(self) -> bool:
        return self.status in {"filled", "partial_filled"} and self.fill_quantity > 0
