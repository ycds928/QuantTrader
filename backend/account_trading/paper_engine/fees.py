from __future__ import annotations

from decimal import Decimal

from .schemas import FeeRule, OrderSide


class FeeCalculator:
    def __init__(self, rule: FeeRule | None = None) -> None:
        self.rule = rule or FeeRule()

    def calculate(self, side: OrderSide, amount: Decimal) -> tuple[Decimal, Decimal, Decimal, Decimal]:
        commission = amount * self.rule.commission_rate
        if commission > 0 and commission < self.rule.min_commission:
            commission = self.rule.min_commission
        stamp_tax = amount * self.rule.stamp_tax_rate_sell if side == "sell" else Decimal("0")
        transfer_fee = amount * self.rule.transfer_fee_rate
        total_fee = commission + stamp_tax + transfer_fee
        return (
            commission.quantize(Decimal("0.0001")),
            stamp_tax.quantize(Decimal("0.0001")),
            transfer_fee.quantize(Decimal("0.0001")),
            total_fee.quantize(Decimal("0.0001")),
        )
