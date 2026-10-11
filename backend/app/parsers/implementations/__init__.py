"""
Parser initialization and registration
"""

from app.parsers.registry import register_parser
from app.parsers.implementations.gold import GoldSignalParser


def init_parsers():
    """Initialize and register all available parsers"""
    
    register_parser("gold_signal_v1", GoldSignalParser())
    for name in ("gold_buy_limit_v1", "gold_scaling_sell_v1", "multi_entry_v1"):
        register_parser(name, GoldSignalParser(name))
