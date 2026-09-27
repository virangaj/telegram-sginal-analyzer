"""
Parser initialization and registration
"""

from app.parsers.registry import register_parser
from app.parsers.implementations.examples import (
    GoldBuyLimitParser,
    GoldScalingSellParser,
    MultiEntryParser
)


def init_parsers():
    """Initialize and register all available parsers"""
    
    # Register example parsers
    register_parser("gold_buy_limit_v1", GoldBuyLimitParser())
    register_parser("gold_scaling_sell_v1", GoldScalingSellParser())
    register_parser("multi_entry_v1", MultiEntryParser())
    
    # Add more parsers here as needed
