"""
Base signal parser abstract class
"""

from abc import ABC, abstractmethod
from typing import Optional
from pydantic import BaseModel


class NormalizedSignal(BaseModel):
    """Internal representation of any trading signal - normalized format"""
    
    symbol: str  # e.g., "XAUUSD", "EURUSD"
    direction: str  # "BUY" or "SELL"
    order_type: str  # "LIMIT" or "MARKET"
    
    # Can have multiple entries (for scaling)
    entries: list[float]
    
    # Single stop loss
    stop_loss: float
    
    # Can have multiple take profits (for scaling)
    take_profits: list[float]
    
    # Optional metadata
    timeframe: Optional[str] = None
    provider: Optional[str] = None
    confidence: Optional[float] = None  # 0.0 to 1.0
    notes: Optional[str] = None
    raw_signal_type: Optional[str] = None  # Parser name that parsed this


class SignalParser(ABC):
    """
    Base class for all signal parsers.
    Each parser is responsible for converting a message format
    into the normalized NormalizedSignal format.
    
    Design:
    1. Messages are ALWAYS stored to database first (regardless of parse success)
    2. Parser attempts to extract signal
    3. If successful, normalized signal is stored
    4. If failed, parse_error is recorded for later reprocessing
    """
    
    category: Optional[str] = None

    def __init__(self, name: str):
        self.name = name
    
    @abstractmethod
    def can_parse(self, message: str) -> bool:
        """
        Check if this parser can handle the message.
        
        Use deterministic rules (regex, string matching) NOT AI/LLM.
        This should be fast and 100% reliable.
        
        Args:
            message: Raw message text
            
        Returns:
            True if this parser can parse the message, False otherwise
        """
        pass
    
    @abstractmethod
    async def parse(self, message: str) -> Optional[NormalizedSignal]:
        """
        Convert message to normalized format.
        
        Use deterministic parsing (regex) as primary method.
        Return None if parsing fails - message will be marked with parse error.
        
        Args:
            message: Raw message text
            
        Returns:
            NormalizedSignal if parsing successful, None if parsing failed
        """
        pass
