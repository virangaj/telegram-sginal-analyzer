"""
Example signal parsers - implement these to handle your specific message formats
"""

from app.parsers.base import SignalParser, NormalizedSignal
from typing import Optional
import re


class GoldBuyLimitParser(SignalParser):
    """
    Parses messages like:
    Buy limit GOLD
    Entry: 4288
    SL: 4273
    TP: 4335
    """
    
    def __init__(self):
        super().__init__("gold_buy_limit_v1")
    
    def can_parse(self, message: str) -> bool:
        """Check if message matches buy limit pattern"""
        return "buy limit" in message.lower() and "gold" in message.lower()
    
    async def parse(self, message: str) -> Optional[NormalizedSignal]:
        """Extract fields and create normalized signal"""
        try:
            # Extract numbers
            entry = self._extract_number(message, r"Entry:\s*([\d.]+)")
            sl = self._extract_number(message, r"SL:\s*([\d.]+)")
            tp = self._extract_number(message, r"TP:\s*([\d.]+)")
            
            if entry is None or sl is None or tp is None:
                return None
            
            return NormalizedSignal(
                symbol="XAUUSD",
                direction="BUY",
                order_type="LIMIT",
                entries=[entry],
                stop_loss=sl,
                take_profits=[tp],
                provider="telegram"
            )
        except Exception:
            return None
    
    @staticmethod
    def _extract_number(text: str, pattern: str) -> Optional[float]:
        """Extract a number from text using regex"""
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except (ValueError, IndexError):
                pass
        return None


class GoldScalingSellParser(SignalParser):
    """
    Parses messages like:
    GOLD SELL 4316.6
    MORE SELL 4326.6
    
    TP : 4301.6
    TP : 4286.6
    TP : 4266.6
    
    SL : 4330.6
    """
    
    def __init__(self):
        super().__init__("gold_scaling_sell_v1")
    
    def can_parse(self, message: str) -> bool:
        """Check if message matches scaling sell pattern"""
        return ("gold sell" in message.lower() or "more sell" in message.lower()) and "tp" in message.lower()
    
    async def parse(self, message: str) -> Optional[NormalizedSignal]:
        """Extract fields and create normalized signal"""
        try:
            # Extract entries (SELL prices)
            entries = self._extract_all_numbers(message, r"(?:GOLD\s+)?SELL\s+([\d.]+)")
            more_entries = self._extract_all_numbers(message, r"MORE\s+SELL\s+([\d.]+)")
            all_entries = entries + more_entries
            
            # Extract take profits
            take_profits = self._extract_all_numbers(message, r"TP\s*:\s*([\d.]+)")
            
            # Extract stop loss
            sl = self._extract_number(message, r"SL\s*:\s*([\d.]+)")
            
            if not all_entries or not take_profits or sl is None:
                return None
            
            return NormalizedSignal(
                symbol="XAUUSD",
                direction="SELL",
                order_type="MARKET",
                entries=all_entries,
                stop_loss=sl,
                take_profits=take_profits,
                provider="telegram",
                notes="Scaling sell setup"
            )
        except Exception:
            return None
    
    @staticmethod
    def _extract_number(text: str, pattern: str) -> Optional[float]:
        """Extract a single number from text using regex"""
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except (ValueError, IndexError):
                pass
        return None
    
    @staticmethod
    def _extract_all_numbers(text: str, pattern: str) -> list[float]:
        """Extract all numbers matching pattern"""
        matches = re.findall(pattern, text, re.IGNORECASE)
        numbers = []
        for match in matches:
            try:
                numbers.append(float(match))
            except ValueError:
                pass
        return numbers


class MultiEntryParser(SignalParser):
    """
    Parses messages with multiple entries and take profits:
    Entry: 4335
    SL: 4322
    TP: 4373
    
    Entry: 4350
    SL: 4322
    TP: 4373
    """
    
    def __init__(self):
        super().__init__("multi_entry_v1")
    
    def can_parse(self, message: str) -> bool:
        """Check if message has multiple entry/tp pairs"""
        return message.lower().count("entry:") >= 2
    
    async def parse(self, message: str) -> Optional[NormalizedSignal]:
        """Extract fields and create normalized signal"""
        try:
            # Extract all entries
            entries = self._extract_all_numbers(message, r"Entry:\s*([\d.]+)")
            
            # Extract all take profits
            take_profits = self._extract_all_numbers(message, r"TP:\s*([\d.]+)")
            
            # Extract single stop loss (usually same for all entries)
            sl = self._extract_number(message, r"SL:\s*([\d.]+)")
            
            if not entries or not take_profits or sl is None:
                return None
            
            return NormalizedSignal(
                symbol="XAUUSD",
                direction="BUY",  # Assume BUY - modify if needed
                order_type="LIMIT",
                entries=entries,
                stop_loss=sl,
                take_profits=take_profits,
                provider="telegram"
            )
        except Exception:
            return None
    
    @staticmethod
    def _extract_number(text: str, pattern: str) -> Optional[float]:
        """Extract a single number from text using regex"""
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except (ValueError, IndexError):
                pass
        return None
    
    @staticmethod
    def _extract_all_numbers(text: str, pattern: str) -> list[float]:
        """Extract all numbers matching pattern"""
        matches = re.findall(pattern, text, re.IGNORECASE)
        numbers = []
        for match in matches:
            try:
                numbers.append(float(match))
            except ValueError:
                pass
        return numbers
