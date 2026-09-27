"""
Market regime and setup-decision skeleton.

This is intentionally a thin skeleton for Phase 5 (see project spec section 11).
Full market-structure/liquidity/FVG detection algorithms are NOT implemented
here yet — each method is a clear extension point. Do not treat any single
indicator (e.g. RSI) as the primary decision driver when filling these in.
"""

from dataclasses import dataclass, field
from typing import List, Literal, Optional

Regime = Literal["BULLISH", "BEARISH", "RANGE", "TRANSITION", "UNKNOWN"]
Decision = Literal["WAIT", "VALID_SETUP", "INVALIDATED", "NO_SETUP", "ACTIVE", "COMPLETED"]


@dataclass
class RegimeResult:
    """Descriptive market regime with the reasons behind it"""

    regime: Regime
    timeframe: str
    reasons: List[str] = field(default_factory=list)


@dataclass
class SetupDecision:
    """Outcome of comparing a signal against current market context"""

    decision: Decision
    reason: str
    preferred_entry: Optional[float] = None
    invalidation: Optional[float] = None
    targets: List[float] = field(default_factory=list)


class MarketAnalysisEngine:
    """
    Determines market regime/structure and validates a signal against
    current market context before it becomes a trade setup.

    Extension points (not yet implemented):
      - detect_structure(candles) -> HH/HL/LH/LL, BOS, CHoCH
      - detect_liquidity(candles) -> swing highs/lows, equal highs/lows, sweeps
      - detect_supply_demand(candles) -> zones
      - detect_fvg(candles) -> 3-candle fair value gaps
      - calculate_atr(candles) / calculate_vwap(candles) / calculate_rsi(candles)
    """

    @staticmethod
    def determine_regime(timeframe: str) -> RegimeResult:
        """
        Placeholder regime determination.

        TODO: replace with real structure detection (HH/HL/LH/LL, BOS, CHoCH)
        once candle data and structure detection are implemented.
        """
        return RegimeResult(
            regime="UNKNOWN",
            timeframe=timeframe,
            reasons=["Market structure detection not yet implemented"],
        )

    @staticmethod
    def validate_setup(
        direction: str,
        current_price: Optional[float],
        preferred_entry: Optional[float],
        invalidation: Optional[float],
        targets: List[float],
    ) -> SetupDecision:
        """
        Compare signal direction/entry against current price.

        A signal must NOT automatically become a trade recommendation —
        this always defaults to WAIT until real structure/liquidity checks
        are implemented (see extension points above).
        """
        if current_price is None or preferred_entry is None:
            return SetupDecision(
                decision="NO_SETUP",
                reason="Insufficient market data to evaluate this signal",
            )

        return SetupDecision(
            decision="WAIT",
            reason="Price has not reached the preferred entry zone",
            preferred_entry=preferred_entry,
            invalidation=invalidation,
            targets=targets,
        )
