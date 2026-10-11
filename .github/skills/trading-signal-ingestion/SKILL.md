---
name: trading-signal-ingestion
description: 'Use when implementing or debugging Telegram trading signal parsing, normalization, entry ranges, signal edits, follow-ups, cancellations, deduplication, UTC timestamps, or source provenance.'
---

# Trading Signal Ingestion and Normalization

## Activation and Scope
Own raw-message ingestion, deterministic extraction, validation, and revision linkage.
Support BUY/SELL with MARKET, LIMIT, and STOP orders; do not evaluate trade outcomes here.

## Inspect First
Read `backend/app/parsers/base.py`, `registry.py`, `implementations/examples.py`,
`backend/app/telegram/listener.py`, `backend/app/services/signal_service.py`, and
`backend/app/database/models.py`. Inspect neighboring tests before changing behavior.
The current parser accepts only message text and requires entries, SL, and TPs.
Metadata and partial signals require an explicit compatible extension, not silent coercion.
Read [architecture and quantitative rules](../../../ARCHITECTURE.md).

## Responsibilities and Domain Rules
- Store original text and source identity before parsing; preserve failed messages for review.
- Distinguish new signals from replies, modifications, cancellations, and commentary.
- Preserve ordered target labels, entry ranges versus scaling entries, original timestamp,
  timezone, publication time, receipt time, parser version, and edit history.
- Normalize GOLD/XAU/USD aliases using configured instrument mappings, not arbitrary guesses.
- Validate finite positive prices, supported order semantics, directional SL/TP placement,
  UTC conversion, and ambiguity. Never fabricate missing values or silently swap levels.
- Use source message identity for idempotency; identical text from different sources is
  not necessarily a duplicate. Link a follow-up only with defensible source evidence.
- Apply the shared as-of rules to edits: future revisions cannot alter an earlier assessment.

## Inputs, Outputs, and Contracts
Input: immutable message envelope, source/channel identity, timestamps, optional reply/edit
metadata, and configured parser policy. Output: a validated canonical signal revision,
partial/review result, cancellation event, or structured parse error with provenance.
Consult the shared data-model and lifecycle contracts before adding persistent fields.

## Workflow
1. Reproduce with a sanitized message fixture and identify the owning parser/service.
2. Define expected extracted fields and absent/ambiguous fields before editing.
3. Make the smallest parser or metadata-boundary change; retain existing plugin APIs.
4. Persist raw evidence and revisions transactionally with idempotent keys.
5. Run targeted parser and ingestion tests; document any schema migration required.

## Tests and Acceptance
Cover all six direction/order combinations, ranges, scaling entries, multiple targets,
missing levels, edits, follow-ups, cancellations, replayed messages, cross-channel identical
text, UTC offsets, and DST ambiguities. Reprocessing twice must not create two signals.
Malformed input must remain auditable without crashing the ingestion loop.

## Failure Cases and Exclusions
Overlapping SELL/MORE SELL patterns can double-count entries; test exact extracted arrays.
Do not treat successful parsing as a profitable trade, infer timezone from machine settings,
erase original messages, select parsers using undocumented registry order, execute trades,
or promise profitability. Do not fix unrelated ingestion architecture during a parser task.

## References
- [Canonical data contracts](../../../docs/data-model.md)
- [Signal revisions and lifecycle](../../../docs/signal-lifecycle.md)
