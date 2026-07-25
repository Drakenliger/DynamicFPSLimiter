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

## Proposed sequence-item-2 decisions pending independent review

The following durable design decisions were produced by the local RTSS Stage 2
sequence-item-2 planning session. They are not accepted implementation
authority until the planning commit is independently reviewed and explicitly
accepted.

34. Capability and supported-name policy is pure, deterministic, immutable,
    mechanism-specific, and fail-closed. Its terminal decision is exactly one
    of `SUPPORTED`, `UNSUPPORTED`, or `UNKNOWN`, with all applicable typed
    reasons in one stable order.
35. Every pure capability evaluation takes an immutable
    `RtssCapabilityEvaluationContext` separate from the requirement and
    evidence. It identifies the expected observation, backend generation,
    capability generation, profile kind, and exact policy scope. It is matching
    context, not support proof; structural equality is sufficient and caller-
    authored context can never substitute for an admitted observation.
36. Support state, evidence validity, and evidence origin are orthogonal. The
    closed decision algebra validates the request, matches context, checks
    authenticity and freshness, then evaluates primitive records and compound
    dependencies. A current explicit unsupported dependency dominates a
    current unknown dependency; unusable stale or invalid records remain
    `UNKNOWN` while preserving any unsupported claim diagnostically.
37. A whole admitted capability observation has no unavailable state. Absence
    is a missing observation; `STALE` and `INVALID` are observation validity;
    contradiction is one current factory-admitted observation with no
    selectable records; and temporary unavailability exists only on a current
    primitive record. Illegal cross-products are rejected by the admission
    factory. A contradictory observation always evaluates
    `UNKNOWN / CONTRADICTORY_EVIDENCE`.
38. Primitive backend operations, terminal compound capability requirements,
    internal dependency bundles, and future verified postconditions are
    separate closed taxonomies. Coordinated fractional update is exactly one
    internal ordered, reversible numerator/denominator write bundle. It is not
    atomic, is not publicly selectable, and never independently returns a
    terminal mutation-support decision. Existing fractional mutation includes
    capture reads, the internal write bundle, save, activation, exact readback,
    and exact restoration capability.
39. Integer limit, fractional numerator, fractional denominator, optional
    effective rational representability, and stored-field bit width use
    immutable domain-specific exact ranges. Bit-width derivation recognizes
    only unsigned `[0, 2^w - 1]` and two's-complement signed
    `[-2^(w-1), 2^(w-1) - 1]` for positive `w`; other representations are
    `UNKNOWN`. Non-integral configured bounds are converted exactly to discrete
    stored-field bounds with ceiling/floor rules, never rounding or float
    conversion. Controller bounds restrict requests but do not derive cap
    ladders or prove RTSS representability.
40. Raw supported-name requests use one aggregating structural classifier with
    a closed reason order and one leading reason. NUL/control/impossible input,
    path forms, traversal/separators, and ADS/colon are checked before current
    identity-model shape and representability, which are checked before
    capability and namespace evidence. Structural invalidity and current-model
    incompatibility both dominate missing or supporting backend evidence;
    backend evidence cannot override injection, path-confusion, or accepted
    ownership-identity boundaries.
41. Sequence item 2 may inspect any structurally valid raw name, but may return
    `SUPPORTED` only when the exact name is representable by the currently
    accepted `CanonicalProfileIdentity`, `RtssGeneration`, and
    `RtssOwnershipToken` model. Otherwise the deterministic result is
    `UNSUPPORTED / IDENTITY_MODEL_INCOMPATIBLE`, even if backend evidence would
    otherwise support it. Broader support requires a separately planned,
    reviewed, and accepted identity-model migration.
42. Name rules use one separate immutable, factory-controlled
    `RtssAdmittedNameRuleSet`, parent-bound to the admitted capability
    observation and its backend/capability generations and scoped to profile
    kind, mechanism, operation, and name context. Raw caller-authored rules,
    direct construction, stale/foreign/replaced rules, incomplete coverage,
    and mismatches cannot prove support. Duplicate or overlapping applicability
    is admitted only as one typed contradictory rule set and evaluates
    `UNKNOWN`.
43. Namespace and collision evidence is immutable, factory-controlled,
    observation-identity-bound, backend/capability-generation-bound, and
    complete by either proved enumeration or authoritative exact-query
    semantics. A public request references that evidence and never supplies a
    peer set. Missing, stale, incomplete, foreign, or generation-mismatched
    namespace evidence is `UNKNOWN`; a proved case, normalization, or encoding
    collision is always `UNSUPPORTED`.
44. `EXACT_NONE` normalization uses the external exact key unchanged. A known
    `NAMED` normalization is compatible only when admitted current complete
    evidence proves an auditable one-to-one mapping among the external exact
    name, external normalized key, and current canonical ownership key, with no
    exact, normalized, encoded, case, or canonical collider. Existing lookup
    and mutation require one matching existing identity; creation requires
    authoritative absence for every collision key and an unambiguous predicted
    ownership key. Collision or many-to-one mapping is `UNSUPPORTED`;
    incomplete proof is `UNKNOWN`.
45. Supported-name policy is evaluated for the exact profile kind, primitive
    or compound requirement, mechanism, existing lookup, existing mutation, or
    creation context,
    and admitted capability observation, name-rule set, and namespace
    observation. Exact original spelling is immutable audit evidence; no
    truncation, replacement, case change, normalization, basename extraction,
    suffix insertion, or fallback occurs.
46. `RtssCapabilityInfo`, caller-created `RtssCapabilityEvidence`, raw reports,
    Booleans, version labels, and caller-authored generations remain
    non-authoritative. Sequence item 2 defines immutable shapes and pure
    evaluation only. Item 3 or item 12 will later bind trusted live context;
    item 2 admits no live observation and consumes no item-1 ownership.
47. Sequence item 2 creates no coordinator registry, performs no capture,
    query, filesystem access, operation, conflict handling, rollback,
    restoration, or mutation. The detailed unresolved-fact and later-owner
    table in `IMPLEMENTATION_PLAN.md` is authoritative; this file deliberately
    does not duplicate it.

## Unresolved decisions

This is a high-level project summary only. The sequence-item-2 IDs, exact
fail-closed rules, owners, and gates in the
`IMPLEMENTATION_PLAN.md` authoritative unresolved-decision table control if
this summary is ever incomplete or appears inconsistent.

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
