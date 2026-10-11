---
name: technical-market-analysis
description: 'Use when implementing RSI, EMA, MACD, Bollinger Bands, ATR, ADX, VWAP, relative volume, multi-timeframe indicators, trends, swings, support/resistance, volatility regimes, FVGs, or liquidity sweeps.'
---

# Technical Indicator and Market Structure Analysis

## Activation and Scope
Own deterministic indicator and structure calculations. Keep heuristic interpretation
separate from measured facts, signal outcome evaluation, and execution.

## Inspect First
Read `backend/app/analysis/engine.py`, `regime.py`, `backend/app/market/base.py`,
`backend/app/database/models.py`, and the dependency declarations. `regime.py` is currently
a placeholder, not an implemented structure engine. Pandas/NumPy are not direct declared
dependencies; justify any addition. Read [shared architecture](../../../ARCHITECTURE.md).

## Responsibilities and Domain Rules
- Define RSI, EMA, MACD, Bollinger Bands, ATR, ADX, and optional VWAP/RVOL formulas,
  parameter sets, smoothing/seed convention, warm-up lengths, and numeric tolerances.
- Use only closed, available bars at the as-of timestamp; align higher-timeframe bars by
  closing time. Preserve unknown/insufficient-history values instead of replacing with zero.
- Configure 5m, 15m, 1H, 4H, and daily analysis without assuming providers support each.
- Swings using right-hand bars become available only after confirmation; distinguish
  the extremum timestamp from confirmation time. Never backdate a confirmed decision.
- Define trend, breakout, volatility, support/resistance, FVG, and sweep rules explicitly,
  including tolerances, invalidation, mitigation, and confirmation timing.
- Compute VWAP or relative volume only with meaningful labeled volume and a declared
  session/window; tick-volume proxies are not centralized traded volume.
- Keep results pure and deterministic; version parameters and source data.

## Inputs, Outputs, and Contracts
Input: validated ordered single-feed candles, as-of timestamp, calendar, and parameter set.
Output: timestamped indicator series and structure facts with valid-from/confirmation time,
warm-up status, quality flags, algorithm version, and separately labeled heuristics.
Use the shared indicator contract and analytics-metric definitions.

## Workflow
1. Identify the consumer and mathematical definition before choosing an implementation.
2. Build small known-price fixtures; select a trusted reference with matching conventions.
3. Implement pure functions using suitable existing libraries where available.
4. Verify prefix invariance, warm-up, and multi-timeframe alignment before persistence.
5. Integrate through existing analysis boundaries; record parameters and provenance.

## Tests and Acceptance
Test flat/trending/gapped data, short history, missing/NaN bars, zero denominators,
ties, session resets, resampling, and confirmation delays. Compare reference calculations
within stated tolerance. Appending future bars must not change prior available results.

## Failure Cases and Exclusions
Flat repeated fixtures can create tied phantom swings; use deliberate sequences.
Do not use centered windows as contemporaneous facts, forward-fill unavailable higher
timeframes, confuse heuristic labels with measured certainty, generate unsupported
forecasts, promise profits, or implement trade placement.

## References
- [Indicator data contracts](../../../docs/data-model.md)
- [Metric definitions](../../../docs/analytics-metrics.md)
- [Historical availability rules](../../../docs/backtesting-rules.md)
