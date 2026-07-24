# Dynamic FPS Limiter Repository Guide

## Repository context

- Fork: `Drakenliger/DynamicFPSLimiter`
- Upstream: `SameSalamander5710/DynamicFPSLimiter`
- Default branch: `main`
- Primary environment: Windows
- Target GPU context: AMD Radeon RX 7900 XTX
- External software context: RivaTuner Statistics Server (RTSS) and Lossless Scaling
- Review baseline: `5f89c49a9e18612b4645bb46a3b6a6e875612e04`

Read `CURRENT_STATUS.md`, `REVIEW_FINDINGS.md`, `DECISIONS.md`,
`IMPLEMENTATION_PLAN.md`, and `TEST_PLAN.md` before implementation work.

## Repository safety

- Never commit directly to `main`.
- Never merge automatically.
- Push only with explicit user approval.
- Use focused branches and draft pull requests.
- Keep changes small, independently reviewable, and limited to the stated scope.
- Do not add dependencies unless they are necessary and explicitly approved.
- Preserve Apache License 2.0 notices and attribution.
- Do not change working behavior solely for style.
- Avoid unrelated formatting, refactoring, and cleanup.
- Report changed files, tests, and external-state effects.

## Architecture boundaries

Keep these concerns separated:

- controller policy and cap selection;
- sensor acquisition and health;
- RTSS profile transactions and restoration;
- GUI presentation and dispatch;
- lifecycle, cancellation, and session ownership.

Reusable controller logic must not depend on Dear PyGui state. Sensor backends
must publish typed, timestamped health data rather than mutate controller or GUI
state. Worker threads enqueue GUI updates; they do not own GUI state.

## Controller expectations

Favor stability over maximum instantaneous FPS:

- reduce caps quickly only after sustained overload;
- increase caps slowly only after sustained headroom;
- use separate upper and lower thresholds;
- apply a settling period after a verified RTSS change;
- reject one-sample spikes and stale or invalid evidence;
- ignore loading screens, menus, invalid FPS, and invalid sensors;
- stay within validated minimum and maximum limits;
- distinguish CPU-bound policy from thermal and power safety constraints;
- log the reason and evidence for every cap change;
- support deterministic simulated traces.

RX 7900 XTX thresholds such as approximately 78-80% lower, 82% target, and
84-85% upper are configurable starting points, not universal values. Do not tune
them before correctness, restoration, freshness, and lifecycle safety are
established.

## Sensor backends

When LibreHardwareMonitor is selected:

- it is the authoritative backend;
- PDH validity or a positive PDH value must not gate decisions;
- use stable hardware and sensor identifiers, with exact names and types;
- prefer the verified AMD render/load sensor;
- handle missing, stale, non-finite, and temporarily invalid samples;
- handle driver restart and sensor re-enumeration;
- distinguish integrated and discrete GPUs;
- missing required control sensors veto increases;
- honor configured increase and decrease confirmation delays.

When legacy PDH is selected:

- reuse owned query handles where practical;
- close old handles before replacement;
- prevent duplicate counter registration;
- synchronize query and sample state;
- publish health, freshness, and source generation;
- clear stale samples during reinitialization;
- release resources on stop, exit, and failure;
- do not silently select a different GPU when the chosen adapter disappears.

The application must not have a startup dependency on the unselected backend.
PDH may remain diagnostic-only until physical RX 7900 XTX and Lossless Scaling
attribution is validated.

## RTSS safety

All `LoadProfile` -> property access -> `SaveProfile` work belongs to one
serialized transaction because RTSS property calls operate on the previously
loaded profile.

Before an RTSS mutation:

- validate the canonical profile identity and reject path traversal;
- validate the rational cap and supported integer range;
- capture the previous cap, denominator, relevant limiter flags, and ownership;
- carry application/session generation and canonical profile identity;
- apply through one serialized boundary;
- verify success through readback;
- roll back on partial failure when possible;
- commit controller state only after verified readback.

Restore session-owned state on stop, switch, exit, and handled failure. Do not
mutate RTSS global state merely by opening the application. If profile-file
editing remains unavoidable, use validated complete-document writes and atomic
replacement.

## Lifecycle and threading

- Use one lifecycle owner with explicit, idempotent start and stop operations.
- Use a one-way cancellation token and immutable identity per session.
- Retain worker handles and join before restart.
- Reject writes and GUI messages from canceled or stale generations.
- Make profile switching transactional.
- Keep idle state within one session/profile generation.
- Protect shared sensor and controller state.
- Stop producers before closing LHM, PDH, RTSS, tray, or GUI resources.
- Destroy Dear PyGui only after workers and GUI dispatch are quiescent.
- Handle RTSS and display-driver restarts gracefully where practical.

## Testing requirements

Controller tests must not require RTSS, a physical GPU, or a running game.
Every behavioral fix needs a regression test that fails against the reviewed
behavior and passes after the correction. Cover at minimum:

- cap step up/down, boundaries, and a cap absent from the list;
- sustained overload/headroom, spikes, hysteresis, confirmation, and settling;
- missing, stale, NaN, and infinite FPS or sensor values;
- required LHM sensor loss and LHM operation while PDH is zero or unavailable;
- CPU-bound and loading-screen policy;
- RTSS write failure, readback mismatch, and exact cap/flag restoration;
- rapid stop/start, duplicate-loop prevention, and no post-cancel writes;
- profile switching, Autopilot, and per-profile idle behavior;
- PDH reinitialization without leaked handles;
- long-uptime idle arithmetic and pointer-sized Win32 ABI declarations.

Run Windows integration and physical RX 7900 XTX, RTSS, and Lossless Scaling
acceptance only in the explicit manual acceptance phase. Record the Windows,
Adrenalin, RTSS, LHM, game, display, and Lossless Scaling versions/settings.

## Documentation and pull requests

Update project status, findings, decisions, tests, and release notes with each
focused change. A draft pull request must describe:

- problem and root cause;
- files changed;
- behavior before and after;
- tests performed;
- manual validation;
- known limitations;
- rollback considerations.

Do not claim RTSS-version, RX 7900 XTX, or Lossless Scaling compatibility until
the applicable physical matrix has passed.
