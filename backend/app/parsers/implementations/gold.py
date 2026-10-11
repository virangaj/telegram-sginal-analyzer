import math
import re
from typing import Optional

from app.parsers.base import NormalizedSignal, SignalParser


class GoldSignalParser(SignalParser):
    def __init__(self, name="gold_signal_v1"):
        super().__init__(name)

    def can_parse(self, message: str) -> bool:
        return bool(re.search(r"\b(?:GOLD|XAU\s*/?\s*USD)\b", message, re.IGNORECASE) and re.search(r"\b(?:BUY|SELL)\b", message, re.IGNORECASE))

    async def parse(self, message: str) -> Optional[NormalizedSignal]:
        text = message.upper()
        if not self.can_parse(text) or re.search(r"\b(?:CANCEL(?:LED)?|CLOSED|HIT|RESULTS?|UPDATE|BREAKEVEN)\b", text):
            return None
        directions = set(re.findall(r"\b(BUY|SELL)\b", text))
        if len(directions) != 1:
            return None
        direction = directions.pop()
        orders = set(re.findall(r"\b(?:BUY|SELL)\s+(LIMIT|STOP|MARKET)\b", text))
        if len(orders) > 1:
            return None
        order_type = next(iter(orders), "MARKET")
        entries, targets, stops = [], [], []
        number = r"\d+(?:\.\d+)?"
        for raw_line in text.splitlines():
            line = re.sub(r"^[^A-Z0-9]+", "", raw_line.strip())
            field = re.match(r"^(ENTRY|ENTRIES|SL|STOP\s*LOSS|TP\s*\d*|TPS|TAKE\s*PROFIT\s*\d*)\s*[:=@-]?\s*(.*)$", line)
            inline = re.match(rf"^(?:(?:GOLD|XAU\s*/?\s*USD|MORE)\s+)?{direction}\s+(?:(?:LIMIT|STOP|MARKET|NOW)\s+)?[:=@]?\s*({number})\s*$", line)
            if inline:
                entries.append(float(inline.group(1)))
            elif field:
                label, values = field.groups()
                if not re.fullmatch(rf"{number}(?:\s*,\s*{number})*\s*", values):
                    return None
                prices = [float(value.strip()) for value in values.split(",")]
                if label in ("ENTRY", "ENTRIES"):
                    entries.extend(prices)
                elif label == "SL" or label.startswith("STOP"):
                    stops.extend(prices)
                else:
                    targets.extend(prices)
        if not entries or not targets or len(set(stops)) != 1:
            return None
        stop = stops[0]
        if any(not math.isfinite(price) or price <= 0 for price in entries + targets + [stop]):
            return None
        valid = stop < min(entries) and all(target > max(entries) for target in targets) if direction == "BUY" else stop > max(entries) and all(target < min(entries) for target in targets)
        if not valid:
            return None
        return NormalizedSignal(symbol="XAUUSD", direction=direction, order_type=order_type,
                                entries=entries, stop_loss=stop, take_profits=targets, provider="telegram")