# Implementation Plan

The sequence below is accepted for work after the review baseline
`5f89c49a9e18612b4645bb46a3b6a6e875612e04`. Each phase uses a focused branch
and draft pull request. Branch names describe scope; they do not imply work has
started.

## RTSS Stage 1 gate - complete

Pull request #3, `Add deterministic RTSS transaction contracts`, is merged into
`Drakenliger/DynamicFPSLimiter:main` as squash commit
`f8c4d4a2f7c6e1db39f3fd3c037ed98e07c39c95`. Before Stage 2 planning began,
local `main` and `origin/main` were independently verified at that commit with
zero divergence, a clean worktree, and an empty index. The existing
deterministic suite passed all 95 tests without cache or bytecode artifacts.

Stage 1 is therefore complete. It remains preparatory infrastructure: no
production RTSS caller uses its contracts.

## RTSS Stage 2 coordinator plan

### Planning state and boundary

Planning is active on local branch
`feature/rtss-transaction-coordinator`. Coordinator source, contract
corrections, fakes, and tests are not implemented. The branch has not been
pushed and no Stage 2 pull request exists.

Stage 2 implements a deterministic coordinator and its required contract
prerequisites. It does not wire `DFL_v5.py`, `rtss_functions.py`,
`config_manager.py`, Autopilot, Dear PyGui, lifecycle workers, or live RTSS.
Those changes belong to a later production-integration phase after the
coordinator is independently reviewed.

### Design goals and invariants

The coordinator must enforce these invariants:

1. One canonical, case-insensitive application/profile identity is admitted
   before any backend call.
2. Application, session, profile, and backend generations are checked before
   capture, immediately before the first mutation, and before accepting
   readback or restoration.
3. Request structure, policy, capabilities, and the intersection of configured
   and backend ranges are validated before state capture or mutation.
4. DLL names and derived profile filenames are single validated components
   whose byte/character limits come from explicit capabilities, not guessed
   RTSS constants.
5. Traversal, rooted, drive-relative, UNC, device, alternate-data-stream,
   separator, reserved-name, trailing-dot/space, control-character, lossy
   encoding, and containment failures are rejected.
6. Every mutation has an exact pre-mutation capture, including profile
   existence, stored numerator, stored denominator, effective rational cap,
   owned limiter bits, backend generation, and required document/revision
   evidence.
7. A profile created by a transaction is session-owned and exact restoration
   deletes it and verifies absence.
8. All loaded-profile operations and all global limiter-flag operations pass
   through one serialization boundary.
9. Cap arithmetic and comparison use integers and exact rationals only; no
   float conversion is permitted.
10. A successful or no-change result requires exact readback. The controller
    may advance logical state only after receiving a verified apply result.
11. Failure before mutation is distinct from failure after mutation. Any
    possible partial mutation triggers rollback unless cancellation or backend
    loss makes rollback impossible, in which case the result is durably
    degraded.
12. Exact restoration verifies every owned field. Partial restoration reports
    all unresolved owned limiter bits plus the cap, profile, document, and
    revision uncertainty that remains.
13. Duplicate commands, concurrent writers, stale generations, and stale
    ownership tokens are rejected before mutation.
14. Restore, stop, cancellation, and ownership release are idempotent.
15. Coordinator behavior and operation ordering are deterministic without
    RTSS, Windows, a GPU, a game, a GUI, LHM, PDH, or Lossless Scaling.

### Proposed interfaces

The implementation should keep these explicit boundaries:

| Boundary | Responsibility |
| --- | --- |
| `RtssIdentityCapabilityPolicy` | Canonical identity admission, supported-name rules, resolved denominator policy, configured/backend range intersection, and capability-driven DLL/profile component limits. |
| `RtssCapabilitySource` | Return immutable capabilities and the current backend generation without choosing an unsupported version or mechanism. |
| `RtssStateReader` | Read profile existence, exact stored numerator/denominator, effective cap, owned flags, document evidence, revision evidence, and verified absence. |
| `RtssProfileMutator` | Load/create/delete one admitted profile and mutate exact cap fields or owned flag bits without saving or activating implicitly. |
| `RtssActivationPort` | Save the loaded profile and request RTSS profile activation/update as separately injectable operations. |
| `RtssReadbackPort` | Perform an exact post-save/update readback with backend-generation evidence. |
| `RtssLifecycleAdmission` | Admit current application/session/profile/backend generations, cancellation state, profile ownership, and ownership transfer. |
| `RtssTransactionCoordinator` | Serialize apply/restore, reject duplicates, enforce phase ordering, classify failures, invoke rollback, retain or release ownership, and return structured results. |
| Controller-facing port | Accept immutable commands and return `RtssApplyResult` or `RtssRestoreResult`; expose no GUI or monitoring state. |
| Deterministic fake backend | Model loaded-profile semantics, profiles, flags, revisions, document bytes, backend restarts, barriers, operation logs, false returns, and exceptions. |
| Event sink | Record transaction identity, generation, phase, reason, evidence summary, result, and degradation without affecting control flow. |
| Later production adapters | Translate the boundaries to supported RTSS DLL/profile mechanisms and integrate application callers only after separate review. |

The coordinator may use a wrapper command containing the Stage 1
`RtssApplyRequest` plus an immutable transaction identifier. This avoids
overloading the Stage 1 request while allowing in-flight and completed duplicate
rejection.

### Required Stage 1 prerequisites and focused contract extensions

The first implementation work must be contract/test-only:

- `S1-READBACK-001`: define an explicit read-only outcome/failure-step table
  for `RtssReadback`. Mutation-only outcomes such as
  `FAILED_ROLLED_BACK` and mutation/rollback-only steps must be rejected.
- `S1-TEST-001`: add an exhaustive acceptance/rejection matrix over every
  `RtssOutcome` and `RtssFailureStep`, with a fail-closed assertion when either
  enum changes.
- `S1-DESIGN-001`: introduce explicit capability fields and policy checks for
  DLL-name byte length and derived-profile-filename component length, including
  exact boundary tests.
- Add representation-exact stored numerator and denominator evidence to
  capture/readback planning. `RationalCap` deliberately reduces equivalent
  values, so it proves effective-cap equality but cannot by itself prove exact
  restoration of a prior stored pair such as `120/2`. Any contract extension
  must retain the effective `RationalCap` and add, rather than infer, stored
  representation.
- Add structured unresolved-state accounting for cap/profile/document/revision
  fields alongside the existing exact `unrestored_flag_mask`, unless an
  independent review demonstrates that the current restore result expresses
  every durable degraded state without ambiguity.

These corrections require focused regression tests and independent review
before coordinator logic relies on them.

### Capability and supported-name policy

The policy receives both configured safety bounds and observed backend
capabilities. It computes their intersection for:

- numerator and denominator integer ranges;
- numerator and denominator bit widths;
- effective-cap minimum/maximum and inclusivity;
- supported denominator strategies;
- exact readback, flag read/write, document, revision, create, and delete
  support; and
- DLL-name and profile-filename component limits.

An empty intersection is `UNSUPPORTED_CAPABILITY`; an unresolved mechanism is
`POLICY_REQUIRED`. The policy must not silently fall back from an API strategy
to profile-file editing.

Name admission first validates `CanonicalProfileIdentity`, then derives the DLL
name and relative profile filename, then checks capability limits and lexical
containment under an abstract profiles root. Both raw input and derived names
are rejected for `/`, `\`, rooted or drive-relative forms, UNC/device prefixes,
ADS colons, dot components, reserved Windows stems, controls, trailing
dot/space, unsupported encoding, or a resolved target outside the admitted
root. Reparse-point enforcement belongs to the later filesystem adapter, but
the deterministic policy and fake model must express containment failure.

### Transaction phase ordering

One apply transaction proceeds in this exact logical order:

1. Allocate/admit the immutable transaction identifier; reject a duplicate or
   an already-owned conflicting profile.
2. Check cancellation and application/session/profile generations.
3. Canonicalize and admit identity and the derived adapter targets.
4. Read capabilities and backend generation.
5. Validate the request, denominator strategy, owned flag intent, component
   limits, and the complete capability-range intersection.
6. Acquire the coordinator serialization lease.
7. Recheck cancellation and every generation after waiting for the lease.
8. Load/read without mutation and capture profile existence, exact stored
   numerator/denominator, effective cap, owned limiter bits, document bytes or
   approved immutable digest, revision, and verified absence as applicable.
9. Validate capture completeness, profile-creation permission, and the
   backend generation; establish created-profile and flag ownership.
10. Recheck cancellation/generations immediately before the first mutation.
11. If exact capture already equals the request, perform exact readback and
    return a verified no-change result without save or update.
12. Apply only the required changes in deterministic order: create/load the
    profile if authorized, set exact numerator, set exact denominator, and set
    only owned limiter bits.
13. Save the admitted profile.
14. Request update/activation.
15. Read back profile existence, stored numerator/denominator, effective cap,
    owned flags, document/revision evidence, and backend generation.
16. Compare exact requested state and return `VERIFIED`; only then may a
    controller commit logical cap state. Retain session ownership needed for
    later restore.
17. On any false return, exception, cancellation, stale generation, backend
    restart, or mismatch after possible mutation, run rollback while still
    holding serialization.
18. Rollback restores the complete captured document or exact fields according
    to the approved mechanism, restores only owned limiter bits, saves,
    updates, and performs exact readback. A transaction-created profile is
    deleted and verified absent.
19. Return `FAILED_ROLLED_BACK` only after exact verified restoration;
    otherwise return a durable `DEGRADED`, `CONFLICT`, or
    `UNSUPPORTED_CAPABILITY` result with complete unresolved ownership.
20. Release the serialization lease. Release profile/session ownership only
    after verified restore or an explicit durable degraded handoff.

A normal restore uses the same serialized capture-conflict, mutation,
save/update, and exact-readback phases. Repeated restore after verified release
returns an idempotent verified no-change/released result and performs no
mutation.

### Generation, cancellation, and ownership model

- Application generation changes on application-level reinitialization.
- Session generation is immutable for one start/stop ownership interval.
- Profile generation changes on every transactional profile switch.
- Backend generation changes on RTSS adapter initialization or detected RTSS
  restart.
- A transaction admission snapshot contains all four dimensions plus canonical
  profile identity and a cancellation token.
- Backend generation is compared with capability, capture, mutation admission,
  and readback evidence; a change before mutation rejects the request, while a
  change after possible mutation produces rollback or a durable degraded
  result.
- Ownership is keyed by canonical profile identity and session/profile
  generation. Created-profile ownership and owned limiter bits are explicit.
- A profile switch restores and releases A before B can acquire ownership.
  Transfer is never inferred from GUI selection.
- Cancellation is one-way. Each deterministic phase has a barrier and a
  cancellation check. Cancellation before mutation is state-free; cancellation
  after possible mutation enters rollback.
- Stop waits for the in-flight transaction to resolve, then invokes idempotent
  restore. Repeated stop cannot create another mutation.

### Apply, rollback, restore, and conflict transitions

- `VERIFIED`: exact requested state or exact verified no-change.
- `REJECTED_VALIDATION`, `STALE_GENERATION`, `UNSUPPORTED_CAPABILITY`, or
  `POLICY_REQUIRED`: pre-capture/state-free rejection.
- `FAILED`: pre-mutation failure, or post-mutation failure only when exact
  readback proves the captured state never changed.
- `FAILED_ROLLED_BACK`: possible mutation followed by exact verified
  restoration.
- `CONFLICT`: external revision/document change for which policy forbids
  overwrite.
- `DEGRADED`: possible mutation with incomplete rollback, missing verification,
  backend-generation loss, or unresolved owned state.

External edits are detected by comparing captured and current revision/document
evidence before destructive restoration. The default safe planning assumption
is fail closed and report `CONFLICT`; whether stop may merge or overwrite any
externally edited field remains an unresolved policy decision.

### Serialization and duplicate prevention

The deterministic coordinator owns one fair process-local lock for every
loaded-profile/property/save/update sequence and for global flag access.
Per-profile locks alone are insufficient because the current DLL property APIs
operate on whichever profile was most recently loaded, and limiter flags are
global.

The admission registry tracks in-flight transaction IDs, completed IDs,
canonical profile owners, and backend generation. A repeated in-flight or
completed transaction ID returns a structured rejection and never replays a
mutation. Concurrent requests for the same or different profiles serialize;
after lock acquisition each request revalidates generations and ownership.

Cross-process writers cannot be prevented by this coordinator alone. Revision
and document conflict evidence must detect them. Whether a supported
production adapter can provide a stronger RTSS-wide lock remains a later
integration decision.

### Deterministic fake and failure-injection design

The fake backend must:

- model Global, existing, absent, and transaction-created profiles;
- model RTSS shared loaded-profile semantics and global flags;
- retain exact stored numerator/denominator separately from the reduced
  effective cap;
- expose immutable capabilities and incrementable backend generation;
- retain complete document bytes/digests, revisions, and verified absence;
- append every operation and argument to an ordered log;
- inject false returns or exceptions at capability, load, each capture field,
  create, numerator write, denominator write, flag read/write, save, update,
  readback, restore, delete, and verification;
- expose deterministic barriers at admission, capture, pre-mutation, each
  mutation, save, update, readback, rollback, and release;
- inject cancellation, external edits, backend restart, and generation changes
  at every barrier; and
- assert no unplanned operation occurred after a terminal result.

No fake should import or simulate Dear PyGui, PDH, LHM, GPU, game, or Lossless
Scaling behavior.

### Production RTSS call-site inventory

The current production call sites remain unchanged in Stage 2:

| File and symbol | Trigger and current ordering | Current identity/state behavior | Allocation |
| --- | --- | --- | --- |
| `src/core/rtss_functions.py:RTSSController.get_profile_property` | Loads a supplied ASCII name, then reads one property. | Empty string represents Global; no canonical admission, serialization, generation, document/revision evidence, or compound read consistency. | Later production read/capture adapter. |
| `RTSSController.set_profile_property` | Load -> set -> save -> optional update. | Raw caller name; ignores save/update verification and returns only the property-set Boolean; no capture or rollback. | Later production mutation/activation adapter behind the coordinator. |
| `RTSSController.create_profile` | Load Global -> set properties -> save under raw name -> update. | No component/containment validation, capture, ownership, per-property result check, or readback. No active production caller was found. | Later production create adapter; coordinator owns authorization and restoration. |
| `RTSSController.delete_profile` and `ConfigManager.delete_selected_profile_callback` | GUI configuration deletion directly calls DLL deletion. | Raw GUI/config section name; no update/readback, generation, created-profile ownership, or restoration policy. | Later profile-management integration, using coordinator ownership rules. |
| `RTSSController.reset_profile` | Direct DLL reset. | Raw identity and no verification; no active production caller was found. | Exclude until a later adapter plan proves a safe use. |
| `RTSSController.set_limit_denominator` | Build `Profiles/<name>.cfg` -> read lines -> rewrite file -> optional update. | Raw path component, non-atomic complete-file rewrite, no capture/revision/containment/readback. | Later profile-file adapter only if the supported-version decision approves it. |
| `RTSSController.set_fractional_framerate` | Float-derived numerator/denominator -> optional file denominator write -> DLL cap write/save -> update. | Raw identity, float conversion, split mechanisms, ignored failure, no exact readback or rollback. | Later composition adapter; do not reuse as coordinator logic. |
| `RTSSController.set_fractional_fps_direct` | Directly read/rewrite `Limit` and `LimitDenominator` -> optional update. | Raw path component, direct non-atomic file edit, no complete prior capture or verification; current local variables also permit a pre-write failure. | Later profile-file adapter or removal after capability decision. |
| `RTSSController.get_framerate_limit` | DLL numerator read, optional profile-file denominator read, then float division. | Split, non-atomic evidence and lossy effective cap; no active production caller was found. | Later exact state-reader adapter, replaced rather than reused as-is. |
| `RTSSController.enable_limiter` from `DFL_v5.py` module startup | Set global flags -> update during application opening. | Unconditional global mutation with no prior flag capture, session owner, exact readback, or restoration. | Later startup integration; startup mutation must be removed or transaction-owned. |
| `RTSSController.disable_limiter` / `set_flags` | Direct global flag mutation and optional update. | `disable_limiter` toggles bit 4; no active production caller was found and `GetFlags` is not bound. | Stage 2 models owned bits; later production flag adapter must be idempotent and capability-verified. |
| `DFL_v5.py:start_stop_callback` | Toggles `running`, starts/stops workers, resets logical state, then always performs a direct file write followed by the API writer. | Uses mutable `cm.current_profile`; no previous-state capture or result check; writes on both start and stop. | Later lifecycle/production integration. |
| `DFL_v5.py:monitoring_loop` overload/headroom paths | Updates `CurrentFPSOffset` before invoking the writer. | Mutable profile and controller globals; no generation admission or acknowledgment, so controller state advances before verification. | Later controller and production integration; coordinator returns verified results first. |
| `DFL_v5.py:monitoring_loop` idle enter/exit | Saves `last_active_fps_cap` locally and writes idle/active caps. | State can cross profile transitions; no capture, ownership, verification, or restore. | Later profile/idle/controller integration. |
| `DFL_v5.py:exit_gui` | Sets stop flags, optionally writes a configured Global cap, then closes resources/GUI. | Not restoration of captured state; no join-before-write, generation, readback, or failure result. | Later lifecycle/exit integration. |
| `DFL_v5.py` and `autopilot.py` profile switches | GUI/config selection changes while monitoring; later iterations or start callback initiate writes. | Case-sensitive mutable names; profile A is not restored before B becomes current; no ownership transfer. | Later profile-switch and Autopilot integration. |

No other tracked production mutation initiator was found. `rtss_interface.py`
reads RTSS shared-memory FPS/process data but does not mutate profiles.

### Stage 2 versus later integration allocation

Stage 2 coordinator implementation includes:

- the three named Stage 1 prerequisites;
- narrowly reviewed stored-representation and degraded-state contract
  extensions required for exact restoration;
- pure identity/capability policy;
- lifecycle/ownership admission contracts;
- deterministic serialized apply, no-change, rollback, restore, cancellation,
  duplicate, and conflict coordination;
- controller-facing structured results;
- coordinator-specific fakes and failure-injection tests; and
- no physical RTSS requirement.

Later production RTSS integration includes:

- choosing supported RTSS versions and denominator mechanisms from evidence;
- live DLL bindings, exact flags support, and any approved profile-file
  implementation;
- reparse-aware filesystem containment and atomic complete-document
  replacement;
- wiring all production call sites listed above;
- startup, stop, exit, idle, profile-switch, and Autopilot behavior;
- cross-process conflict behavior available from actual RTSS mechanisms; and
- Windows disposable-profile and supported-version validation.

Production-caller modification is prohibited in the first Stage 2
implementation commit unless a later independently reviewed plan explicitly
authorizes it.

### Deferred Stage 1 items

`S1-READBACK-001`, `S1-TEST-001`, and `S1-DESIGN-001` are mandatory Stage 2
coordinator prerequisites.

The durable tracked ledger gives no root-cause, location, or acceptance text
for `S1-FINAL-005`, `S1-FINAL-006`, or `S1-FINAL-007`; it records only that
they are deferred and non-blocking. All three remain allocated to deferred
test-maintenance/provenance cleanup until independent review supplies their
definitions. They are not silently closed. If recovered evidence shows that
one affects coordinator correctness, it must be promoted to the Stage 2
coordinator implementation through a focused plan correction; production
adapter, controller, or integration concerns remain in their corresponding
later phases.

### Unresolved decisions

Independent review or later physical evidence must still decide:

- supported RTSS versions and capability discovery;
- API denominator support versus a profile-file mechanism;
- concrete DLL-name and profile-filename component limits for each supported
  capability set;
- which immutable document digest schemes, if any beyond complete bytes and
  SHA-256, are approved;
- whether and how stop handles external edits, including merge, refuse, or
  explicitly authorized overwrite;
- how durable degraded ownership survives process restart;
- whether RTSS exposes a usable cross-process serialization or revision token;
- whether deletion and exact absence can be verified by every supported
  backend;
- backend restart recovery and whether ownership can be safely reacquired; and
- whether the existing result contracts need explicit non-flag unresolved
  ownership fields.

No Stage 2 plan selects an RTSS version, fractional mechanism, overwrite policy,
or compatibility claim.

### Proposed small implementation commits

1. `test: close RTSS readback and name-policy prerequisites`
   - implement `S1-READBACK-001`, `S1-TEST-001`, and `S1-DESIGN-001` with
     exhaustive matrices and component-boundary tests.
2. `test: model exact RTSS capture and transaction admission`
   - add stored numerator/denominator evidence, transaction identity,
     ownership/admission contracts, and focused regression tests.
3. `test: add deterministic RTSS coordinator fakes`
   - add ordered operation logs, barriers, generation/restart controls, and
     false/exception injection without coordinator behavior.
4. `feat: coordinate verified RTSS apply transactions`
   - implement admission, serialization, exact capture, no-change, mutation,
     save/update, readback, and structured results.
5. `feat: coordinate RTSS rollback and restoration`
   - add partial-failure rollback, exact restore, created-profile deletion,
     conflict handling, degraded accounting, cancellation, and idempotent
     ownership release.
6. `docs: record RTSS Stage 2 coordinator review`
   - update durable status, findings/decisions if independently accepted, test
     results, limitations, and later integration gate.

Each commit requires the complete deterministic suite and an independent
read-only scope/design review before the next behavior-bearing commit.

### Explicit exclusions

- No production caller changes.
- No live DLL, profile-file, registry, GUI, lifecycle-thread, LHM, PDH, GPU,
  game, or Lossless Scaling interaction.
- No dependency installation or new dependency.
- No controller policy, cap-ladder, threshold, confirmation, or settling
  change.
- No RTSS-version, RX 7900 XTX, or Lossless Scaling compatibility claim.
- No silent fallback or external-edit overwrite policy.

### Completion criteria and review gates

Stage 2 coordinator implementation is complete only when:

- every admitted mutation is serialized and exact-state captured;
- all four generation dimensions and cancellation are enforced at the defined
  barriers;
- duplicate and concurrent writes are deterministically rejected or
  serialized;
- all operation false/exception paths have deterministic tests;
- apply success and no-change require exact readback;
- partial mutation always produces exact verified rollback or complete durable
  degraded accounting;
- created profiles and owned limiter bits restore exactly;
- repeated restore/stop is idempotent;
- controller-facing results cannot imply advancement before verified apply;
- tests import no production runtime dependency and require none of the
  excluded external systems;
- the full suite passes without cache/bytecode artifacts; and
- an independent read-only review accepts the contract changes, coordinator
  ordering, test matrices, and production-integration boundary.

The implementation remains blocked until the present planning commit receives
that independent review. Push and pull-request creation require separate
explicit approval.

### Rollback considerations

Stage 2 remains deterministic and unwired, so reverting its focused commits
removes only pure contracts, fakes, coordinator code, tests, and documentation.
No RTSS profile or hardware state requires restoration. Contract corrections
should be reverted in dependency order so callers never retain a coordinator
that expects removed invariants. Any degraded-state schema must remain readable
until no persisted diagnostic or handoff can reference it.

## 1. `test/controller-and-adapter-harness`

**Objective:** Create deterministic seams and regression scaffolding without
changing production policy.

- **Status:** Initial pure contracts, fake adapters, cap-list validation
  scaffolding, legacy decrease characterization, discovery, and import
  isolation are implemented. `CTRL-001` remains defective by design,
  `CTRL-005` remains unwired, CI is absent, and later production adapters remain
  outstanding.
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

## 2. RTSS transaction and restoration workstream

**Objective:** Replace overlapping writers with one validated, serialized,
generation-aware, reversible RTSS boundary.

- **Branch boundary:** `fix/rtss-transaction-and-restore` is the historical
  Stage 1 branch and must not be reused. Stage 2 planning uses
  `feature/rtss-transaction-coordinator`; later production integration requires
  a separately reviewed branch and plan.
- **Stage 1 status:** Complete and merged through PR #3 as squash commit
  `f8c4d4a2f7c6e1db39f3fd3c037ed98e07c39c95`, with 95 passing deterministic
  unit tests. Stage 1 provides identity, request, capture, readback, apply,
  restore, ownership, evidence, and result contracts plus deterministic fakes
  and regressions.
- **Stage 2 status:** Planning started on local branch
  `feature/rtss-transaction-coordinator`. No coordinator source or planned
  Stage 2 test is implemented, no production caller uses the Stage 1
  contracts, and production integration remains later work.
- **Additional Stage 2 prerequisites from the independent PR review:**
  1. Restrict `RtssReadback` to valid read-only outcomes and failure steps.
  2. Add an exhaustive readback outcome/failure-step matrix.
  3. Consider an exhaustive apply outcome/failure-step matrix.
  4. Define capability-driven application and profile component-length limits
     before filesystem integration.
  5. Preserve every existing transaction, ownership, readback, rollback, and
     restoration requirement listed below.
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
- **Manual validation:** none in the deterministic coordinator stage.
  Disposable RTSS profiles across candidate versions, including
  Global/application, integer/fractional, flags, missing profiles, failures,
  restart, and external edits, belong to later production integration.
- **Rollback:** coordinator-stage rollback reverts only unwired deterministic
  contracts, fakes, tests, code, and documentation. Later live-adapter rollback
  must preserve captured disposable profiles and document any state whose
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
