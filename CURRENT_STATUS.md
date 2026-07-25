# Current Status

## Repository

- Fork: `Drakenliger/DynamicFPSLimiter`
- Upstream reference: `SameSalamander5710/DynamicFPSLimiter`
- Default branch: `main`
- Current local branch: `feature/rtss-transaction-coordinator`
- Current phase: RTSS Stage 2 planning correction review
- Review baseline: `5f89c49a9e18612b4645bb46a3b6a6e875612e04`
- Stage 1 squash merge:
  `f8c4d4a2f7c6e1db39f3fd3c037ed98e07c39c95`
  (`Add deterministic RTSS transaction contracts (#3)`)
- Stage 2 planning baseline:
  `7adfb5406b091ccd8c55872fc1b75036029fee8a`
  (`docs: begin RTSS Stage 2 planning`)
- First Stage 2 planning correction:
  `15a3774eb0ff10741e6684bf3414b4fdde61ae72`
  (`docs: address RTSS Stage 2 planning review`)

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

## Independent Stage 2 planning review

The local planning commit
`7adfb5406b091ccd8c55872fc1b75036029fee8a` changed exactly:

- `CURRENT_STATUS.md`;
- `IMPLEMENTATION_PLAN.md`; and
- `TEST_PLAN.md`.

An independent read-only review of that commit completed on 25 July 2026. Its
result was **Approved after specified documentation corrections**. During the
review, all 95 deterministic tests passed, the worktree and index remained
clean, and no cache or bytecode artifacts were produced.

The review confirmed that no Stage 2 source implementation exists, no
production caller uses the Stage 1 contracts, and no remote Stage 2 branch,
configured branch upstream, push, or pull request exists.

The accepted correction-required blockers are:

- `S2-DEGRADED-001`;
- `S2-NAME-001`;
- `S2-SEQUENCE-001`; and
- `S1-PROVENANCE-001`.

The smaller required corrections are:

- `S2-STATUS-001`;
- `S2-INVENTORY-001`; and
- `S2-DECISION-001`.

Correction commit `15a3774eb0ff10741e6684bf3414b4fdde61ae72` addressed those
findings; its second independent-review disposition is recorded below.

## Second independent Stage 2 correction review

The first documentation correction,
`15a3774eb0ff10741e6684bf3414b4fdde61ae72`, received a second independent,
read-only review on 25 July 2026. The review recommendation was **Not approved;
further correction required**. All 95 deterministic tests passed during that
review.

The second review found these findings fully corrected:

- `S2-NAME-001`;
- `S1-PROVENANCE-001`;
- `S2-STATUS-001`; and
- `S2-DECISION-001`.

It found these findings only partially corrected:

- `S2-DEGRADED-001`, because degraded results and handoffs did not yet bind all
  identity and generation evidence explicitly;
- `S2-SEQUENCE-001`, because the first mutation-bearing Stage 5 slice was not
  concretely bounded; and
- `S2-INVENTORY-001`, because the non-default `update=True` path and its two
  update activations were not recorded.

The subsequent documentation correction addresses those three remaining
planning items. It must still receive another independent, read-only review and
must not be treated as independently verified or accepted. Stage 2
implementation remains blocked. No Stage 2 source implementation, production
integration, remote branch, configured branch upstream, or pull request exists.

## Current work

RTSS Stage 1 is complete and merged. It provides deterministic identity,
rational-cap, generation, capability, capture, readback, apply, restoration,
ownership, evidence, and result contracts with deterministic tests.

RTSS Stage 2 planning, the first planning correction, and both independent
reviews are recorded on `feature/rtss-transaction-coordinator`. Stage 2 source
implementation has not started. No transaction coordinator exists, and no
production caller uses the Stage 1 contracts.

The initial local Stage 2 planning commit changed exactly:

- `CURRENT_STATUS.md`;
- `IMPLEMENTATION_PLAN.md`; and
- `TEST_PLAN.md`.

The follow-up corrections are documentation-only and limited to:

- `CURRENT_STATUS.md`;
- `REVIEW_FINDINGS.md`;
- `IMPLEMENTATION_PLAN.md`; and
- `TEST_PLAN.md`.

They do not change production source, tests, configuration, workflows, ignored
review inputs, or external state. The branch remains local only: no Stage 2
push, remote branch, configured upstream for this branch, or pull request
exists.

## Design-review status

**Proposed Stage 2 design pending independent verification and explicit
acceptance.**

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
- require immutable degraded-state accounting for every unresolved owned field,
  save/update uncertainty, backend epoch, retained ownership, unavailable or
  unreadable evidence, and external conflicts;
- distinguish always-invalid lexical/path forms from capability-dependent,
  exactly encoded supported names, with non-ASCII rejected by default;
- add explicit transaction identity/admission around immutable Stage 1
  requests so duplicates and concurrent writers can be rejected; and
- keep deterministic coordination separate from later live DLL, profile-file,
  GUI, lifecycle, and production-caller integration.

These items and their tests are planned only. They are not implemented, tested,
closed, or production-reachable.

The tracked ledger identifies `S1-FINAL-005`, `S1-FINAL-006`, and
`S1-FINAL-007` only as deferred identifiers and does not retain their
root-cause or acceptance text. No technical allocation or closure is permitted
without provenance recovery. They are not treated as coordinator prerequisites
unless recovered evidence proves that they are. Any recovered requirement must
be added to durable tracked documentation and receive appropriate regression
coverage before disposition; ignored local reports must never be required by a
fresh clone.

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

The next action is an independent, read-only review of the additional local
documentation correction that addresses the three remaining partial Stage 2
planning-review findings.

Stage 2 implementation remains blocked pending that correction review and
explicit user acceptance of the corrected plan. Any push and pull-request
creation remain separately blocked and require explicit approval. A later
implementation task must use small, independently reviewable commits, may not
admit mutation before its complete applicable rollback and degraded-state
handling exist, and must keep production callers out of the coordinator phase.

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
