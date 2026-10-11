# Analytics Metrics

Status: authoritative definitions for future implementations. Existing helpers/UI use
inconsistent nearest-target versus average-target R:R; reconcile consumers explicitly.
See [backtesting rules](backtesting-rules.md) and [data contracts](data-model.md).

## Price Distance and Planned R

For supported entry E and stop S, price risk distance is D = abs(E - S), with D > 0.
For direction sign q (+1 BUY, -1 SELL) and target T, reward distance is q * (T - E).
Planned target R = reward distance / D. Return null with reason for absent/invalid stop,
unavailable entry, nonfinite values, zero D, or wrong-side target; do not use abs to hide
invalid directional targets. Never calculate R as absolute target price divided by D.

Report R per labeled target. If an aggregate is needed, specify its exit-allocation and
fill weighting; a simple average TP is not automatically an actual exit plan.
For scaling, planned weighted entry is not proof all legs filled. Report filled-leg
metrics separately from hypothetical planned metrics.

## Monetary Risk and Execution R

Price distance is not currency risk or broker lots. Monetary risk requires quantity,
contract multiplier, quote/account currency conversion, costs, and instrument conventions.
Planned budget = account balance * risk_percent / 100 with an explicit valid risk bound.
For allocated legs, sum modeled monetary stop losses to the total budget; do not assign
the whole budget to every leg. Reject negative/invalid allocations and nonpositive equity.

Realized execution R = net observed execution PnL / declared initial monetary risk when
both are supported. Hypothetical replay R must be named accordingly. Declare whether
costs are included in initial risk. Never infer execution PnL from publisher messages alone.

## MFE and MAE

After a supported entry until the declared exit/evaluation horizon, define favorable
signed movement q * (P(t) - E). MFE is max(0, maximum signed movement); MAE is
max(0, maximum negative signed movement). Report price units and optionally divide by D
for R units. Specify observation granularity, quote side, feed, horizon, and cost treatment.
Exclude movement before entry. OHLC extrema after same-bar entry may belong before the
entry; use intrabar evidence or label those bounds ambiguous. Gaps imply incomplete bounds,
not exact extrema. Exposure-weighted scaling metrics require an explicit definition.

## Outcomes and Aggregate Statistics

Each statistic declares cohort, period, unit of analysis (signal, leg, or execution), feed,
policy/data version, total count, eligible/triggered count, evaluated count, unknown count,
ambiguous count, and exclusions. Not-triggered or unavailable signals are not losses/wins.

Win rate = wins / definitively evaluated win-or-loss cases under the declared definition.
Also disclose what fraction of the full cohort was definitively evaluated. Multi-target
events must not inflate the number of winning signals. Break-even and partial exits need
explicit classification. Profit factor, expectancy, cumulative PnL, drawdown, or Sharpe
require suitable net-return/exposure sequences and assumptions, not a list of R:R plans.
Report gross/net separately, sample sizes, and an appropriate uncertainty interval.
Zero denominator or insufficient evidence produces unavailable, not zero or infinity.

## Context Associations

Compare measured contemporaneous features with later outcomes only after the historical
context snapshot is frozen. Disclose cohort selection, missingness, sample size, tested
hypotheses, holdout policy, and multiple-comparison limitations. Associations do not imply
causation or stable future prediction; historical performance does not guarantee returns.

## Acceptance

Validate known BUY/SELL examples, per-target R, zero/invalid stops, costs/conversion,
scaled risk conservation, prefix invariance of context, post-entry excursions, partial
exits, ambiguous events, missing data, denominator changes, and nonfinite-value handling.
