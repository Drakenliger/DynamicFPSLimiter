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

These decisions define boundaries and safety properties, not completed
behavior.

## Unresolved decisions

| Decision | Evidence needed | Must be resolved by |
| --- | --- | --- |
| Supported RTSS versions | Capability and restoration matrix on disposable profiles | RTSS boundary release gate |
| Fractional denominator API versus profile-file fallback | Versioned API/property and file behavior, exact readback, atomicity | RTSS boundary design |
| Stop policy for externally edited profiles | Conflict tests and user-safety policy | Restoration design |
| Exact LHM version and runtime | Packaged Windows tests, `pythonnet` runtime evidence, RX 7900 XTX coverage | LHM identity/health phase |
| Control sensor roles and quorum | Recorded sensor traces and failure-mode analysis | Controller-validity phase |
| CPU-bound policy | CPU/GPU-bound traces while preserving safety-sensor actions | Controller-validity phase |
| Physical settle and delay values | Frametime and sensor traces with RTSS and Lossless Scaling | Physical acceptance phase |

Until resolved, implementations must expose capability or policy decisions
explicitly and fail safely. They must not silently select a version contract,
fallback mechanism, restore policy, sensor quorum, or tuning value.
