---
name: quant-testing
description: 'Use when testing signal parsers, quantitative indicators, entry triggers, trade replay, MFE/MAE, SL/TP collisions, provider resilience, API integrity, deduplication, timezones/DST, look-ahead bias, or numerical regressions.'
---

# Quantitative Testing and Data Integrity

## Activation and Scope
Own measurable correctness and regression design across domain boundaries. Do not
rewrite the application merely to introduce a new testing framework.

## Inspect First
Read `backend/tests/test_channels.py`, `test_database.py`, owning parser/analysis/trade
modules, `backend/requirements.txt`, and `frontend/package.json`. Pytest is current;
there is no verified frontend behavioral-test framework or substantive numerical suite.
Read [shared quantitative rules](../../../ARCHITECTURE.md).

## Responsibilities and Domain Rules
- Use deterministic known-price sequences, sanitized messages, isolated databases, and
  mocked provider clocks/network responses. Disable Telegram/network startup in tests.
- Define numeric tolerances, warm-up expectations, event ordering, coverage thresholds,
  and missingness before asserting calculations.
- Check trusted reference indicators using matching seed/smoothing/session conventions.
- Test prefix invariance: appending future data cannot change an earlier available
  decision. Confirmed swings may appear later but cannot be backdated as known.
- Preserve fixed channel/signal cohorts including failed, expired, untriggered, and
  unavailable cases; quantify exclusion to prevent survivorship and selection bias.
- Test publication/receipt/revision timestamps, UTC offsets, DST folds/nonexistent times,
  broker calendars, and higher-timeframe bar closure.
- Test provider 429/timeouts/outages, bounded retry recovery, resumable batches,
  uniqueness races, transactional rollback, and versioned recalculation.

## Inputs, Outputs, and Contracts
Input: documented behavior, canonical fixtures, data/assumption versions, and target module.
Output: focused tests, explicit numeric/event expectations, regression evidence, and
known unverified scenarios. Use shared backtesting and analytics-metric contracts as oracles.

## Workflow
1. Choose the smallest test that can disprove the current behavior hypothesis.
2. Create fixtures in existing tests/helpers when possible; avoid real credentials.
3. Capture the failure before implementing the local correction.
4. Rerun the focused test; widen only for affected shared contracts.
5. Report executed commands, results, and gaps without claiming unrun coverage.

## Tests and Acceptance
Cover parsing/scaling duplicates, MARKET/LIMIT/STOP triggers, gaps, SL/TP collisions,
multiple targets, null levels, missing candles, fees/spreads, cancellations, replay,
API filters/auth/CORS, and provider/database integration. Unknown must remain unknown.
Use monotonic ramps around deliberate extrema instead of accidentally tied flat swings.
Current backend gate: `python -m pytest tests -q` from `backend`.
Frontend gate: `npm run type-check`, plus browser checks for changed interactions.

## Failure Cases and Exclusions
Do not tune expectations to broken implementations, assert exact floats unnecessarily,
depend on live price/network timing, mix feeds, leak secrets, allow test fixtures to place
orders, hide bias through filtered cohorts, or infer profitability from passing tests.

## References
- [Replay acceptance rules](../../../docs/backtesting-rules.md)
- [Numerical definitions](../../../docs/analytics-metrics.md)
- [Data-integrity contracts](../../../docs/data-model.md)
