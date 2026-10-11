# Signal Lifecycle

Status: target semantics; current runtime does not implement this complete state machine.
See [architecture](../ARCHITECTURE.md) and [data model](data-model.md).

## Separate Lifecycles

- Parsing: received -> pending -> extracted, partial/review, failed, or invalid.
- Signal revision: published -> revised or cancelled; original evidence remains immutable.
- Evaluation: ineligible/awaiting_entry -> triggered -> tracking -> terminal outcome,
  or unknown/ambiguous when evidence is insufficient.
- Execution: external submitted/fill/close evidence, if imported, is a separate lifecycle.
  This application does not submit orders.

Current `ParseStatus.SUCCESS` means parsing succeeded, not trading profit. Current
`SignalStatus` contains PENDING/ACTIVE/COMPLETED/CANCELLED/INVALID; future detailed
outcome states require explicit compatibility/migration. Do not silently replace enums
or equate status labels with analytical results.

## Eligibility and Revision Timing

A signal is eligible only after publication and availability under the declared replay
policy. Entry, SL, TP, expiry, and cancellation changes take effect only at their known
revision/event times. A later edit cannot improve the original historical signal.
Follow-ups require a reply/reference or other defensible linkage; ambiguity means review.
Source deletion does not erase collected evidence, subject to an approved retention policy.

## Entry and Tracking

MARKET needs the first eligible executable observation/fill, not an assumed publication
price. LIMIT and STOP use direction-aware trigger rules; entry-range and scaling policies
must specify fills and allocations. No targets, MFE/MAE, or realized R can be attributed
to an untriggered signal. An entry trigger and an executable fill are distinct evidence.

Each target touch, supported partial exit, SL, cancellation, expiry, and ambiguity event
has an event time, available time, source price basis, and assumption/evidence reference.
Multiple target hits are preserved even if one terminal summary is produced. Replaying
unchanged evidence must not append duplicate events.

## Terminal Classification

Use structured outcomes rather than a single overloaded success flag: not_triggered,
expired_before_entry, cancelled_before_entry, observed_target/stop/other_exit,
hypothetical_target/stop/other_exit, ambiguous, or insufficient_data.
Cancellation/expiry after entry requires a declared exit policy; it is not automatically
a flat-price close. Missing SL/TP makes associated metrics unavailable, not synthetic.
Missing coverage can invalidate terminal classification even if the observed path looks favorable.

## Persistence and Acceptance

Keep message revisions and analytical runs append-only where practical; uniqueness and
transactions must protect message/signal/run/event identity. Preserve source timestamp,
as-of revision, data version, and replay policy. Test entry-before-exit, delayed revisions,
same-bar collisions, duplicate events, post-entry cancellation, and unknown final outcomes.
See [backtesting rules](backtesting-rules.md) for ordering and fill evidence.
