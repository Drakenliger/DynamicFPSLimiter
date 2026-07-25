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
- Unicode/canonical name policy and containment;
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
