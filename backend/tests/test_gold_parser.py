import asyncio
from types import SimpleNamespace

import pytest

from app.parsers.implementations.gold import CryptoSignalParser, GoldSignalParser
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


@pytest.mark.parametrize("parser_name,category,text", [
    ("gold_signal_v1", "crypto", "GOLD BUY 2000\nTP: 2020\nSL: 1990"),
    ("gold_buy_limit_v1", "crypto", "GOLD BUY 2000\nTP: 2020\nSL: 1990"),
    ("crypto_signal_v1", "cfds", "BTCUSDT BUY 100\nTP: 120\nSL: 90"),
])
def test_explicit_parser_cannot_bypass_channel_category(parser_name, category, text):
    init_parsers()
    message_type = SimpleNamespace(parser_name=parser_name)
    assert asyncio.run(get_registry().parse_message(text, message_type, category=category)) is None


@pytest.mark.parametrize("symbol", ["BTCUSDT", "ETH/USD", "SOLUSDC"])
@pytest.mark.parametrize("direction", ["BUY", "SELL"])
def test_crypto_parser_keeps_explicit_pair_and_levels(symbol, direction):
    stop, target = (90, 120) if direction == "BUY" else (110, 80)
    text = f"{symbol} {direction} MARKET 100\nTP1: {target}\nSL: {stop}"
    parsed = asyncio.run(CryptoSignalParser().parse(text))
    expected_symbol = symbol.upper().replace("/", "")
    assert parsed.symbol == expected_symbol
    assert parsed.direction == direction
    assert parsed.entries == [100]


def test_crypto_parser_rejects_unknown_or_ambiguous_symbols():
    parser = CryptoSignalParser()
    for text in ("UNKNOWNCOINUSD BUY 100\nTP: 120\nSL: 90", "BTCUSDT BUY or SELL 100\nTP: 120\nSL: 90"):
        assert asyncio.run(parser.parse(text)) is None


@pytest.mark.parametrize("marker", ["{index}) ", "{index}. ", ""])
@pytest.mark.parametrize("direction,targets,stop", [
    ("LONG", [1.5, 1.6], 1.1),
    ("SHORT", [1.0, 0.9], 1.5),
])
def test_crypto_price_lists_preserve_all_levels(marker, direction, targets, stop):
    def price_lines(prices):
        return "\n".join(marker.format(index=index) + str(price) for index, price in enumerate(prices, 1))

    text = (
        f"BTW/USDT {direction} LIMIT\nEntry Price:\n{price_lines([1.3, 1.2])}"
        f"\nTake-Profit Targets:\n{price_lines(targets)}\nStop Loss:\n{price_lines([stop])}"
    )
    init_parsers()
    parsed = asyncio.run(get_registry().parse_message(text))
    assert parsed is not None
    assert parsed.symbol == "BTWUSDT"
    assert parsed.direction == ("BUY" if direction == "LONG" else "SELL")
    assert parsed.order_type == "LIMIT"
    assert parsed.entries == [1.3, 1.2]
    assert parsed.take_profits == targets
    assert parsed.stop_loss == stop


@pytest.mark.parametrize("text,symbol,entry,target,stop", [
    ("**FUTURE (SHORT)**\n**BTC/USDT**\n**Enter Price : 85500**\nLeverage 10x\n**Target - 77000 (+100%)**\n**SL - 94000 (-100%)**\nUse only 1% From your Futures Balance", "BTCUSDT", 85500, 77000, 94000),
    ("BTW /USDT\nSignal Type: Regular (Short)\nLeverage: Cross 10x or 20x\nEntry Price\n1.3377\nTake-Profit Targets:\nTP 1 : 0.9426\nStop Loss\n1.5603", "BTWUSDT", 1.3377, 0.9426, 1.5603),
    ("Coin: SOL/USDT\nDirection: LONG\nEntry Price: 100\nTP1: 120\nStop Loss: 90", "SOLUSDT", 100, 120, 90),
])
def test_decorated_crypto_formats(text, symbol, entry, target, stop):
    parsed = asyncio.run(CryptoSignalParser().parse(text))
    assert parsed is not None
    assert parsed.symbol == symbol
    assert parsed.entries == [entry]
    assert parsed.take_profits == [target]
    assert parsed.stop_loss == stop


@pytest.mark.parametrize("text,reason", [
    ("Coin: PNUT /USDT\nDirection: LONG\nEntry: Limit Order\nRange: 0.04797 - 0.03892\nTargets:\nTP1: 15%\nStop Loss: 0.03723", "Entry range"),
    ("Trade entry alert\nXRP long at 1.494\n1% capital\n2X leverage", "quote currency"),
    ("Coin Pair: CHIP\nSignal Type: sell / Short\nEntry: current market\nTake Profit\n15%\n30%\nLadder: 0.07150\nStop Loss: 0.07340", "Percentage targets"),
    ("BTCUSDT SHORT\nEntry: 100\nTP1: 15%\nSL: 110", "Percentage targets"),
    ("BTCUSDT LONG\nEntry: 100\nSL: 90", "incomplete"),
])
def test_partial_crypto_signals_have_explicit_review_reasons(text, reason):
    parser = CryptoSignalParser()
    assert parser.can_parse(text)
    assert asyncio.run(parser.parse(text)) is None
    assert reason in parser.review_reason(text)


def test_unicode_bold_and_emoji_labels_are_normalized():
    text = "𝗖𝗼𝗶𝗻 𝗣𝗮𝗶𝗿: BTW/USDT\n𝗦𝗶𝗴𝗻𝗮𝗹 𝗧𝘆𝗽𝗲: Short\n💵𝗘𝗻𝘁𝗿𝘆: 1.3377\n🎯TP1: 0.9426\n🟥𝗦𝘁𝗼𝗽 𝗟𝗼𝘀𝘀: 1.5603"
    parsed = asyncio.run(CryptoSignalParser().parse(text))
    assert parsed is not None
    assert parsed.direction == "SELL"
    assert parsed.symbol == "BTWUSDT"


@pytest.mark.parametrize("text", [
    "BTCUSDT LONG\nEntry: 100\nTP: 120\nSL: -90",
    "BTCUSDT LONG\nEntry: 100\nTP: 15%\nSL: 90",
    "BTCUSDT LONG\nETHUSDT\nEntry: 100\nTP: 120\nSL: 90",
    "BTCUSDT LONG\nEntry: 100\nTarget: 120-130\nSL: 90",
    "BTCUSDT LONG\nEntry: 100\nTP1 HIT: 120\nSL: 90",
    "BTCUSDT LONG\nEntry:\n1) 100-110\nTargets:\n1) 120\nSL: 90",
    "BTCUSDT LONG\nEntry: 100\nTargets:\n1) 15%\nSL: 90",
    "BTCUSDT LONG\nEntry: 100\nTargets:\n1) 120\n2) 80\nSL: 90",
    "BTCUSDT LONG\nEntry: 100\nTargets:\n1) 120\nStop Loss:\n1) 90\n2) 95",
])
def test_crypto_prices_and_source_are_not_silently_corrected(text):
    assert asyncio.run(CryptoSignalParser().parse(text)) is None