---
name: macro-context
description: 'Use when integrating macroeconomic calendar data, point-in-time economic releases (CPI, NFP, FOMC), data revisions, event blackout windows, DXY/Yield correlations, and cryptocurrency institutional catalysts.'
---

# Macroeconomic & Fundamental Context Engine

## Activation and Scope
Use this skill when developing or testing fundamental event filters, economic calendar ingestion, and macro correlation feeds in `backend/app/analysis/` and `backend/app/market/` (supporting [backend/app/analysis/regime.py](backend/app/analysis/regime.py) and [backend/app/database/models.py](backend/app/database/models.py)).

*Core Quantitative Principle: Point-in-Time Integrity*. Macroeconomic data is subject to frequent retroactive revisions (e.g., initial Non-Farm Payrolls revised weeks later). Historical backtesting and signal validation **must strictly use point-in-time snapshots** (`available_at <= evaluation_timestamp`). Injecting later revisions or using future announcement times introduces fatal look-ahead bias.

---

## Event Ingestion & Point-in-Time Revision Mechanics

```
Timeline of a Macroeconomic Release:
---+------------------------+-------------------------+---------------------> Time
   |                        |                         |
T_scheduled             T_actual                  T_revised
Scheduled Release       Initial Release           Subsequent Revision
(Forecast/Prior known)  (Actual = 216k published) (Revised to 175k next month)
```

### 1. The Immutable Revision Chain
Never overwrite an existing economic release record with revised data. Every update creates a new immutable revision record:
- **Record 1 (Original)**: Published at `2026-03-06 13:30:00 UTC`, Available at `13:30:05 UTC`. `actual = 216,000`, `revision_index = 0`.
- **Record 2 (Revision)**: Published at `2026-04-03 13:30:00 UTC`, Available at `13:30:05 UTC`. `actual = 175,000`, `revision_index = 1`, `revised_from_id = <Record 1 ID>`.
- **Query Rule**: For backtest evaluation at $T = \text{2026-03-15}$, the database query must return Record 1 (216k), as Record 2 did not exist at $T$.

### 2. Event Classification & Significance
- **Tier 1 (High Impact - Market Moving)**:
  - US: Consumer Price Index (CPI), Core PCE Price Index, Non-Farm Payrolls (NFP) / Unemployment Rate, FOMC Interest Rate Decision & Press Conference, GDP Advance.
  - Eurozone/UK: ECB Interest Rate Decision, BoE Rate Decision, UK CPI.
- **Tier 2 (Medium Impact)**:
  - Retail Sales, ISM Manufacturing / Services PMI, Producer Price Index (PPI), Consumer Sentiment (UoM).
- **Tier 3 (Low Impact)**:
  - Weekly Initial Jobless Claims (except during high-stress regimes), Trade Balance, Regional Fed Surveys.

---

## Macro Filters & Volatility Blackout Windows

High-impact macroeconomic releases cause temporary microstructure breakdown: bid-ask spreads widen $5\times$ to $20\times$, order book depth evaporates, and aggressive slippage occurs.

### Event Blackout Protocol
```python
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel

class MacroBlackoutConfig(BaseModel):
    pre_event_buffer_minutes: int = 15     # Halt signal execution 15m prior
    post_event_buffer_minutes: int = 30    # Await price discovery 30m post
    block_high_impact: bool = True
    block_medium_impact: bool = False

class EventProximityStatus(BaseModel):
    in_blackout: bool
    nearest_event_name: Optional[str]
    nearest_event_impact: Optional[str]
    minutes_to_event: Optional[float]
    minutes_since_event: Optional[float]
    action_directive: str  # "PROCEED", "HALT_NEW_ENTRIES", "TIGHTEN_STOPS"
```

- **Blackout Rule**: If `in_blackout == True`, downstream engines must suppress new market and limit entry triggers, labeling the signal `REJECTED_MACRO_BLACKOUT`.

---

## Cross-Asset Macro Correlation (Forex & Metals)

### 1. DXY (US Dollar Index) & Real Yields vs. Gold (XAUUSD)
- Gold is an unyielding, dollar-denominated monetary asset.
- **Microstructure Mechanism**:
  - Rising US Real Yields (Nominal 10Y Treasury Yield minus 10Y Breakeven Inflation) increase the opportunity cost of holding non-yielding Gold $\rightarrow$ Structural Bearish Headwind for Gold.
  - Rising DXY (Dollar strength) increases the purchasing cost of Gold in foreign currencies $\rightarrow$ Bearish Headwind.
- **Quantitative Correlation Metric**:
  Rolling 30-day Pearson correlation $\rho_{\text{30D}}(\Delta P_{\text{XAU}}, \Delta P_{\text{DXY}})$:
  $$\rho = \frac{\sum (x - \bar{x})(y - \bar{y})}{\sqrt{\sum (x - \bar{x})^2 \sum (y - \bar{y})^2}}$$
  When $\rho > -0.20$ (correlation decoupling from its historical $-0.70$ baseline), flag `REGIME_ANOMALY` (indicating geopolitical flight to safety overriding interest rate differentials).

---

## Cryptocurrency Catalysts & Institutional Flow Metrics

For Bitcoin and Ethereum, macroeconomic context incorporates institutional liquidity metrics:
1. **Spot ETF Net Flows**: Daily aggregate inflow/outflow (USD) across US Spot ETFs.
   - Point-in-Time Availability: Typically published after 01:00 UTC following the trading day.
   - Quantitative Rule: Net inflow $> +250\text{M}$ USD over 3 consecutive trading days constitutes `BULLISH_FLOW_ALIGNMENT`.
2. **Stablecoin Supply Expansion / Contraction**: 7-day change in aggregate USDT + USDC market capitalization (liquidity injection vs. extraction).

---

## Data Schemas & Contracts

```python
from datetime import datetime
from decimal import Decimal
from typing import List, Literal, Optional
from pydantic import BaseModel, Field

ImpactLevel = Literal["HIGH", "MEDIUM", "LOW", "NONE"]

class EconomicEvent(BaseModel):
    id: str
    event_key: str  # e.g., "USD_CPI_YOY"
    name: str
    country: str
    currency: str
    scheduled_at: datetime
    actual_published_at: Optional[datetime] = None
    available_at: datetime
    impact: ImpactLevel
    actual: Optional[Decimal] = None
    forecast: Optional[Decimal] = None
    previous: Optional[Decimal] = None
    is_revision: bool = False
    revision_index: int = 0
    source: str

class MacroContextSnapshot(BaseModel):
    symbol: str
    as_of: datetime
    active_blackout: bool
    blackout_reason: Optional[str] = None
    next_high_impact_event: Optional[EconomicEvent] = None
    dxy_trend: Optional[Literal["BULLISH", "BEARISH", "NEUTRAL"]] = None
    us10y_yield_trend: Optional[Literal["RISING", "FALLING", "FLAT"]] = None
    macro_bias_alignment: Literal["ALIGNED", "OPPOSED", "NEUTRAL", "UNAVAILABLE"]
    reason_codes: List[str] = Field(default_factory=list)
```

---

## Test Suite & Verification Requirements

### 1. Point-in-Time Simulation Integrity Test
- Populate test database with initial NFP release at $T_0$ (`actual=250k`) and revised NFP at $T_0 + 30\text{ days}$ (`actual=180k`).
- Query macro context at $T_0 + 5\text{ days}$.
- **Assertion**: Returned actual value must strictly equal `250k`, with `revision_index=0`.

### 2. Blackout Window Unit Test
- Schedule High Impact FOMC rate announcement at `18:00:00 UTC`.
- Evaluate signal candidate at `17:48:00 UTC` (12 minutes prior).
  - Verify `active_blackout == True`, `action_directive == "HALT_NEW_ENTRIES"`.
- Evaluate signal candidate at `18:35:00 UTC` (35 minutes post).
  - Verify `active_blackout == False`, `action_directive == "PROCEED"`.

### 3. Outage & Delay Resilience
- Simulate provider downtime where CPI release is delayed by 15 minutes past scheduled time.
- Verify system remains in `HALT_NEW_ENTRIES` blackout state until actual release data is ingested or timeout window expires.
