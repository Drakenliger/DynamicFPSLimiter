# Current Status

## Repository

- Fork: `Drakenliger/DynamicFPSLimiter`
- Upstream: `SameSalamander5710/DynamicFPSLimiter`
- Default branch: `main`
- Status snapshot branch: `docs/review-baseline`
- Reviewed commit and branch point:
  `5f89c49a9e18612b4645bb46a3b6a6e875612e04`
- Current phase: review reconciliation and documentation baseline

## Completed

- The main-branch deep technical review is complete.
- Three independent P0 verification batches covering controller/hardware,
  RTSS/security, and lifecycle/Autopilot are recorded as complete.
- The three batches independently reverified 24 existing findings: 23 were
  Confirmed, while `RTSS-008` remained Medium / Likely because compatibility
  depends on the supported RTSS version and fractional-limit mechanism.
- The original 48 deep-review findings retain stable identifiers.
- Two additional findings were accepted: `HW-013` is High / Confirmed and
  `RTSS-009` is Low / Confirmed, producing a 50-item active ledger.
- `GUI-003` was upgraded to Medium / Confirmed for its inconsistent,
  unnormalized, case-sensitive process-identity design. Its Windows, RTSS, and
  Lossless Scaling manifestations remain environment-dependent and require
  runtime validation.
- No application code has changed and no fix has been released.

The three detailed verification reports under `review-input/codex-results/`
were local, ignored review inputs used to reconcile this documentation
baseline. They are not tracked in Git and are not required by a fresh clone.

The durable repository sources of truth are:

- `CURRENT_STATUS.md`
- `REVIEW_FINDINGS.md`
- `DECISIONS.md`
- `IMPLEMENTATION_PLAN.md`
- `TEST_PLAN.md`
- `RELEASE_NOTES.md`

## Release status

Not ready for unattended RX 7900 XTX or Autopilot use. Controller evidence can
be stale or backend-coupled, RTSS writes are not serialized or reversible, and
lifecycle races can permit stale generations to act.

No RTSS-version, RX 7900 XTX, or Lossless Scaling compatibility claim extends
beyond the statically reviewed baseline.

## Next work

Next implementation branch:

1. `test/controller-and-adapter-harness`

Following branches:

2. `fix/rtss-transaction-and-restore`
3. `fix/session-lifecycle`

The complete accepted order is maintained in `IMPLEMENTATION_PLAN.md`.

## Physical validation still required

- Stable RX 7900 XTX LHM hardware/sensor identities and RX 7000 power-sensor
  behavior.
- PDH LUID and engine attribution with Lossless Scaling.
- Supported RTSS versions, fractional denominator behavior, readback, and exact
  restoration.
- Cap-write timing, settle delays, and frametime effects.
- Game, Lossless Scaling, desktop, and launcher identity transitions.
- Long-uptime idle behavior, Win32 ABI behavior, driver/RTSS restart, sleep, and
  shutdown resilience.

## Documentation branch scope

These seven documentation files were prepared on
`docs/review-baseline` and introduced through pull request #1:

- `AGENTS.md`
- `CURRENT_STATUS.md`
- `REVIEW_FINDINGS.md`
- `DECISIONS.md`
- `IMPLEMENTATION_PLAN.md`
- `TEST_PLAN.md`
- `RELEASE_NOTES.md`

This branch contains documentation-only changes. No application source code has
changed, and no production fix has been implemented or released.
