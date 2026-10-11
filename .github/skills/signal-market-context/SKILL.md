---
name: signal-market-context
description: 'Use when assessing signal quality or publication/entry market context, trend alignment, volatility, momentum, support/resistance proximity, channel comparisons, gold/USD/yield context, or economic events without look-ahead bias.'
---

# Market Context and Signal Quality Analysis

## Activation and Scope
Own contemporaneous context and historical associations. Consume validated indicators
and outcomes; do not duplicate their engines or produce unsupported trading predictions.

## Inspect First
Read `backend/app/analysis/regime.py`, `analysis/engine.py`, `backend/app/database/models.py`,
and current signal-service/API consumers. Context decisions are currently placeholders
and not a complete wired analytics service. Read [shared architecture](../../../ARCHITECTURE.md).

## Responsibilities and Domain Rules
- Capture separate publication-time and entry-time snapshots using only information
  available at each timestamp, including swing confirmation and data-release timing.
- Analyze measurable trend alignment, momentum, volatility, structure, and distances to
  support/resistance across configurable 5m/15m/1H/4H/daily closed bars.
- For gold, include USD indices, Treasury yields, and economic releases only when reliable
  timestamped series exist. Distinguish scheduled events from later released/revised values.
- Record absent data explicitly; do not infer macro values or future event surprises.
- Compare channels using identical feed/assumption policies, fixed cohorts, coverage
  disclosures, sample sizes, confidence/uncertainty, and duplicate-handling rules.
- Separate objective features, heuristic quality labels, observed correlations, and causal
  hypotheses. Avoid selection bias and tuning rules against their evaluation period.

## Inputs, Outputs, and Contracts
Input: signal revision, publication/trigger timestamps, as-of market facts, optional macro
series with release provenance, and cohort policy. Output: two context snapshots, feature
values, missingness flags, evidence references, and versioned historical association reports.
Use shared indicator, context-response, backtesting, and metrics contracts.

## Workflow
1. Specify the assessment timestamp and information set.
2. Inspect feed coverage and algorithm confirmation times.
3. Calculate features; label heuristic interpretation separately.
4. Define cohorts and holdout windows before comparing outcomes.
5. Produce evidence-linked reports with sample sizes, assumptions, and uncertainty.

## Tests and Acceptance
Cover unavailable higher-timeframe bars, future revisions, macro release lags, entry
after publication, missing external series, sparse channel cohorts, and filtering bias.
Appending future observations must not change an earlier context snapshot.
Every association must identify cohort, denominator, observation period, and coverage.

## Failure Cases and Exclusions
Do not call correlation causation, rate channels using only surviving/winning signals,
silently combine brokers, treat UNKNOWN as neutral evidence, invent a confidence score,
execute trades, promise profits, or imply historical associations guarantee future results.

## References
- [Context snapshots](../../../docs/data-model.md)
- [As-of and cohort rules](../../../docs/backtesting-rules.md)
- [Association reporting](../../../docs/analytics-metrics.md)
