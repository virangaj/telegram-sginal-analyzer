---
name: backtesting-risk
description: 'Use when implementing backtesting engines, trade replay simulation, position sizing, instrument specifications (tick size, contract value), cost modeling (spread, slippage, swap, funding), collision resolution, and quantitative risk metrics.'
---

# Backtesting & Quantitative Risk Simulation Engine

## Activation and Scope
Use this skill when developing or testing trade replay, execution simulation, position sizing, and risk reporting in `backend/app/risk/`, `backend/app/trade/`, and `backend/app/analysis/` (expanding [backend/app/risk/engine.py](backend/app/risk/engine.py), [backend/app/trade/engine.py](backend/app/trade/engine.py), and aligning with [docs/backtesting-rules.md](docs/backtesting-rules.md) and [docs/analytics-metrics.md](docs/analytics-metrics.md)).

*Strict Quantitative Mandate*:
1. **Conservative Ambiguity Resolution**: If a candle's price range touches both Stop-Loss and Take-Profit without sub-bar tick data to sequence them, **assume Stop-Loss was hit first**. Favorable intrabar outcomes must never be assumed.
2. **Realistic Execution Friction**: Zero-spread, zero-commission, or zero-slippage simulations are strictly prohibited.
3. **No In-Sample Profitability Claims**: Never report a strategy or signal channel as viable based solely on in-sample backtest curves. All performance disclosures must report Out-of-Sample (OOS) and Walk-Forward metrics.

---

## Instrument Specifications & Position Sizing

Integrates with and expands [backend/app/risk/engine.py](backend/app/risk/engine.py):

```
+-----------------------------------------------------------------------------------------+
| Instrument Class      | Contract / Lot Size | Tick Size / Value   | Margin / Sizing     |
|-----------------------|---------------------|---------------------|---------------------|
| Forex Majors (EURUSD) | 100,000 base units  | 0.0001 = $10 / lot  | Leverage / pip val  |
| Forex JPY (USDJPY)    | 100,000 base units  | 0.01 = Variable USD | Rate conversion     |
| Commodities (XAUUSD)  | 100 troy ounces     | 0.01 = $1.00 / lot  | $1.00 move = $100   |
| Crypto Spot (BTCUSDT) | 1.0 Coin            | Step size (e.g. 1e-5)| Cash funded         |
| Crypto Perps (Linear) | 1.0 Coin (or USD)   | Mark price based    | Isolated/Cross marg.|
+-----------------------------------------------------------------------------------------+
```

### Risk-Budgeted Sizing Formula
For an account with equity $E$ and configured risk fraction $r_{\%}$ (e.g. 1.0%), max monetary risk is:
$$R_{\text{monetary}} = E \times \frac{r_{\%}}{100}$$

For scaling entries $k = 1 \dots M$ with planned entry prices $P_{entry, k}$, allocations $w_k$ ($\sum w_k = 1.0$), and stop price $P_{stop}$:
$$\bar{D} = \sum_{k=1}^M w_k \cdot |P_{entry, k} - P_{stop}| \quad (\text{Weighted price distance})$$
$$\text{Position Size Units } Q = \frac{R_{\text{monetary}}}{\bar{D} \times \text{ContractMultiplier} \times \text{QuoteToAccountRate}}$$

*Invariant*: If all allocated legs fill and price is stopped at $P_{stop}$, total realized loss (excluding fees/slippage) strictly equals $R_{\text{monetary}}$.

---

## Realistic Execution Simulation & Cost Modeling

All trade replay simulations must apply side-aware pricing and frictions:

### 1. Side-Aware Quote Evaluation
- **BUY Orders**: Fill at Ask ($P_{\text{ask}} = P_{\text{mid}} + \frac{\text{Spread}}{2}$). Exit at Bid ($P_{\text{bid}} = P_{\text{mid}} - \frac{\text{Spread}}{2}$).
- **SELL Orders**: Fill at Bid ($P_{\text{bid}}$). Exit at Ask ($P_{\text{ask}}$).
- **Limit Order Fill Rule**:
  - BUY Limit fills if and only if $\text{Ask}_{\text{low}} \le P_{\text{limit}}$.
  - SELL Limit fills if and only if $\text{Bid}_{\text{high}} \ge P_{\text{limit}}$.
- **Stop Order Fill Rule**:
  - BUY Stop triggers if $\text{Ask}_{\text{high}} \ge P_{\text{stop\_entry}}$.
  - SELL Stop triggers if $\text{Bid}_{\text{low}} \le P_{\text{stop\_entry}}$.

### 2. Slippage and Market Impact Modeling
$$\text{Execution Price} = P_{\text{trigger}} \pm \left( \text{BaseSlippage} + \lambda \times \text{ATR}_{14} \times \sqrt{\frac{\text{OrderVolume}}{\text{AverageVolume}}} \right)$$
- Gaps: If a bar opens beyond a Stop-Loss price, fill occurs at the **Open price of that bar**, NOT the requested stop-loss price.

### 3. Financing & Carrying Costs
- **Forex Rollover (Swap)**: Applied daily at 21:00 UTC (17:00 NY):
  $$\text{SwapCost} = \text{Lots} \times \text{SwapRate} \times \text{DaysHeld}$$
  Triple swap charged on Wednesday to account for weekend settlement.
- **Crypto Perpetual Funding**: Applied every 8 hours (00:00, 08:00, 16:00 UTC):
  $$\text{FundingPayment} = \text{PositionValue} \times F_{\text{rate}}$$

---

## Intrabar Ambiguity & Collision Handling Protocol

```
           [Bar High]
               |
        --------------- Take-Profit Level
               |
        --------------- Stop-Loss Level
               |
           [Bar Low]
```

When evaluating a candle where BOTH Stop-Loss and Take-Profit (or Entry and Stop-Loss) fall within $[Low_i, High_i]$:
1. **Resolution Step 1**: Search for lower-timeframe observations (e.g. 1m bars or tick tape) within the interval of candle $i$. If available, replay sub-bars chronologically.
2. **Resolution Step 2 (Deterministic Pessimism)**: If sub-bar evidence is absent:
   - For pending entry + stop: Assume order did NOT trigger, or assume it triggered and stopped out immediately.
   - For open trade with SL + TP in same bar: **Enforce Stop-Loss Hit First**.
   - Set collision flag: `outcome_ambiguity="CONSERVATIVE_STOP_FIRST"`.

---

## Quantitative Performance & Risk Metrics

Formulas conforming to [docs/analytics-metrics.md](docs/analytics-metrics.md):

### 1. Core Statistics
- **Win Rate (WR)**:
  $$\text{WR} = \frac{N_{\text{wins}}}{N_{\text{evaluated\_trades}}} \quad (\text{Scratch / Breakeven trades isolated})$$
- **Profit Factor (PF)**:
  $$\text{PF} = \frac{\sum \text{Gross Profits}}{\sum |\text{Gross Losses}|}$$
- **Mathematical Expectancy ($E$)**:
  $$E = (\text{WR} \times \bar{W}) - ((1 - \text{WR}) \times \bar{L})$$
- **Maximum Drawdown (MDD)**:
  $$\text{MDD} = \max_{t \in [0, T]} \left( \frac{\max_{s \le t} E_s - E_t}{\max_{s \le t} E_s} \right)$$

### 2. Risk-Adjusted Ratios
- **Sharpe Ratio** (annualized, zero risk-free rate assumption):
  $$\text{Sharpe} = \sqrt{252} \times \frac{\mu_{r}}{\sigma_{r}}$$
- **Sortino Ratio** (downside deviation $\sigma_d$ where only negative returns are penalized):
  $$\text{Sortino} = \sqrt{252} \times \frac{\mu_{r}}{\sigma_d}, \quad \sigma_d = \sqrt{\frac{1}{N} \sum \min(0, r_t)^2}$$

---

## Out-of-Sample & Walk-Forward Validation Standard

To prevent data-snooping and curve-fitting:
```
+------------------------------------+------------------+------------------+
| In-Sample / Training (60%)         | Validation (20%) | Holdout (20%)    |
| (Model / Strategy Development)     | (Hyperparameters)| (Final OOS Test) |
+------------------------------------+------------------+------------------+
```

1. **Walk-Forward Optimization (WFO)**:
   - Anchor or roll an in-sample window (e.g. 6 months), calibrate parameters, and evaluate on an out-of-sample window (e.g. 1 month). Slide forward across the entire historical period.
   - **Walk-Forward Efficiency (WFE)**:
     $$\text{WFE} = \frac{\text{Annualized Return}_{\text{OOS}}}{\text{Annualized Return}_{\text{IS}}}$$
     A strategy with $\text{WFE} < 50\%$ is rejected as severely overfitted.

---

## Data Schemas & Contracts

```python
from datetime import datetime
from decimal import Decimal
from typing import List, Literal, Optional
from pydantic import BaseModel, Field

TradeOutcome = Literal["TP_FULL", "TP_PARTIAL_SL", "SL_FULL", "BE_SCRATCH", "CANCELLED", "AMBIGUOUS"]

class SimulatedFill(BaseModel):
    fill_time: datetime
    fill_type: Literal["ENTRY", "TP", "SL", "PARTIAL_TP"]
    price: Decimal
    quantity: Decimal
    commission: Decimal
    slippage: Decimal
    quote_spread: Decimal

class SimulatedTradeRecord(BaseModel):
    trade_id: str
    signal_id: str
    symbol: str
    direction: Literal["BUY", "SELL"]
    entry_time: datetime
    exit_time: datetime
    entry_price: Decimal
    exit_price: Decimal
    quantity: Decimal
    gross_pnl: Decimal
    net_pnl: Decimal
    realized_r: Decimal
    mfe_price: Decimal
    mfe_r: Decimal
    mae_price: Decimal
    mae_r: Decimal
    outcome: TradeOutcome
    collision_flag: Optional[str] = None
    fills: List[SimulatedFill]

class BacktestReport(BaseModel):
    strategy_id: str
    evaluation_window_start: datetime
    evaluation_window_end: datetime
    data_snapshot_id: str
    total_signals: int
    executed_trades: int
    win_rate: Decimal
    profit_factor: Decimal
    expectancy: Decimal
    max_drawdown_percent: Decimal
    sharpe_ratio: Decimal
    sortino_ratio: Decimal
    trades: List[SimulatedTradeRecord]
```

---

## Test Suite & Verification Requirements

### 1. Deterministic Unit Tests
- **Pessimistic Collision Test**: Single candle has Open=100, High=110, Low=90, Close=105. Position has Entry=100, SL=95, TP=108.
  - Verify simulation records `SL_FULL` with `collision_flag="CONSERVATIVE_STOP_FIRST"`.
- **Gap Down on Stop**: Position Long at 2000, SL at 1990. Weekend gap opens at 1980.
  - Verify fill occurs at 1980 (not 1990), with realized loss reflecting the full gap.
- **Risk Invariance Test**: Test scaling entry with 3 tranches. Verify combined worst-case stop loss equals account balance $\times r_{\%}$.
