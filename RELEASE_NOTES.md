# Release Notes

## Unreleased

No fix has been released from the review baseline.

### RTSS Stage 2 - prerequisite contract correction

The first accepted Stage 2 sequence item adds deterministic closed read-only
outcome and failure-step allowlists for `RtssReadback` and exact stored
numerator and denominator evidence distinct from reduced `RationalCap`
equality. Its first implementation did not pass independent review because
ownership release and degraded accounting were not yet sufficiently
evidence-bound.

The first focused local correction bound ownership to exact captured state,
required one owner-bound exact-restoration proof, preserved requested
exact-field applicability after inconclusive observations, added typed
field-specific diagnostics, and hardened relevant enums against aliases. It
also did not pass independent review: failed or unsupported readback could
still expose a complete available exact pair, while readback, operation,
conflict, capability, and backend-epoch evidence remained insufficiently bound
to one transaction.

The second focused local correction rejects complete available exact pairs on
non-verified readback; requires transaction-bound readback evidence for
degraded state; makes operation and conflict evidence factory-only and
owner-bound; derives conflict values, backend/capability epochs,
classification, accounting, and ownership retention; and rejects conflicting
or cross-transaction evidence. Immutable ownership-token copies use structural
logical identity; single-consumption enforcement remains deferred to the
future coordinator registry.

Independent review of the second correction confirmed its complete-pair
protection but did not approve it: internally consistent caller-created future
backend and capability generations could still become trusted readback,
operation, conflict, and degraded-state evidence. The third focused local
correction anchors bound readback and capability generations to the ownership
token's captured evidence. It intentionally adds no mechanism for trusting an
advanced generation. Independent read-only review of approved source commit
`4011d7e1e29fc2a4bbe901d184c53774b33e7baa` ended **Approved with
non-blocking review findings**. Sequence item 1 deterministic contracts are
therefore independently approved and complete.

Regressions cover the readback and apply outcome/failure-step matrices, exact
stored `120/2` versus normalized `60/1` restoration, foreign or stale ownership
proofs, failed and unsupported exact-field applicability, non-verified
complete-pair rejection, partial field observations, transaction/profile/kind/
generation/capability provenance, trusted operation evidence, owned conflict
derivation, backend-epoch observations, contradictory evidence,
`dataclasses.replace()` bypasses, structural token copies, field-specific
diagnostics, enum aliases, forged future generations, and accepted and rejected
handoff behavior. The deterministic suite contains 181 passing tests.

The independent approval passed all 181 tests. Two non-blocking test-quality
observations remain deferred: a historical targeted-parent replay count is
corrected from 35 tests with 8 failures to 35 tests with 9 failures, and some
downstream rejection tests stop at readback binding before separately invoking
the downstream constructor. Neither requires a source or test correction now
or reopens sequence item 1.

No transaction coordinator, mutation, production wiring, live RTSS behavior,
profile write, capability/name policy, dependency, or external-system behavior
changes in this prerequisite slice. Sequence item 2 planning and design review
are authorized next, but sequence item 2 implementation remains unauthorized.
No production integration, push, pull request, live validation, release, or
RTSS, Windows, RX 7900 XTX, Lossless Scaling, display, VRR, or frame-generation
compatibility claim exists.

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
