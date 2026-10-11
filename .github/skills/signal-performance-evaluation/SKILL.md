---
name: signal-performance-evaluation
description: 'Use when backtesting trading signals, evaluating entry triggers, market/limit/stop entries, SL/TP ordering, multi-target outcomes, expiry, MFE, MAE, reward-to-risk, spreads, slippage, or execution assumptions.'
---

# Signal Performance and Trade Outcome Evaluation

## Activation and Scope
Own historical replay and evidence-based outcomes. Separate theoretical signal performance
from observed fills and realized execution; do not implement a broker order engine.

## Inspect First
Read `backend/app/trade/entry_engine.py`, `trade/engine.py`, `risk/engine.py`,
`backend/app/services/signal_service.py`, and lifecycle/analysis models in
`backend/app/database/models.py`. Existing entry/risk helpers are not an outcome simulator.
Read [shared quantitative rules](../../../ARCHITECTURE.md).

## Responsibilities and Domain Rules
- Replay only prices after publication and applicable revision availability; establish
  eligibility, entry trigger, and fill evidence before tracking SL/TP outcomes.
- Specify market, limit, stop, range, scaling, expiry, and cancellation semantics.
- Use side-aware quotes and declared gap/fill policy; a candle touching a level is not
  sufficient proof of a fill at that price. Never assume a signal publisher's claimed fill.
- Record every target event; calculate exits only using explicit partial-exit allocations.
- Mark same-bar entry/SL/TP ordering ambiguous when intrabar sequence is unavailable.
  Report conservative bounds or unknown, not an invented winning sequence.
- Missing SL makes risk-based metrics unavailable; missing TP permits observed path
  metrics but not an invented target outcome. Gaps in coverage can make outcomes unknown.
- Track MFE/MAE only after entry over a documented observation horizon and price basis.
- Record spreads, fees, slippage, lot constraints, contract multipliers, and currency
  conversion where known; distinguish missing costs from zero costs.

## Inputs, Outputs, and Contracts
Input: canonical signal revision/events, publication time, single-feed market history,
coverage metadata, and versioned replay assumptions. Output: trigger evidence, event
timeline, outcome classification, ambiguity bounds, MFE/MAE, R metrics, and provenance.
Use shared lifecycle, backtesting, and analytics-metric contracts.

## Workflow
1. Define the exact entry/exit rules and unavailable evidence before coding.
2. Build deterministic price paths covering each state transition.
3. Implement idempotent replay independently of API routes and broker adapters.
4. Persist versioned results keyed by signal revision, data snapshot, and assumptions.
5. Reconcile summary metrics with event evidence and run targeted regression tests.

## Tests and Acceptance
Cover BUY/SELL MARKET/LIMIT/STOP, untriggered signals, entry gaps, same-candle collisions,
multiple targets, partial exits, missing levels/data, expiry, cancellation, and duplicate
replay. Every reported exit must follow a supported entry and include its assumptions.

## Failure Cases and Exclusions
Do not divide absolute TP price by stop distance, count untriggered targets as wins,
double-count scaling entries, infer intrabar order from OHLC, overwrite historical runs,
conflate parse status with outcome, place trades, or guarantee future profitability.

## References
- [Replay and execution rules](../../../docs/backtesting-rules.md)
- [Lifecycle](../../../docs/signal-lifecycle.md)
- [R, MFE, MAE, and aggregation definitions](../../../docs/analytics-metrics.md)
