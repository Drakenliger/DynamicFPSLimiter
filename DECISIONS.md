# Architectural Decisions

These decisions apply to implementation after the review baseline at
`5f89c49a9e18612b4645bb46a3b6a6e875612e04`.

## Accepted decisions

1. Create deterministic test seams before behavior changes.
2. Use one serialized and reversible RTSS boundary.
3. Every RTSS operation carries application/session generation and canonical
   profile identity.
4. Commit controller state only after verified RTSS readback.
5. Use one lifecycle owner with idempotent start and stop operations.
6. Use one-way per-session cancellation and join all prior workers before
   restart.
7. Make profile switching transactional.
8. Make LibreHardwareMonitor authoritative when selected.
9. Missing or stale required sensors veto cap increases.
10. Isolate PDH; it may become diagnostic-only until physically validated.
11. Idle state belongs to one session/profile generation.
12. Worker threads enqueue GUI updates rather than directly owning GUI state.
13. Do not tune RX 7900 XTX thresholds before correctness and lifecycle safety.
14. Do not claim RTSS-version compatibility without physical testing.
15. Canonical RTSS profile equality and hashing use canonical case-insensitive
    identity.
16. Profile display spelling is diagnostic metadata and is not ownership
    identity.
17. Limiter-flag mutation requires exact captured prior ownership for every
    bit the request may change.
18. Ordinary apply `FAILED` is limited to pre-mutation failure or an exact,
    verified no-change result.
19. Restore-result outcomes form a closed state machine with explicitly
    permitted failure steps and no recursive rollback disposition.
20. Exact restoration uses `VERIFIED`.
21. Unresolved post-mutation restoration uses an explicit unresolved
    disposition rather than ordinary `FAILED`.
22. Every non-verified rollback accounts for every unresolved owned limiter bit.
23. Profile-document and revision evidence use explicit availability states,
    including verified absence, unsupported evidence, and read failure.
24. Document restoration is verified with immutable complete bytes or an
    approved immutable SHA-256 digest.
25. RTSS Stage 1 remains deterministic contracts and tests only; it changes no
    production caller or runtime behavior.
26. Stage 2 transaction coordination and production integration remain
    separate work and start only after the Stage 1 pull request is reviewed and
    merged.
27. Reduced mathematical cap equality is distinct from exact stored-state
    equality. Exact stored numerator and denominator evidence is mandatory
    wherever an admitted mechanism exposes or mutates those fields; a stored
    `120/2` is not exactly restored by `60/1`.
28. Every Stage 2 degraded result and handoff carries immutable complete
    unresolved-field, canonical-identity, profile-kind, request/transaction,
    generation, evidence-availability, backend/capability epoch, current-owner,
    and retained-ownership information.
29. RTSS ownership is released only after exact restoration is verified for the
    same canonical identity and applicable generations, or after a defined
    recipient explicitly accepts a complete degraded handoff. Rejected or
    incomplete handoff retains ownership.
30. RTSS supported-name and encoding admission is capability-driven and
    fail-closed. Always-invalid lexical and path forms remain invalid
    independently of capabilities; non-ASCII remains rejected unless explicit
    lossless capability and policy evidence permits it.
31. No mutation is admitted before its complete applicable capture, ordered
    operation recording, save/activation semantics, exact readback, rollback,
    degraded-state handling, ownership retention, and deterministic failure
    tests exist.
32. The first Stage 2 mutation-bearing slice is limited to one existing-profile
    exact-cap operation against Global or one application profile through one
    already-admitted exact and reversible capability mechanism. Creation,
    deletion, flags, switching, ownership transfer, additional mechanisms, and
    production integration remain excluded.
33. Production RTSS adapters, live mechanism selection, caller wiring, and
    Windows disposable-profile validation remain a separately planned and
    reviewed phase after the deterministic coordinator.

Decisions 15-25 are implemented in the Stage 1 contracts and deterministic
tests. They do not represent completed production behavior. The Stage 1 merge
satisfies the prerequisite portion of Decision 26; its separation requirement
remains active. Decisions 27-33 were explicitly accepted on 25 July 2026 after
independent review of corrected Stage 2 planning commit
`677b6b5750ac52953fd1581efbc658adbc171b22`. They define Stage 2 architecture
and sequencing, not completed implementation or production behavior.

## Unresolved decisions

| Decision | Evidence needed | Must be resolved by |
| --- | --- | --- |
| Supported RTSS versions | Capability and restoration matrix on disposable profiles | RTSS boundary release gate |
| Fractional denominator API versus profile-file fallback | Versioned API/property and file behavior, exact readback, atomicity | RTSS boundary design |
| Concrete supported-name encoding and component limits | Versioned DLL/profile filename encoding, character, encoded-byte, and suffix-expansion evidence | Production filesystem-adapter design |
| Stop policy for externally edited profiles | Conflict tests and user-safety policy | Restoration design |
| Cross-process RTSS serialization | Supported-version evidence for an RTSS-wide lock or equivalent conflict mechanism | Production adapter design |
| Profile deletion and exact-absence verification | Supported-version deletion/readback matrix on disposable profiles | Profile-creation integration |
| Backend/RTSS restart recovery | Backend epoch, reacquisition, rollback, and restoration evidence | Production adapter design |
| Degraded ownership persistence across application restart | Durable storage, recovery, recipient, and stale-evidence policy | Production lifecycle integration |
| Exact LHM version and runtime | Packaged Windows tests, `pythonnet` runtime evidence, RX 7900 XTX coverage | LHM identity/health phase |
| Control sensor roles and quorum | Recorded sensor traces and failure-mode analysis | Controller-validity phase |
| CPU-bound policy | CPU/GPU-bound traces while preserving safety-sensor actions | Controller-validity phase |
| Physical settle and delay values | Frametime and sensor traces with RTSS and Lossless Scaling | Physical acceptance phase |

Until resolved, implementations must expose capability or policy decisions
explicitly and fail safely. They must not silently select a version contract,
fallback mechanism, restore policy, sensor quorum, or tuning value.
