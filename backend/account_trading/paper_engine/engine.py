from __future__ import annotations

from decimal import Decimal

from .fees import FeeCalculator
from .market_data import MarketDataProvider, MockMarketDataProvider
from .schemas import FeeRule, MatchDecision, OrderBookLevel, PaperOrderRequest, SlippageRule
from .slippage import SlippageCalculator


class PaperTradingEngine:
    def __init__(
        self,
        market_data: MarketDataProvider | None = None,
        fee_rule: FeeRule | None = None,
        slippage_rule: SlippageRule | None = None,
        volume_limit_ratio: Decimal = Decimal("0.05"),
    ) -> None:
        self.market_data = market_data or MockMarketDataProvider()
        self.fee_calculator = FeeCalculator(fee_rule)
        self.slippage_calculator = SlippageCalculator(slippage_rule)
        self.volume_limit_ratio = volume_limit_ratio

    async def match_order(
        self,
        request: PaperOrderRequest,
        *,
        available_cash: Decimal,
        available_quantity: int,
    ) -> MatchDecision:
        quote = await self.market_data.get_quote(request.symbol)
        empty = self._empty_decision(request, quote)
        if quote.trading_status not in {"trading", "unknown"}:
            return empty("rejected", f"证券当前不可交易: {quote.trading_status}")
        if request.quantity <= 0 or request.price <= 0:
            return empty("rejected", "委托价格和数量必须大于 0")

        reference_price = self._reference_price(request.side, quote)
        if reference_price <= 0:
            return empty("submitted", "暂无可用实时盘口，订单保持待成交")
        fill_price = self.slippage_calculator.apply(request.side, reference_price)
        if not self._passes_limit_price(request, fill_price):
            return empty("submitted", "限价条件未满足，订单保持待成交")
        if quote.limit_up is not None and fill_price > quote.limit_up:
            return empty("rejected", "成交价超过涨停价")
        if quote.limit_down is not None and fill_price < quote.limit_down:
            return empty("rejected", "成交价低于跌停价")

        max_quantity = self._max_fill_quantity(request, quote)
        if max_quantity <= 0:
            return empty("submitted", "当前行情成交量不足，订单保持待成交")
        fill_quantity = min(request.quantity, max_quantity)
        amount = (fill_price * Decimal(fill_quantity)).quantize(Decimal("0.0001"))
        commission, stamp_tax, transfer_fee, total_fee = self.fee_calculator.calculate(request.side, amount)
        cash_need = amount + total_fee
        if request.side == "buy" and available_cash < cash_need:
            return empty("rejected", f"模拟账户可用资金不足，需要 {cash_need}，当前 {available_cash}")
        if request.side == "sell" and available_quantity < fill_quantity:
            return empty("rejected", f"模拟账户可卖持仓不足，需要 {fill_quantity}，当前 {available_quantity}")

        status = "filled" if fill_quantity == request.quantity else "partial_filled"
        return MatchDecision(
            status=status,
            fill_price=fill_price,
            fill_quantity=fill_quantity,
            requested_quantity=request.quantity,
            amount=amount,
            commission=commission,
            stamp_tax=stamp_tax,
            transfer_fee=transfer_fee,
            total_fee=total_fee,
            quote=quote,
            reason="订单已按实时行情撮合成交" if status == "filled" else "订单受成交量约束部分成交",
            market_value_price=quote.last_price,
        )

    def _empty_decision(self, request: PaperOrderRequest, quote):
        def build(status: str, reason: str) -> MatchDecision:
            return MatchDecision(
                status=status,  # type: ignore[arg-type]
                fill_price=Decimal("0"),
                fill_quantity=0,
                requested_quantity=request.quantity,
                amount=Decimal("0"),
                commission=Decimal("0"),
                stamp_tax=Decimal("0"),
                transfer_fee=Decimal("0"),
                total_fee=Decimal("0"),
                quote=quote,
                reason=reason,
                market_value_price=quote.last_price,
            )

        return build

    def _reference_price(self, side: str, quote) -> Decimal:
        levels: list[OrderBookLevel] = quote.ask_levels if side == "buy" else quote.bid_levels
        if levels:
            return levels[0].price
        return quote.last_price

    def _passes_limit_price(self, request: PaperOrderRequest, fill_price: Decimal) -> bool:
        if request.side == "buy":
            return fill_price <= request.price
        return fill_price >= request.price

    def _max_fill_quantity(self, request: PaperOrderRequest, quote) -> int:
        book_levels: list[OrderBookLevel] = quote.ask_levels if request.side == "buy" else quote.bid_levels
        book_volume = sum(max(level.volume, 0) for level in book_levels)
        volume_cap = int(quote.volume * self.volume_limit_ratio) if quote.volume else request.quantity
        candidates = [request.quantity]
        if book_volume > 0:
            candidates.append(book_volume)
        if volume_cap > 0:
            candidates.append(volume_cap)
        return max(0, min(candidates))
