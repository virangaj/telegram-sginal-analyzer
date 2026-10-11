---
name: market-analytics-backend
description: 'Use when designing FastAPI market analytics endpoints, SQLAlchemy models, Alembic migrations, signal/candle/indicator/outcome storage, pagination, filtering, transactions, recalculation, idempotency, or authorization.'
---

# Analytics API and Database Design

## Activation and Scope
Own persistence and API contracts for signals, candles, indicators, performance, and
context. Keep domain calculations in services/engines rather than route handlers.

## Inspect First
Read `backend/app/main.py`, `api/routes/`, `api/schemas.py`, `database/base.py`,
`database/models.py`, `services/signal_service.py`, `backend/tests/`, and dependency files.
SQLite and synchronous SQLAlchemy are current; Alembic is declared but not configured.
Inspect actual OpenAPI routes rather than assuming frontend API methods exist.
Read [shared architecture](../../../ARCHITECTURE.md).

## Responsibilities and Domain Rules
- Design additive versioned models with UTC-aware timestamps, source/data provenance,
  foreign keys, uniqueness, indexes, bounded queries, and explicit nullability.
- Define validated pagination, stable ordering, UTC half-open date ranges, instrument,
  timeframe, source-channel, direction, and outcome filters.
- Separate immutable messages, signal revisions, parsing statuses, trigger events,
  theoretical outcomes, observed execution, and analytics-run metadata.
- Use database uniqueness plus transactions for idempotency; in-memory checks alone
  cannot prevent concurrent duplicates. Roll back failed sessions before reuse.
- Version recalculation inputs and assumptions; never silently replace historical evidence.
- Establish Alembic baseline and upgrade/backfill policy before schema changes; do not
  claim `create_all` migrates existing columns or that changing a URL provisions PostgreSQL.
- Follow current local-only Telegram/channel management guards and local-origin CORS.
  Telegram authorization is not application authentication; remote/multi-user use needs
  approved identity, ownership, authorization, secret transport, and migration design.

## Inputs, Outputs, and Contracts
Input: validated query/command models and domain results. Output: OpenAPI-documented
responses with stable identifiers, provenance, availability status, pagination, and errors.
Use shared data-model and analytics-response definitions; keep frontend contracts aligned.

## Workflow
1. Inspect owning route, schema, service, database table, and nearby tests.
2. Specify the smallest compatible API/model change and migration/backfill needs.
3. Implement transactions and bounded access separately from domain math.
4. Add OpenAPI examples using sanitized evidence and explicit unavailable fields.
5. Test routes and migration upgrade/idempotency; document rollout and rollback limits.

## Tests and Acceptance
Cover validation/404/409 errors, pagination boundaries, tied timestamps, filters,
duplicate concurrency, rollback, UTC ranges, as-of revisions, local CORS preflight, and
unauthorized access. Test schema changes on existing data, not only fresh databases.

## Failure Cases and Exclusions
Do not serialize undocumented enum states, hide migration failures, expose Telegram
sessions, treat local access as multi-user auth, add Celery/PostgreSQL by default, mix
future data into analytics, execute trades, or guarantee returns.

## References
- [Models and response contracts](../../../docs/data-model.md)
- [Separate lifecycle states](../../../docs/signal-lifecycle.md)
