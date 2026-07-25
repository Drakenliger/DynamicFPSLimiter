# Current Status

## Repository

- Fork: `Drakenliger/DynamicFPSLimiter`
- Upstream: `SameSalamander5710/DynamicFPSLimiter`
- Default branch: `main`
- Current branch: `fix/rtss-transaction-and-restore`
- Published Stage 1 head before the local documentation correction:
  `afd43e0373001a9f471573bbfb3535ae0b3c1ac3`
- Reviewed commit and branch point:
  `5f89c49a9e18612b4645bb46a3b6a6e875612e04`
- Current phase: draft PR #3 reviewed; documentation correction committed
  locally and awaiting separate review and push approval

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
- No controller-policy fix has been implemented or released.
- The `test/controller-and-adapter-harness` branch now contains a deterministic
  standard-library `unittest` suite, pure controller contracts, scripted
  adapters, an unwired cap-ladder validator, and characterization of the
  reviewed decrease selector.
- The production monitoring loop delegates decrease-cap selection to the
  characterized pure selector without changing the reviewed controller policy.
- `CTRL-001` and `CTRL-005` remain open. The former is characterized with its
  defect preserved; the latter has pure validation scaffolding that is not
  wired into startup or runtime.
- The automated-suite portion of `TEST-001` exists, but CI remains absent.
  `TEST-002` has initial deterministic clock, FPS/process, sensor, RTSS, and
  generation seams; production adapters and later controller work remain
  outstanding.
- RTSS Stage 1 contracts and deterministic tests are complete in local commit
  `42a4485c6d6b078d442e57061e745a2ea43e3d89`
  (`test: add deterministic RTSS transaction contracts`).
- The Stage 1 documentation snapshot was committed in
  `afd43e0373001a9f471573bbfb3535ae0b3c1ac3`
  (`docs: record RTSS Stage 1 completion`).
- Stage 1 corrected all six blocking independent-review findings:
  `S1-FINAL-001`, `S1-FINAL-002`, `S1-FINAL-003`, `S1-FINAL-004`,
  `S1-FINAL-002-R1`, and `S1-FINAL-003-R1`.
- Two independent read-only reviews were completed. The final independent
  review found no remaining Stage 1 blockers or regressions.
- The Stage 1 branch was pushed only to `Drakenliger/DynamicFPSLimiter`.
- Draft pull request #3 targets `main` from
  `fix/rtss-transaction-and-restore`. It is open, draft, and unmerged.
- Before this local documentation correction, the published PR contained two
  commits and 12 changed files at head
  `afd43e0373001a9f471573bbfb3535ae0b3c1ac3`.
- Publication and the independent PR review each completed with all 95
  deterministic unit tests passing. GitHub reported no automated checks.
- The independent PR review found no code or RTSS-safety merge blocker.
  `S1-DOC-001` was the only required pre-merge correction.
- `S1-DOC-001` is corrected by the current local documentation-only commit.
  That correction is not part of the remote branch or PR until a later
  explicitly approved push.
- `S1-READBACK-001`, `S1-TEST-001`, and `S1-DESIGN-001` are deferred Stage 2
  prerequisites and are not production-reachable in Stage 1.
- Stage 2 has not started. No production RTSS caller uses the Stage 1 contracts,
  and no production RTSS behavior changed.
- No physical RTSS, GPU, driver, game, GUI, LibreHardwareMonitor, PDH, or
  Lossless Scaling validation has been performed.

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

RTSS Stage 2 remains unstarted and blocked until all of these steps complete:

1. Review this local documentation-only correction and push it only with
   explicit approval.
2. Reverify draft PR #3 after the correction is published.
3. Merge PR #3 only after its review requirements are met.
4. Synchronize local `main` with the merged fork branch.

Stage 2 must begin on a new, focused branch based on that synchronized `main`.
Its deferred prerequisites and the complete accepted implementation order are
recorded in `IMPLEMENTATION_PLAN.md`.

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

The earlier `docs/review-baseline` branch contained documentation-only changes.
No application source code changed on that historical branch, and no production
fix was implemented or released there.

The published `fix/rtss-transaction-and-restore` branch and draft PR #3 contain
the Stage 1 contract/test commit
`42a4485c6d6b078d442e57061e745a2ea43e3d89` and documentation commit
`afd43e0373001a9f471573bbfb3535ae0b3c1ac3`. This documentation correction is
one additional local commit and is not published until a later explicitly
approved push. No production RTSS runtime behavior changed, and Stage 2 has not
started.
