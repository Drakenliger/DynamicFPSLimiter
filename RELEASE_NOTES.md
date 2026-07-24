# Release Notes

## Unreleased

No fix has been released from the review baseline.

### RTSS Stage 1 - preparatory internal infrastructure

RTSS Stage 1 adds deterministic contracts for RTSS profile identity, apply
requests, captured state, readback, apply results, and restoration results. It
includes exact rational FPS representation, canonical case-insensitive
application-profile identity, captured limiter-flag ownership, rollback
uncertainty enforcement, explicit evidence availability, and exact
document/revision restoration verification.

Deterministic fakes and regression tests cover identity collisions, ownership,
failure and rollback outcomes, immutable document bytes and SHA-256 evidence,
revision evidence, verified absence, exhaustive result matrices, and import
isolation. The completed suite contains 95 deterministic unit tests.

No production RTSS caller uses the new transaction contracts yet. No runtime
behavior change, live RTSS/profile write, Windows integration, RX 7900 XTX,
Lossless Scaling, LHM, PDH, GUI, or lifecycle validation is included. This is
preparatory internal infrastructure; Stage 2 transaction coordination and
production integration remain future work.

Current work consists only of review reconciliation, safety architecture, test
planning, tracked project-status documentation, the initial deterministic
controller/adapter harness, and the RTSS Stage 1 contract layer and tests. The
harness uses standard-library `unittest`, characterizes the reviewed legacy
decrease behavior, and supplies pure contracts and fakes without changing
production controller or RTSS policy.

`CTRL-001` remains open and its defective no-step-down result is intentionally
preserved. `CTRL-005` has pure cap-ladder validation scaffolding, but it is not
wired into runtime. The automated-suite portion of `TEST-001` exists without
CI, while `TEST-002` has initial deterministic seams and still requires later
production adapters.

### Known high-priority limitations

- The normal controller decrease path can fail to step down.
- FPS, process, and sensor evidence can be stale, ambiguous, or tied to the
  wrong backend.
- LibreHardwareMonitor mode remains coupled to legacy PDH behavior.
- RTSS changes are not one serialized, verified, reversible transaction.
- Previous cap and limiter state are not captured and restored.
- Stop/start and profile transitions can leave stale worker generations active.
- Autopilot, idle, and process identity are not generation-safe.
- The initial automated regression suite is local only; CI and broader
  production-adapter coverage remain absent.

This branch is not production-ready. It makes no compatibility claim for any
RTSS version, the RX 7900 XTX, or Lossless Scaling beyond the statically
reviewed baseline. No live RTSS, LHM, PDH, GUI, game, profile, or Lossless
Scaling validation was performed. Windows integration and physical acceptance
remain required.
