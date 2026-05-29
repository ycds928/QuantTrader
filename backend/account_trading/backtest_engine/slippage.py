from __future__ import annotations

from decimal import Decimal

from .schemas import OrderSide, SlippageRule


class BacktestSlippageCalculator:
    def __init__(self, rule: SlippageRule | None = None) -> None:
        self.rule = rule or SlippageRule()

    def apply(self, side: OrderSide, price: Decimal) -> Decimal:
        if self.rule.type == "fixed_tick":
            delta = self.rule.value
        elif self.rule.type == "percent":
            delta = price * self.rule.value
        else:
            delta = Decimal("0")
        adjusted = price + delta if side == "buy" else price - delta
        return max(adjusted, Decimal("0")).quantize(Decimal("0.0001"))
