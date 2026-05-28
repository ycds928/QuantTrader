from __future__ import annotations

from decimal import Decimal

from .fees import BacktestFeeCalculator
from .schemas import BacktestBar, BacktestOrderRequest, MatchResult
from .slippage import BacktestSlippageCalculator


class BacktestMatcher:
    def __init__(
        self,
        fee_calculator: BacktestFeeCalculator,
        slippage_calculator: BacktestSlippageCalculator,
        volume_limit_ratio: Decimal,
    ) -> None:
        self.fee_calculator = fee_calculator
        self.slippage_calculator = slippage_calculator
        self.volume_limit_ratio = volume_limit_ratio

    def match(
        self,
        request: BacktestOrderRequest,
        bar: BacktestBar,
        *,
        available_cash: Decimal,
        available_quantity: int,
    ) -> MatchResult:
        if request.quantity <= 0:
            return self._empty("rejected", "委托数量必须大于 0")
        if bar.paused or bar.volume <= 0:
            return self._empty("submitted", "标的停牌或成交量为 0，订单保持待成交")

        raw_price = self._raw_match_price(request, bar)
        if raw_price is None:
            return self._empty("submitted", "限价条件未满足，订单保持待成交")

        fill_price = self.slippage_calculator.apply(request.side, raw_price)
        if bar.limit_up is not None and fill_price > bar.limit_up:
            return self._empty("rejected", "成交价超过涨停价")
        if bar.limit_down is not None and fill_price < bar.limit_down:
            return self._empty("rejected", "成交价低于跌停价")

        max_quantity = self._max_fill_quantity(request, bar)
        if max_quantity <= 0:
            return self._empty("submitted", "成交量约束导致当前 bar 无法成交")
        fill_quantity = min(request.quantity, max_quantity)
        amount = (fill_price * Decimal(fill_quantity)).quantize(Decimal("0.0001"))
        commission, stamp_tax, transfer_fee, total_fee = self.fee_calculator.calculate(request.side, amount)
        if request.side == "buy" and available_cash < amount + total_fee:
            return self._empty("rejected", f"回测账户可用资金不足，需要 {amount + total_fee}，当前 {available_cash}")
        if request.side == "sell" and available_quantity < fill_quantity:
            return self._empty("rejected", f"回测账户可卖持仓不足，需要 {fill_quantity}，当前 {available_quantity}")

        return MatchResult(
            status="filled" if fill_quantity == request.quantity else "partial_filled",
            fill_price=fill_price,
            fill_quantity=fill_quantity,
            amount=amount,
            commission=commission,
            stamp_tax=stamp_tax,
            transfer_fee=transfer_fee,
            total_fee=total_fee,
            reason="订单按下一根历史 K 线撮合成交" if fill_quantity == request.quantity else "订单受成交量约束部分成交",
        )

    def _raw_match_price(self, request: BacktestOrderRequest, bar: BacktestBar) -> Decimal | None:
        if request.order_type == "market":
            return bar.open
        if request.price is None or request.price <= 0:
            return None
        if request.side == "buy":
            if request.price < bar.low:
                return None
            return min(request.price, bar.open).quantize(Decimal("0.0001"))
        if request.price > bar.high:
            return None
        return max(request.price, bar.open).quantize(Decimal("0.0001"))

    def _max_fill_quantity(self, request: BacktestOrderRequest, bar: BacktestBar) -> int:
        volume_cap = int(Decimal(bar.volume) * self.volume_limit_ratio) if bar.volume > 0 else 0
        if volume_cap <= 0:
            return 0
        return min(request.quantity, volume_cap)

    def _empty(self, status: str, reason: str) -> MatchResult:
        return MatchResult(
            status=status,  # type: ignore[arg-type]
            fill_price=Decimal("0"),
            fill_quantity=0,
            amount=Decimal("0"),
            commission=Decimal("0"),
            stamp_tax=Decimal("0"),
            transfer_fee=Decimal("0"),
            total_fee=Decimal("0"),
            reason=reason,
        )
