---
name: liquidity-smc
description: 'Use when implementing Smart Money Concepts (SMC) and liquidity algorithms: equal highs/lows (EQH/EQL), buy-side/sell-side liquidity pools, liquidity sweeps, Order Blocks, Fair Value Gaps (FVG), Inverse FVGs, Breaker Blocks, and Premium/Discount zones.'
---

# Liquidity & Smart Money Concepts (SMC) Quantitative Engine

## Activation and Scope
Use this skill when developing or auditing algorithmic liquidity detection in `backend/app/analysis/` (supporting [backend/app/analysis/regime.py](backend/app/analysis/regime.py) and [backend/app/trade/entry_engine.py](backend/app/trade/entry_engine.py)). This engine formalizes structural liquidity, price imbalances, and supply/demand zones into rigorous, deterministic data models.

*Architectural Boundary & Epistemic Guardrail*: SMC terminology frequently employs anthropomorphic narratives ("market makers hunting stops", "institutional footprints"). In this quantitative system, all SMC concepts are treated strictly as **observable price-action heuristics and geometric imbalance structures**. Inferred institutional intent must never be asserted as factual truth.

---

## Pure Mathematical Formulations & Zone Mechanics

### 1. Equal Highs (EQH) and Equal Lows (EQL)
Resting stop orders cluster above repetitive swing peaks and below troughs.
- Given two confirmed swing points $S_1, S_2$ with prices $P_1, P_2$ separated by at least $K_{min}$ bars and at most $K_{max}$ bars:
  $$|P_1 - P_2| \le \delta, \quad \text{where } \delta = \alpha \times \text{ATR}_{14}$$
  Default: $\alpha = 0.05$ (5% of 14-period ATR), $K_{min}=3, K_{max}=100$.
- **Pool Classification**:
  - Two or more swings meeting tolerance form an **Equal Extrema Cluster**.
  - Clustered highs $\rightarrow$ **Buy-Side Liquidity (BSL) Pool**.
  - Clustered lows $\rightarrow$ **Sell-Side Liquidity (SSL) Pool**.

### 2. Liquidity Sweeps & Failed Breakouts
A sweep occurs when price penetrates a resting liquidity level but fails to establish acceptance beyond it.

```
Bearish Liquidity Sweep (BSL Swept):
              [Wick High > Pool Level]
                    /\
                   /  \  <-- Candle closes BACK BELOW Pool Level
      ------------/----\------------------- BSL Pool Level
                 /      \
            [Open]      [Close]
```

- **Bullish Sweep Event** (Sell-Side Sweep):
  $$\text{Low}[i] < \text{SSL\_Level} \quad \text{and} \quad \text{Close}[i] > \text{SSL\_Level}$$
- **Bearish Sweep Event** (Buy-Side Sweep):
  $$\text{High}[i] > \text{BSL\_Level} \quad \text{and} \quad \text{Close}[i] < \text{BSL\_Level}$$
- **Confirmation Timing**: A sweep is valid **only on the close** of bar $i$. Intrabar penetrations that have not closed are unverified candidates.

### 3. Fair Value Gaps (FVG) - 3-Candle Imbalance
A Fair Value Gap represents an inefficiency where price moved violently in one direction, leaving an unauctioned price void between candle 1 and candle 3 of a 3-candle triad $(C_{i-2}, C_{i-1}, C_i)$.

```
Bullish FVG:
Candle i-2: High = H_{i-2}  ---+
                                |  <-- Imbalance Void: [H_{i-2}, L_i]
Candle i-1: Large Bullish Body  |      Consequent Encroachment (CE) = Midpoint
                                |
Candle i:   Low = L_i       ---+   (Condition: L_i > H_{i-2})
```

- **Bullish FVG Condition**:
  $$\text{Low}[i] > \text{High}[i-2]$$
  $$\text{Top} = \text{Low}[i], \quad \text{Bottom} = \text{High}[i-2], \quad \text{CE (Midpoint)} = \frac{\text{Top} + \text{Bottom}}{2}$$
- **Bearish FVG Condition**:
  $$\text{High}[i] < \text{Low}[i-2]$$
  $$\text{Top} = \text{Low}[i-2], \quad \text{Bottom} = \text{High}[i], \quad \text{CE (Midpoint)} = \frac{\text{Top} + \text{Bottom}}{2}$$
- **Minimum Significance Filter**:
  $$\text{Gap Size} = |\text{Top} - \text{Bottom}| \ge \beta \times \text{ATR}_{14} \quad (\text{default } \beta = 0.25)$$
- **FVG Lifecycle States**:
  1. `ACTIVE`: Created, price has not entered $[\text{Bottom}, \text{Top}]$.
  2. `PARTIALLY_MITIGATED`: Price has retraced into the gap but not crossed CE or the opposite boundary.
  3. `FULLY_MITIGATED`: Price touched or crossed the opposite boundary.
  4. `INVALIDATED`: Candle body closes completely through the opposite boundary.

### 4. Inverse FVG (IFVG) & Breaker Blocks
- **Inverse FVG (IFVG)**:
  When a previously valid Bullish FVG suffers an invalidating body close below its bottom, it flips polarity. It is cataloged as a Bearish Resistance IFVG, expecting downward rejection upon retest from below.
- **Order Block (OB)**:
  - *Bullish Order Block*: The lowest down-close (bearish) candle immediately preceding a displacement leg that created a confirmed Bullish BOS or Bullish FVG.
  - *Bearish Order Block*: The highest up-close (bullish) candle immediately preceding a displacement leg that created a confirmed Bearish BOS or Bearish FVG.
  - *Mitigation*: A retest of the OB zone $[OB_{low}, OB_{high}]$. An invalidation occurs when candle body closes beyond $OB_{low}$ (for bullish) or $OB_{high}$ (for bearish).
- **Breaker Block**:
  An Order Block that originally took liquidity (formed a swing high/low that swept a prior level) and was subsequently broken through with displacement. Once broken, the zone flips polarity.

### 5. Premium, Discount, and Equilibrium Zones
Calculated dynamically over the active trading range defined by the most recent confirmed HTF swing low ($S_{low}$) and swing high ($S_{high}$):
- **Equilibrium (EQ)**:
  $$\text{EQ} = \frac{S_{high} + S_{low}}{2}$$
- **Discount Zone**: $[S_{low}, \text{EQ})$ — Statistically favorable for long entries.
- **Premium Zone**: $(\text{EQ}, S_{high}]$ — Statistically favorable for short entries.
- **Optimal Trade Entry (OTE)**: Configurable Fibonacci retracement window:
  $$\text{OTE Bullish Range} = [S_{high} - 0.79 \cdot (S_{high} - S_{low}), \, S_{high} - 0.618 \cdot (S_{high} - S_{low})]$$

---

## Data Schemas & Contracts

```python
from datetime import datetime
from decimal import Decimal
from typing import List, Literal, Optional
from pydantic import BaseModel, Field

ZoneStatus = Literal["ACTIVE", "PARTIALLY_MITIGATED", "FULLY_MITIGATED", "INVALIDATED"]
ZoneType = Literal["FVG_BULLISH", "FVG_BEARISH", "IFVG", "ORDER_BLOCK", "BREAKER", "BSL_POOL", "SSL_POOL"]

class PriceZone(BaseModel):
    id: str
    symbol: str
    timeframe: str
    zone_type: ZoneType
    top: Decimal
    bottom: Decimal
    midpoint: Decimal
    created_at: datetime
    created_bar_index: int
    status: ZoneStatus = "ACTIVE"
    mitigated_at: Optional[datetime] = None
    invalidation_level: Decimal
    touch_count: int = 0
    source_event_ids: List[str] = Field(default_factory=list)

class LiquiditySweepEvent(BaseModel):
    id: str
    symbol: str
    timeframe: str
    pool_id: str
    sweep_type: Literal["BUY_SIDE_SWEEP", "SELL_SIDE_SWEEP"]
    penetration_price: Decimal
    close_price: Decimal
    sweep_bar_index: int
    candle_close_at: datetime

class SMCAnalysisSnapshot(BaseModel):
    symbol: str
    timeframe: str
    as_of: datetime
    active_zones: List[PriceZone]
    recent_sweeps: List[LiquiditySweepEvent]
    premium_discount_status: Literal["PREMIUM", "DISCOUNT", "EQUILIBRIUM"]
    equilibrium_price: Decimal
```

---

## Zone Management & Deduplication Rules
1. **Overlap Consolidation**: When two active zones of the same type overlap by more than 50% of their vertical range ($IoU > 0.5$), merge them into a single consolidated zone or mark the older zone as absorbed to prevent duplicate signal triggers.
2. **Zone Aging / Pruning**: Zones that remain untouched for $> 300$ bars on the current timeframe are retired to `EXPIRED` status to limit memory footprint and avoid reacting to stale historical artifacts.

---

## Test Suite & Verification Requirements

### 1. Unit Tests
- **Bullish FVG Creation**: Bar 1 High = 100.0, Bar 2 High = 108.0 (Low = 100.5), Bar 3 Low = 102.0.
  - Verify FVG created with Bottom = 100.0, Top = 102.0, CE = 101.0.
- **FVG Mitigation Progression**:
  - Feed subsequent bar with Low = 101.5: Verify status changes to `PARTIALLY_MITIGATED`.
  - Feed subsequent bar with Low = 99.8 and Close = 99.5: Verify status changes to `INVALIDATED`.
- **Liquidity Sweep vs. Breakout**:
  - Equal highs at 2000.0.
  - Test Bar A: High = 2002.5, Close = 1999.0 $\rightarrow$ Emits `LiquiditySweepEvent`.
  - Test Bar B: High = 2002.5, Close = 2001.5 $\rightarrow$ Emits `No Sweep` (candidate breakout).

### 2. Look-Ahead Bias Verification
Ensure zone mitigation lifecycle is evaluated strictly sequentially:
```python
def test_fvg_sequential_lifecycle():
    candles = load_test_candles()
    # Zone created at bar 50 cannot be marked mitigated at bar 45
    for i in range(1, len(candles)):
        snapshot = smc_engine.evaluate(candles[:i], as_of=candles[i-1].close_time)
        for zone in snapshot.active_zones:
            assert zone.created_bar_index < i
            if zone.mitigated_at:
                assert zone.mitigated_at <= candles[i-1].close_time
```
