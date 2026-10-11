# Backtesting and Outcome Rules

Status: implementation specification, not an existing replay engine. Follow
[architecture rules](../ARCHITECTURE.md) and [lifecycle semantics](signal-lifecycle.md).

## Information Set and Reproducibility

For decision time T, select only signal revisions and prices/features available by T.
Closed-bar indicators require candle close/availability <= T. Confirmed swings require
confirmation <= T; macro inputs require original publication/release availability <= T.
Downloading corrected history today does not prove it was available then. When historical
availability is inferred from bar closure, label the reconstruction assumption and do not
present it as audited real-time knowledge. Store revision/data snapshot and algorithm IDs.

Freeze cohort, test period, parameters, feed, and assumptions before evaluation. Use
chronological training/validation/holdout periods if tuning. Do not select only channels
or signals that survived or won; disclose missing history, exclusions, and sample size.

## Entry Semantics

Use one documented broker/feed and side-aware prices. BUY executes at ask and sells at
bid; SELL executes at bid and buys at ask, subject to instrument conventions.
Market entry uses first eligible observation after availability plus declared latency;
a fill claim requires quote/execution evidence. A publication price is not a guaranteed fill.

Limit contact convention: BUY ask <= limit; SELL bid >= limit. Stop trigger convention:
BUY ask >= stop entry; SELL bid <= stop entry. Brokers may differ; record overrides.
Trigger contact does not guarantee execution. Specify spread/latency/liquidity/slippage
assumptions and gap behavior; do not assume an order fills at a skipped level.

For ranges, declare first contact, preferred price, or another defensible fill policy.
For scaling, evaluate each leg independently with nonnegative allocations summing to
one for the planned total. Range endpoints are not two filled legs. Expiry/cancellation
limits eligibility using available event times; post-entry exit handling must be explicit.

## Exits and Ambiguity

Track each target independently and apply only declared partial-exit allocations.
BUY exit evaluation uses bid and SELL exit evaluation uses ask when available.
Mid/last OHLC simulation requires explicit price-basis/spread assumptions.
If entry, SL, and TP occur within one bar and order is unknowable, report ambiguous.
Finer eligible same-feed ticks may resolve it; otherwise provide bounds, an explicit
conservative stop-first scenario, or unknown. Do not count a chosen scenario as observed fact.

Missing SL makes planned/realized risk multiples unavailable. Missing TP makes target
completion unavailable; path metrics may still be reported for a declared horizon.
Coverage gaps before entry or during tracking can make trigger/exit and MFE/MAE unknown
or bounded. Never assert a level was not hit merely because it was not observed.

## Costs and Result Modes

Record fees, commissions, spread basis, slippage, contract multiplier, currency conversion,
lot/tick increments, liquidity assumptions, latency, fill policy, partial exits, expiry,
and horizon. Unknown costs are not zero costs. Gross and net results must be separate.
Signal quality, hypothetical replay performance, and observed execution results are
distinct. Only external fill/close evidence supports realized executable results.
The system must not place broker orders or guarantee future profitability.

## Acceptance

Use deterministic BUY/SELL MARKET/LIMIT/STOP paths; untriggered entries; gaps; same-bar
SL/TP/entry collisions; multiple targets; scaled fills; cancellation/expiry; missing levels;
cost assumptions; feed mismatch; duplicate replay; and future revisions. Every result must
be traceable to evidence, assumptions, coverage, and an explicit observation window.
