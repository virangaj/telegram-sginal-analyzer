---
name: market-analyzer-frontend
description: 'Use when building the Next.js trading dashboard, signal charts and entry/SL/TP overlays, market-context views, channel selection, analytics filters, live/delayed/stale labels, MFE/MAE displays, or responsive frontend states.'
---

# Market Analyzer Dashboard

## Activation and Scope
Own presentation and interaction; consume authoritative backend analytics rather than
recomputing outcome or indicator rules in the browser.

## Inspect First
Read `frontend/pages/`, `components/`, `lib/api.ts`, `lib/types.ts`, `lib/store.ts`,
`styles/globals.css`, and `package.json`; verify backend OpenAPI for every API call.
Use the Pages Router, React 18, Tailwind, Axios, Zustand, Recharts, and Lucide already
present. Read [shared architecture](../../../ARCHITECTURE.md).

## Responsibilities and Domain Rules
- Preserve the requested dark-blue gradient/glass theme; keep operational surfaces
  compact, legible, keyboard-accessible, and responsive rather than marketing-style.
- Keep selected listening channels first, persist checkbox changes, and distinguish
  selected, listening, disconnected, saving, and failed states.
- Display recent signals, provider-labeled quotes and historical candles; overlay entry
  zones, SL, TP labels, publication time, and supported entry-trigger evidence.
- Provide date, instrument, timeframe, direction, channel, and outcome filters using
  backend contracts. Show context at publication separately from context at entry.
- Display R:R, MFE/MAE, outcomes, costs, assumptions, uncertainty, and quality without
  converting missing metrics to zero or hypothetical performance into realized profit.
- Label live, delayed, stale, simulated, and historical data from backend provenance;
  refreshing a page must not reset the provider timestamp or freshness status.
- Format prices using instrument precision, UTC/timezone-aware labels, and finite values.
- Reuse existing charts where suitable; adopt Lightweight Charts only for a demonstrated
  candlestick/overlay requirement. Do not replace the router or chart library arbitrarily.

## Inputs, Outputs, and Contracts
Input: verified API responses for signals, candles, indicators, outcomes, context, provider
quality, and channel selection. Output: accessible views, filters, overlays, and mutations
with truthful state. Extend `lib/types.ts` and API methods alongside backend contracts.

## Workflow
1. Inspect the existing view and actual endpoint, including null/error responses.
2. Define loading, empty, error, stale, ambiguous, and permission-denied states.
3. Make a focused component/API change using existing theme and control conventions.
4. Type-check; verify browser interactions and desktop/mobile screenshots.
5. Test chart timestamps/levels and restore any mocked browser routes afterward.

## Tests and Acceptance
Run `npm run type-check`; use `npm run build` for routing/build changes and browser
checks when no frontend test framework exists. Test filter results, selected-first
reordering, failed saves, missing levels, stale quotes, chart alignment, and overflow.
No overlay may imply execution where the backend reports only hypothetical contact.

## Failure Cases and Exclusions
Do not call nonexistent endpoints, assume all instruments use two decimals, crash on
empty entry/TP arrays, show infinite R:R, hide unknown outcomes, expose login secrets,
add broker-order controls, or present historical charts as guaranteed future returns.

## References
- [Response contracts](../../../docs/data-model.md)
- [Provider/freshness labels](../../../docs/market-data-contracts.md)
- [Displayed metric semantics](../../../docs/analytics-metrics.md)
