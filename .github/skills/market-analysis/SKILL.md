---
name: market-analysis
description: 'Master orchestration skill for Forex and cryptocurrency market analysis. Use when coordinating market data, market structure, liquidity, volume/order-flow, macroeconomic context, confluence scoring, trade setup validation, and backtesting.'
---

# Quantitative Market Analysis Master Specification

## Orchestration and Architecture Overview
This skill is the central orchestration and architectural authority for analyzing Forex (spot/CFDs) and cryptocurrency (spot and perpetual derivatives) markets. It establishes the quantitative contracts, timestamp discipline, dependency hierarchy, and verification standards across all specialized analytical engines.

```
                           +----------------------------+
                           |    Market Data Pipeline    |
                           | (Quotes, Candles, Feeds)   |
                           +--------------+-------------+
                                          |
                +-------------------------+-------------------------+
                |                         |                         |
                v                         v                         v
     +--------------------+    +--------------------+    +--------------------+
     |  Market Structure  |    |   Liquidity & SMC  |    |  Volume/Orderflow  |
     | (Swings, BOS, MSS) |    | (Pools, FVG, OB)   |    | (Profile, VWAP,OI) |
     +----------+---------+    +----------+---------+    +----------+---------+
                |                         |                         |
                +-------------------+     |     +-------------------+
                                    |     |     |
                                    v     v     v
                        +--------------------------------+
                        |     Macroeconomic Context      |
                        |   (Calendar, DXY, Crypto Cat.) |
                        +---------------+----------------+
                                        |
                                        v
                        +--------------------------------+
                        |   Confluence Signals Engine    |
                        |  (Scoring, Setup Rules, R:R)   |
                        +---------------+----------------+
                                        |
                                        v
                        +--------------------------------+
                        |   Backtesting & Risk Engine    |
                        | (Execution Replay, PnL, Draw.) |
                        +--------------------------------+
```

### Specialized Engine Index
When implementing or modifying a specific analytical subsystem, consult its dedicated skill:

| Analytical Subsystem | Dedicated Skill | Core Responsibilities |
|---|---|---|
| Market Structure | [.github/skills/market-structure/SKILL.md](.github/skills/market-structure/SKILL.md) | Swings, HH/HL/LH/LL, BOS, MSS, CHoCH, consolidation, MTF alignment |
| Liquidity & SMC | [.github/skills/liquidity-smc/SKILL.md](.github/skills/liquidity-smc/SKILL.md) | BSL/SSL pools, EQH/EQL, sweeps, Order Blocks, FVGs, IFVGs, Premium/Discount |
| Volume & Order-Flow | [.github/skills/volume-orderflow/SKILL.md](.github/skills/volume-orderflow/SKILL.md) | Volume Profile (POC/VAH/VAL), VWAP, Delta, CVD, Footprint, OI, Funding |
| Macroeconomic Context | [.github/skills/macro-context/SKILL.md](.github/skills/macro-context/SKILL.md) | Economic calendar releases, revisions, DXY, Yields, Crypto flows, Point-in-time |
| Confluence & Setups | [.github/skills/confluence-signals/SKILL.md](.github/skills/confluence-signals/SKILL.md) | Evidence matrix, correlation penalties, setup scoring, entry plans, reason codes |
| Backtesting & Risk | [.github/skills/backtesting-risk/SKILL.md](.github/skills/backtesting-risk/SKILL.md) | Fill replay, sizing, slippage, fees, collision resolution, walk-forward stats |

Existing related codebase references: [ARCHITECTURE.md](ARCHITECTURE.md), [docs/data-model.md](docs/data-model.md), [docs/market-data-contracts.md](docs/market-data-contracts.md), [docs/backtesting-rules.md](docs/backtesting-rules.md), and [docs/analytics-metrics.md](docs/analytics-metrics.md).

---

## Supported Market Types & Microstructure Realities
Different market classes possess fundamentally distinct clearing, settlement, liquidity, and data mechanics. Algorithms must branch on asset class capabilities:

```
+---------------------------------------------------------------------------------------+
| Market Class    | Clearing / Venue   | Spread / Pricing     | Volume Characteristics  |
|-----------------|--------------------|----------------------|-------------------------|
| Forex Spot/CFD  | Decentralized OTC, | Fragmented bid/ask,  | Tick volume (activity); |
|                 | multi-bank ECN/LP  | broker markups, swap | no centralized depth    |
|-----------------|--------------------|----------------------|-------------------------|
| Crypto Spot     | Central limit      | Exchange order-book  | Real traded volume;     |
|                 | order book (CLOB)  | matching; taker fees | centralized per venue   |
|-----------------|--------------------|----------------------|-------------------------|
| Crypto Perps    | Derivatives CLOB,  | Mark price vs index  | Real volume + Open Int. |
|                 | 8h funding cycles  | price basis; liquid. | & dynamic funding rate  |
+---------------------------------------------------------------------------------------+
```

1. **Forex & Metals (Spot/CFD, e.g., XAUUSD, EURUSD)**:
   - Decentralized OTC trading without a consolidated tape.
   - Volume reported by broker feeds is strictly **tick volume** (frequency of quote updates), never actual traded lots. Never calculate order-flow delta from broker tick volume.
   - Financing costs are overnight swap credits/debits.
2. **Cryptocurrency Spot (e.g., BTC/USDT, ETH/USDT)**:
   - Central Limit Order Book (CLOB) on distinct exchanges (Binance, Coinbase, OKX, etc.).
   - Volume is true exchange-traded units. Aggressor side (maker/taker) is observable via raw trade feeds.
3. **Cryptocurrency Perpetual Contracts (e.g., BTC-PERP)**:
   - Dual-price mechanisms: Index Price (spot benchmark), Mark Price (fair liquidation price), and Last Traded Price.
   - Perpetual funding rates exchange payments between longs and shorts every 4 or 8 hours; Open Interest tracks active contracts.

---

## Canonical Data Contracts & Precision Conventions
To eliminate rounding distortion and runtime type ambiguity across engines, enforce strict numerical and structural conventions.

### Numerical Representation
- **Prices, Lots, Pip Dimensions, Account Balances**: Use Python `Decimal` (or string-serialized decimals in API boundaries) for all persistence, sizing, and settlement calculations. Never use raw floating-point arithmetic for monetary calculations.
- **Oscillators & Continuous Series**: Floating-point NumPy/Python arrays are permitted only for vectorized continuous indicator computation (e.g., RSI, ATR, EMA), validated with explicit `math.isfinite()` bounds checks before persistence.
- **Nullability**: Unavailable or uncalculated values MUST be represented as explicit `None` (or JSON `null`) with a companion reason code (e.g., `{"value": null, "reason": "INSUFFICIENT_WARMUP_BARS"}`). Never substitute zero (`0.0`) for missing data.

### Timestamps & Range Semantics
All temporal processing must conform to [docs/market-data-contracts.md](docs/market-data-contracts.md):
- **Aware UTC Only**: Every timestamp must carry timezone information (`datetime.timezone.utc`). Reject naive timestamps at ingestion.
- **Timestamp Hierarchy**:
  - `source_event_at`: Matching engine trade execution time.
  - `provider_observed_at`: Ingestion time by external provider.
  - `available_at`: Point-in-time timestamp when the bar/quote became fully confirmed and visible to client logic.
  - `ingested_at`: Local database insertion timestamp.
  - `candle_open_at` / `candle_close_at`: Canonical UTC interval boundaries.
- **Range Boundaries**: All time range queries must be half-open intervals: `[start_time, end_time)`.
- **Closed-Bar Rule**: Analytical indicators and market structure calculations may only evaluate completed, closed bars where `candle_close_at <= evaluation_timestamp`. Incomplete/forming bars must never be fed into historical structure detection.

---

## Multi-Timeframe (MTF) Alignment Principles
Every analysis workflow combines a macro hierarchical perspective with micro execution timing.

```
       [Higher Timeframe: 1D / 4H]  ---> Macro Bias, Trend, Major Swing Structure
                    |
                    v
       [Intermediate Timeframe: 1H] ---> Market Regime, Key FVGs, BSL/SSL Zones
                    |
                    v
       [Lower Timeframe: 15m / 5m]  ---> Entry Trigger, BOS/MSS, Liquidity Sweep
```

1. **No Forward Resampling Leakage**: When querying HTF context (e.g., 4H) at a lower-timeframe moment $T$ (e.g., 15m bar at 14:15 UTC), only HTF bars with `candle_close_at <= 14:15 UTC` (e.g., the 4H bar closing at 12:00 UTC) are accessible. The incomplete 12:00-16:00 4H bar is strictly inaccessible.
2. **Session Boundaries**: Timeframe rolls must align to standard institutional session markers:
   - Asian Session: 00:00 - 08:00 UTC
   - London Session: 07:00 - 16:00 UTC
   - New York Session: 12:00 - 21:00 UTC
   - Daily Roll: 21:00 UTC (Forex 5pm NY close) or 00:00 UTC (Crypto calendar day).

---

## Deterministic Calculations, Reproducibility & Auditing
Every output produced by the analysis suite must be 100% reproducible:
1. **Prefix Invariance**: For any slice of candles $C_{0..k}$, the calculated structure and indicators at index $k$ must be identical whether the algorithm processed $C_{0..k}$ alone or $C_{0..k+n}$ (where $n > 0$). Future data must not alter past states.
2. **Analysis Run Provenance**: Every analytical result must persist an `AnalysisRun` record matching [backend/app/database/models.py](backend/app/database/models.py):
   - `model_version`: Git commit SHA or semver string of the analytical code.
   - `parameter_hash`: SHA-256 of the serialized configuration parameters.
   - `market_timestamp`: Precise point-in-time snapshot timestamp.
   - `feed_id`: Provider and venue identifier.

---

## Signal Explainability & Auditability
Black-box numerical scores are forbidden. Every setup validation or rejection must emit:
1. **Machine-Readable Reason Codes**: Standardized uppercase enum keys (e.g., `STRUCTURE_BULLISH_CONFIRMED`, `COUNTER_TREND_REJECTED`, `SPREAD_EXCEEDS_THRESHOLD`).
2. **Human-Readable Synthesis**: Structured plain text explaining the confluence rationale, opposing market factors, and precise invalidation level.
3. **Evidence Matrix Snapshot**: Detailed weight and pass/fail state for each sub-engine.

---

## Testing & Verification Standard
Every engine implementation must satisfy four testing layers:
1. **Unit Tests**: Pure deterministic fixtures checking boundary conditions (flat markets, single-tick wicks, zero volatility, gaps).
2. **Look-Ahead Bias Verification**: Automated test verifying that sliding the evaluation window bar-by-bar produces identical historical states without retroactive repainting.
3. **Integration Pipeline Tests**: End-to-end flow from raw candles through structure, liquidity, macro, confluence, and simulated fills.
4. **Data Corruption & Resilience Tests**: Explicit handling of missing bars, provider 429 errors, out-of-order ticks, and holiday session closures.

---

## Engine Implementation Workflow & DoD
When developing any engine in this suite, adhere to this sequence:
1. **Contract Definition**: Define immutable Pydantic schemas in `backend/app/analysis/` or [backend/app/api/schemas.py](backend/app/api/schemas.py).
2. **Deterministic Algorithm**: Implement pure calculation functions with zero side-effects or external network calls.
3. **Edge Case Fixture Suite**: Build synthetic price series targeting edge cases before wiring live feeds.
4. **Integration Adapter**: Connect the pure engine to SQLAlchemy persistence and the service layer.
5. **Definition of Done (DoD)**:
   - Full test suite passes via `python -m pytest tests -q`.
   - Zero look-ahead bias or repainting verified via prefix-invariance tests.
   - Code conforms strictly to existing application conventions without introducing unapproved dependencies.
