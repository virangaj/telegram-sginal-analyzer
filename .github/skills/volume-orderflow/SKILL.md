---
name: volume-orderflow
description: 'Use when implementing volume and order-flow algorithms: Volume Profile (POC, VAH, VAL, HVN, LVN), VWAP, Anchored VWAP, Volume Delta, Cumulative Volume Delta (CVD), Footprint charts, Open Interest, and Funding Rates.'
---

# Volume & Order-Flow Quantitative Engine

## Activation and Scope
Use this skill when developing or reviewing volume profiling and microstructure order-flow analytics in `backend/app/analysis/` and `backend/app/market/`. 

*Strict Microstructure Boundary*: Market mechanics differ profoundly between decentralized Forex and centralized/crypto exchanges. This engine enforces rigid provider capability checks. **Never fabricate aggressor-side delta, bid/ask splits, or order-book depth from standard OHLCV or broker tick-volume feeds.** When required raw data is absent, emit an explicit `UNSUPPORTED` state.

---

## Market-Specific Volume Semantics & Data Capabilities

```
+------------------------------------------------------------------------------------------+
| Data Type            | Forex / CFD (e.g. XAUUSD)      | Crypto Spot & Derivatives        |
|----------------------|--------------------------------|----------------------------------|
| OHLCV Volume         | Tick Volume (quote update rate)| True Traded Base/Quote Volume    |
| VWAP Validity        | Heuristic / Activity-weighted  | Exact Volume-Weighted Avg Price  |
| Volume Delta / CVD   | STRICTLY UNSUPPORTED           | Supported (aggressor trade feeds)|
| Footprint Profile    | STRICTLY UNSUPPORTED           | Supported with L2/tick trades    |
| Open Interest / Fund.| N/A (OTC / swaps instead)      | Supported on Perpetual Futures   |
+------------------------------------------------------------------------------------------+
```

### Provider Capability Verification Protocol
Before executing any order-flow calculation, query provider capabilities:
```python
from enum import Enum
from typing import Set

class VolumeCapability(str, Enum):
    TICK_VOLUME = "TICK_VOLUME"             # Activity count only (Forex/CFD)
    CENTRALIZED_VOLUME = "CENTRALIZED_VOLUME"# Real traded volume (Crypto Spot/Perps)
    AGGRESSOR_TRADES = "AGGRESSOR_TRADES"   # Buyer/seller initiated trade flags
    ORDER_BOOK_DEPTH = "ORDER_BOOK_DEPTH"   # L2/L3 order book snapshots
    DERIVATIVES_METRICS = "DERIVATIVES_METRICS" # Open Interest, Funding Rate

def verify_capability(provider_capabilities: Set[VolumeCapability], required: VolumeCapability):
    if required not in provider_capabilities:
        raise UnsupportedVolumeMetricError(
            f"Metric requires {required.value}, but provider only supports "
            f"{[c.value for c in provider_capabilities]}"
        )
```

---

## Pure Mathematical Formulations & Algorithms

### 1. Volume Profile (Fixed-Range & Periodic)
Constructs a price-volume histogram over a specified temporal window $[T_{start}, T_{end})$.
- **Price Discretization**:
  Divide the price interval $[\min(\text{Low}), \max(\text{High})]$ into discrete bins of size $\Delta p$:
  $$\Delta p = \max(\text{TickSize}, \, \gamma \times \text{ATR}_{14}) \quad (\text{default } \gamma = 0.05)$$
- **Volume Accumulation**:
  - *With Tick-Level Trade Data*: Add trade volume directly to the corresponding price bin $b(P_{trade})$.
  - *With OHLCV Bars (Approximation)*: Distribute bar volume across bins intersecting $[L_i, H_i]$. Must be explicitly labeled with quality flag `PROFILE_METHOD="OHLCV_APPROXIMATION"`.
- **Key Profile Metrics**:
  - **Point of Control (POC)**:
    $$\text{POC} = \arg\max_b V_b$$
  - **Value Area (VA)**: Symmetrical or dual-step expansion encompassing $70.0\%$ (standard 1-sigma Gaussian analog) of total volume $V_{total}$:
    1. Initialize with $b_{poc}$ and set accumulated volume $V_{acc} = V(b_{poc})$.
    2. Compare the next two bins above versus the next two bins below the current area.
    3. Add the higher 2-bin sum to the Value Area until $V_{acc} \ge 0.70 \times V_{total}$.
    4. Define **Value Area High (VAH)** as upper boundary bin price and **Value Area Low (VAL)** as lower boundary bin price.
  - **High Volume Nodes (HVN)**: Local peaks in the smoothed profile indicating market acceptance/fair value.
  - **Low Volume Nodes (LVN)**: Local troughs indicating rapid rejection/slippage zones.

### 2. VWAP and Anchored VWAP (aVWAP)
- **Standard VWAP Formula**:
  $$\text{VWAP}_t = \frac{\sum_{i=1}^t P_{typical, i} \cdot V_i}{\sum_{i=1}^t V_i}, \quad \text{where } P_{typical, i} = \frac{H_i + L_i + C_i}{3}$$
- **Variance and Standard Deviation Bands**:
  $$\sigma_t = \sqrt{ \frac{\sum_{i=1}^t V_i \cdot (P_{typical, i} - \text{VWAP}_t)^2}{\sum_{i=1}^t V_i} }$$
  $$\text{Upper Band}_k = \text{VWAP}_t + k \cdot \sigma_t, \quad \text{Lower Band}_k = \text{VWAP}_t - k \cdot \sigma_t \quad (k \in \{1.0, 2.0, 3.0\})$$
- **Anchoring Protocol**: Reset the accumulator $(\sum PV = 0, \sum V = 0)$ strictly at the declared anchor event:
  - `SESSION`: Daily 00:00 UTC (Crypto) or 17:00 NY / 21:00 UTC (Forex).
  - `WEEKLY`: Monday market open.
  - `EVENT`: Macro news release (e.g. CPI timestamp) or significant structural swing.

### 3. Volume Delta and Cumulative Volume Delta (CVD)
*Requires `AGGRESSOR_TRADES` capability.*
- **Aggressor Side Classification** (Trade Tape):
  - Trade price $\ge \text{Ask}$: Buyer-initiated (Aggressor Buy, $V_{buy}$).
  - Trade price $\le \text{Bid}$: Seller-initiated (Aggressor Sell, $V_{sell}$).
  - Tick-rule fallback if quotes absent: Price uptick $\rightarrow V_{buy}$; downtick $\rightarrow V_{sell}$.
- **Bar Delta ($\Delta_i$)**:
  $$\Delta_i = V_{buy, i} - V_{sell, i}$$
- **Cumulative Volume Delta ($\text{CVD}_t$)**:
  $$\text{CVD}_t = \text{CVD}_{t-1} + \Delta_t$$
- **Delta Divergence**:
  - *Absorption Bullish Divergence*: Price prints LL while CVD prints HL (aggressive sellers absorbed by passive limit bids).
  - *Exhaustion Bearish Divergence*: Price prints HH while CVD prints LH (lack of aggressive buying at premium).

### 4. Perpetual Derivatives Metrics (Open Interest & Funding)
*Requires `DERIVATIVES_METRICS` capability.*
- **Open Interest (OI) Trend Analysis**:
  - Price $\uparrow$, OI $\uparrow$: Aggressive new longs entering (strong bullish trend).
  - Price $\uparrow$, OI $\downarrow$: Short squeeze / short covering (fragile rally).
  - Price $\downarrow$, OI $\uparrow$: Aggressive new shorts entering (strong bearish trend).
  - Price $\downarrow$, OI $\downarrow$: Long liquidation cascade.
- **Predicted Funding Rate**: Annualized or 8-hour rate. Extreme positive funding ($> +0.05\%$/8h) indicates over-leveraged longs susceptible to long squeeze.

---

## Data Schemas & Contracts

```python
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field

class VolumeProfileBin(BaseModel):
    price_level: Decimal
    volume: Decimal
    buy_volume: Optional[Decimal] = None
    sell_volume: Optional[Decimal] = None

class VolumeProfile(BaseModel):
    symbol: str
    timeframe: str
    start_time: datetime
    end_time: datetime
    poc_price: Decimal
    vah_price: Decimal
    val_price: Decimal
    total_volume: Decimal
    bins: List[VolumeProfileBin]
    method: Literal["EXACT_TICKS", "OHLCV_APPROXIMATION"]

class VWAPPoint(BaseModel):
    timestamp: datetime
    vwap: Decimal
    upper_band_1: Decimal
    lower_band_1: Decimal
    upper_band_2: Decimal
    lower_band_2: Decimal
    std_dev: Decimal
    anchor_type: Literal["SESSION", "WEEKLY", "EVENT"]

class OrderFlowSnapshot(BaseModel):
    symbol: str
    timestamp: datetime
    status: Literal["AVAILABLE", "UNSUPPORTED", "STALE"]
    bar_delta: Optional[Decimal] = None
    cvd: Optional[Decimal] = None
    delta_divergence: Optional[Literal["BULLISH_ABSORPTION", "BEARISH_EXHAUSTION", "NONE"]] = None
    open_interest: Optional[Decimal] = None
    funding_rate_8h: Optional[Decimal] = None
    reason_code: Optional[str] = None
```

---

## Test Suite & Verification Requirements

### 1. Deterministic Unit Tests
- **VWAP Flat Volume**: Feed identical bars with equal volume: verify VWAP equals simple moving average of typical prices.
- **Value Area Summation**: Test volume distribution with known symmetric bell curve: verify Value Area contains $\ge 70.0\%$ and $< 75\%$ of volume.
- **Forex Capability Rejection**:
  - Feed `XAUUSD` provider with only `TICK_VOLUME` to Delta/CVD calculation function.
  - Verify function raises `UnsupportedVolumeMetricError` or returns `status="UNSUPPORTED"` with reason code `TICK_LEVEL_DATA_UNAVAILABLE`.

### 2. Prefix-Invariance Test
- Compute rolling VWAP on series $C_{0..k}$. Ensure adding future bars $C_{k+1..n}$ does NOT alter $\text{VWAP}_t$ for any $t \le k$.
