# Implementation Plan

The repository-wide sequence and accepted decisions already recorded in
`DECISIONS.md` apply after the review baseline
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

Planning was completed on local branch
`feature/rtss-transaction-coordinator`. Corrected planning commit
`677b6b5750ac52953fd1581efbc658adbc171b22` was independently reviewed and
approved for explicit user acceptance on 25 July 2026, and the user explicitly
accepted it that day. Accepted Stage 2 decisions are recorded in
`DECISIONS.md`.

**Accepted Stage 2 design; prerequisite sequence item 1 implemented locally.**
The readback correction, exact stored-field evidence, immutable degraded-state
and retained-ownership contracts, and their deterministic matrices are
implemented locally after separate authorization. The coordinator, capability
and supported-name policy, mutation, and production integration are not
implemented. The branch has not been pushed and no Stage 2 pull request exists.

Stage 2 implements a deterministic coordinator and its required contract
prerequisites. It does not wire `DFL_v5.py`, `rtss_functions.py`,
`config_manager.py`, Autopilot, Dear PyGui, lifecycle workers, or live RTSS.
Those changes belong to a later production-integration phase after the
coordinator is independently reviewed.

### Design goals and invariants

The coordinator must enforce these invariants:

1. One canonical, case-insensitive application/profile identity is admitted
   before any backend call. Always-invalid lexical and path forms are rejected
   independently of backend capabilities; encoding and supported-name admission
   are separate capability-policy decisions.
2. Application, session, profile, and backend generations are checked before
   capture, immediately before the first mutation, and before accepting
   readback or restoration.
3. Request structure, policy, capabilities, and the intersection of configured
   and backend ranges are validated before state capture or mutation.
4. DLL names and derived profile filenames are single validated components
   whose encoded-byte and character limits, exact encoding, and supported-name
   policy come from explicit capabilities, not guessed RTSS constants.
5. Traversal, rooted, drive-relative, UNC, device, alternate-data-stream,
   separator, reserved-name, trailing-dot/space, control-character, lossy
   encoding, and containment failures are rejected.
6. Every mutation has an exact pre-mutation capture, including profile
   existence, exact stored numerator, exact stored denominator, reduced
   effective rational cap, owned limiter bits, backend generation, and required
   document/revision evidence.
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
12. Exact restoration verifies every owned field. Partial restoration uses an
    immutable degraded-state representation that accounts for every unresolved
    owned field and evidence state: stored numerator, stored denominator,
    effective cap, profile existence/deletion, document, revision, limiter
    bits, save, update/activation, backend epoch, retained ownership,
    unavailable or unreadable evidence, and external conflict.
13. Duplicate commands, concurrent writers, stale generations, and stale
    ownership tokens are rejected before mutation.
14. Restore, stop, cancellation, and ownership release are idempotent. Silent
    ownership release is invalid: release requires exact verified restoration
    or transfer to a defined degraded-handoff recipient with complete unresolved
    state and retained-ownership evidence.
15. Coordinator behavior and operation ordering are deterministic without
    RTSS, Windows, a GPU, a game, a GUI, LHM, PDH, or Lossless Scaling.

### Proposed interfaces

The implementation should keep these explicit boundaries:

| Boundary | Responsibility |
| --- | --- |
| `RtssIdentityCapabilityPolicy` | Canonical identity, always-invalid lexical/path forms, exact encoding and supported-name admission, resolved denominator policy, configured/backend range intersection, and capability-driven DLL/profile character and encoded-byte component limits. |
| `RtssCapabilitySource` | Return immutable capabilities and the current backend generation without choosing an unsupported version or mechanism. |
| `RtssStateReader` | Read profile existence, exact stored numerator/denominator as independent evidence, reduced effective cap, owned flags, document evidence, revision evidence, and verified absence. |
| `RtssProfileMutator` | Load/create/delete one admitted profile and mutate exact cap fields or owned flag bits without saving or activating implicitly. |
| `RtssActivationPort` | Save the loaded profile and request RTSS profile activation/update as separately injectable operations. |
| `RtssReadbackPort` | Perform an exact post-save/update readback with backend-generation evidence. |
| `RtssLifecycleAdmission` | Admit current application/session/profile/backend generations, cancellation state, profile ownership, and ownership transfer. |
| `RtssTransactionCoordinator` | Serialize apply/restore, reject duplicates, enforce phase ordering, classify failures, invoke rollback, retain or release ownership, and return structured results. |
| Degraded-state and handoff model | Account immutably for every unresolved owned field, save/update uncertainty, unavailable evidence, conflict, backend epoch, retained ownership, and an explicit handoff recipient. |
| Controller-facing port | Accept immutable commands and return `RtssApplyResult` or `RtssRestoreResult`; expose no GUI or monitoring state. |
| Deterministic fake backend | Model loaded-profile semantics, profiles, flags, revisions, document bytes, backend restarts, barriers, operation logs, false returns, and exceptions. |
| Event sink | Record transaction identity, generation, phase, reason, evidence summary, result, and degradation without affecting control flow. |
| Later production adapters | Translate the boundaries to supported RTSS DLL/profile mechanisms and integrate application callers only after separate review. |

The coordinator may use a wrapper command containing the Stage 1
`RtssApplyRequest` plus an immutable transaction identifier. This avoids
overloading the Stage 1 request while allowing in-flight and completed duplicate
rejection.

### Required Stage 1 prerequisites and focused contract extensions

The first implementation work was completed locally as a contract/test-only
slice:

- `S1-READBACK-001`: define an explicit read-only outcome/failure-step table
  for `RtssReadback`. Mutation-only outcomes such as
  `FAILED_ROLLED_BACK` and mutation/rollback-only steps must be rejected.
- `S1-TEST-001`: add an exhaustive acceptance/rejection matrix over every
  `RtssOutcome` and `RtssFailureStep`, with a fail-closed assertion when either
  enum changes.
- `S1-DESIGN-001`: introduce explicit capability fields and policy checks for
  DLL-name encoded-byte and character length, exact encoding support, and
  derived-profile-filename component length, including exact boundary tests.
- Add required representation-exact stored numerator and denominator evidence
  to capture and readback contracts. `RationalCap` is the reduced effective
  mathematical cap: `60/1` cannot alone prove prior storage as `120/2`. Exact
  restoration compares and restores the independently captured stored fields
  wherever the selected mechanism exposes them. Adapter capabilities declare
  which exact stored fields can be read and written.
- Add an immutable degraded-state and retained-ownership schema covering every
  unresolved owned field: exact numerator, denominator, effective cap,
  existence/deletion, document, revision, limiter bits, save,
  update/activation, backend epoch, unavailable or unreadable evidence, and
  external conflict. It must distinguish exact restoration, partial
  restoration, unresolved mutation, conflict, unavailable evidence, read
  failure, retained ownership, and explicit degraded handoff. Silent ownership
  release is invalid.

These corrections now have focused regression tests in the 122-test
deterministic suite. Independent read-only review of the implementation commit
remains required before later Stage 2 logic may rely on them.

### Mandatory degraded-state identity and handoff schema

Every degraded result and every proposed degraded handoff must preserve enough
immutable evidence to attribute unresolved state to exactly one transaction,
profile, and generation. “Complete unresolved state” is not an implicit
substitute for any explicitly required identity or generation field.

The identity portion must carry:

- canonical profile identity and its profile kind (`Global` or application);
- diagnostic display spelling when it is retained;
- the exact requested identity;
- the exact captured identity; and
- the exact readback or restoration identity.

Canonical case-insensitive identity is authoritative for equality, ownership,
and attribution. Display spelling is diagnostic metadata and never establishes
or changes ownership identity.

The generation portion must carry every applicable immutable dimension:

- `RtssGeneration.application_generation`;
- `RtssGeneration.session_generation`;
- `RtssGeneration.profile_generation`;
- the immutable transaction identifier, or a transaction generation if a
  later accepted contract uses one instead;
- `RtssGeneration.source_generation` for source-state evidence;
- the complete `RtssGeneration`, including `source_generation`, attached to
  captured evidence;
- the complete `RtssGeneration`, including `source_generation`, attached to
  readback or restoration evidence;
- backend generation or epoch, including the latest known backend epoch; and
- capability-generation or immutable capability-snapshot identity wherever
  capabilities can change.

The captured-evidence and readback-evidence requirements reuse the Stage 1
`RtssGeneration` terminology and object rather than inventing duplicate
counters. The schema preserves the requested, captured, and readback or
restoration generation snapshots separately so their consistency and
freshness can be checked.

Every degraded handoff must contain:

- canonical identity, profile kind, and the exact requested, captured, and
  readback or restoration identities;
- complete applicable generation evidence and the immutable
  transaction/request identity;
- all unresolved owned fields and all unavailable or failed evidence states;
- the latest known backend epoch;
- the current ownership holder and the defined recipient;
- explicit responsibility-transfer status; and
- the reason ownership cannot be released normally.

A named recipient alone is insufficient. The recipient must reject the handoff
if any identity or generation evidence required to attribute the unresolved
state safely is omitted, inconsistent, stale, ambiguous, or unavailable
without an explicit fail-closed disposition.

Ownership may be released only when:

1. exact restoration is verified against the same canonical identity and every
   applicable generation; or
2. a complete explicit degraded handoff is accepted by its defined recipient
   with all identity, generation, unresolved-state, and responsibility evidence
   preserved.

If either condition fails, ownership remains retained and the result remains
degraded or unresolved.

These attribution rules apply after cancellation, profile switching, session
replacement, backend restart, capability-generation change, stale worker
completion, and case-only profile spelling changes. A degraded result from one
profile or generation is never reusable against another. Case-only spelling
changes may compare as the same canonical identity but do not relax generation
checks. Persistence across a complete application-process restart remains an
unresolved production-integration decision; the deterministic Stage 2 schema
must nevertheless preserve complete in-model identity and generation
attribution.

### Capability and supported-name policy

The policy receives both configured safety bounds and observed backend
capabilities. It computes their intersection for:

- numerator and denominator integer ranges;
- numerator and denominator bit widths;
- effective-cap minimum/maximum and inclusivity;
- supported denominator strategies;
- exact readback, flag read/write, document, revision, create, and delete
  support;
- exact stored-field read/write support;
- supported name encodings and lossless conversion;
- DLL-name and profile-filename encoded-byte and character component limits.

An empty intersection is `UNSUPPORTED_CAPABILITY`; an unresolved mechanism is
`POLICY_REQUIRED`. The policy must not silently fall back from an API strategy
to profile-file editing.

Name admission separates four concerns:

1. canonical case-insensitive profile identity;
2. always-invalid lexical and path forms;
3. backend supported-name and exact-encoding capabilities; and
4. capability-driven encoded-byte and character length limits.

Raw and derived names are always rejected for `/`, `\`, rooted or
drive-relative forms, UNC/device prefixes, ADS colons, dot components, reserved
Windows stems, controls, trailing dot/space, or a resolved target outside the
admitted root. Non-ASCII names are rejected by default, but are not permanently
invalid identity: future admission requires explicit supported-name evidence,
lossless exact encoding, defined case canonicalization, and applicable DLL and
derived-filename limits including suffix expansion. Lossy conversion is always
rejected. Capability or encoding changes across backend generations require
fresh admission. Reparse-point enforcement belongs to the later filesystem
adapter, but the deterministic policy and fake model must express containment
failure. No Unicode support is claimed.

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
    `UNSUPPORTED_CAPABILITY` result with complete per-field unresolved state,
    evidence availability, backend epoch, and retained ownership.
20. Release the serialization lease. Release profile/session ownership only
    after exact verified restoration or transfer to a defined degraded-handoff
    recipient carrying complete unresolved state and ownership responsibility.
    A result with no defined recipient or incomplete state cannot release
    ownership.

A normal restore uses the same serialized capture-conflict, mutation,
save/update, and exact-readback phases. Repeated restore after verified release
returns an idempotent verified no-change/released result and performs no
mutation.

This is the complete logical coordinator ordering across all later slices. It
does not broaden the first mutation-bearing Stage 5 admission, which is limited
explicitly below.

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
- `DEGRADED`: possible mutation with incomplete rollback, save or activation
  uncertainty, missing/unreadable evidence, backend-generation loss, or any
  unresolved owned state. The result retains ownership unless a complete
  explicit degraded handoff transfers responsibility.

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
- model immutable per-field degraded state, save/update activation uncertainty,
  retained ownership, and explicit handoff recipients;
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
| `RTSSController.set_fractional_framerate` | Calculates a positive denominator and unconditionally attempts the direct denominator profile-file rewrite before the numerator property write. With the active/default `update=False` path, both writes defer activation and the method performs one final `UpdateProfiles`. With non-default `update=True`, the denominator helper updates once and the numerator property helper updates again, for two activations. | Raw identity, float conversion, split mechanisms, ignored failure, no exact readback or rollback. All identified active callers omit `update` and therefore use the one-final-update path; the two-update non-default path remains part of the method inventory. | Later composition adapter; do not reuse as coordinator logic. |
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

For `set_fractional_framerate`, the denominator file rewrite is unconditional
in both branches; only update count and timing differ. The active/default
`update=False` path calls `set_limit_denominator(..., update=False)`, then
`set_profile_property(..., update=False)`, then performs one final
`UpdateProfiles`. The non-default `update=True` path calls
`set_limit_denominator(..., update=True)` for one update and
`set_profile_property(..., update=True)` for a second update, with no final
method-level update. Later integration must characterize and account for both
paths even though no active caller currently selects `update=True`.

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

The durable tracked ledger gives no root-cause, location, acceptance text, or
technical definition for `S1-FINAL-005`, `S1-FINAL-006`, or `S1-FINAL-007`; it
records only deferred identifiers. No technical allocation or closure is
permitted without provenance recovery, and ignored local reports must not be
required for a fresh clone. They are not treated as coordinator prerequisites
unless recovered evidence proves that they are. Any recovered requirement must
be added to durable tracked documentation, receive appropriate regression
coverage, and pass focused review before disposition.

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
- whether RTSS exposes a usable cross-process serialization or revision token;
- whether deletion and exact absence can be verified by every supported
  backend;
- backend restart recovery and whether ownership can be safely reacquired; and
- how degraded ownership persists across a complete application-process
  restart.

The deterministic Stage 2 model must account for every unresolved owned field
and retain or explicitly hand off ownership. It does not claim that
restart-persistent storage has been designed. No Stage 2 plan selects an RTSS
version, fractional mechanism, overwrite policy, cross-process lock, restart
recovery mechanism, universal component limit, or compatibility claim.

### Accepted small implementation commits

The independently verified and explicitly accepted implementation sequence is:

1. **Prerequisite contract correction - completed locally**
   - restrict `RtssReadback` to read-only outcome/failure-step allowlists;
   - add the exhaustive readback matrix and a justified exhaustive apply
     matrix;
   - add exact stored-field evidence types; and
   - add the immutable degraded-state and retained-ownership schema.
   - completed without transaction coordination, mutation, or production
     integration; independent read-only review is the next gate.
2. **Capability and supported-name policy**
   - add configured/backend range intersections, exact-field capabilities,
     component lengths, lexical/path rejection, and exact encoding policy.
3. **Coordinator admission and capture**
   - add process-local serialization, generation and transaction admission,
     exact state capture, and verified no-change flow;
   - enable no mutation.
4. **Rollback foundations**
   - add a mutation journal or equivalent deterministic operation record,
     rollback operation interfaces, failure classification, and degraded-state
     construction;
   - retain fail-closed mutation admission until rollback coverage exists.
5. **Existing-profile exact-cap apply**
   - admit only the exact Stage 5 mutation boundary defined below, together
     with its save, activation, exact readback, rollback, degraded-state,
     ownership-retention, and complete false/exception/mismatch matrix.
6. **Profile creation and created-profile restoration**
   - separately add authorized profile creation, created-profile deletion,
     verified absence, repeated restore, retained ownership, and explicit
     degraded handoff.
7. **Limiter-flag mutation**
   - separately add limiter-flag mutation with exact prior-bit ownership,
     readback, rollback, restoration, and degraded accounting.
8. **Additional capability mechanisms**
   - separately admit each additional exact, reversible mechanism with its own
     complete ordered-operation and failure matrix.
9. **Profile switching**
   - separately add restore-before-acquire switching and ownership transfer
     between profiles.
10. **Cancellation and generation transitions**
   - separately add cancellation, session replacement, stale workers, backend
     epoch and capability-generation changes, and generation-safe ownership.
11. **Coordinator regression completion**
   - complete the deterministic state-machine and interleaving matrix, import
     isolation, and durable documentation synchronization.
12. **Separate later production adapters**
   - plan and implement supported mechanism selection, live adapters/callers,
     and Windows disposable-profile validation only after separate review.

#### Stage 5 first mutation-bearing boundary

Stage 5 admits exactly one operation: apply an exact cap change to an already
existing application or Global profile through one already-admitted capability
mechanism that exposes and supports every exact field and operation required
for capture, mutation, save, update/activation, readback, rollback, and exact
restoration verification.

The request may change the exact stored numerator. It may also change the exact
stored denominator only when the selected capability mechanism treats numerator
and denominator as one complete exact-cap operation. If that mechanism cannot
atomically or reversibly support both required exact fields, the request remains
fail closed and Stage 5 must not partially implement it.

Stage 5 does not admit:

- creation of a missing profile, deletion of a profile, or Global-derived
  profile creation;
- limiter-flag mutation or startup global-limiter mutation;
- direct complete-document replacement as a production mechanism;
- external-edit conflict resolution beyond fail-closed detection;
- profile switching or ownership transfer between profiles;
- cross-process serialization;
- production caller integration or live RTSS adapter selection;
- unsupported fractional fallback; or
- any mutation mechanism lacking exact readback and rollback evidence.

Every excluded request returns a structured unsupported or rejected result
before mutation.

A Stage 5 mutation-bearing commit may include only operations for which that
commit and its prior prerequisites provide exact capture, ordered operation
recording, save and activation semantics, exact readback, every applicable
false and exception path, rollback, degraded-state construction, ownership
retention, and deterministic tests. Stage 5 may be split into smaller commits
if numerator and denominator handling, save/update activation, or rollback
cannot remain independently reviewable as one slice. Smaller mutation slices
are preferred over combining mechanisms.

Later focused slices separately own profile creation and created-profile
deletion restoration; limiter-flag mutation and exact prior-bit ownership;
additional capability mechanisms; profile switching; cancellation and
generation transitions; and production adapters. None of those operations is
admitted by Stage 5.

No intermediate commit may permit mutation without its complete applicable
rollback and degraded-state behavior. Each mutation-bearing commit must include
its applicable false, exception, readback-mismatch, rollback, and unresolved-
ownership matrix. Every commit requires the complete deterministic suite and an
independent read-only scope/design review before the next behavior-bearing
commit.

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
- no intermediate commit admits mutation before its complete applicable
  rollback and degraded-state path exists;
- exact stored fields, created profiles, documents/revisions, and owned limiter
  bits restore exactly;
- repeated restore/stop is idempotent;
- controller-facing results cannot imply advancement before verified apply;
- tests import no production runtime dependency and require none of the
  excluded external systems;
- the full suite passes without cache/bytecode artifacts; and
- an independent read-only review accepts the contract changes, coordinator
  ordering, test matrices, and production-integration boundary.

The planning-review and explicit-acceptance gates are satisfied, and sequence
item 1 is implemented locally with no admitted mutation. The next gate is an
independent read-only review of that implementation commit. Sequence item 2 and
each later mutation-bearing slice remain unauthorized and gated by their
applicable review, rollback, degraded-state, ownership, and failure-matrix
requirements. Push and pull-request creation require separate explicit
approval.

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
- **Stage 2 status:** Planning commit
  `7adfb5406b091ccd8c55872fc1b75036029fee8a`, first correction commit
  `15a3774eb0ff10741e6684bf3414b4fdde61ae72`, and final correction commit
  `677b6b5750ac52953fd1581efbc658adbc171b22` are complete on local branch
  `feature/rtss-transaction-coordinator`. The final independent review
  recommendation was **Approved for explicit user acceptance**, and the user
  explicitly accepted the corrected plan on 25 July 2026. Acceptance commit
  `d10feead8a3707ee52a54f80e4e53c14945309d0` records that gate. The focused
  prerequisite contract/test sequence item is implemented locally and passes
  all 122 deterministic tests. No coordinator or mutation exists, no
  production caller uses the contracts, and production integration remains
  later work.
- **Additional Stage 2 prerequisites from the independent PR review:**
  1. Restrict `RtssReadback` to valid read-only outcomes and failure steps.
  2. Add an exhaustive readback outcome/failure-step matrix.
  3. Add a justified exhaustive apply outcome/failure-step matrix.
  4. Add exact stored numerator/denominator evidence separate from reduced
     effective-cap equality.
  5. Add mandatory immutable degraded-state and retained-ownership accounting.
  6. Define capability-driven encoding, supported-name, application-name, and
     profile-filename component limits before filesystem integration.
  7. Preserve every existing transaction, ownership, readback, rollback, and
     restoration requirement listed below.
- **Included findings:** `RTSS-001` through `RTSS-009`, `SEC-002`, and the RTSS
  handshake portion of `RTSS-005`.
- **Expected areas:** RTSS interface/controller boundary; canonical profile
  identity; capability-dependent exact encoding and supported-name policy;
  rational-cap validation; exact stored-field evidence; previous-state and
  degraded ownership; readback, rollback, restoration, and limiter-flag
  handling.
- **Required tests:** parser edge cases; path/name/encoding matrix; capability
  handling; transaction interleavings; partial failures; readback mismatch;
  exact prior numerator, denominator, effective cap, existence, document,
  revision, flag, save/update state, and retained ownership; created-profile and
  external-edit conflicts; generation rejection; idempotent flag operations.
- **Explicit exclusions:** controller thresholds; lifecycle worker rewrite;
  supported-version claims not backed by the physical matrix.
- **Dependencies:** phase 1 fakes and deterministic result assertions.
- **Completion criteria:** one write boundary owns every RTSS mutation; no
  startup mutation; no intermediate commit admits mutation without complete
  applicable rollback/degraded handling; callers receive structured verified
  results; failed applies do not advance logical state; owned state can be
  restored exactly or a complete durable degraded result retains or explicitly
  hands off ownership.
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
