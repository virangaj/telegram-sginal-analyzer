---
name: market-structure
description: 'Use when implementing swing detection, swing classification (HH, HL, LH, LL), trend determination, Break of Structure (BOS), Market Structure Shift (MSS), Change of Character (CHoCH), consolidation ranges, and multi-timeframe structure alignment.'
---

# Market Structure Quantitative Engine

## Activation and Scope
Use this skill when designing or implementing market structure algorithms in `backend/app/analysis/` (specifically expanding [backend/app/analysis/regime.py](backend/app/analysis/regime.py)). Market structure provides the fundamental topological framework for price action across Forex and Crypto, identifying turning points, directional bias, and structural breaks.

Downstream consumers: [backend/app/analysis/regime.py](backend/app/analysis/regime.py), [.github/skills/liquidity-smc/SKILL.md](.github/skills/liquidity-smc/SKILL.md), and [.github/skills/confluence-signals/SKILL.md](.github/skills/confluence-signals/SKILL.md).

---

## Pure Mathematical Algorithms & Definitions

### 1. Swing Point Detection (Fractal Extrema)
A swing point is a local extremum defined over a symmetrical or asymmetrical window of closed candles: $L$ left bars and $R$ right bars ($L, R \ge 2$, standard default $L=2, R=2$ for 5-bar fractals; $L=5, R=5$ for major swings).

```
          [High i]  <-- Swing High candidate at index i
         /        \
        /          \
   [i-2] [i-1]    [i+1] [i+2]
   <--- L --->    <--- R --->
```

- **Swing High at index $i$**:
  $$\text{High}[i] > \max_{k \in [1, L]} \text{High}[i-k] \quad \text{and} \quad \text{High}[i] \ge \max_{m \in [1, R]} \text{High}[i+m]$$
- **Swing Low at index $i$**:
  $$\text{Low}[i] < \min_{k \in [1, L]} \text{Low}[i-k] \quad \text{and} \quad \text{Low}[i] \le \min_{m \in [1, R]} \text{Low}[i+m]$$
- **Tie-Breaking Convention**: If two identical extrema occur within the window, the first chronologically is designated the candidate, or an explicit tie-breaking rule must be applied. Flat candle series must never generate multiple phantom swings.
- **Swing Confirmation Delay (Anti-Repainting Rule)**:
  A swing occurring at candle index $i$ with timestamp $T_i$ is **unconfirmed** until candle $i+R$ has completely closed at timestamp $T_{i+R}$.
  $$\text{confirmed\_at} = \text{candle\_close\_at}[i+R]$$
  No downstream analytical engine, strategy, or backtest may access or act upon swing $i$ at any evaluation time $T < T_{i+R}$.

### 2. Swing Classification & Progression
Maintain an ordered sequence of confirmed swing highs and lows:
- **Higher High (HH)**: Confirmed Swing High with price $> \text{previous confirmed Swing High}$.
- **Lower High (LH)**: Confirmed Swing High with price $< \text{previous confirmed Swing High}$.
- **Higher Low (HL)**: Confirmed Swing Low with price $> \text{previous confirmed Swing Low}$.
- **Lower Low (LL)**: Confirmed Swing Low with price $< \text{previous confirmed Swing Low}$.
- **Equal High (EQH) / Equal Low (EQL)**: Extrema within a configurable threshold $\epsilon$ (e.g., $|\Delta| \le 0.05 \times \text{ATR}_{14}$). (Delegated to liquidity analysis for pool mapping).

### 3. Structural Breaks: BOS, MSS, and CHoCH
Explicit distinctions between continuation and reversal breaks must be enforced:

```
Uptrend Continuation (BOS):
        (HH)
        /\          /\  <-- Break of Structure (BOS)
       /  \        /  \
      /    \  (HL)/    \
     /      \/
 (HL)

Uptrend Reversal (MSS / CHoCH):
        (HH)
        /\
       /  \
      /    \  (HL)
     /      \/   \
 (HL)             \    <-- Market Structure Shift (MSS) breaks lowest HL
                   \ /
                    V
```

- **Break of Structure (BOS)**: Continuation break in the direction of the prevailing trend.
  - *Bullish BOS*: Candle closes above the most recent confirmed HH while in an established uptrend.
  - *Bearish BOS*: Candle closes below the most recent confirmed LL while in an established downtrend.
- **Market Structure Shift (MSS)**: Reversal break signaling a potential change in macro trend.
  - *Bearish MSS*: While in an uptrend, price breaks below the specific key HL that directly preceded the highest HH.
  - *Bullish MSS*: While in a downtrend, price breaks above the specific key LH that directly preceded the lowest LL.
- **Change of Character (CHoCH)**:
  - Explicit definition: An early, aggressive structural break of minor/sub-structure (often on intermediate swings or prior counter-trend swing points) preceding full MSS.
  - Configuration parameter:
    ```python
    class StructureBreakConfig(BaseModel):
        confirmation_mode: Literal["BODY_CLOSE", "WICK_PENETRATION"] = "BODY_CLOSE"
        break_threshold_ticks: int = 1  # Minimum penetration beyond swing level
        choch_mode: Literal["SUB_STRUCTURE", "MAJOR_SWING"] = "SUB_STRUCTURE"
    ```
  - *Standard Institutional Rule*: By default, require `BODY_CLOSE` (`close > swing_high` for bullish; `close < swing_low` for bearish). A wick penetration without body close is classified as a *Sweep Candidate*, not a confirmed BOS/MSS.

### 4. Consolidation & Range Detection
Market regimes must be classified deterministically into `BULLISH`, `BEARISH`, `RANGE`, or `TRANSITION`:
- **Range Criteria**:
  - Failure to establish consecutive directional swings: A sequence exhibiting alternating HH followed by LH, or LL followed by HL without a decisive break.
  - *Range Bounds*: Upper boundary = highest confirmed Swing High in window; Lower boundary = lowest confirmed Swing Low in window.
  - *ATR Bandwidth / ADX Guard*: ADX(14) $< 20$ or Bollinger Band Width in the lowest 20th percentile of the trailing 100 bars.

---

## Data Contracts & Schemas

```python
from datetime import datetime
from decimal import Decimal
from typing import List, Literal, Optional
from pydantic import BaseModel, Field

SwingType = Literal["HIGH", "LOW"]
SwingLabel = Literal["HH", "LH", "HL", "LL", "UNCERTAIN"]
BreakType = Literal["BOS", "MSS", "CHOCH"]
Direction = Literal["BULLISH", "BEARISH"]

class ConfirmedSwing(BaseModel):
    id: str
    symbol: str
    timeframe: str
    swing_type: SwingType
    price: Decimal
    extremum_time: datetime = Field(..., description="Timestamp of the bar containing the swing")
    confirmed_at: datetime = Field(..., description="Timestamp of close of the R-th bar confirming the swing")
    label: SwingLabel
    bar_index: int
    confirmation_index: int

class StructureBreakEvent(BaseModel):
    break_type: BreakType
    direction: Direction
    broken_swing_id: str
    break_price: Decimal
    candle_close_at: datetime
    bar_index: int
    wick_only: bool = False

class MarketStructureSnapshot(BaseModel):
    symbol: str
    timeframe: str
    as_of: datetime
    regime: Literal["BULLISH", "BEARISH", "RANGE", "TRANSITION"]
    active_swings: List[ConfirmedSwing]
    latest_break: Optional[StructureBreakEvent]
    range_high: Optional[Decimal] = None
    range_low: Optional[Decimal] = None
```

---

## Multi-Timeframe Alignment Protocol
Multi-timeframe structure operates hierarchically:
1. **Primary Timeframe (4H or 1D)**: Determines Macro Trend (`BULLISH` / `BEARISH` / `RANGE`) and major swing boundaries.
2. **Intermediate Timeframe (1H)**: Identifies structural zones and intermediate BOS/MSS.
3. **Execution Timeframe (15m or 5m)**: Generates trade trigger via LTF CHoCH or MSS aligned with HTF bias.
4. **Alignment Rules**:
   - If HTF is `BULLISH` and LTF confirms a `Bullish MSS`, mark as high-confluence trend continuation.
   - If HTF is `BULLISH` and LTF confirms a `Bearish MSS`, mark as counter-trend pullback (flagged with reduced confidence).

---

## Test Suite & Verification Requirements

### 1. Deterministic Unit Tests
- **Symmetric 5-bar Fractal**: Test price sequence `[100, 102, 105, 101, 99]`. Swing High at index 2 (105) must confirm ONLY on the close of bar 4 (99).
- **Tie Breaker**: Test price sequence `[100, 105, 105, 102, 98]`. Verify handling according to the strict tie-breaker policy.
- **Wick vs. Close Break**:
  - Bar closes at 104 with wick to 106 against Swing High of 105: Under `BODY_CLOSE`, verify no BOS is emitted. Under `WICK_PENETRATION`, verify BOS emitted.

### 2. Prefix-Invariance (Anti-Repainting) Test
```python
def test_market_structure_prefix_invariance():
    candles = load_historical_candles("XAUUSD", "15m", count=500)
    # Evaluate at step 250
    snapshot_at_250 = engine.compute_structure(candles[:250], as_of=candles[249].close_time)
    
    # Evaluate at step 500
    snapshot_at_500 = engine.compute_structure(candles[:500], as_of=candles[499].close_time)
    
    # Check that confirmed swings up to index 250 - R are strictly identical
    swings_250 = [s for s in snapshot_at_250.active_swings if s.confirmation_index < 250]
    swings_500_sliced = [s for s in snapshot_at_500.active_swings if s.confirmation_index < 250]
    assert swings_250 == swings_500_sliced
```

### 3. Edge Cases & Error Handling
- **Insufficient Warmup**: For window $L+R$, series with length $< L+R+1$ must return `regime="UNKNOWN"` and empty swings with warning reason code `INSUFFICIENT_HISTORY`.
- **Gapped Data / Weekend Closes**: Structure engine must track calendar gaps and not synthesize nonexistent bars across weekends.
