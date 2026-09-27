"""
Trade analysis and setup engine
"""

from dataclasses import dataclass
from typing import Optional
from app.parsers.base import NormalizedSignal


@dataclass
class TradeSetup:
    """Represents a complete trade setup"""
    
    signal: NormalizedSignal
    risk_reward_ratio: float
    pip_risk: float
    pip_reward: float
    position_size: Optional[float] = None
    notes: Optional[str] = None


class AnalysisEngine:
    """Performs technical analysis on signals"""
    
    @staticmethod
    def calculate_risk_reward(setup: NormalizedSignal) -> float:
        """
        Calculate risk/reward ratio for a setup.
        
        Args:
            setup: Normalized signal
            
        Returns:
            Risk/reward ratio
        """
        if not setup.entries or not setup.take_profits:
            return 0.0
        
        avg_entry = sum(setup.entries) / len(setup.entries)
        avg_tp = sum(setup.take_profits) / len(setup.take_profits)
        
        risk = abs(avg_entry - setup.stop_loss)
        reward = abs(avg_tp - avg_entry)
        
        if risk == 0:
            return 0.0
        
        return reward / risk
    
    @staticmethod
    def calculate_pips(symbol: str, price_diff: float) -> float:
        """
        Calculate pips for a price difference.
        Assumes standard 4-decimal pips for most pairs, 2-decimal for XAU.
        
        Args:
            symbol: Trading symbol
            price_diff: Price difference
            
        Returns:
            Number of pips
        """
        if symbol == "XAUUSD" or "XAU" in symbol:
            # Gold typically uses 1-decimal pips (0.1)
            return price_diff * 10
        else:
            # Standard pairs use 4-decimal pips (0.0001)
            return price_diff * 10000
