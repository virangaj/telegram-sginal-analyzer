"""
Trade management and execution engine
"""

from typing import Optional
from app.parsers.base import NormalizedSignal


class TradeEngine:
    """Manages trade setup, execution, and monitoring"""
    
    @staticmethod
    def create_trade_setup(
        signal: NormalizedSignal,
        account_balance: float,
        risk_percent: float = 2.0
    ) -> dict:
        """
        Create a trade setup from a signal.
        
        Args:
            signal: Normalized signal
            account_balance: Current account balance
            risk_percent: Risk percentage per trade (default 2%)
            
        Returns:
            Trade setup dictionary with position sizing
        """
        if not signal.entries or not signal.take_profits:
            return {}
        
        # Calculate risk amount
        risk_amount = account_balance * (risk_percent / 100)
        
        # Calculate average entry and pips
        avg_entry = sum(signal.entries) / len(signal.entries)
        pips_to_sl = abs(avg_entry - signal.stop_loss)
        
        if pips_to_sl == 0:
            return {}
        
        # Calculate lot size (simplified - doesn't account for symbol pip value)
        lot_size = risk_amount / pips_to_sl
        
        return {
            "signal": signal.model_dump(),
            "risk_amount": risk_amount,
            "lot_size": lot_size,
            "average_entry": avg_entry,
            "stop_loss": signal.stop_loss,
            "take_profits": signal.take_profits,
            "risk_reward_ratio": sum(signal.take_profits) / len(signal.take_profits) / pips_to_sl
        }
