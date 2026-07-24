# Implementation Plan

The sequence below is accepted for work after the review baseline
`5f89c49a9e18612b4645bb46a3b6a6e875612e04`. Each phase uses a focused branch
and draft pull request. Branch names describe scope; they do not imply work has
started.

## 1. `test/controller-and-adapter-harness`

**Objective:** Create deterministic seams and regression scaffolding without
changing production policy.

- **Included findings:** `TEST-001`, `TEST-002`, and test-first coverage for
  `CTRL-001` and `CTRL-005`.
- **Expected areas:** test layout and runner; cap-list/controller boundaries;
  fake clock, FPS, sensor, RTSS, profile, and lifecycle adapters; CI definition
  if approved.
- **Required tests:** pure cap selection; invalid profiles; deterministic
  controller traces; adapter contract tests; test discovery and isolation.
- **Explicit exclusions:** production policy changes; RTSS profile access;
  physical GPU dependencies; threshold tuning.
- **Dependencies:** none beyond the reviewed baseline.
- **Completion criteria:** tests run without RTSS, LHM, PDH, a physical GPU, or
  a game; P0/P1 fixtures can express time, failures, generations, and readback;
  existing behavior is characterized.
- **Manual validation:** test command works on the supported development
  environment; no external RTSS or sensor state changes.
- **Rollback:** remove only the added harness/seams and CI definition; production
  behavior remains unchanged.

## 2. `fix/rtss-transaction-and-restore`

**Objective:** Replace overlapping writers with one validated, serialized,
generation-aware, reversible RTSS boundary.

- **Included findings:** `RTSS-001` through `RTSS-009`, `SEC-002`, and the RTSS
  handshake portion of `RTSS-005`.
- **Expected areas:** RTSS interface/controller boundary; canonical profile
  identity; rational-cap validation; previous-state ownership; readback,
  rollback, restoration, and limiter-flag handling.
- **Required tests:** parser edge cases; path/name matrix; capability handling;
  transaction interleavings; partial failures; readback mismatch; prior cap,
  denominator, and flag restoration; created-profile and external-edit
  conflicts; generation rejection; idempotent flag operations.
- **Explicit exclusions:** controller thresholds; lifecycle worker rewrite;
  supported-version claims not backed by the physical matrix.
- **Dependencies:** phase 1 fakes and deterministic result assertions.
- **Completion criteria:** one write boundary owns every RTSS mutation; no
  startup mutation; callers receive structured verified results; failed
  applies do not advance logical state; owned state can be restored exactly or
  a durable degraded result is returned.
- **Manual validation:** disposable RTSS profiles across candidate versions,
  including Global/application, integer/fractional, flags, missing profiles,
  failures, restart, and external edits.
- **Rollback:** revert to the reviewed implementation only on a disposable test
  setup; preserve captured pre-test profiles and document any state whose
  restoration could not be verified.

## 3. `fix/session-lifecycle`

**Objective:** Establish one lifecycle owner with immutable session generations,
one-way cancellation, idempotent start/stop, and join-before-restart.

- **Included findings:** `THR-001` through `THR-005`.
- **Expected areas:** start/stop/shutdown ownership; monitoring and plotting
  workers; sensor worker admission; Autopilot/tray/GUI lifecycle intents; GUI
  dispatch; ordered shutdown.
- **Required tests:** duplicate start/stop; deterministic sleep barriers; stale
  generation rejection; cancellation before/after evaluation; no post-stop RTSS
  writes; bounded joins; ordered resource close; worker failure and timeout.
- **Explicit exclusions:** controller tuning; full profile/idle behavior change;
  hardware-specific sensor policy.
- **Dependencies:** phases 1 and 2, including a generation-aware RTSS API.
- **Completion criteria:** exactly one active session generation; repeated
  start/stop is idempotent; restart waits for prior joins/restoration; workers
  enqueue rather than directly own GUI state; Dear PyGui is destroyed last.
- **Manual validation:** rapid GUI/tray/Autopilot start/stop and exit stress on
  Windows, with generation, worker, and RTSS traces.
- **Rollback:** stop and restore the active session through the RTSS owner before
  reverting; retain diagnostics for any worker that missed its join deadline.

## 4. `fix/controller-validity-and-delays`

**Objective:** Correct cap selection and make decisions depend on validated,
fresh, confirmed evidence and verified writes.

- **Included findings:** `CTRL-001` through `CTRL-006` and controller-state
  aspects of `RTSS-005`.
- **Expected areas:** pure controller step; cap-list selection; immutable runtime
  profile validation; FPS/process freshness; confirmation, cooldown, warm-up,
  and settling states; sensor-role policy interface.
- **Required tests:** all cap-list boundaries; stale/missing/non-finite values;
  loading screens; sustained/spike/hysteresis traces; both direction delays;
  settle timing; CPU/GPU/safety roles; failed RTSS result leaves state unchanged.
- **Explicit exclusions:** final RX 7900 XTX thresholds; final CPU-bound policy
  before evidence; backend identity implementation.
- **Dependencies:** deterministic phase 1 seams, verified phase 2 results, and
  phase 3 session identity.
- **Completion criteria:** one pure decision path is deterministic; runtime
  configuration is validated before start; only current, healthy, confirmed
  evidence is eligible; logical cap changes only after verified apply.
- **Manual validation:** Windows controller traces with synthetic/fake adapters;
  physical timing values remain provisional until phase 9.
- **Rollback:** restore the prior verified RTSS state and revert controller
  policy independently of lifecycle/RTSS infrastructure.

## 5. `fix/lhm-identity-health`

**Objective:** Give LibreHardwareMonitor stable identity, atomic snapshots,
freshness/health, required-sensor quorum, recovery, and correct runtime
selection.

- **Included findings:** `HW-002`, `HW-003`, `HW-006`, `HW-007`, `HW-009`, and
  `HW-010`.
- **Expected areas:** LHM loader and runtime selection; hardware/sensor identity;
  discovery lifecycle; snapshot publication; poller recovery; sensor quorum.
- **Required tests:** identical-GPU identities; enumeration reorder; missing,
  stale, NaN, and infinite sensors; atomic snapshots; driver/re-enumeration
  recovery; missing required sensor veto; discovery resource closure; runtime
  selection.
- **Explicit exclusions:** final LHM version choice without packaged testing;
  PDH repair; RX 7900 XTX threshold tuning.
- **Dependencies:** phases 1, 3, and 4 snapshot/generation/controller contracts.
- **Completion criteria:** selected sensors use stable identities; publications
  are immutable, timestamped, and healthy; missing/stale required sensors cannot
  permit increases; discovery/poller resources close cleanly.
- **Manual validation:** packaged Windows runtime inspection and RX 7900 XTX
  identifier/recovery runs, including iGPU and driver reset scenarios.
- **Rollback:** keep prior LHM settings exportable; revert the LHM adapter without
  changing RTSS/lifecycle contracts.

## 6. `fix/backend-isolation-and-pdh`

**Objective:** Remove startup and decision coupling between selected sensor
backends, and repair or demote legacy PDH.

- **Included findings:** `HW-001`, `HW-004`, `HW-005`, `HW-008`, `HW-011`,
  `HW-012`, and `HW-013`.
- **Expected areas:** backend construction/lifecycle; PDH query and handle
  ownership; LUID identity/aggregation; health, freshness, reinitialization, and
  percentile calculation.
- **Required tests:** LHM start with PDH absent/zero; Legacy start with LHM
  absent; close-before-swap; no duplicate counters; counter loss clears health;
  full-LUID identity; multi-GPU aggregation policy; percentile boundaries;
  session/backend reset.
- **Explicit exclusions:** claiming PDH as a control-quality source before
  physical attribution; LHM sensor-policy redesign already covered in phase 5.
- **Dependencies:** phases 1, 3, and 5 backend/snapshot contracts.
- **Completion criteria:** only the selected backend is required for startup and
  controller eligibility; PDH owns and closes handles safely; stale data is
  invalid; unsupported attribution is explicitly diagnostic-only.
- **Manual validation:** LHM-only and Legacy-only starts; PDH handle-count and
  reinit stress; full-LUID mapping with RX 7900 XTX, iGPU, and Lossless Scaling.
- **Rollback:** disable PDH control eligibility and retain it as diagnostic-only
  if physical attribution or resource behavior fails acceptance.

## 7. `fix/profile-autopilot-idle`

**Objective:** Make profile switching, process identity, Autopilot, and idle
state transactional and generation-owned.

- **Included findings:** `GUI-001` through `GUI-006`.
- **Expected areas:** canonical process identity; immutable profile runtime;
  Autopilot selection; profile switch transaction; idle state; typed Win32 ABI;
  Quick Load defaults.
- **Required tests:** A -> B -> Global profile transitions; case/normalization
  identity; PSAPI/RTSS disagreement; idle enter/exit across switches; failed
  apply/restore; long-uptime arithmetic; pointer-sized handles and prototypes;
  first-run Quick Load.
- **Explicit exclusions:** changing RTSS capability policy; tuning idle or settle
  values without phase 9 evidence.
- **Dependencies:** phase 2 restoration, phase 3 lifecycle, phase 4 controller
  state, and current-generation sensor publications.
- **Completion criteria:** no iteration combines old and new profile state;
  process identity is canonical; idle owns the last verified active cap within
  one session/profile; Win32 calls have explicit ABI declarations.
- **Manual validation:** game A/game B/desktop/launcher/Lossless Scaling
  transitions; long-uptime Windows smoke; protected-process lookup behavior.
- **Rollback:** transactionally stop and restore the active profile before
  reverting; preserve per-profile settings backups.

## 8. `hardening/config-packaging-logging`

**Objective:** Harden persistence, privileged startup, artifact integrity, and
durable diagnostics.

- **Included findings:** `SEC-001`, `SEC-003`, `SEC-004`, `SEC-005`,
  `MAINT-001`, and `MAINT-004`.
- **Expected areas:** configuration persistence/recovery; installation and asset
  trust; pre-launch behavior; Task Scheduler invocation; dependency/release
  metadata; structured logs and worker diagnostics.
- **Required tests:** atomic configuration interruption/recovery; argument
  construction; integrity failures; no recursive MOTW removal; worker exception
  capture; bounded/rotating logs; no-console diagnostics.
- **Explicit exclusions:** new dependencies without approval; broad packaging
  rewrite; controller or hardware policy.
- **Dependencies:** stable lifecycle/error/result structures from prior phases.
- **Completion criteria:** persistence is recoverable; privileged inputs and
  assets have an explicit trust policy; worker failures are durable and
  actionable; packaging metadata is reproducible enough for acceptance.
- **Manual validation:** installed-build ACL and integrity audit; downloaded
  artifact/MOTW behavior; Task Scheduler create/query/delete; no-console fault
  exercise.
- **Rollback:** preserve last-known-good configuration and installer artifacts;
  provide a documented way to disable new hardening paths without weakening
  RTSS restoration.

## 9. `docs/rx7900xtx-acceptance`

**Objective:** Execute and document the physical acceptance matrix, resolve
version/tuning decisions, and align release documentation.

- **Included findings:** release evidence for every open hardware- or
  version-dependent finding, plus `MAINT-002` and `MAINT-003`.
- **Expected areas:** acceptance procedures/results; support matrix; controller
  traces; documentation, versions, dependencies, and release notes; disposition
  of invalid maintenance artifacts.
- **Required tests:** all automated suites from phases 1-8; Windows integration;
  supported RTSS matrix; physical RX 7900 XTX and Lossless Scaling matrix.
- **Explicit exclusions:** presenting planned behavior as shipped; expanding
  support claims beyond tested versions/configurations; unrelated feature work.
- **Dependencies:** all prior phases and explicit access to the target Windows
  hardware/software environment.
- **Completion criteria:** every P0/P1 finding is closed or explicitly deferred
  with accepted rationale; supported versions/configurations are named; exact
  restoration and lifecycle resilience pass; thresholds/delays are backed by
  traces; status and release notes match delivered behavior.
- **Manual validation:** the complete environment-tagged physical matrix in
  `TEST_PLAN.md`.
- **Rollback:** withdraw failed support claims, retain the last validated
  configuration, and reopen the associated finding rather than masking a failed
  acceptance result with tuning.
