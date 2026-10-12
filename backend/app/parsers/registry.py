"""
Parser registry for managing available signal parsers
"""

from typing import Dict, Optional
from app.parsers.base import SignalParser, NormalizedSignal
from app.database.models import SignalMessageType


class ParserRegistry:
    """Central registry of all available signal parsers"""
    
    def __init__(self):
        self._parsers: Dict[str, SignalParser] = {}
    
    def register(self, name: str, parser: SignalParser) -> None:
        """
        Register a new parser.
        
        Args:
            name: Unique name for the parser
            parser: SignalParser instance
        """
        self._parsers[name] = parser
    
    def unregister(self, name: str) -> None:
        """Unregister a parser."""
        self._parsers.pop(name, None)
    
    def get(self, name: str) -> Optional[SignalParser]:
        """
        Get a parser by name.
        
        Args:
            name: Parser name
            
        Returns:
            SignalParser instance or None if not found
        """
        return self._parsers.get(name)
    
    def list_parsers(self) -> list[str]:
        """Get list of registered parser names"""
        return list(self._parsers.keys())
    
    async def parse_message(
        self,
        message: str,
        message_type: Optional[SignalMessageType] = None,
        category: Optional[str] = None,
    ) -> Optional[NormalizedSignal]:
        """
        Parse a message.
        
        If message_type is provided, use its specified parser.
        Otherwise, auto-detect by trying all parsers.
        
        Args:
            message: Raw message text
            message_type: Optional SignalMessageType from database
            category: Restrict parsing to this channel category when supplied
            
        Returns:
            NormalizedSignal if successful, None if parsing failed
        """
        if message_type:
            # Use specific parser from message_type
            parser = self.get(message_type.parser_name)
            if not parser or (category is not None and parser.category != category):
                return None
            result = await parser.parse(message)
            if result:
                result.raw_signal_type = parser.name
            return result
        else:
            # Auto-detect parser
            return await self.parse_message_auto(message, category=category)
    
    async def parse_message_auto(self, message: str, category: Optional[str] = None) -> Optional[NormalizedSignal]:
        """
        Attempt to parse a message with parsers matching the supplied category.
        Useful for auto-detection of signal format.
        
        Args:
            message: Raw message text
            
        Returns:
            NormalizedSignal if any parser succeeds, None if all fail
        """
        for parser in self._parsers.values():
            if category is not None and parser.category != category:
                continue
            if parser.can_parse(message):
                result = await parser.parse(message)
                if result:
                    result.raw_signal_type = parser.name
                    return result
        return None


# Global registry instance
_registry = ParserRegistry()


def get_registry() -> ParserRegistry:
    """Get the global parser registry"""
    return _registry


def register_parser(name: str, parser: SignalParser) -> None:
    """Register a parser in the global registry"""
    _registry.register(name, parser)
