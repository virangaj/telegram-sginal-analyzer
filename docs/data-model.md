# Data Model and Analytics Contracts

Status: design contracts for incremental implementation, not a description of fully
implemented database columns or endpoints. Read [architecture](../ARCHITECTURE.md) first.

## Current Mapping

`Message` preserves raw text and parsing metadata; `Signal` stores required entries,
SL/TP through related tables and normalized JSON. `Channel` holds enabled selection.
`MarketCandle`, analysis-run/market-analysis, and trade-setup models exist but do not
establish a working provider, replay, or context pipeline. Current floats, naive UTC
defaults, and required SL do not yet satisfy all contracts below.

Prefer additive adapters and migrations over replacing working models. Establish Alembic
baseline/backfills before changing persistent columns. Keep current IDs and API consumers
compatible; SQLAlchemy stores enum member names by default, while API values may differ.

## Common Envelope

Every normalized record has a schema version, stable identity, instrument, source/feed
identity, aware UTC timestamps, provenance, and quality flags. Monetary/price calculations
must specify precision and units; prefer Decimal for exact persisted prices/costs and
decimal strings in new APIs. Float indicator arrays need finite-value validation and
documented tolerance. Existing float APIs require an explicit compatibility adapter.

Unavailable values are null with reason codes; unknown is not zero or success.
UTC serialization uses ISO 8601 with `Z` or `+00:00`. Preserve original timestamp text,
timezone/offset, and DST fold when known. Never assume the host timezone for naive input.

## Message and Signal Revision

Message identity: `(platform, account/source scope, external_channel_id, external_message_id)`.
Store original text, publication/receipt times, reply identity, and edits as immutable
evidence. An edit/follow-up creates a linked revision or event, not an overwrite.

Canonical signal fields:

| Field | Contract |
|---|---|
| identity | signal_id, revision_id, original message identity, source channel/account |
| availability | published_at, received_at, revision_available_at, original timezone metadata |
| instrument | canonical symbol and instrument specification/version |
| direction/order | BUY or SELL; MARKET, LIMIT, or STOP |
| entry specification | kind: single, range, or scaling; price or low/high or ordered price/allocation levels |
| levels | stop_loss nullable; ordered targets with stable labels/prices and optional exit allocations |
| lifecycle | expiry/cancellation/update references with availability timestamps |
| extraction | parser version, raw evidence spans, validation state, ambiguity and missing-field reasons |

Do not represent an entry range as two scaling fills. Explicitly incomplete signals can
be stored for review; the current strict parser must not receive invented SL/TP values.
Validate positive finite prices, ordered ranges, recognized instruments/order semantics,
directional stop/target placement, and valid nonnegative allocations. Reject unsupported
semantics or flag ambiguity rather than silently correcting the source.

## Candle and Quote

See [market-data contracts](market-data-contracts.md). A candle carries feed/instrument,
timeframe, open/close times, OHLC, nullable volume with kind, price basis, completeness,
available_at, ingested_at, revision, and quality. A quote carries bid/ask or labeled
last/mid price, source/observation/ingestion times, freshness mode, and precision.

## Indicator and Context Snapshot

Indicator output: `(feed, instrument, timeframe, algorithm_version, parameter_hash,
bar_close_at, available_at, data_snapshot_id)`, values, units, warm-up state, and quality.
Store confirmation time separately from an extremum's occurrence time.
Context output: signal revision, publication or entry snapshot kind, assessment time,
available feature values, optional macro release versions, labeled heuristic interpretation,
missingness, and evidence references. Both must obey as-of availability rules.

## Outcome and Analytical Run

An outcome includes signal revision, run ID, evaluation start/end, trigger/fill evidence,
ordered events, classification, ambiguous bounds, MFE/MAE, target results, costs,
coverage, and assumptions. Mark mode as hypothetical or observed_execution.
Observed execution requires external fill evidence, not a replay label.

Run identity records algorithm/version, parameter hash, data snapshot/revision identifiers,
feed, source revisions, as-of policy, creation time, and all replay assumptions. Re-running
the same inputs is idempotent; new inputs produce a versioned run rather than rewriting
old evidence. Domain services compute these records; routes serialize them.

## Analytics Response

Proposed paginated responses have `schema_version`, `items`, `next_cursor`, `generated_at`,
`filters`, `evaluation_period`, `provider`, `data_quality`, and `assumptions_id`.
Items reference signal/run/revision IDs and metric values plus availability/reason codes.
Aggregate responses include cohort/denominator definitions, excluded/unknown counts,
sample size, coverage, and uncertainty. Do not promise these APIs exist until OpenAPI
and their services implement them. Cursor ordering must include a stable ID tie-breaker.

## Acceptance

Test required/nullable fields, aware timestamps, enum compatibility, range/scaling
distinction, revision uniqueness, concurrent duplicate ingestion, transactional rollback,
and migration of existing data. Preserve original evidence and unavailable-value reasons.
