"""
Entry engine: calculates entry zone, stop loss, targets, and R:R for a signal.

Independent from the signal parser and from the risk engine. This engine
answers "where would we enter and what does the setup look like" — it does
NOT decide position sizing or dollar risk (see app.risk.engine.RiskEngine).
"""

from dataclasses import dataclass
from typing import List, Optional

from app.parsers.base import NormalizedSignal


@dataclass
class ScaledEntry:
    """A single scaling entry with its suggested allocation"""

    price: float
    allocation_percent: float  # 0.0 - 1.0


@dataclass
class EntryPlan:
    """Computed entry plan for a signal, given the current market price"""

    signal_entry: float  # average of the entries as given in the raw signal
    current_price: Optional[float]
    preferred_entry: float  # best single entry price within the zone
    entry_zone_low: float
    entry_zone_high: float
    invalidation: float  # price beyond which the setup is no longer valid (== stop_loss for now)
    stop_loss: float
    take_profits: List[float]  # TP1, TP2, TP3...
    risk_reward: float  # based on preferred_entry vs stop_loss vs nearest TP
    distance_to_stop: float
    distance_to_target: float  # distance to first take profit
    scaled_entries: List[ScaledEntry]
    atr: Optional[float] = None


class EntryEngine:
    """
    Builds an EntryPlan from a normalized signal.

    Scaling allocations are configurable inputs, not hard-coded trading
    rules — callers may pass their own weighting, or accept the even-split
    default.
    """

    @staticmethod
    def build_plan(
        signal: NormalizedSignal,
        current_price: Optional[float] = None,
        atr: Optional[float] = None,
        allocations: Optional[List[float]] = None,
    ) -> Optional[EntryPlan]:
        """
        Args:
            signal: Normalized signal (entries, stop_loss, take_profits)
            current_price: Latest market price, if available
            atr: Current ATR value for volatility context, if available
            allocations: Fraction of position per entry, same length/order as
                signal.entries. Must sum to 1.0. Defaults to an even split.

        Returns:
            EntryPlan, or None if the signal has insufficient data.
        """
        if not signal.entries or not signal.take_profits:
            return None

        entries = signal.entries
        n = len(entries)

        if allocations is None:
            allocations = [1.0 / n] * n
        elif len(allocations) != n or abs(sum(allocations) - 1.0) > 1e-6:
            raise ValueError("allocations must match entries length and sum to 1.0")

        scaled_entries = [
            ScaledEntry(price=price, allocation_percent=alloc)
            for price, alloc in zip(entries, allocations)
        ]

        entry_zone_low = min(entries)
        entry_zone_high = max(entries)
        signal_entry = sum(entries) / n

        # Preferred entry: allocation-weighted average price (favors the
        # heaviest-weighted scaling level rather than a plain midpoint).
        preferred_entry = sum(p * a for p, a in zip(entries, allocations))

        stop_loss = signal.stop_loss
        take_profits = sorted(
            signal.take_profits,
            key=lambda tp: abs(tp - preferred_entry),
        )
        nearest_tp = take_profits[0]

        distance_to_stop = abs(preferred_entry - stop_loss)
        distance_to_target = abs(nearest_tp - preferred_entry)

        risk_reward = (
            distance_to_target / distance_to_stop if distance_to_stop > 0 else 0.0
        )

        return EntryPlan(
            signal_entry=signal_entry,
            current_price=current_price,
            preferred_entry=preferred_entry,
            entry_zone_low=entry_zone_low,
            entry_zone_high=entry_zone_high,
            invalidation=stop_loss,
            stop_loss=stop_loss,
            take_profits=take_profits,
            risk_reward=risk_reward,
            distance_to_stop=distance_to_stop,
            distance_to_target=distance_to_target,
            scaled_entries=scaled_entries,
            atr=atr,
        )
