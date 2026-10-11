# Market Data Contracts

Status: provider-independent target contracts. The existing ABC in
`backend/app/market/base.py` has latest-price/bid-ask/recent-ticks/latest-N OHLC methods;
it does not yet provide a provenance-rich historical range API or a working provider.
See [architecture](../ARCHITECTURE.md).

## Instrument and Provider Capabilities

Declare canonical symbol, provider symbol, broker/feed, base/quote currency, price precision,
tick size, contract multiplier, timezone/session calendar, supported intervals, history
depth, rate limits, and supported price/volume types. Specify spot, CFD, futures, or other
instrument type. Do not equate XAUUSD with GC futures or assume Forex volume is centralized.

Capabilities must report historical ranges, quote delay, bid/ask availability, revisions,
tick ordering, calendar coverage, and whether data is simulated. Unsupported operations
return explicit capability errors. The current equal bid/ask and always-open defaults
are fallbacks, not evidence of a measured zero spread or an open market.

## Timestamp Semantics

- source_event_at: exchange/venue event time when supplied; do not invent it for OTC Forex.
- provider_observed_at: provider observation time, distinct from exchange timestamps.
- available_at: when this value/revision could be known under the evaluation policy.
- ingested_at: local receipt time; refresh/retry must not alter source-event freshness.
- candle_open_at/candle_close_at: aware UTC boundaries of the declared interval/calendar.

Use half-open requested ranges `[start, end)`, chronological output, and explicit boundary
alignment. A candle is eligible for closed-bar analytics only after its close and availability.
Resampling must exclude incomplete higher-timeframe bars and disclose partial intervals.
Keep original timezone/calendar and provider timestamp semantics alongside normalized UTC.

## Candles

Required: instrument/feed, timeframe, open/close times, open/high/low/close, price_basis,
completeness, revision/source snapshot, available_at, ingested_at, and quality flags.
Volume is nullable and labeled centralized, tick, provider_proxy, or unavailable.
Do not replace missing volume with zero. Validate finite positive OHLC and
`low <= min(open, close) <= max(open, close) <= high`.

Storage key includes feed, instrument, timeframe, candle_open_at, and revision strategy.
An upsert may update a current view but must preserve revisions used by historical runs.
Never deduplicate different brokers into one unlabeled price series.

## Quotes and Freshness

Quote: instrument/feed, bid and ask when measured, otherwise labeled last/mid value,
source/provider/availability/ingestion times, delay, precision, and quality. Validate bid <= ask.
Status is live, delayed, stale, simulated, historical, unavailable, or unknown; thresholds
are provider/instrument-specific. Without timestamp/delay evidence, do not claim live.
`get_current_price()` alone cannot prove quote-side execution or freshness.

## Coverage and Failure Handling

Return requested/actual ranges, expected/observed candles, calendar closures, missing
intervals, duplicates/revisions, quality reasons, and checkpoint state. Missing bars are
not proof that price levels were untouched. Imputation, if used for display, must be
labeled synthetic and excluded from evidence-based fill/outcome evaluation.

Use bounded batches, request timeouts, rate-limit-aware retries/backoff/jitter, cancellation,
and resumable checkpoints. Separate transient 429/5xx/timeouts from permanent auth/symbol
errors. Exhaustion returns an observable failure and retains the last valid source timestamp.
No API keys or raw sensitive responses may appear in logs.

## Acceptance

Test interval/DST/calendar boundaries, unsupported symbols, bid/ask fallback labeling,
stale updates, 429/Retry-After, interrupted batches, out-of-order data, revisions, duplicate
upserts, and missing volume. Historical replay must identify the exact feed/data version.
