import math
import re
import unicodedata
from typing import Optional

from app.parsers.base import NormalizedSignal, SignalParser


class GoldSignalParser(SignalParser):
    category = "cfds"

    def __init__(self, name="gold_signal_v1"):
        super().__init__(name)

    def can_parse(self, message: str) -> bool:
        text = normalize_gold_text(message)
        return bool(re.search(r"\b(?:GOLD|XAU\s*/?\s*USD)\b", text) and re.search(r"\b(?:BUY|SELL)\b", text))

    def review_reason(self, message: str) -> Optional[str]:
        text = normalize_gold_text(message)
        if re.search(r"\b(?:CANCEL(?:LED)?|CLOSED|HIT|RESULTS?|UPDATE|BREAKEVEN)\b", text):
            return None
        if re.search(r"\bRANGE\s*:", text) or re.search(
            r"\bENTRY(?:\s+(?:POINT|PRICE))?\s*[:=@-]?\s*\d+(?:\.\d+)?\s*[-–]\s*\d", text
        ):
            return "Entry range requires range-aware storage; endpoints are not scaling fills"
        return "CFD signal is incomplete, ambiguous, or has invalid entry/SL/TP levels"

    async def parse(self, message: str) -> Optional[NormalizedSignal]:
        text = normalize_gold_text(message)
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
            field = re.match(
                r"^(ENTRY(?:\s+(?:POINT|PRICE))?|ENTRIES|SL|STOP\s*LOSS|TP\s*\d*|TPS|TARGET\s*\d*|TAKE\s*PROFIT\s*\d*)\s*[:=@-]?\s*(.*)$",
                line,
            )
            inline = re.match(rf"^(?:(?:GOLD|XAU\s*/?\s*USD|MORE)\s+)?{direction}\s+(?:(?:LIMIT|STOP|MARKET|NOW)\s+)?[:=@]?\s*({number})\s*$", line)
            if inline:
                entries.append(float(inline.group(1)))
            elif field:
                label, values = field.groups()
                values = re.sub(r"\s*\([^)]*\)\s*$", "", values).strip()
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


def normalize_gold_text(message: str) -> str:
    text = unicodedata.normalize("NFKC", message).upper().replace("*", "").replace("_", " ").replace("–", "-")
    lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        line = re.sub(r"^[^A-Z0-9]+", "", line)
        line = re.sub(r"[^A-Z0-9)]+$", "", line)
        lines.append(line)
    return "\n".join(lines)


def normalize_crypto_text(message: str) -> str:
    text = unicodedata.normalize("NFKC", message).upper().replace("*", "").replace("_", " ")
    return "\n".join(re.sub(r"^[^A-Z0-9]+", "", line.strip()) for line in text.splitlines())


class CryptoSignalParser(GoldSignalParser):
    category = "crypto"

    BASES = (
        "BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "DOGE", "AVAX", "DOT", "LINK",
        "LTC", "BCH", "TON", "TRX", "SHIB", "PEPE", "SUI", "NEAR", "APT", "UNI", "PNUT", "BTW", "CHIP",
    )
    PAIRS = re.compile(r"\b(" + "|".join(BASES) + r")\s*[/_-]?\s*(USDT|USDC|USD)\b", re.IGNORECASE)

    def __init__(self, name="crypto_signal_v1"):
        super().__init__(name)

    def can_parse(self, message: str) -> bool:
        text = normalize_crypto_text(message)
        instrument = self.PAIRS.search(text) or re.search(r"\b(?:" + "|".join(self.BASES) + r")\b", text)
        return bool(instrument and re.search(r"\b(?:BUY|SELL|LONG|SHORT)\b", text))

    def review_reason(self, message: str) -> str:
        text = normalize_crypto_text(message)
        if re.search(r"\b(?:CANCEL(?:LED)?|CLOSED|HIT|RESULTS?|UPDATE|BREAKEVEN)\b", text):
            return ""
        if re.search(r"\bRANGE\s*:", text):
            return "Entry range requires range-aware storage; endpoints are not scaling fills"
        if re.search(r"(?:TP\s*\d*|TARGETS?|TAKE\s*PROFIT)[\s\S]*?\d\s*%", text):
            return "Percentage targets require an explicit price/leveraged-return convention; absolute targets were not supplied"
        if not self.PAIRS.search(text):
            return "Crypto quote currency is missing or unsupported; no USD/USDT/USDC pair was inferred"
        return "Crypto signal is incomplete, ambiguous, or has invalid entry/SL/TP levels"

    async def parse(self, message: str) -> Optional[NormalizedSignal]:
        text = normalize_crypto_text(message)
        matches = list(self.PAIRS.finditer(text))
        symbols = {f"{match.group(1)}{match.group(2)}" for match in matches}
        if len(symbols) != 1 or not self.can_parse(text):
            return None
        if re.search(r"\b(?:CANCEL(?:LED)?|CLOSED|HIT|RESULTS?|UPDATE|BREAKEVEN)\b", text):
            return None
        directions = {"BUY" if value in ("BUY", "LONG") else "SELL" for value in re.findall(r"\b(BUY|SELL|LONG|SHORT)\b", text)}
        if len(directions) != 1:
            return None
        direction = directions.pop()
        orders = set(re.findall(r"\b(LIMIT|MARKET)\b", text))
        if re.search(r"\b(?:BUY|SELL|LONG|SHORT)\s+STOP\b", text):
            orders.add("STOP")
        if len(orders) > 1 or re.search(r"\bRANGE\s*:", text):
            return None
        number = r"\d+(?:\.\d+)?"
        values = {"entry": [], "target": [], "stop": []}
        pending = None
        for line in text.splitlines():
            if not line:
                continue
            field = re.match(r"^(?:ENTRY\s*PRICE|ENTER\s*PRICE|ENTRY|ENTRIES|TAKE[ -]?PROFIT\s*TARGETS?|TAKE\s*PROFIT|TARGETS?|TP\s*\d*|STOP\s*LOSS|SL)\s*[:=\-]?\s*(.*)$", line)
            if field:
                label = line[:field.start(1)]
                pending = "stop" if label.startswith(("SL", "STOP")) else "entry" if label.startswith(("ENTRY", "ENTER", "ENTRIES")) else "target"
                remainder = field.group(1)
                if not remainder:
                    continue
            elif pending and re.match(r"^\d", line):
                remainder = line
            else:
                pending = None
                inline = re.match(r"^(?:" + "|".join(self.BASES) + r")\s+(?:LONG|SHORT|BUY|SELL)\s+AT\s+(" + number + r")\s*$", line)
                if inline:
                    values["entry"].append(float(inline.group(1)))
                pair = self.PAIRS.match(line)
                pair_entry = re.fullmatch(r"\s+(?:BUY|SELL|LONG|SHORT)\s+(?:(?:MARKET|LIMIT|STOP|NOW)\s+)?(" + number + r")", line[pair.end():]) if pair else None
                if pair_entry:
                    values["entry"].append(float(pair_entry.group(1)))
                continue
            remainder = re.sub(r"^[^A-Z0-9+-]+", "", remainder.strip())
            remainder = re.sub(r"^\d+[.)]\s+", "", remainder)
            remainder = re.sub(r"\s*\([^)]*\)\s*$", "", remainder).strip()
            if not re.fullmatch(number + r"(?:\s*,\s*" + number + r")*", remainder):
                return None
            values[pending].extend(float(value.strip()) for value in remainder.split(","))
        entries, targets, stops = values["entry"], values["target"], values["stop"]
        if not entries or not targets or len(set(stops)) != 1:
            return None
        stop = stops[0]
        if any(not math.isfinite(price) or price <= 0 for price in entries + targets + [stop]):
            return None
        valid = stop < min(entries) and all(target > max(entries) for target in targets) if direction == "BUY" else stop > max(entries) and all(target < min(entries) for target in targets)
        if not valid:
            return None
        return NormalizedSignal(symbol=symbols.pop(), direction=direction, order_type=next(iter(orders), "MARKET"), entries=entries, stop_loss=stop, take_profits=targets, provider="telegram")