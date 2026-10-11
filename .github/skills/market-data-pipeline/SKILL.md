---
name: market-data-pipeline
description: 'Use when adding market data providers, historical OHLCV ingestion, live bid/ask quotes, XAUUSD symbol mapping, candle storage, freshness, quality checks, missing candles, retries, rate limits, or provider outages.'
---

# Market Data Acquisition and Storage

## Activation and Scope
Own provider adapters, acquisition, normalization, quality, and storage. Indicators and
trade outcomes are consumers, not responsibilities of this skill.

## Inspect First
Read `backend/app/market/base.py`, `backend/app/market/providers/`,
`backend/app/config.py`, `backend/app/database/models.py`, and `backend/requirements.txt`.
The current async ABC exposes current price, bid/ask, recent ticks, and limited OHLC.
`market/providers/biquote.py` implements cached quotes with provenance and freshness;
historical candles are explicitly unsupported. Read [shared architecture](../../../ARCHITECTURE.md).

## Responsibilities and Domain Rules
- Declare provider capabilities, broker/feed identity, symbol mappings, calendars,
  price basis, precision, history depth, and whether quotes are delayed or simulated.
- Fetch historical UTC intervals explicitly; a latest-N API alone is insufficient for replay.
- Preserve source, provider observation, candle open/close, and ingestion timestamps.
- Normalize interval boundaries and sort/deduplicate within a single feed, never across
  brokers silently. Record weekend closures separately from missing expected candles.
- Forex volume may be tick volume, centralized volume, or absent; label the kind and
  never replace unavailable volume with zero or present midpoint as executable bid/ask.
- Validate OHLC bounds, finite prices, bid <= ask, chronological order, and coverage.
- Use bounded retries for transient failures, jitter/backoff, timeouts, rate-limit headers,
  pagination checkpoints, and explicit terminal errors. Record freshness and quality.
- Apply shared historical availability rules; corrected candles retain revision provenance.

## Inputs, Outputs, and Contracts
Input: canonical instrument, provider, timeframe, UTC range, and capability requirements.
Output: normalized quote/candle batches plus provider, coverage, freshness, and quality
metadata. Storage identity includes feed, instrument, interval, and timestamp.
Use the shared market-data contract; changing the current ABC requires consumer updates.

## Workflow
1. Inspect the provider's actual documented capabilities and existing consumers.
2. Define mapping, time semantics, quality thresholds, and failure behavior.
3. Add an adapter behind the existing abstraction; add dependencies only when justified.
4. Validate and upsert bounded batches with resumable checkpoints and transactions.
5. Test deterministic fixtures first, then opt-in real-provider checks without logged secrets.

## Tests and Acceptance
Cover duplicate/upsert batches, gaps, revisions, interval boundaries, unsupported symbols,
missing volume, stale quotes, 429/Retry-After, transient failures, exhausted retries, and
out-of-order data. Re-ingestion must be idempotent and quality flags reproducible.
Outages must not cause stale values to acquire a fresh source timestamp.

## Failure Cases and Exclusions
The ABC's equal bid/ask fallback and always-open default are not measured market facts.
Never label demo/delayed values live, synthesize missing candles as observations, mix feeds
without disclosure, assume XAUUSD equals gold futures, or place orders. Do not add a queue,
PostgreSQL migration, or provider subscription without a scoped requirement.

## References
- [Provider, candle, quote, and quality contracts](../../../docs/market-data-contracts.md)
- [Storage and provenance model](../../../docs/data-model.md)
