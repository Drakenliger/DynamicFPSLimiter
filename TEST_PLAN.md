# Test Plan

## Test principles

- Unit and adapter tests must run without RTSS, Windows PDH, LHM, a physical
  GPU, a game, or Lossless Scaling.
- Time, sensor data, process identity, failures, RTSS state, and thread barriers
  must be injectable and deterministic.
- Hardware- or version-dependent consequences remain pending until an explicitly
  tagged integration or physical acceptance run passes.
- Every regression records the finding identifier, initial state, stimulus,
  expected decision/result, and external-state invariant.
- Physical hardware is used only in the sections explicitly titled physical,
  Lossless Scaling, or supported RTSS-version matrix.

## Current automated harness

Run the initial deterministic suite with:

```text
python -m unittest discover -s tests -t . -v
```

The harness currently covers pure legacy decrease characterization
(`CTRL-001`), an unwired structural cap-ladder validator (`CTRL-005`),
standard-library discovery and import isolation (`TEST-001`), and initial fake
clock, FPS/process, sensor, RTSS-result, and generation contracts (`TEST-002`).
It also covers the RTSS Stage 1 contract and deterministic-fake validation
recorded below. It performs no live RTSS, GUI, sensor, process, registry,
profile, or hardware interaction. CI and later production adapters remain
outstanding.

## RTSS Stage 1 validation record

RTSS Stage 1 completed 95 deterministic unit tests. The validation covered:

- canonical case-insensitive profile equality and hashing;
- case-only set and dictionary collision behavior;
- request, capture, and readback matching across case variants;
- captured limiter-flag ownership and exact prior values;
- partial and unresolved rollback masks;
- conflict, unsupported, failed, and degraded rollback outcomes;
- closed apply and restore state machines;
- pre-mutation versus post-mutation failure classification;
- exact no-change proof;
- immutable document bytes and SHA-256 evidence;
- revision evidence and verified absence;
- exhaustive outcome and failure-step matrices;
- import isolation;
- cache and bytecode checks; and
- tracked and untracked whitespace checks.

These are contract and deterministic-fake tests only. Stage 1 did not test:

- physical RTSS or profile writes;
- Windows runtime behavior;
- RX 7900 XTX hardware;
- Lossless Scaling;
- LibreHardwareMonitor;
- PDH; or
- GUI and lifecycle integration.

No supported-version, hardware, profile-file, or runtime compatibility claim is
established by this validation.

## RTSS Stage 2 deterministic coordinator tests - planned

Every test in this section is **planned**. None is implemented or passing as
part of the Stage 2 planning commit. The historical Stage 1 result remains 95
passing deterministic tests.

The corrected Stage 2 test plan at
`677b6b5750ac52953fd1581efbc658adbc171b22` was independently verified and
explicitly accepted on 25 July 2026. Acceptance does not make any planned test
implemented or passing. The first separately authorized implementation gate is
the prerequisite contract matrices and exact stored/degraded-state contract
coverage below; it must remain contract/test-only and enable no mutation.

The Stage 2 tests will use only pure contracts, an in-memory fake backend, a
fake lifecycle/admission owner, deterministic barriers, and an ordered
operation log. They must run on any supported development platform without
RTSS, Windows, a GPU, a game, Dear PyGui, LibreHardwareMonitor, PDH, or Lossless
Scaling.

### Planned prerequisite contract matrices

- **Planned `S1-READBACK-001` / `S1-TEST-001`:** iterate every
  `RtssOutcome`/`RtssFailureStep` pair and assert the explicit read-only
  acceptance table. Verify `VERIFIED/NONE`, permitted validation, generation,
  capability, conflict, and readback failures, and reject mutation-only apply,
  save, update, rollback, restore, and delete states. Assert the table covers
  every enum member so additions fail closed.
- **Planned apply matrix:** iterate every
  `RtssOutcome`/`RtssFailureStep` pair with the minimum valid supporting state
  for that pair. Accept only the defined pre-mutation, exact no-change,
  verified apply, verified rollback, conflict, and degraded graphs; reject all
  other pairs. If one cross-product cell cannot be represented independently,
  document the invariant that makes it impossible and retain a fail-closed
  assertion over both enums.
- **Planned restore matrix:** retain the Stage 1 exhaustive matrix and extend
  it for any new non-flag unresolved-state accounting without weakening the
  existing exact-restoration and closed-state assertions.
- **Planned capability-name prerequisite (`S1-DESIGN-001`):** test zero,
  one-below, exact, and one-above boundaries for DLL-name bytes and derived
  profile-filename components, including the `.cfg` suffix and Global mapping.

### Planned request, identity, path, and capability admission

- Valid Global and application requests with canonical case-only equality.
- Request identity versus capture/readback/profile-owner identity mismatch.
- Application, session, profile, source/evidence, and backend generation
  mismatches varied independently.
- Mismatch before lock acquisition, after lock acquisition, before mutation,
  during readback, during rollback, and during restore.
- Negative, zero where disallowed, Boolean, non-integer, non-finite, and
  over-wide cap inputs.
- Exact configured/backend capability-range intersection for numerator,
  denominator, bit widths, and inclusive/exclusive effective-cap limits.
- Empty intersections, unsupported denominator strategies, missing exact
  readback, missing create/delete support, missing flag read/write support, and
  unresolved policy.
- Exact rational handling for reducible, irreducible, high-precision, minimum,
  maximum, and boundary caps without any float conversion.
- Exact stored numerator/denominator evidence distinct from reduced effective
  rational equality, including rejection of prior `120/2` being treated as
  exactly restored by `60/1`.
- Capability-driven DLL and filename component lengths with separate encoded-
  byte and character boundaries, suffix expansion, and backend-policy changes.
- Always-invalid rejection matrix for empty input, whitespace, controls,
  missing `.exe`, dot components, trailing dot/space, reserved Windows stems,
  forward/back separators, mixed separators, drive-rooted, drive-relative,
  rooted, UNC, extended/device, `\??\`, ADS/colon, and containment-escape forms.
- Default rejection of unsupported Unicode; acceptance only with an explicit
  supported-name capability, exact lossless encoding, defined case
  canonicalization, and satisfied character and encoded-byte limits.
- Lossy encoding rejection, suffix-expanded filename boundaries, and
  capability/encoding changes across backend generations.
- Abstract-root containment failure and a simulated reparse escape reported by
  the adapter; no real filesystem or reparse point is required.
- No capture or mutation operation after any admission rejection.

### Planned exact capture and ownership

- Existing Global and application profiles capture exact stored numerator,
  denominator, effective cap, existence, backend generation, owned limiter
  bits, document evidence, and revision evidence.
- Missing application profile records verified absence for profile, document,
  and revision; missing Global is rejected.
- Complete document bytes and approved immutable SHA-256 digest cases,
  including matching, mismatch, unsupported, read-failed, truncated, mutable
  input, and ambiguous dual-evidence rejection.
- Exact revision available, verified absent, unsupported, read failure, and
  changed-between-fields cases.
- Requested limiter bits require exact prior ownership; unrequested/unowned
  bits remain outside apply ownership.
- Profile creation requires explicit permission and produces created-profile
  ownership bound to the admitted session/profile generation.
- Capture failure for profile existence, numerator, denominator, flags,
  document, revision, or backend generation is pre-mutation and state-free.
- False-return and exception variants for every capture operation.

### Planned Stage 5 admission gates

- Admit exact-cap requests for an already existing application or Global
  profile only when one already-admitted capability mechanism supports every
  exact field and operation required for capture, mutation, save,
  update/activation, readback, rollback, and exact restoration verification.
- Reject a missing-profile request before mutation in Stage 5.
- Reject a profile-creation request before mutation in Stage 5.
- Reject a profile-deletion request before mutation in Stage 5.
- Reject a limiter-flag request before mutation in Stage 5.
- Reject a profile-switch request before mutation in Stage 5.
- Reject unsupported fractional mechanisms before mutation.
- Reject numerator-only mutation when exact denominator ownership is required,
  and reject denominator-only mutation when the selected capability requires
  one combined exact-cap operation.
- Perform no mutation when exact readback or rollback support is unavailable.
- Every excluded Stage 5 request returns a structured unsupported or rejected
  pre-mutation result.
- The ordered fake-adapter trace contains only the documented existing-profile
  exact-cap operation for an admitted Stage 5 mutation.
- Every admitted Stage 5 mutation false return, exception, or readback mismatch
  enters rollback or complete degraded handling.
- Incomplete future mutation implementations remain fail closed and cannot
  become admitted through a partially implemented capability path.

### Planned complete-coordinator apply, save, update, and readback

These tests span Stage 5 and separately planned later mutation slices. They do
not expand the Stage 5 admission boundary.

- Successful apply logs the exact order:
  admission -> capability -> lock -> generation recheck -> load/read/capture ->
  pre-mutation recheck -> mutation -> save -> update -> readback -> verify ->
  ownership retention -> unlock.
- Exact verified no-change performs capture and exact readback but no mutation,
  save, or update.
- Existing-profile cap-only apply, flag-only apply where representable, and
  combined cap/owned-flag apply.
- Authorized missing-profile creation from the approved adapter mechanism,
  followed by exact readback and created-profile ownership.
- Exact numerator and denominator write ordering without Decimal-to-float or
  binary-float conversion.
- False-return and exception paths for profile load/create, numerator write,
  denominator write, each owned flag read/write, save, update, each readback
  field, and final verification.
- Readback mismatch for existence, numerator, denominator, effective cap,
  owned flags, document evidence, revision evidence, canonical identity, and
  backend generation.
- Verified readback with unrelated flag bits or unrelated document fields
  according to the admitted mechanism.
- Controller-facing fake state remains unchanged for validation rejection,
  stale generation, unsupported capability, policy required, failure,
  conflict, rollback, and degraded results; it advances only after
  `RtssApplyResult.succeeded` is verified.

### Planned rollback and durable degradation

- Every possible mutation failure at numerator, denominator, flags, save,
  update, and readback enters rollback while serialization is retained.
- Rollback success restores exact prior numerator, denominator, effective cap,
  profile existence, complete document/digest evidence, revision evidence, and
  owned limiter bits, then saves, updates, and verifies.
- Successful rollback produces `FAILED_ROLLED_BACK`, never ordinary `FAILED`
  or `DEGRADED`.
- Exact readback proving no change after a post-mutation failure permits
  ordinary `FAILED` and performs no unnecessary restoration write.
- False-return and exception paths for every rollback mutation, save, update,
  delete, and readback operation.
- Partial rollback produces immutable degraded-state reporting for every
  unresolved owned field independently and in combinations: exact numerator,
  exact denominator, reduced effective cap, profile existence, deletion state,
  document evidence, revision evidence, limiter flags, save state,
  update/activation state, backend generation, and retained ownership.
- Degraded state distinguishes partial restoration, unresolved post-mutation
  state, external-edit conflict, unavailable evidence, read failure, ownership
  retained, and ownership transferred to a defined handoff recipient.
- Unresolved owned limiter-bit masks are exact for all bits, requested subsets,
  missing flag readback, and backend-generation mismatch; unrelated bits are
  excluded.
- A transaction-created profile is deleted on rollback/restore and exact
  absence is verified. Delete false, exception, profile still present, and
  delete unsupported cases are degraded.
- Backend restart before mutation is state-free rejection; restart after
  possible mutation attempts permitted rollback and otherwise reports durable
  degradation with the lost backend generation.
- Reject a degraded result that omits any unresolved owned field, save/update
  uncertainty, evidence availability, backend epoch, or retained ownership.
- Reject silent ownership release, a handoff without a defined recipient, and a
  handoff that omits any unresolved state or ownership responsibility.
- Reject an exact-restoration result when required evidence is unavailable or
  unreadable, or when rational equivalence is substituted for exact stored-
  field equality.
- Reject degraded results that omit partial save or update/activation
  uncertainty, including backend-epoch change with unresolved ownership.

### Planned degraded-handoff identity and generation rejection

Each identity or generation omission/mismatch is first rejected by degraded-
result construction and then by degraded-handoff acceptance.

- Reject a handoff that omits or mismatches canonical profile identity.
- Reject a handoff that omits or mismatches profile kind.
- Reject a handoff that omits or mismatches application generation.
- Reject a handoff that omits or mismatches session generation.
- Reject a handoff that omits or mismatches profile generation.
- Reject a handoff that omits or mismatches immutable transaction identity or
  transaction generation.
- Reject a handoff that omits or mismatches the Stage 1
  `RtssGeneration.source_generation` for source-state evidence.
- Reject a handoff that omits or mismatches the complete captured-evidence
  `RtssGeneration`, including its `source_generation`.
- Reject a handoff that omits or mismatches the complete readback/restoration-
  evidence `RtssGeneration`, including its `source_generation`.
- Reject a handoff that omits or mismatches backend generation/epoch.
- Reject a handoff that omits or mismatches the capability-generation or
  capability-snapshot identity where applicable.
- Accept case-only spelling equivalence only when canonical profile identity
  and every applicable generation match; diagnostic display spelling never
  changes ownership identity.
- Reject handoff to the wrong profile, a stale session, or a profile generation
  invalidated by profile switching.
- Reject handoff after backend restart or capability-generation change when the
  handoff does not preserve and consistently attribute both the captured and
  latest known epochs.
- Reject a stale worker attempting to transfer ownership.
- Reject a handoff with a defined recipient but incomplete identity or
  generation evidence.
- Reject a handoff whose fields are complete but whose requested, captured,
  readback/restoration, backend, or capability generations are inconsistent.
- When any handoff is rejected, assert that ownership is not released and the
  result remains degraded or unresolved.

### Planned external edits and revision conflicts

- External document/revision edit before the first mutation rejects or
  recaptures only according to explicit policy and never overwrites silently.
- External edit after capture but before apply is detected by the pre-mutation
  conflict check.
- External edit after verified apply but before stop/restore returns
  `CONFLICT` under the default fail-closed policy.
- Field-disjoint merge behavior is tested only if a later decision explicitly
  authorizes it; until then, tests require no overwrite.
- ABA revision, same bytes with changed revision, changed bytes with same
  revision, missing evidence, and backend-restart conflicts.
- Conflict outcomes retain ownership/degraded handoff information and never
  claim exact restoration.

### Planned duplicates, serialization, and profile switching

- Duplicate in-flight transaction ID, duplicate completed transaction ID, and
  replay after retry are rejected without mutation.
- Two requests for the same profile and two requests for different profiles
  cannot interleave loaded-profile/property/save/update operations.
- Global flag access serializes with every profile transaction.
- A request waiting for the lock rechecks all generations, cancellation, and
  ownership before capture or mutation.
- Operation logs prove deterministic order for concurrent scheduling scripts.
- Profile A -> B before A mutation: A releases without mutation and B may then
  acquire.
- Profile A -> B after possible A mutation: A is exactly restored and released
  before B capture; failed A restoration blocks B and returns durable degraded
  ownership.
- Switching among case-only identity spellings does not create a second owner.
- Ownership transfer never depends on mutable GUI state.

### Planned cancellation, stop, and idempotent restore

- Cancellation is injected at admission, capability read, lock wait, every
  capture field, pre-mutation, create, numerator write, denominator write, flag
  mutation, save, update, readback, rollback, verification, and release.
- Cancellation before mutation is state-free; cancellation after possible
  mutation completes rollback/restoration as far as capability permits.
- Stop during each transaction phase waits for the serialized result and then
  performs at most one restore.
- Repeated stop, repeated restore, restore after verified release, and
  concurrent stop requests are idempotent and produce no repeated mutation.
- Stale application/session/profile/backend generation cannot restore or write
  state owned by a newer generation.
- Ownership release occurs only after exact verified restoration or explicit
  durable degraded handoff.
- Adapter exceptions never escape as an unstructured controller success and
  never permit controller state advancement.

### Planned operation-order and isolation assertions

- **Planned legacy `S2-INVENTORY-001` characterization:** use an ordered fake to
  prove that `set_fractional_framerate(..., update=False)` attempts the
  denominator rewrite without activation, writes the numerator without
  activation, and performs exactly one final `UpdateProfiles`.
- **Planned legacy `S2-INVENTORY-001` characterization:** use an ordered fake to
  prove that `set_fractional_framerate(..., update=True)` performs one
  `UpdateProfiles` in the denominator helper and another in the numerator
  property helper, for exactly two activations and no final method-level
  activation.
- Every scenario asserts the complete ordered operation log, not only its
  terminal result.
- Unexpected operations after a terminal result fail the test.
- Failure-injection tables cover both Boolean failure and exception behavior
  for every adapter operation.
- Import-isolation tests reject Dear PyGui, Windows registry/Win32, RTSS DLL,
  LHM, PDH, GPU, game, and Lossless Scaling imports from coordinator modules.
- Test teardown proves no in-flight transaction, held serialization lease,
  profile owner, pending barrier, or unconsumed scripted operation remains.
- Running the planned suite with `PYTHONDONTWRITEBYTECODE=1` must leave no
  `__pycache__`, `.pyc`, or `.pyo` artifact in the repository.

### Accepted implementation-sequence gates

- No mutation test or implementation path becomes enabled before the
  applicable rollback interfaces, degraded-state construction, and failure
  tests exist.
- Every mutation-bearing commit passes its complete applicable Boolean-failure,
  exception, readback-mismatch, rollback, and unresolved-ownership matrix.
- Intermediate admission, capture, no-change, journal, or rollback-foundation
  commits remain fail closed for ordinary mutation.
- A deterministic guard proves that an admitted mutation cannot terminate
  without exact verified apply, exact verified rollback, or complete degraded
  state with retained or explicitly transferred ownership.

## Pure controller unit tests

Exercise one controller step using immutable runtime configuration and typed
samples:

- sustained overload and exactly one decrease;
- sustained headroom and exactly one increase;
- one-sample spike rejection and hysteresis;
- loading/menu/invalid-FPS suppression;
- CPU-bound, GPU-bound, mixed-bound, and safety-sensor roles;
- minimum/maximum clamping;
- state unchanged after rejected or failed RTSS results;
- reset on session, process, profile, backend, sensor, or cap generation change.

## Cap-list selection tests

Cover ascending lists at index zero, middle, and maximum; current cap absent;
one-element and empty lists; duplicate/unsorted input rejection; Decimal values;
finite/range validation; and proposed values below, equal to, or above measured
FPS. These tests characterize `CTRL-001` before its behavior changes.

## Fake clock and freshness tests

Use a monotonic fake clock for:

- FPS and sensor freshness/expiry;
- warm-up windows and confirmation duration/count;
- interrupted confirmation sequences;
- cooldown and post-write settling;
- clock jumps in non-monotonic inputs;
- source-generation changes;
- 32-bit input-tick wrap and 64-bit uptime scenarios.

## Fake sensor/backend tests

Provide independent fake LHM, PDH, CPU, and FPS backends:

- selected-backend startup with every unselected backend absent;
- healthy, missing, stale, NaN, infinite, and recovering samples;
- required versus optional/diagnostic sensor roles and quorum;
- immutable atomic snapshots under concurrent publication;
- stable identifiers, identical GPU names, and enumeration reorder;
- driver-reset/re-enumeration health transitions;
- no cap increase when any required sensor is unavailable.

## Fake RTSS transaction/readback/restoration tests

Model Global and application profiles, capability differences, shared
loaded-profile semantics, files, and limiter flags:

- canonical name and complete traversal/rooted/UNC/ADS/device/reparse matrix;
- existing and missing profiles, including Global-derived creation;
- integer/fractional caps, reduction, precision, range, and non-finite rejection;
- serialized `LoadProfile`/get/set/save/update interleavings;
- every sub-step false/exception and readback mismatch;
- partial file/API failure, rollback success/failure, and degraded state;
- exact prior numerator, denominator, effective cap, existence, and flag restore;
- external-edit conflicts and created-profile ownership;
- idempotent apply/restore/flag behavior, including `RTSS-009`;
- stale application/session/profile generations rejected before mutation;
- controller state unchanged until verified readback.

## Lifecycle and cancellation tests

Use deterministic barriers before/after sleeps, observation, evaluation, queue,
RTSS admission, and GUI dispatch:

- duplicate/concurrent start and stop requests;
- one-way cancellation and join-before-restart;
- exactly one monitoring and plotting generation;
- no post-cancel RTSS write or GUI commit;
- worker failure, bounded join, timeout, and degraded lifecycle state;
- ordered shutdown and no resource close while a worker can use it;
- GUI/tray/Autopilot intents routed through one owner;
- reset and warm-up of process-lifetime services by generation.

## Profile-switch and idle tests

- profile A -> B -> Global with distinct ladders, thresholds, and caps;
- canceled A work cannot write to B;
- A is restored before B ownership begins;
- canonical case/normalization and PSAPI/RTSS identity disagreement;
- only-profile Autopilot self-stop and non-only transactional switch;
- idle enter/exit using the last verified active cap;
- idle state cannot cross session/profile generations;
- failed idle apply/restore leaves logical state unchanged or degraded;
- first-run Quick Load uses defined defaults.

## PDH handle-lifecycle tests

Use a fake PDH API that counts handles and counter registrations:

- initialize, sample, reinitialize, counter loss, adapter change, and cleanup;
- close-before-swap and exactly-once close;
- no duplicate counters or unsynchronized query replacement;
- stale percentile invalidated when the worker stops or counters disappear;
- complete source reset/warm-up;
- full LUID identity and explicit multi-GPU aggregation;
- percentile boundary selection from sorted data.

## LibreHardwareMonitor identity/recovery tests

Use fake managed objects and loader/runtime metadata:

- stable hardware and sensor identifiers survive display-name collisions and
  enumeration reorder;
- selected name/type/identifier are recorded;
- missing/stale/non-finite samples and required-sensor quorum;
- atomic timestamped snapshots;
- discovery and poller resources close exactly once;
- recovery after sensor re-enumeration and source-generation change;
- selected runtime/asset matches the declared policy;
- LHM-only mode never constructs or gates on PDH.

## Win32 ABI tests

- assert explicit `restype` and `argtypes` for all used functions;
- preserve synthetic high-bit `HWND` and `HANDLE` values;
- `OpenProcess` success/failure and exactly-once `CloseHandle`;
- process/module-name failure propagation;
- typed `GetLastInputInfo`, `GetTickCount`, and `GetTickCount64`;
- wrap-safe idle arithmetic;
- tray window-handle propagation.

These tests use fake callables and structures and do not require Windows.

## Windows integration tests

Run on a disposable Windows test environment; no particular physical GPU is
required unless the run is also declared under physical acceptance:

- packaged/runtime imports and LHM asset selection;
- typed Win32 foreground/process lookup and idle smoke tests;
- Dear PyGui dispatch and ordered shutdown;
- PDH query open/reinit/close with handle-count observation;
- temporary-directory RTSS profile containment and failure injection;
- configuration interruption/recovery, logging, Task Scheduler, installation
  ACL, integrity, and Mark-of-the-Web behavior.

Do not use real user RTSS profiles for destructive/failure tests.

## Physical RX 7900 XTX tests

Record Windows build, Adrenalin version, GPU topology, LHM version/runtime, RTSS
version, game, display/refresh, and sampling settings.

- identify exact GPU and sensor identifiers/types/names;
- establish render load, hotspot/junction, memory, and total-board-power behavior;
- verify finite values, freshness, recovery, and stability across reboot, driver
  reset, sleep/resume, and iGPU changes;
- map PDH full LUIDs and determine whether aggregation is fit for control;
- validate sustained/spike/quorum/controller behavior from recorded traces;
- stress repeated start/stop, game switches, and resource counts;
- measure cap-write frametime effects before choosing settle/delay values.

## Lossless Scaling tests

For each supported LS mode/settings combination:

- distinguish game render, LS/presentation, launcher, and desktop identity;
- compare native rendering with LSFG enabled/disabled;
- verify headroom control, loading/menu suppression, and one-step transitions;
- exercise game -> desktop -> game and game A -> game B;
- restart/exit Lossless Scaling during a session;
- confirm no wrong-profile, post-stop, or stale-generation RTSS writes;
- capture frametimes and 1% lows around cap changes.

## Supported RTSS-version matrix

For every candidate supported RTSS version, use disposable profiles and record:

- DLL capabilities, `GetFlags`, and fractional denominator property support;
- API versus profile-file behavior and chosen mechanism;
- Global and existing/missing application profile behavior;
- 59.94, 60, 117.5, and boundary/precision caps;
- exact readback, normalization, unrelated-field preservation, and write timing;
- prior cap/denominator/flags restoration on stop, switch, exit, handled failure,
  RTSS restart, and external-edit conflict;
- capability-dependent exact encoding, canonical name policy, and containment;
- failure behavior while RTSS exits/restarts.

No compatibility claim is made for a version until its complete required row
passes.

## P0/P1 coverage map

Categories below refer to the sections above. `Physical` evidence is additional;
it is never a prerequisite for running the automated category.

| Finding | Automated category | Integration/manual category |
| --- | --- | --- |
| CTRL-001 | Pure controller; cap-list selection | Physical RX 7900 XTX |
| CTRL-002 | Fake clock/freshness; profile switch | Windows; Lossless Scaling |
| CTRL-003 | Pure controller; fake clock | Physical RX 7900 XTX; Lossless Scaling |
| CTRL-004 | Pure controller; fake sensors | Physical RX 7900 XTX; Lossless Scaling |
| CTRL-005 | Cap-list/config validation; lifecycle | Windows invalid-input run |
| CTRL-006 | Fake clock; fake sensors | Physical burst traces |
| HW-001 | Fake sensor/backend | LHM-only Windows/physical run |
| HW-002 | Fake sensors; LHM identity/recovery | Physical RX 7900 XTX |
| HW-003 | Fake clock/sensors; LHM recovery | Physical driver/reset matrix |
| HW-004 | PDH handle lifecycle; lifecycle | Windows PDH handle stress |
| HW-005 | PDH identity/aggregation | Physical LUID/LS mapping |
| HW-006 | LHM identity/runtime selection | Packaged Windows; physical LHM |
| HW-009 | Fake sensors; LHM quorum | Physical sensor-loss run |
| HW-010 | Fake sensors; LHM snapshot | Windows/physical poll stress |
| HW-011 | Fake backend startup | LHM-only Windows run |
| HW-012 | Fake clock; PDH health | Windows counter-loss/driver run |
| HW-013 | Fake backend startup | Legacy-only Windows run without LHM |
| RTSS-001 | Fake RTSS parser/transaction | Supported RTSS matrix |
| RTSS-002 | Fake RTSS restoration | Supported RTSS matrix |
| RTSS-003 | Fake RTSS failure/readback | Supported RTSS matrix |
| RTSS-004 | Fake RTSS interleavings | Concurrent disposable-profile run |
| RTSS-005 | Fake RTSS result; pure controller | Forced RTSS failure |
| RTSS-007 | Fake RTSS flag ownership | Supported RTSS matrix |
| RTSS-008 | Fake RTSS capability/rational cap | Supported RTSS matrix |
| THR-001 | Lifecycle barriers | Windows rapid start/stop |
| THR-002 | Lifecycle; GUI queue | Dear PyGui Windows stress |
| THR-003 | Lifecycle; fake sensors | Cross-backend/profile Windows run |
| THR-004 | Lifecycle ordered shutdown | Windows exit stress |
| THR-005 | Lifecycle; fake RTSS | Autopilot/LS self-stop |
| GUI-001 | Profile switch; fake RTSS | Lossless Scaling A -> B |
| GUI-002 | Profile switch/idle | Windows/LS idle transition |
| GUI-003 | Profile identity | Windows/RTSS/LS identity matrix |
| GUI-004 | Fake clock; Win32 ABI | Long-uptime Windows smoke |
| GUI-005 | Win32 ABI | 64-bit Windows handle run |
| SEC-001 | Integrity/install policy tests | Windows ACL/install audit |
| SEC-002 | Fake RTSS path matrix | Elevated disposable containment |
| TEST-001 | Test discovery and CI self-check | Not applicable |
| TEST-002 | Deterministic adapter contract suite | Not applicable |
| MAINT-001 | Worker/error/logging tests | No-console Windows fault run |

All deep-review P0 and P1 findings, plus high-severity `HW-013`, appear in this
map. Lower-priority findings remain covered in the relevant sections and active
ledger.
