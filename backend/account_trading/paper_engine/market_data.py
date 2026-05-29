from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Protocol

from api_data.router import fetch_tencent_quote

from .schemas import OrderBookLevel, RealtimeQuote


class MarketDataProvider(Protocol):
    async def get_quote(self, symbol: str) -> RealtimeQuote:
        ...

    async def get_quotes(self, symbols: list[str]) -> dict[str, RealtimeQuote]:
        ...


class MockMarketDataProvider:
    """Fallback provider used before an external realtime quote service is wired."""

    def __init__(self, fallback_price: Decimal | str | int | float = Decimal("10")) -> None:
        price = Decimal(str(fallback_price or "10"))
        self.fallback_price = price if price > 0 else Decimal("10")

    async def get_quote(self, symbol: str) -> RealtimeQuote:
        return self._quote(symbol)

    async def get_quotes(self, symbols: list[str]) -> dict[str, RealtimeQuote]:
        return {symbol: self._quote(symbol) for symbol in symbols}

    def _quote(self, symbol: str) -> RealtimeQuote:
        price = self.fallback_price
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


class TencentMarketDataProvider:
    """Realtime A-share quote provider backed by Tencent quote endpoint."""

    def __init__(self, fallback_price: Decimal | str | int | float | None = None) -> None:
        self.fallback_price = self._decimal(fallback_price or Decimal("0"))

    async def get_quote(self, symbol: str) -> RealtimeQuote:
        data = fetch_tencent_quote(symbol)
        if not data:
            return self._unavailable_quote(symbol)
        return self._quote_from_payload(symbol, data)

    async def get_quotes(self, symbols: list[str]) -> dict[str, RealtimeQuote]:
        return {symbol: await self.get_quote(symbol) for symbol in symbols}

    def _quote_from_payload(self, symbol: str, data: dict) -> RealtimeQuote:
        last_price = self._decimal(data.get("last_price"))
        if last_price <= 0:
            return self._unavailable_quote(symbol)
        bid_levels = [
            OrderBookLevel(price=self._decimal(row.get("price")), volume=max(0, int(row.get("volume") or 0)) * 100)
            for row in data.get("bid_levels") or []
            if self._decimal(row.get("price")) > 0
        ]
        ask_levels = [
            OrderBookLevel(price=self._decimal(row.get("price")), volume=max(0, int(row.get("volume") or 0)) * 100)
            for row in data.get("ask_levels") or []
            if self._decimal(row.get("price")) > 0
        ]
        return RealtimeQuote(
            symbol=str(data.get("symbol") or symbol),
            name=data.get("name") or None,
            exchange=data.get("exchange") or None,
            last_price=last_price,
            pre_close=self._optional_decimal(data.get("pre_close")),
            open_price=self._optional_decimal(data.get("open_price")),
            high_price=self._optional_decimal(data.get("high_price")),
            low_price=self._optional_decimal(data.get("low_price")),
            volume=max(sum(level.volume for level in bid_levels + ask_levels), 1),
            timestamp=self._parse_timestamp(data.get("timestamp")),
            trading_status="trading",
            bid_levels=bid_levels,
            ask_levels=ask_levels,
        )

    def _decimal(self, value) -> Decimal:
        try:
            return Decimal(str(value or "0"))
        except (InvalidOperation, ValueError):
            return Decimal("0")

    def _optional_decimal(self, value) -> Decimal | None:
        decimal = self._decimal(value)
        return decimal if decimal > 0 else None

    def _parse_timestamp(self, value) -> datetime:
        text = str(value or "")
        try:
            return datetime.strptime(text, "%Y%m%d%H%M%S")
        except ValueError:
            return datetime.now()

    def _unavailable_quote(self, symbol: str) -> RealtimeQuote:
        return RealtimeQuote(
            symbol=symbol,
            name=None,
            last_price=Decimal("0"),
            timestamp=datetime.now(),
            trading_status="unknown",
            bid_levels=[],
            ask_levels=[],
        )
