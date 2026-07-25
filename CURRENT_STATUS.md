# Current Status

## Repository

- Fork: `Drakenliger/DynamicFPSLimiter`
- Upstream reference: `SameSalamander5710/DynamicFPSLimiter`
- Default branch: `main`
- Current local branch: `feature/rtss-transaction-coordinator`
- Current phase: RTSS Stage 2 planning
- Review baseline: `5f89c49a9e18612b4645bb46a3b6a6e875612e04`
- Stage 1 squash merge:
  `f8c4d4a2f7c6e1db39f3fd3c037ed98e07c39c95`
  (`Add deterministic RTSS transaction contracts (#3)`)

## Verified Stage 1 merge state

On 25 July 2026, the repository and fork were independently checked before
this planning branch was created:

- local `main`, `origin/main`, and the initial `HEAD` all resolved to
  `f8c4d4a2f7c6e1db39f3fd3c037ed98e07c39c95`;
- local `main` was zero commits ahead of and zero commits behind
  `origin/main`;
- pull request #3 in `Drakenliger/DynamicFPSLimiter` was merged into `main`;
- GitHub reported the PR #3 merge commit as
  `f8c4d4a2f7c6e1db39f3fd3c037ed98e07c39c95`;
- the repository was clean and the index was empty;
- no local or `origin` branch named
  `feature/rtss-transaction-coordinator` existed; and
- the existing Stage 1 branch `fix/rtss-transaction-and-restore` was not
  switched to, reused, reset, deleted, or modified.

Only `origin` was fetched and queried. The upstream repository was not
contacted.

The deterministic command
`python -m unittest discover -s tests -t . -v`, with
`PYTHONDONTWRITEBYTECODE=1`, passed all 95 tests before this planning branch was
created. The repository remained clean and contained no `__pycache__`, `.pyc`,
or `.pyo` artifacts.

## Current work

RTSS Stage 1 is complete and merged. It provides deterministic identity,
rational-cap, generation, capability, capture, readback, apply, restoration,
ownership, evidence, and result contracts with deterministic tests.

RTSS Stage 2 planning has started on
`feature/rtss-transaction-coordinator`. Stage 2 source implementation has not
started. No transaction coordinator exists, and no production caller uses the
Stage 1 contracts.

The current planning task changes exactly:

- `CURRENT_STATUS.md`;
- `IMPLEMENTATION_PLAN.md`; and
- `TEST_PLAN.md`.

It does not change production source, tests, configuration, workflows, ignored
review inputs, or external state. The branch is local only: no Stage 2 push,
remote branch, configured upstream for this branch, or pull request exists.

## Design-review status

The Stage 2 design review preserves the Stage 1 contract layer while planning
the focused prerequisites and extensions required by a deterministic
coordinator:

- correct `S1-READBACK-001` by restricting `RtssReadback` to read-only
  outcomes and failure steps;
- correct `S1-TEST-001` with an exhaustive readback outcome/failure-step
  acceptance and rejection matrix;
- correct `S1-DESIGN-001` with capability-driven DLL-name and derived-profile
  component limits;
- add exact stored numerator and denominator capture because the existing
  reduced `RationalCap` represents the effective value but cannot alone prove
  representation-exact restoration;
- add explicit transaction identity/admission around immutable Stage 1
  requests so duplicates and concurrent writers can be rejected; and
- keep deterministic coordination separate from later live DLL, profile-file,
  GUI, lifecycle, and production-caller integration.

These items are planned only. They are not implemented, tested, closed, or
production-reachable.

The tracked ledger identifies `S1-FINAL-005`, `S1-FINAL-006`, and
`S1-FINAL-007` only as deferred, non-blocking items and does not retain their
root-cause or acceptance text. This planning task therefore does not invent or
silently close them. Each remains deferred test-maintenance/provenance cleanup
until an independent review supplies durable definitions; any item then shown
to affect coordinator correctness must be promoted into a separately reviewed
Stage 2 prerequisite.

## Production status

The existing production RTSS paths remain unchanged and unsafe for unattended
use:

- `RTSSController` exposes separate, unserialized profile loads, property
  reads/writes, saves, updates, direct profile-file rewrites, deletion, and
  global flag mutation;
- application startup unconditionally enables the RTSS limiter;
- start and stop both initiate cap writes;
- the monitoring loop performs overload, headroom, idle-entry, and idle-exit
  writes and advances logical cap state before write verification;
- exit may write the Global cap without a captured prior state or verified
  restoration;
- profile deletion is initiated directly by `ConfigManager`; and
- Autopilot and monitoring profile changes are not transactional or
  generation-owned.

No physical RTSS, profile-file, Windows runtime, GPU, driver, game, GUI,
LibreHardwareMonitor, PDH, registry, or Lossless Scaling validation was
performed. No supported RTSS-version, RX 7900 XTX, or Lossless Scaling
compatibility claim is made.

## Release status

Not ready for unattended RX 7900 XTX or Autopilot use. Controller evidence can
be stale or backend-coupled, RTSS writes are not serialized or reversible, and
lifecycle races can permit stale generations to act.

No RTSS-version, RX 7900 XTX, or Lossless Scaling compatibility claim extends
beyond the statically reviewed baseline.

## Next action and gates

The next action is an independent, read-only review of the local planning
commit.

Stage 2 implementation, any push, and pull-request creation remain blocked
pending that review. A later implementation task must use small, independently
reviewable commits and must not wire production callers in the first
coordinator implementation commit.

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

## Historical documentation scope

The seven durable project documents were introduced through pull request #1:

- `AGENTS.md`;
- `CURRENT_STATUS.md`;
- `REVIEW_FINDINGS.md`;
- `DECISIONS.md`;
- `IMPLEMENTATION_PLAN.md`;
- `TEST_PLAN.md`; and
- `RELEASE_NOTES.md`.

The Stage 1 branch and pull request #3 added the deterministic RTSS contracts,
tests, and synchronized documentation. PR #3 is now merged; its final squash
commit is
`f8c4d4a2f7c6e1db39f3fd3c037ed98e07c39c95`. Production RTSS behavior did not
change in Stage 1.
