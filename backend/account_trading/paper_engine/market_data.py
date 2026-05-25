from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Protocol

from .schemas import OrderBookLevel, RealtimeQuote


class MarketDataProvider(Protocol):
    async def get_quote(self, symbol: str) -> RealtimeQuote:
        ...

    async def get_quotes(self, symbols: list[str]) -> dict[str, RealtimeQuote]:
        ...


class MockMarketDataProvider:
    """Fallback provider used before an external realtime quote service is wired."""

    async def get_quote(self, symbol: str) -> RealtimeQuote:
        return self._quote(symbol)

    async def get_quotes(self, symbols: list[str]) -> dict[str, RealtimeQuote]:
        return {symbol: self._quote(symbol) for symbol in symbols}

    def _quote(self, symbol: str) -> RealtimeQuote:
        price = Decimal("10")
        return RealtimeQuote(
            symbol=symbol,
            name="",
            last_price=price,
            pre_close=price,
            limit_up=price * Decimal("1.1"),
            limit_down=price * Decimal("0.9"),
            volume=10_000_000,
            timestamp=datetime.now(),
            trading_status="trading",
            bid_levels=[OrderBookLevel(price=price, volume=1_000_000)],
            ask_levels=[OrderBookLevel(price=price, volume=1_000_000)],
        )
