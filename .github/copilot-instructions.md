# Signal Analyzer

Analyze external trading signals, primarily Telegram XAU/USD, against timestamped market
evidence. Do not execute trades. Read [architecture](../ARCHITECTURE.md) and the relevant
shared contracts before changing domain behavior. Source and actual OpenAPI outrank
historical scaffold examples, status claims, and repository memory.

## Current Architecture

- Backend: FastAPI, Pydantic, synchronous SQLAlchemy, SQLite default, Telethon, asyncio tasks.
- Owners: `backend/app/parsers`, `telegram`, `market`, `analysis`, `risk`, `trade`,
  `services`, `database`, and `api`. Keep domain math out of controllers and presentation.
- Frontend: Next.js Pages Router/React 18, TypeScript, Tailwind, Axios, Zustand, Recharts,
  Lucide. Preserve dark-blue gradient/glass styling and selected-first channel ordering.
- Alembic is declared but not configured; PostgreSQL and durable queues are not current.
  Market providers and quantitative analysis/replay are incomplete. Do not replace working
  technologies or add dependencies without a concrete scoped need.

## Non-Negotiable Rules

Use only evidence available at the assessment timestamp; never leak future candles,
revisions, swing confirmations, or macro releases into historical decisions. Report SL/TP
ordering ambiguity conservatively. Missing data is not proof a level was untouched.
Preserve provider/broker identity, quote basis, timestamps, coverage, data revisions, and
all entry/exit/cost assumptions. Never mix feeds silently or call simulated/delayed data live.
Separate signal quality, hypothetical performance, and observed executable results.
Never place broker orders, invent missing price levels, promise profits, or present past
performance as a guarantee. Never commit/log credentials, login codes, passwords, session
files, or sensitive raw messages. Local Telegram auth is not multi-user application auth;
do not bypass local management guards or broaden CORS without an approved access design.

## Consult Focused Skills

| Work | Skill |
|---|---|
| Messages, parsing, revisions, normalization | [trading-signal-ingestion](skills/trading-signal-ingestion/SKILL.md) |
| Providers, quotes/candles, storage quality | [market-data-pipeline](skills/market-data-pipeline/SKILL.md) |
| Indicators, swings, structure, regimes | [technical-market-analysis](skills/technical-market-analysis/SKILL.md) |
| Triggers, replay, SL/TP, MFE/MAE, outcomes | [signal-performance-evaluation](skills/signal-performance-evaluation/SKILL.md) |
| Publication/entry context and channel comparisons | [signal-market-context](skills/signal-market-context/SKILL.md) |
| Models, migrations, APIs, filters, authorization | [market-analytics-backend](skills/market-analytics-backend/SKILL.md) |
| Dashboard, charts, filters, channel controls | [market-analyzer-frontend](skills/market-analyzer-frontend/SKILL.md) |
| Numerical tests, integrity, bias, provider recovery | [quant-testing](skills/quant-testing/SKILL.md) |
| Architecture, secrets, quality, operational changes | [market-analyzer-architecture](skills/market-analyzer-architecture/SKILL.md) |

Load only the skills relevant to the task; follow their linked contracts rather than
copying all skill content into every implementation or instruction file.

## Workflow and Verification

Inspect the owning code, nearby consumers/tests, and repository instructions first.
Make a small justified change, preserve unrelated user work, and run focused validation.
Use database constraints/transactions for idempotency; `create_all` is not a migration.
Update affected contracts/tests/docs when behavior changes. Do not claim unrun coverage.

From `backend`: `python -m pytest tests -q`. From `frontend`: `npm run type-check`;
run `npm run build` for routing/build changes and browser checks for changed interactions.
Numerical/provider/frontend behavior coverage is incomplete; add deterministic targeted
tests as needed. Real-provider checks are opt-in and must not reveal secrets.
