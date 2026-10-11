"""
Risk engine: calculates position sizing and worst-case risk.

Kept fully independent from the entry engine and parsers.
No prop-firm or broker rules are hard-coded here.
"""

from dataclasses import dataclass
from typing import List


@dataclass
class RiskEntry:
    """A single scaling entry: price + fraction of total position allocated to it"""

    price: float
    allocation: float  # 0.0 - 1.0, fraction of the position size


@dataclass
class RiskResult:
    """Computed risk figures for a trade setup"""

    account_balance: float
    risk_percent: float
    max_risk: float  # account_balance * risk_percent / 100
    position_size: float  # total units, sized so max_risk is the worst-case loss
    risk_per_entry: List[float]  # dollar risk contributed by each entry
    total_risk: float  # sum of risk_per_entry, should equal max_risk


class RiskEngine:
    """
    Computes total worst-case risk across all scaling entries.

    Key invariant: adding more scaling entries must NOT increase the total
    risk beyond `risk_percent` of the account. Each entry's position size is
    scaled down by its allocation so the combined worst-case loss (all
    entries filled, stopped out at stop_loss) equals max_risk.
    """

    @staticmethod
    def calculate(
        account_balance: float,
        risk_percent: float,
        stop_loss: float,
        entries: List[RiskEntry],
    ) -> RiskResult:
        if account_balance <= 0:
            raise ValueError("account_balance must be positive")
        if not entries:
            raise ValueError("at least one entry is required")
        if abs(sum(e.allocation for e in entries) - 1.0) > 1e-6:
            raise ValueError("entry allocations must sum to 1.0")

        max_risk = account_balance * (risk_percent / 100)

        # Weighted-average distance to stop across all entries, weighted by allocation.
        # This is the "risk per unit" of the full (100%) position.
        weighted_distance = sum(
            e.allocation * abs(e.price - stop_loss) for e in entries
        )

        if weighted_distance <= 0:
            raise ValueError("stop_loss must differ from entry prices")

        # Total position size such that worst-case loss across all entries == max_risk
        position_size = max_risk / weighted_distance

        risk_per_entry = [
            position_size * e.allocation * abs(e.price - stop_loss)
            for e in entries
        ]

        return RiskResult(
            account_balance=account_balance,
            risk_percent=risk_percent,
            max_risk=max_risk,
            position_size=position_size,
            risk_per_entry=risk_per_entry,
            total_risk=sum(risk_per_entry),
        )
