---
name: confluence-signals
description: 'Use when synthesizing multi-source market evidence into trade setups: higher-timeframe bias, lower-timeframe triggers, indicator correlation de-biasing, heuristic confluence scoring, rejection rules, entry plans, and explainable reason codes.'
---

# Confluence & Setup Validation Quantitative Engine

## Activation and Scope
Use this skill when developing the setup evaluation and decision logic in `backend/app/analysis/` and `backend/app/trade/` (integrating [backend/app/analysis/regime.py](backend/app/analysis/regime.py), [backend/app/trade/entry_engine.py](backend/app/trade/entry_engine.py), and [backend/app/risk/engine.py](backend/app/risk/engine.py)).

This engine synthesizes outputs from Market Structure, Liquidity & SMC, Volume & Order-Flow, and Macro Context into a validated, explainable `TradeSetup`.

*Critical Quantitative Guardrails*:
1. **No Pseudo-Probability Claims**: A heuristic confluence score (e.g. 78/100) is **not an empirical win probability**. Never label heuristic scores as probabilities unless calibrated out-of-sample via isotonic regression or Platt scaling with documented Brier scores.
2. **Correlation Clustering**: Never treat collinear indicators (e.g. RSI, Stochastics, and MACD all signaling oversold) as independent additive confirmations. Collinear signals must be grouped into a single constrained category.
3. **Missing Data Defense**: Unavailable data (e.g. missing order-flow delta on Forex) must **never** be silently converted to a positive score or default true.

---

## The Multi-Layer Confluence Matrix

```
+---------------------------------------------------------------------------------------+
| Category               | Weight | Metrics / Sub-Engine Evidence                       |
|------------------------|--------|-----------------------------------------------------|
| 1. Macro & Environment | 15%    | Non-blackout status, DXY/Yield alignment, Session   |
| 2. HTF Structure Bias  | 25%    | 4H/1D Trend alignment, Major BOS, Discount/Premium  |
| 3. LTF Trigger & Shift | 25%    | 15m/5m MSS or CHoCH with displacement candle close   |
| 4. Liquidity & SMC     | 20%    | Confirmed sweep of BSL/SSL, active FVG or OB test   |
| 5. Volume & Order Flow | 15%    | POC/VAH/VAL rejection, VWAP touch, CVD divergence   |
+---------------------------------------------------------------------------------------+
```

### Correlation De-Biasing Algorithm
Indicators are partitioned into orthogonal analytical clusters:
- **Cluster A (Trend / Structure)**: Moving Averages, Supertrend, Market Structure Swings.
- **Cluster B (Momentum / Oscillators)**: RSI, Stochastics, CCI, MACD histogram.
- **Cluster C (Volatility / Bands)**: ATR, Bollinger Bands, Keltner Channels.
- **Cluster D (Volume / Microstructure)**: Volume Profile, CVD, VWAP.
- **Mathematical Rule**: The composite score for any cluster $k$ is bounded by the maximum weight allocated to that cluster, regardless of how many individual indicators within that cluster fire:
  $$\text{Score}_{\text{cluster}} = \min \left( W_{\text{max}, k}, \, \sum_{j \in \text{cluster}} w_j \cdot I_j \right)$$

---

## Hard Rejection Criteria (Pre-Score Filters)
Before computing the confluence score, evaluate deterministic rejection filters. If any filter triggers, the setup is immediately marked `REJECTED` and processing halts:

```python
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel

class RejectionReason:
    MACRO_BLACKOUT = "MACRO_BLACKOUT"
    INSUFFICIENT_RR = "INSUFFICIENT_RR"
    COUNTER_HTF_TREND = "COUNTER_HTF_TREND"
    WRONG_SIDE_LEVELS = "WRONG_SIDE_LEVELS"
    EXCESSIVE_SPREAD = "EXCESSIVE_SPREAD"
    STALE_EVIDENCE = "STALE_EVIDENCE"
    UNFAVORABLE_PREMIUM_DISCOUNT = "UNFAVORABLE_PREMIUM_DISCOUNT"

def evaluate_hard_rejections(setup_candidate) -> Optional[str]:
    # 1. Macro Blackout Guard
    if setup_candidate.macro.active_blackout:
        return RejectionReason.MACRO_BLACKOUT
    
    # 2. Risk/Reward Boundary (Minimum 1.5 R:R)
    if setup_candidate.planned_rr < Decimal("1.5"):
        return RejectionReason.INSUFFICIENT_RR
        
    # 3. Geometric Direction Consistency
    if setup_candidate.direction == "BUY":
        if setup_candidate.stop_loss >= setup_candidate.entry_price:
            return RejectionReason.WRONG_SIDE_LEVELS
        if setup_candidate.target_1 <= setup_candidate.entry_price:
            return RejectionReason.WRONG_SIDE_LEVELS
        # 4. Premium/Discount Guard: Buying in extreme Premium is prohibited
        if setup_candidate.smc.premium_discount_status == "PREMIUM":
            return RejectionReason.UNFAVORABLE_PREMIUM_DISCOUNT
            
    elif setup_candidate.direction == "SELL":
        if setup_candidate.stop_loss <= setup_candidate.entry_price:
            return RejectionReason.WRONG_SIDE_LEVELS
        if setup_candidate.target_1 >= setup_candidate.entry_price:
            return RejectionReason.WRONG_SIDE_LEVELS
        if setup_candidate.smc.premium_discount_status == "DISCOUNT":
            return RejectionReason.UNFAVORABLE_PREMIUM_DISCOUNT

    return None
```

---

## Entry Zone, Stop-Loss & Target Construction

Integrating with [backend/app/trade/entry_engine.py](backend/app/trade/entry_engine.py):

### 1. Invalidation Level (Stop-Loss)
- Must be anchored to an objective structural invalidation point, NOT an arbitrary pip distance:
  - **BUY Setup**: Stop-Loss placed below the lowest point of the sweeping candle or below the lower boundary of the mitigating Bullish FVG/OB minus an ATR buffer ($\text{SL} = \text{Anchor}_{\text{low}} - 0.2 \times \text{ATR}_{14}$).
  - **SELL Setup**: Stop-Loss placed above the highest point of the sweeping candle or above the upper boundary of the mitigating Bearish FVG/OB plus an ATR buffer ($\text{SL} = \text{Anchor}_{\text{high}} + 0.2 \times \text{ATR}_{14}$).

### 2. Entry Zone Construction
- **Preferred Entry**: Consequent Encroachment (50% midpoint) of the trigger FVG, or the retest level of the broken swing high/low.
- **Entry Zone Range**: $[\text{Zone}_{\text{low}}, \text{Zone}_{\text{high}}]$. Orders are canceled if price moves to Target 1 prior to filling within the entry zone.

### 3. Multi-Target Framework & Planned R
Conforming to [docs/analytics-metrics.md](docs/analytics-metrics.md):
- **Target 1 (Liquidity Target)**: Nearest opposing liquidity pool (EQH for longs, EQL for shorts) or nearest opposing FVG.
- **Target 2 (Structural Target)**: HTF major swing high (longs) or major swing low (shorts).
- **Target 3 (Expansion Target)**: $1.618$ Fibonacci extension of the trigger swing leg.
- **Planned $R$**:
  $$R_k = \frac{q \cdot (T_k - E)}{\text{Stop Distance}}, \quad q = +1 \text{ (BUY)}, -1 \text{ (SELL)}$$

---

## Signal Lifecycle & Deduplication Protocol

```
Candidate Generated
       |
       v
Hard Rejections Checked ---> [FAILED] ---> REJECTED (Archived with reason)
       |
    [PASSED]
       |
       v
Confluence Score Computed ---> [Score < Threshold] ---> NO_SETUP
       |
  [Score >= Threshold]
       |
       v
Deduplication Check ---> [Duplicate within N bars] ---> SUPPRESSED_DUPLICATE
       |
   [UNIQUE]
       |
       v
ACTIVE_SETUP (Awaiting Price Trigger in Entry Zone)
       |
       +---> [Price touches Invalidation before Fill] ---> INVALIDATED_PRE_ENTRY
       +---> [Price reaches Target 1 before Fill]     ---> EXPIRED_MISSED_MOVE
       +---> [Price fills in Entry Zone]              ---> FILLED (Tracked by Replay)
```

---

## Data Schemas & Contracts

```python
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field

SetupStatus = Literal[
    "ACTIVE_PENDING", "FILLED", "INVALIDATED", 
    "EXPIRED_MISSED", "REJECTED", "SUPPRESSED_DUPLICATE"
]

class ConfluenceEvidence(BaseModel):
    category: str
    component_name: str
    weight: Decimal
    score_contribution: Decimal
    is_aligned: bool
    details: str

class TradeSetupResult(BaseModel):
    setup_id: str
    symbol: str
    timeframe: str
    direction: Literal["BUY", "SELL"]
    created_at: datetime
    status: SetupStatus
    heuristic_score: Decimal = Field(..., ge=0, le=100)
    preferred_entry: Decimal
    entry_zone_low: Decimal
    entry_zone_high: Decimal
    stop_loss: Decimal
    take_profits: List[Decimal]
    risk_reward_r1: Decimal
    risk_reward_weighted: Decimal
    invalidation_reason: Optional[str] = None
    rejection_code: Optional[str] = None
    human_explanation: str
    machine_reason_codes: List[str]
    evidence_matrix: List[ConfluenceEvidence]
```

---

## Test Suite & Verification Requirements

### 1. Unit Tests
- **Hard Rejection Evaluation**:
  - Test BUY setup with `entry = 2000.0`, `stop_loss = 2005.0`. Verify rejection with `WRONG_SIDE_LEVELS`.
  - Test setup occurring during simulated FOMC blackout. Verify rejection with `MACRO_BLACKOUT`.
- **Collinearity Cap Test**:
  - Simulate 4 momentum indicators all firing simultaneously. Verify the aggregate momentum contribution does not exceed the 25% cluster cap.

### 2. Missing Data Robustness Test
- Pass market state lacking order-flow data (e.g. Forex tick feed).
- Verify the engine does NOT crash, does NOT award unearned points, and reports `reason_codes` containing `ORDERFLOW_METRICS_UNAVAILABLE`.
