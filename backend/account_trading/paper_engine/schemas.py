from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Literal


OrderSide = Literal["buy", "sell"]
TradingStatus = Literal["trading", "halted", "closed", "unknown"]
SlippageType = Literal["none", "fixed_tick", "percent"]


@dataclass(frozen=True)
class OrderBookLevel:
    price: Decimal
    volume: int


@dataclass(frozen=True)
class RealtimeQuote:
    symbol: str
    last_price: Decimal
    timestamp: datetime
    name: str | None = None
    exchange: str | None = None
    pre_close: Decimal | None = None
    open_price: Decimal | None = None
    high_price: Decimal | None = None
    low_price: Decimal | None = None
    limit_up: Decimal | None = None
    limit_down: Decimal | None = None
    volume: int = 0
    turnover: Decimal | None = None
    trading_status: TradingStatus = "unknown"
    bid_levels: list[OrderBookLevel] = field(default_factory=list)
    ask_levels: list[OrderBookLevel] = field(default_factory=list)


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
class PaperOrderRequest:
    symbol: str
    side: OrderSide
    price: Decimal
    quantity: int


@dataclass(frozen=True)
class MatchDecision:
    status: Literal["filled", "partial_filled", "submitted", "rejected"]
    fill_price: Decimal
    fill_quantity: int
    requested_quantity: int
    amount: Decimal
    commission: Decimal
    stamp_tax: Decimal
    transfer_fee: Decimal
    total_fee: Decimal
    quote: RealtimeQuote
    reason: str
    market_value_price: Decimal

    @property
    def is_filled(self) -> bool:
        return self.status in {"filled", "partial_filled"} and self.fill_quantity > 0
