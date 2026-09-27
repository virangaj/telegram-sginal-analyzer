"""
Abstract base class for market data providers
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class OHLC(BaseModel):
    """OHLC (candlestick) data"""
    
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class Tick:
    """Single price tick"""
    symbol: str
    price: float
    timestamp: datetime
    bid: Optional[float] = None
    ask: Optional[float] = None
    volume: Optional[float] = None


class MarketDataProvider(ABC):
    """
    Abstract base class for market data providers.
    
    Implementations provide access to live and historical price data.
    Supports multiple symbols and timeframes.
    
    Design: All methods are async for integration with async signal processing.
    """
    
    def __init__(self, name: str):
        """
        Initialize the market data provider.
        
        Args:
            name: Unique name for this provider
        """
        self.name = name
    
    @abstractmethod
    async def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Get the latest price for a symbol.
        
        Args:
            symbol: Trading symbol (e.g., "XAUUSD", "EURUSD")
            
        Returns:
            Latest price or None if unavailable
        """
        pass
    
    async def get_bid_ask(self, symbol: str) -> Optional[tuple[float, float]]:
        """
        Get the current bid/ask prices for a symbol.
        
        Default implementation returns (current_price, current_price).
        Override for precise bid/ask data.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Tuple of (bid, ask) or None if unavailable
        """
        price = await self.get_current_price(symbol)
        if price:
            return (price, price)
        return None
    
    async def get_ticks(
        self,
        symbol: str,
        limit: int = 100
    ) -> List[Tick]:
        """
        Get recent price ticks for a symbol.
        
        Args:
            symbol: Trading symbol
            limit: Maximum number of ticks to return
            
        Returns:
            List of Tick objects, most recent first
        """
        # Default: return empty list. Override for tick data.
        return []
    
    @abstractmethod
    async def get_ohlc(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 100
    ) -> list[OHLC]:
        """
        Get OHLC data for a symbol.
        
        Args:
            symbol: Trading symbol (e.g., "XAUUSD")
            timeframe: Timeframe (e.g., "1H", "4H", "15M")
            limit: Number of candles to return
            
        Returns:
            List of OHLC candles
        """
        pass
    
    async def is_market_open(self, symbol: str) -> bool:
        """
        Check if market is open for a symbol.
        
        Default implementation assumes market is always open.
        Override for markets with specific trading hours.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            True if market is open, False otherwise
        """
        return True
    
    async def supports_symbol(self, symbol: str) -> bool:
        """
        Check if this provider supports a symbol.
        
        Default implementation returns True.
        Override to implement symbol validation.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            True if symbol is supported, False otherwise
        """
        return True
