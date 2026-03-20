"""
Offer Engine: iBuyer logic.
offer = predicted_resale - transaction_cost - holding_cost - risk_margin
Output: offer_price, expected_profit
"""

from dataclasses import dataclass


@dataclass
class OfferResult:
    offer_price: float
    expected_profit: float
    predicted_resale: float
    expected_hold_days: float
    transaction_cost: float
    holding_cost: float
    risk_margin: float
    is_profitable: bool


class OfferEngine:
    """Compute iBuyer offer and expected profit."""

    def __init__(
        self,
        transaction_cost_pct: float = 0.08,
        holding_cost_per_day: float = 150.0,
        risk_margin_pct: float = 0.05,
    ):
        self.transaction_cost_pct = transaction_cost_pct
        self.holding_cost_per_day = holding_cost_per_day
        self.risk_margin_pct = risk_margin_pct

    def compute(self, predicted_resale: float, expected_hold_days: float) -> OfferResult:
        """
        offer = predicted_resale - transaction_cost - holding_cost - risk_margin
        """
        transaction_cost = self.transaction_cost_pct * predicted_resale
        holding_cost = self.holding_cost_per_day * expected_hold_days
        risk_margin = self.risk_margin_pct * predicted_resale

        offer_price = predicted_resale - transaction_cost - holding_cost - risk_margin
        expected_profit = risk_margin

        return OfferResult(
            offer_price=max(0, offer_price),
            expected_profit=expected_profit,
            predicted_resale=predicted_resale,
            expected_hold_days=expected_hold_days,
            transaction_cost=transaction_cost,
            holding_cost=holding_cost,
            risk_margin=risk_margin,
            is_profitable=offer_price > 0 and expected_profit > 0,
        )
