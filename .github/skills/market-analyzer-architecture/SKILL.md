---
name: market-analyzer-architecture
description: 'Use when reviewing or changing market-analyzer architecture, security, layer boundaries, dependencies, configuration, secrets, observability, background tasks, graceful shutdown, code quality, or project documentation.'
---

# Architecture, Security, and Code Quality

## Activation and Scope
Own cross-cutting architecture and security decisions. Route domain-specific work to
the other focused skills; do not turn routine fixes into system rewrites.

## Inspect First
Read `.github/copilot-instructions.md`, [shared architecture](../../../ARCHITECTURE.md),
`backend/app/main.py`, configuration/database boundaries, dependency files, Docker
configuration, tests, and the touched consumer. Repository source outranks historical
status documents and memory. Check the worktree; preserve unrelated user changes.

## Responsibilities and Domain Rules
- Keep providers, parsers, domain analytics, services, persistence, API schemas, and
  frontend presentation separated according to existing directories and public APIs.
- Preserve FastAPI/synchronous SQLAlchemy/SQLite/asyncio and Next.js Pages Router unless
  a scoped need justifies PostgreSQL, a durable queue, or another compatible evolution.
- Use type hints, bounded resource use, structured/contextual logging, configuration,
  timeouts, safe retries, cancellation, observability, and graceful task/session cleanup.
- Keep API keys, Telegram credentials, auth codes/passwords, database passwords, session
  files, and raw sensitive payloads out of commits, logs, screenshots, and fixtures.
- Treat Telegram session files as bearer credentials. Restrict local account management;
  remote or multi-user deployment requires application identity and ownership isolation.
- Review migrations, enum compatibility, data retention, concurrency, and recovery before
  introducing persistent schema or background-task changes.
- Apply shared as-of, ambiguity, feed-provenance, assumptions, no-execution, and
  no-profit-guarantee rules to every subsystem and report.

## Inputs, Outputs, and Contracts
Input: bounded change request, observed architecture, operational requirements, and
threat/data-integrity model. Output: minimal implementation decision, tradeoffs, versioned
contracts, tests, rollout notes, and explicit unresolved decisions.

## Workflow
1. Identify the owning layer and a falsifiable behavior/architecture hypothesis.
2. Inspect nearby consumers, tests, secrets boundaries, and existing documentation.
3. State necessary contract changes and assumptions; avoid speculative new abstractions.
4. Implement only authorized scope; update relevant tests and docs.
5. Run meaningful focused gates and disclose deployment or numerical gaps.

## Tests and Acceptance
Verify affected domain invariants, configuration validation, authorization/CORS,
redaction, rollback/retry behavior, disconnect/shutdown, and migration compatibility.
New dependencies require a concrete purpose; documentation must separate implemented,
standalone, placeholder, and proposed behavior. No secret may appear in generated assets.

## Failure Cases and Exclusions
Do not trust production-ready labels without evidence, treat `create_all` as migration,
silently widen remote access, adopt queues for their own sake, overwrite user work,
duplicate business rules across layers, execute trades, or promise returns.

## References
- [Shared data contracts](../../../docs/data-model.md)
- [Historical evaluation constraints](../../../docs/backtesting-rules.md)
- [Existing development recipes](../../../DEVELOPMENT.md)
