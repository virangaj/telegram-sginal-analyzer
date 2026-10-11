import asyncio

import pytest

from app.parsers.implementations.gold import GoldSignalParser
from app.parsers.implementations import init_parsers
from app.parsers.registry import get_registry


@pytest.mark.parametrize("direction,stop,targets", [("BUY", 1990, [2020, 2030]), ("SELL", 2030, [1990, 1980])])
def test_scaling_gold_messages_extract_each_entry_once(direction, stop, targets):
    text = f"GOLD {direction} 2000\nMORE {direction} 2010\nTP : {targets[0]}\nTP : {targets[1]}\nSL : {stop}"
    parsed = asyncio.run(GoldSignalParser().parse(text))
    assert parsed.direction == direction
    assert parsed.entries == [2000, 2010]
    assert parsed.take_profits == targets
    assert parsed.stop_loss == stop


@pytest.mark.parametrize("direction", ["BUY", "SELL"])
@pytest.mark.parametrize("order", ["MARKET", "LIMIT", "STOP"])
def test_labeled_prices_and_numbered_targets(direction, order):
    stop, target = (1990, 2020) if direction == "BUY" else (2010, 1980)
    text = f"XAU/USD\n{direction} {order}\nEntry: 2000\nTP1: {target}\nSL: {stop}"
    parsed = asyncio.run(GoldSignalParser().parse(text))
    assert parsed.order_type == order
    assert parsed.entries == [2000]
    assert parsed.take_profits == [target]


@pytest.mark.parametrize("text", [
    "GOLD\nBUY\nEntry: 2000\nTP1: 2020",
    "GOLD\nBUY\nEntry: 2000-2010\nTP1: 2020\nSL: 1990",
    "GOLD\nBUY\nEntry: 2000\nTP1: 1980\nSL: 1990",
    "GOLD\nBUY or SELL\nEntry: 2000\nTP1: 2020\nSL: 1990",
    "Entry: 2000\nEntry: 2010\nTP: 2020\nSL: 1990",
    "GOLD BUY 2000\nTP1 HIT: 2020\nSL: 1990",
    "GOLD BUY\nEntry: 0\nTP: 2020\nSL: 1990",
])
def test_invalid_incomplete_followup_and_range_messages_remain_unparsed(text):
    init_parsers()
    assert asyncio.run(get_registry().parse_message(text)) is None


def test_existing_configured_parser_names_keep_safe_behavior():
    init_parsers()
    text = "Buy limit GOLD\nEntry: 2000\nSL: 1990\nTP: 2020"
    parsed = asyncio.run(get_registry().get("gold_buy_limit_v1").parse(text))
    assert parsed.order_type == "LIMIT"
    assert parsed.direction == "BUY"