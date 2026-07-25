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

**Accepted Stage 2 design; prerequisite sequence item 1 complete and
independently approved with non-blocking review findings.** Implementation commit
`c83aa281d961222eeeb70dbb994c4f33aef46381` was not approved because its
ownership proof, exact-field applicability, degraded evidence, failure
diagnostics, and enum-alias coverage were insufficient. First correction
`c323ddeb5cd62636a608d312af873a1552142f67` also was not approved because
non-verified exact-pair evidence and degraded provenance remained
constructible without sufficient transaction binding. Second correction
`ee9d0c7526861aeb999e1b410b3d2b21b71a6c23` was not approved because
internally consistent caller-forged future backend and capability generations
could still advance trusted evidence. A third focused corrective slice anchors
accepted generations to the owner's captured evidence and passes 181
deterministic tests. Independent read-only review of approved source commit
`4011d7e1e29fc2a4bbe901d184c53774b33e7baa` ended **Approved with
non-blocking review findings**, so sequence item 1 is complete. Capability and
supported-name policy is sequence item 2: its planning and design were
completed locally from starting HEAD
`fed6a33c79d7575c33ac5b4f1585fa536880896f`. Independent review of planning
commit `fd7e3d8aeb57bf7b8cd8acb8bd51448673dc2f1d` returned **Not approved -
blocking planning findings require correction**. This documentation-only
first correction closed `S2-CAP-PLAN-001`, the original
`S2-NAME-PLAN-001` defect, and `S2-DOC-OPEN-001`, but independent review of
correction commit `88efe137be44b8be6f26da9b5982f045e6aa10f0` also returned
**Not approved - blocking planning findings require correction**. This second
documentation-only correction closes the remaining seven blocking capability,
range, name, name-rule, and test-oracle findings plus one non-blocking
reason-order finding in proposed planning terms. Independent review of the
second corrected planning commit
`ae252ff8341570e2c55aa3c8555117dfb4e3db8c` again returned **Not approved —
blocking planning findings require correction**. It found exactly three
remaining blockers: unconditional save/activation dependencies
(`S2-CAP-PLAN-003-R2`), an impossible all-category reason-order fixture
(`S2-TEST-PLAN-002-R2`), and missing literal negative discrete-bound oracles
(`S2-TEST-PLAN-001-R2`). The third documentation-only correction addressed
those defects while preserving every other corrected planning semantic.
Independent review of third corrected commit
`2825a8fbed1b3bc1e10d42e3c5d73b352c57ab73` again returned **Not approved -
blocking planning findings require correction**. Groups A-F, arithmetic
oracles, sequence boundaries, and ledger integrity passed, but the review found
two remaining applicability-contract blockers: child mismatch diagnostics had
no legal public evaluator path (`S2-CAP-PLAN-004-R3`), and applicability plus
equivalent name-rule overlap had no literal predicate
(`S2-CAP-PLAN-005-R3`). This fourth documentation-only correction closes only
those ambiguities. It still requires another independent read-only review and
a later explicit acceptance documentation step. Implementation remains
unauthorized.
The coordinator, mutation, and production integration are not implemented or
authorized. The branch has not been pushed and no Stage 2 pull request exists.

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

The first implementation supplied focused coverage in the 122-test
deterministic suite but did not pass independent review. The first corrective
slice added foreign-proof, exact applicability, derived degraded-evidence,
field-specific diagnostic, and enum-alias regressions, but its 146-test result
also did not pass independent review. The second corrective slice rejects
non-verified complete exact pairs and binds readback, operation, conflict,
capability, and backend-epoch evidence to one exact transaction owner, but its
independent review found that caller-forged future epochs remained
constructible. The third corrective slice requires readback backend generation
and capability evidence to equal the owner's captured evidence, introduces no
trusted advanced-generation observation mechanism, and passes all 181
deterministic tests. Independent read-only review approved that correction with
two non-blocking test-quality observations. Trusted observation of a
legitimately advanced backend or capability generation remains a later design
concern and was not implemented in sequence item 1.

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

This section is the concrete sequence-item-2 design. It is planning only and
does not authorize the types or policy to be implemented.

#### Existing architecture assessment

| Existing fact | Location | Consequence for sequence item 2 |
| --- | --- | --- |
| `ProfileKind` contains only `GLOBAL` and `APPLICATION`. | `src/core/rtss_contracts.py:15` | Preserve the enum and require exact kind matching. Additional kinds require a separately reviewed enum change. |
| `CanonicalProfileIdentity` stores exact display spelling but equality and hashing use a case-folded canonical key; its current constructor also hard-codes ASCII, executable suffix, Windows character, reserved-stem, and filename-derived rules. | `src/core/rtss_contracts.py:329`, `:365`, `:413`, `:421`, `:429` | Preserve accepted ownership equality unless a later accepted decision changes it, but separate current lexical construction from capability-dependent support. Current validation is existing behavior, not evidence of universal RTSS encoding, case, normalization, or filename rules. |
| `RtssDenominatorStrategy` distinguishes unresolved policy, profile-file, and RTSS API strategies. | `src/core/rtss_contracts.py:23` | Preserve it as a request/strategy enum; do not treat either strategy as supported without mechanism evidence or fall back between them. |
| `RtssCapabilityInfo` is a public immutable range/Boolean description with backend generation, denominator strategies, flag read/write, exact readback, cap ranges, bit widths, and an optional version label. | `src/core/rtss_contracts.py:733` | Preserve compatibility, but do not extend its default-false Booleans into authoritative policy: it cannot distinguish unknown from unsupported, has no observation identity or freshness, and is caller-constructible. |
| `RtssGeneration` publicly carries application, session, profile, source, and canonical profile identity. | `src/core/rtss_contracts.py:712` | Reuse it; do not create duplicate application/session/profile/source counters. |
| `RtssCapabilityEvidence` publicly carries transaction, `RtssGeneration`, backend generation, and capability generation but no capability content, validity, or provenance. | `src/core/rtss_contracts.py:2146` | Preserve it as the item-1 ownership marker. A structurally consistent caller-created marker is not proof that a backend supports an operation. |
| `RtssOwnershipToken` binds exact captured state and capability marker; structural immutable copies are one logical token. | `src/core/rtss_contracts.py:2175` | Item 2 may consume matching identity/generation context but must not create, consume, release, or register tokens. |
| `RtssReadbackEvidence.bind`, `RtssOperationEvidence`, and `RtssConflictEvidence.from_readback` are factory-controlled and owner-bound. `RtssDegradedState` derives accounting and classification from those objects. | `src/core/rtss_contracts.py:2239`, `:2491`, `:2760`, `:2957` | Preserve these factory boundaries and captured-generation anchoring. Capability/name policy must not introduce a caller-authored Boolean or generation bypass. |
| `CapturedProfileState`, `RtssApplyRequest`, `RtssReadback`, `RtssCapabilityEvidence`, and `RtssOwnershipToken` have public constructors. | `src/core/rtss_contracts.py:1079`, `:1242`, `:1287`, `:2146`, `:2175` | Treat requests and raw reports as untrusted inputs. Item 1's public constructors enforce structural invariants, not live-backend authenticity. |

The missing sequence-item-2 concepts are: observation identity and provenance;
freshness/validity; explicit unknown, primitive-record unavailability,
observation contradiction, and unsupported states; per-mechanism and
per-operation support; separate
read/write/readback/restoration support; exact-field applicability;
profile-kind scope; name encoding and exact encoded evidence; length,
character, case, normalization, and collision evidence; and typed policy
decisions/reasons.

These contracts belong beside the pure contracts in `src/core`, with no import
from Dear PyGui, RTSS DLL bindings, filesystem adapters, lifecycle workers,
PDH, LHM, or controller state. Adapter observation and coordinator admission
remain later boundaries.

#### Planned typed capability model

The future focused implementation should introduce these immutable concepts,
using the names below unless implementation review identifies a clearer
non-overlapping name:

| Planned type | Required content and invariant |
| --- | --- |
| `RtssPolicyDecisionStatus` | Unique enum: `SUPPORTED`, `UNSUPPORTED`, `UNKNOWN`. Only `SUPPORTED` admits the exact requested policy operation. |
| `RtssCapabilitySupportState` | Unique enum: `SUPPORTED`, `UNSUPPORTED`, `UNKNOWN`, `TEMPORARILY_UNAVAILABLE`. It is one primitive record's observed support state, not provenance or validity. Contradiction is observation-level diagnostic state, not a second meaning of support. |
| `RtssDependencyApplicability` | Unique enum with exactly `REQUIRED`, `NOT_REQUIRED`, and `UNKNOWN`. It says whether one exact save/persist or activate/reload primitive belongs to one exact mechanism/compound/phase dependency graph. It is not primitive support, operation success, or a caller-authored Boolean. |
| `RtssDependencyApplicabilityContext` | Closed unique phase labels for `INTEGER_FORWARD_MUTATION`, `FRACTIONAL_FORWARD_MUTATION`, `INTEGER_EXACT_RESTORATION`, `FRACTIONAL_EXACT_RESTORATION`, `PROFILE_CREATION_INTEGER_FORWARD`, and `PROFILE_CREATION_FRACTIONAL_FORWARD`. A future compound that lists save or activation must add a reviewed exact context before it can be evaluated. |
| `RtssEvidenceValidity` | Unique enum separating `CURRENT`, `STALE`, and `INVALID` for whole observations and their records. Missing evidence is represented by absence. There is deliberately no observation-level unavailable member. |
| `RtssEvidenceOrigin` | Unique enum separating `DIRECT` and `DERIVED`. Derived evidence names its complete immutable source observations. Origin never implies support. |
| `RtssAccessMechanism` | Closed unique identifiers for mechanisms actually modeled. Initial values may correspond to the existing RTSS API and profile-file strategies, but no value implies a supported RTSS version. Enum additions fail closed. |
| `RtssPrimitiveOperation` | Closed primitive backend operations only: profile-existence lookup; integer-limit read/write; fractional-numerator read/write; fractional-denominator read/write; limiter-flag read/write; save/persist; activate/reload; create profile; delete profile; and verify profile absence. |
| `RtssCompoundRequirement` | Closed publicly selectable policy bundles: existing read; existing integer mutation; existing fractional mutation; exact readback; exact restoration; profile creation transaction; deletion restoration; and verified absence. Coordinated fractional update is deliberately absent. |
| `RtssInternalDependencyBundle` | Closed non-public dependency expansion used by terminal requirements. `COORDINATED_FRACTIONAL_WRITE` expands to the admitted ordered numerator-write and denominator-write primitives. It is reversible sequencing, not atomicity, and has no evaluator entry point or terminal decision. |
| `RtssRequiredPostcondition` | Closed required future observations: exact value observed; save confirmed; activation confirmed; profile exists; profile absent; and restored state equals captured state. Item 2 checks whether primitives needed to establish them are supported; runtime truth is recorded only by later sequences. |
| `RtssMechanismCapability` | One mechanism/primitive/profile-kind record containing support state, validity, exact stored-field applicability using existing `RtssStoredFieldKind`, origin, source references, and any domain-specific exact range. Duplicate keys are forbidden. Contradictory direct or derived sources produce the one typed contradictory observation described below. |
| `RtssMechanismDependencyApplicability` | Factory-controlled immutable child record keyed by parent observation identity, backend generation, capability generation, exact mechanism, profile kind, terminal compound requirement, dependency context, exactly one of save/persist or activate/reload, and a non-empty canonical exact field set. It contains `RtssDependencyApplicability`, immutable provenance, and canonical source references. |
| `RtssApplicabilityAdmissionDiagnostic` | Factory-only unique enum, separate from public evaluator reasons. It records untrusted or foreign input; parent, backend-generation, capability-generation, mechanism, profile-kind, compound, phase-context, field-set, or primitive mismatch; exact duplicate; non-empty field overlap; empty field set; missing compound/primitive; and wildcard-like or otherwise non-exact primitive/field scope. |
| `RtssCapabilityObservationIdentity` | Opaque immutable observation identifier, distinct from transaction identity. Equality is structural and auditable. |
| `RtssRawCapabilityReport` | Public untrusted adapter/request-shaped data. It can never directly produce `SUPPORTED`. |
| `RtssAdmittedCapabilityObservation` | Factory-controlled (`init=False`) snapshot containing observation identity, complete immutable primitive records and dependency-applicability records, backend generation, capability generation, observation validity, provenance, source label/version metadata used only diagnostically, and diagnostic state `CONSISTENT` or `CONTRADICTORY`. Legal states are exactly current/stale/invalid consistent snapshots with structurally complete records, or a current contradictory snapshot with contradiction sources and no selectable records. There is no unavailable observation. Direct construction and `dataclasses.replace()` must not create or advance trusted evidence. |
| `RtssCapabilityEvaluationContext` | Public immutable matching context containing expected observation identity, backend generation, capability generation, profile kind, and exact source/policy scope. It contains no support assertion. Transaction/ownership attribution is absent because item 2 owns neither; item 3 later binds context to the active item-1 transaction when required. |
| `RtssCapabilityRequirement` | Pure request for one exact mechanism, compound requirement or primitive query, profile kind, exact-field set, and domain-specific configured policy bounds. It contains intent, not proof. |
| `RtssCapabilityDecision` | Immutable status, exact request, admitted observation identity/generations when present, selected mechanism only on support, effective configured/evidence range intersection, and a non-empty tuple of typed reasons. |
| `RtssPolicyReason` | Unique diagnostic enum covering request/identity failure; missing/untrusted/foreign/stale/invalid/contradictory observations; observation/backend/capability/profile/scope mismatch; ordered primitive unsupported/temporarily-unavailable/unknown states; derivation failure; domain/range failure; and encoding/length/character/canonicalization/collision failure. Free text may supplement but never determine truth. |

The authoritative observation is the factory-controlled snapshot, not
`RtssCapabilityInfo`, `RtssCapabilityEvidence`, a Boolean, a version label, a
caller-authored generation, or an internally consistent caller-created graph.
Sequence item 2 defines the immutable shape and pure evaluator but intentionally
does not create a production path for trusting a current or advanced snapshot.
Sequence item 3 later owns admission against the active transaction/capture
context; sequence item 12 owns production adapter observation. Deterministic
item-2 tests use a test-only admitted-observation fixture that is not exported
as a production trust source.

The exact pure design signature is:

`evaluate_capability(requirement, context, admitted_observation) -> decision`

`context` is matching context, never support evidence. Structural equality of
immutable contexts and admitted evidence is sufficient; object identity is not
required. A caller-authored context paired with missing, raw, directly
constructed, replaced, foreign, or otherwise untrusted evidence cannot produce
`SUPPORTED`. Item 2 admits no live observation. Item 3 will bind an admitted
current observation to coordinator transaction context and item 12 will create
versioned production observations.

##### Mechanism-specific save and activation applicability

Save/persist and activate/reload are conditional dependencies. Their
applicability is never inferred from primitive support-state presence,
absence, success, failure, or a Boolean. The sole applicability state is
`RtssDependencyApplicability`, with exactly:

- `REQUIRED`: the matching primitive is an active dependency and must be
  evaluated;
- `NOT_REQUIRED`: the matching primitive is omitted from this exact dependency
  graph, and its support record is irrelevant to this requirement; and
- `UNKNOWN`: the factory-admitted evidence does not establish whether the
  primitive belongs to this exact dependency graph.

Every factory-admitted mechanism manifest contains exactly one immutable
`RtssMechanismDependencyApplicability` record for each declared complete
applicability key. A compound/context/primitive may declare multiple
field-specific keys only when their canonical field sets are disjoint. A
missing raw source does not let a caller omit a declared exact key: the factory
materializes that key as `UNKNOWN` with canonical
`APPLICABILITY_EVIDENCE_MISSING` provenance. This distinguishes an observed
`UNKNOWN` applicability assertion from absent source evidence while preserving
one applicability state enum and a structurally complete admitted manifest.

Each applicability record is bound to:

- the exact parent `RtssAdmittedCapabilityObservation` identity;
- the exact backend and capability generations;
- the exact access mechanism and profile kind;
- the exact terminal compound requirement;
- the exact dependency context;
- the exact requested/captured field set when restoration or a compound can
  vary by field; and
- exactly one conditional primitive: save/persist or activate/reload.

The record is immutable, structurally comparable, provenance-bearing, and
governed by the parent observation's freshness and validity. A structurally
equal immutable copy of a factory-admitted child is equivalent; object identity
is not required. Every copied-with-replacement or reconstructed child is
untrusted input to the factory and is revalidated. Originating from an admitted
object does not preserve authority after any bound field or nested source is
changed. Direct/raw construction, caller-authored enums or Booleans, changed
nested source references, `dataclasses.replace()`, a foreign parent, generation
mismatch, mechanism mismatch, profile-kind mismatch, compound mismatch, context
mismatch, field-set mismatch, or primitive mismatch can never become a
selectable child in a consistent admitted observation.

The canonical applicability key is literally:

```text
(
    parent_observation_identity,
    backend_generation,
    capability_generation,
    mechanism,
    profile_kind,
    terminal_compound_requirement,
    dependency_phase_context,
    primitive_dependency,
    canonical_exact_field_set,
)
```

`canonical_exact_field_set` is a non-empty immutable tuple of unique
`RtssStoredFieldKind` members sorted by enum declaration order. Raw duplicate
field members are malformed rather than silently deduplicated. Insertion order
therefore cannot affect equality. Empty field sets are illegal: they prove no
exact stored-field scope and never mean "all fields" or "not field-specific."
Each record names exactly one terminal compound, one primitive, one phase, one
mechanism, one profile kind, and one canonical field set. Wildcard, prefix,
range, all-primitives, all-fields, missing-primitive, missing-compound, and
compound-versus-primitive polymorphic scopes are not admitted. A later
production adapter may expand broad source information into independently
validated exact records before admission; that is item 12 work, not item 2.

The base key is the first eight components, excluding
`canonical_exact_field_set`. Two complete canonical keys that are equal are an
exact duplicate. For two records with different base keys there is no
applicability overlap. For the same base key, equal field sets are an exact
duplicate; unequal field sets with a non-empty intersection overlap and
contradict; and disjoint field sets may coexist as distinct field-specific
records. Thus strict subsets, strict supersets, and partial non-empty
intersections contradict, while disjoint field-specific evidence is legal.
Primitive and compound are separate exact dimensions: neither implicitly
supplies or covers the other, and a primitive report never applies to every
compound that references that primitive.

The admission factory uses one policy for all semantic applicability conflicts.
It produces the already-defined current `CONTRADICTORY` parent observation,
with no selectable primitive or applicability records, and records exact
factory-only `RtssApplicabilityAdmissionDiagnostic` values. The diagnostic
names are:

```text
APPLICABILITY_EVIDENCE_UNTRUSTED
FOREIGN_APPLICABILITY_EVIDENCE
APPLICABILITY_PARENT_OBSERVATION_MISMATCH
APPLICABILITY_BACKEND_GENERATION_MISMATCH
APPLICABILITY_CAPABILITY_GENERATION_MISMATCH
APPLICABILITY_MECHANISM_MISMATCH
APPLICABILITY_PROFILE_KIND_MISMATCH
APPLICABILITY_COMPOUND_MISMATCH
APPLICABILITY_REQUIREMENT_CONTEXT_MISMATCH
APPLICABILITY_FIELD_SET_MISMATCH
APPLICABILITY_PRIMITIVE_MISMATCH
APPLICABILITY_EXACT_DUPLICATE
APPLICABILITY_FIELD_SET_OVERLAP
APPLICABILITY_FIELD_SET_EMPTY
APPLICABILITY_FIELD_MEMBER_DUPLICATE
APPLICABILITY_COMPOUND_MISSING
APPLICABILITY_PRIMITIVE_MISSING
APPLICABILITY_PRIMITIVE_SCOPE_NOT_EXACT
APPLICABILITY_FIELD_SCOPE_NOT_EXACT
```

An otherwise admitted child taken from a different admitted parent produces
`FOREIGN_APPLICABILITY_EVIDENCE`; replacing only its parent identity produces
`APPLICABILITY_PARENT_OBSERVATION_MISMATCH`. Backend generation, capability
generation, mechanism, profile kind, compound, phase, field set, and primitive
substitutions are likewise detected at this factory boundary and produce their
correspondingly named diagnostics. Raw enums, Booleans, directly constructed
children, and caller-authored children produce
`APPLICABILITY_EVIDENCE_UNTRUSTED`. Duplicate, overlap, empty, missing, and
broad-scope and repeated-field-member cases use their literal diagnostics
above. In every case
construction succeeds as one admitted contradictory parent, so the public
evaluator may be called with that parent and returns exactly terminal
`UNKNOWN`, public reason tuple `(CONTRADICTORY_EVIDENCE,)`. Admission
diagnostics remain attached to contradiction sources for factory tests and
audit; they are never re-emitted as public evaluator reasons.

Candidate keys are compared after canonicalization. Enum dimensions use
declaration order; structural identities and generations use their canonical
immutable value tuples; field tuples use `RtssStoredFieldKind` declaration
order. Conflict pairs are stored with the lesser key first. Contradiction
sources are sorted by admission-diagnostic declaration order, first canonical
key, second canonical key, then canonical provenance/source-reference tuple.
Duplicate detection, overlap detection, diagnostics, and tests therefore have
the same result under every raw input permutation. No first-wins, last-wins,
set-order choice, or silent deduplication exists. Illegal contradictory
stale/invalid parent combinations remain construction errors because they are
invalid parent-state cross-products, not an alternative child-conflict policy.
A raw report cannot invoke the admission factory as a production trust source.

The required context matrix is:

| Compound requirement | Dependency context | Conditional records |
| --- | --- | --- |
| Existing integer mutation, forward apply | `INTEGER_FORWARD_MUTATION` | save after integer write; activation after integer write |
| Existing integer mutation, exact restoration prerequisite | `INTEGER_EXACT_RESTORATION` | save after integer restoration writes; activation after integer restoration writes |
| Existing fractional mutation, forward apply | `FRACTIONAL_FORWARD_MUTATION` | save after `COORDINATED_FRACTIONAL_WRITE`; activation after that bundle |
| Existing fractional mutation, exact restoration prerequisite | `FRACTIONAL_EXACT_RESTORATION` | save after coordinated fractional restoration writes; activation after those writes |
| Profile creation transaction with an integer value | `PROFILE_CREATION_INTEGER_FORWARD` | save after the creation/write expansion; activation after it |
| Profile creation transaction with a fractional value | `PROFILE_CREATION_FRACTIONAL_FORWARD` | save after the creation/coordinated-write expansion; activation after it |

Applicability-unknown reasons are exact and context-specific:

| Context | Save observed unknown | Save source missing | Activation observed unknown | Activation source missing |
| --- | --- | --- | --- | --- |
| Integer forward | `INTEGER_FORWARD_SAVE_APPLICABILITY_UNKNOWN` | `INTEGER_FORWARD_SAVE_APPLICABILITY_EVIDENCE_MISSING` | `INTEGER_FORWARD_ACTIVATION_APPLICABILITY_UNKNOWN` | `INTEGER_FORWARD_ACTIVATION_APPLICABILITY_EVIDENCE_MISSING` |
| Fractional forward | `FRACTIONAL_FORWARD_SAVE_APPLICABILITY_UNKNOWN` | `FRACTIONAL_FORWARD_SAVE_APPLICABILITY_EVIDENCE_MISSING` | `FRACTIONAL_FORWARD_ACTIVATION_APPLICABILITY_UNKNOWN` | `FRACTIONAL_FORWARD_ACTIVATION_APPLICABILITY_EVIDENCE_MISSING` |
| Integer restoration | `INTEGER_RESTORATION_SAVE_APPLICABILITY_UNKNOWN` | `INTEGER_RESTORATION_SAVE_APPLICABILITY_EVIDENCE_MISSING` | `INTEGER_RESTORATION_ACTIVATION_APPLICABILITY_UNKNOWN` | `INTEGER_RESTORATION_ACTIVATION_APPLICABILITY_EVIDENCE_MISSING` |
| Fractional restoration | `FRACTIONAL_RESTORATION_SAVE_APPLICABILITY_UNKNOWN` | `FRACTIONAL_RESTORATION_SAVE_APPLICABILITY_EVIDENCE_MISSING` | `FRACTIONAL_RESTORATION_ACTIVATION_APPLICABILITY_UNKNOWN` | `FRACTIONAL_RESTORATION_ACTIVATION_APPLICABILITY_EVIDENCE_MISSING` |
| Profile creation integer forward | `PROFILE_CREATION_INTEGER_SAVE_APPLICABILITY_UNKNOWN` | `PROFILE_CREATION_INTEGER_SAVE_APPLICABILITY_EVIDENCE_MISSING` | `PROFILE_CREATION_INTEGER_ACTIVATION_APPLICABILITY_UNKNOWN` | `PROFILE_CREATION_INTEGER_ACTIVATION_APPLICABILITY_EVIDENCE_MISSING` |
| Profile creation fractional forward | `PROFILE_CREATION_FRACTIONAL_SAVE_APPLICABILITY_UNKNOWN` | `PROFILE_CREATION_FRACTIONAL_SAVE_APPLICABILITY_EVIDENCE_MISSING` | `PROFILE_CREATION_FRACTIONAL_ACTIVATION_APPLICABILITY_UNKNOWN` | `PROFILE_CREATION_FRACTIONAL_ACTIVATION_APPLICABILITY_EVIDENCE_MISSING` |

Child mismatch names above are admission diagnostics, not public
`RtssPolicyReason` values. The public evaluator accepts only the complete
`RtssAdmittedCapabilityObservation`; it has no standalone-child overload and
never reinterprets raw, copied-with-modification, replaced, or caller-authored
applicability as admitted evidence. A consistent admitted parent can expose
only a matching selectable child. A contradictory parent exposes no child and
evaluates with the parent-level tuple `(CONTRADICTORY_EVIDENCE,)`. This boundary
is distinct from the primitive evaluator reasons `SAVE_PERSIST_UNSUPPORTED`,
`SAVE_PERSIST_EVIDENCE_MISSING`, `ACTIVATE_RELOAD_UNSUPPORTED`, and
`ACTIVATE_RELOAD_EVIDENCE_MISSING`.

Standalone exact restoration selects its integer or fractional restoration
context and exact field set. A profile-creation transaction's deletion
restoration currently expands only to delete plus verified absence, so it has
no save/activation slot; adding either would require a new reviewed exact
context and applicability records. Exact readback, existing read, verified
absence, and deletion restoration likewise list neither conditional operation.
No forward/restoration equivalence is assumed: for the same mechanism, forward
save may be `REQUIRED` while restoration save is `NOT_REQUIRED`, and forward
activation may be `NOT_REQUIRED` while restoration activation is `REQUIRED`,
only when separately admitted records prove those facts.

For each conditional dependency, the evaluator applies this exact algorithm:

1. Validate the complete parent observation. A current contradictory parent
   returns `UNKNOWN / CONTRADICTORY_EVIDENCE` before child selection. The
   evaluator never accepts or validates a standalone child.
2. In a consistent parent, select the already factory-validated exact-key
   applicability record before consulting the primitive support record. If the
   parent is stale/invalid, or applicability is missing-source or `UNKNOWN`,
   return `UNKNOWN` for that dependency with the exact public applicability
   reason. Do not
   evaluate the conditional primitive for that context. The compound terminal
   result is `UNKNOWN` unless a different active dependency is currently and
   explicitly unsupported under the existing status-precedence rule.
3. If applicability is `NOT_REQUIRED`, omit the primitive and its future
   postcondition entirely. Missing or unsupported primitive evidence is
   irrelevant and contributes no reason.
4. If applicability is `REQUIRED`, evaluate the matching primitive. Current
   explicit `UNSUPPORTED` yields terminal `UNSUPPORTED`; a missing-source,
   unusable, `UNKNOWN`, or temporarily unavailable primitive yields terminal
   `UNKNOWN`; only current explicit `SUPPORTED` satisfies that dependency.
5. Never infer `NOT_REQUIRED` from an unsupported, unknown, unavailable, or
   missing primitive. A caller-authored Boolean cannot substitute for the
   applicability record.

##### Closed capability decision algebra

The admitted-observation factory has no availability input and constructs
exactly these legal whole-observation states:

1. `CONSISTENT + CURRENT`, with exactly one structurally complete record for
   every declared primitive key and exactly one factory-admitted dependency-
   applicability record for every declared complete applicability key, allowing
   only the explicitly permitted disjoint field-specific keys;
2. `CONSISTENT + STALE`, preserving the same complete last-observed record set
   for diagnostics;
3. `CONSISTENT + INVALID`, preserving a complete raw-derived record set plus
   the typed invalidity diagnostics but exposing no selectable support; or
4. `CONTRADICTORY + CURRENT`, with a non-empty canonical contradiction-source
   tuple and no selectable records.

`CONTRADICTORY + STALE`, `CONTRADICTORY + INVALID`, a consistent snapshot whose
post-admission manifest still lacks a declared primitive or applicability key,
a duplicate primitive manifest key, a contradictory snapshot with selectable
records, and any attempted observation-level unavailable flag are construction
errors. Missing raw primitive or applicability source is normalized rather
than omitted: the factory creates the exact keyed `UNKNOWN` primitive record
with `PRIMITIVE_EVIDENCE_MISSING` provenance or the exact keyed `UNKNOWN`
applicability record with `APPLICABILITY_EVIDENCE_MISSING` provenance.
Duplicate complete keys, or equal-base-key field sets with a non-empty
intersection under the literal predicate above, instead create the typed
current contradictory observation. A whole-observation absence is represented
only by `None`. The factory uses exactly one contradiction policy:
contradictory direct, derived, or applicability sources produce the fourth
typed state, which always evaluates `UNKNOWN / CONTRADICTORY_EVIDENCE`;
construction does not also reject that semantic state. A raw report cannot
invoke the admission factory as a public trust source.

Within a consistent observation, legal primitive records combine support
`SUPPORTED | UNSUPPORTED | UNKNOWN | TEMPORARILY_UNAVAILABLE`, their own
record validity `CURRENT | STALE | INVALID`, and origin `DIRECT | DERIVED`,
subject to these rules: a derived
record names a non-empty complete acyclic source tuple; sources match
observation identity, generations, kind, mechanism, field and scope; and its
semantic support is computed rather than caller-selected.
`TEMPORARILY_UNAVAILABLE` is legal only on a `CURRENT` record inside a
`CURRENT` consistent observation. A stale or invalid record, or any record in
a stale or invalid observation, preserves the last non-unavailable semantic
support state and cannot contain `TEMPORARILY_UNAVAILABLE`. Direct and derived
origin remains diagnostic provenance only; neither bypasses whole-observation
or record validity or creates support.

Evaluation phases and terminal precedence are closed:

1. Structural request failure returns `UNSUPPORTED`.
2. Missing or untrusted observation returns `UNKNOWN` in its exclusive
   fixture. For a present admitted observation, aggregate every legally
   co-applicable observation identity, backend generation, capability
   generation, profile kind, scope, and provenance mismatch in that order,
   then return `UNKNOWN`.
3. An `INVALID` observation returns `UNKNOWN / INVALID_EVIDENCE`; a `STALE`
   observation returns `UNKNOWN / STALE_EVIDENCE`; a current contradictory
   observation returns `UNKNOWN / CONTRADICTORY_EVIDENCE`. Observation-level
   unavailability is not a legal branch.
4. In a consistent current observation, evaluate every exact conditional
   save/activation applicability slot. An `UNKNOWN` or missing-source slot
   makes the compound result `UNKNOWN` unless another active dependency is
   conclusively unsupported. A `NOT_REQUIRED` slot removes the primitive and
   its postcondition. A `REQUIRED` slot activates the matching primitive.
5. Any active required current primitive that is
   explicitly
   `UNSUPPORTED` makes the compound result `UNSUPPORTED`, even when another
   required primitive is `UNKNOWN`, unavailable, stale, or invalid.
6. Otherwise any missing, `UNKNOWN`, or temporarily unavailable required
   primitive makes the result `UNKNOWN`.
7. Only complete current supported active primitive dependencies, resolved
   conditional applicability, satisfied exact range requirements, and
   representable identity/name requirements return `SUPPORTED`.

An unsupported claim on the same stale or invalid record is not authoritative:
its terminal result is `UNKNOWN`, while the ordered diagnostic tuple retains
`PRIMITIVE_UNSUPPORTED_REPORTED` after the stale/invalid reason. In a compound
bundle, a different current explicit unsupported dependency remains conclusive
and therefore returns `UNSUPPORTED`.

| Evidence or dependency state | Terminal status | Required leading diagnostic |
| --- | --- | --- |
| Current, valid, supported primitive | `SUPPORTED` | `SUPPORTED_REQUIREMENT` |
| Current, valid, unsupported primitive | `UNSUPPORTED` | exact ordered `*_UNSUPPORTED` reason |
| Current, valid, unknown primitive | `UNKNOWN` | exact ordered `*_UNKNOWN` reason |
| Stale supported record | `UNKNOWN` | `STALE_EVIDENCE` |
| Stale unsupported record | `UNKNOWN` | `STALE_EVIDENCE`, then `PRIMITIVE_UNSUPPORTED_REPORTED` |
| Invalid supported record | `UNKNOWN` | `INVALID_EVIDENCE` |
| Invalid unsupported record | `UNKNOWN` | `INVALID_EVIDENCE`, then `PRIMITIVE_UNSUPPORTED_REPORTED` |
| Current temporarily unavailable primitive record | `UNKNOWN` | `PRIMITIVE_TEMPORARILY_UNAVAILABLE` |
| Contradictory admitted observation | `UNKNOWN` | `CONTRADICTORY_EVIDENCE` |
| Missing admitted observation | `UNKNOWN` | `CAPABILITY_EVIDENCE_MISSING` |
| Foreign observation identity | `UNKNOWN` | `FOREIGN_OBSERVATION` |
| Backend generation mismatch | `UNKNOWN` | `BACKEND_GENERATION_MISMATCH` |
| Capability generation mismatch | `UNKNOWN` | `CAPABILITY_GENERATION_MISMATCH` |
| Applicability observed `UNKNOWN` | `UNKNOWN` | exact context-specific `*_APPLICABILITY_UNKNOWN` reason |
| Applicability source missing | `UNKNOWN` | exact context-specific `*_APPLICABILITY_EVIDENCE_MISSING` reason |
| Applicability `REQUIRED`, matching primitive unsupported | `UNSUPPORTED` | exact ordered primitive `*_UNSUPPORTED` reason |
| Applicability `REQUIRED`, matching primitive missing/unusable | `UNKNOWN` | exact ordered primitive missing/unusable reason |
| Applicability `NOT_REQUIRED` | Continue without that primitive | no applicability or primitive failure reason |
| One current dependency unsupported, another unknown | `UNSUPPORTED` | unsupported reason before unknown reason |
| One dependency stale, another current unsupported | `UNSUPPORTED` | `STALE_EVIDENCE`, then unsupported reason |
| All required dependencies current and supported | `SUPPORTED` | `SUPPORTED_REQUIREMENT` |

Reasons are deduplicated and sorted independently of input record order by this
stable category order: request structure; identity representability; missing
observation; observation identity; backend generation; capability generation;
profile kind; source/policy scope; provenance/authenticity; whole-observation
validity (`INVALID` before `STALE`); contradiction/derivation; primitive
dependencies in the canonical dependency-table order below, with each
conditional dependency's applicability reason immediately before its matching
primitive reason and with `UNSUPPORTED` before
`TEMPORARILY_UNAVAILABLE` before `UNKNOWN` for the same primitive; range domain and
intersection; name encoding/length/character; namespace completeness; case;
normalization; encoding collision; canonical collision. A failing decision
never contains `SUPPORTED_REQUIREMENT`; success is tested separately and its
reason tuple is exactly `(SUPPORTED_REQUIREMENT,)`. Status precedence and
reason display order are deliberately separate.

The global primitive reason order is: profile-existence lookup; integer read;
fractional-numerator read; fractional-denominator read; limiter-flag read;
integer write; fractional-numerator write; fractional-denominator write;
limiter-flag write; save/persist; activate/reload; create; delete; verify
absence. A compound filters this list to its dependencies without reordering
them. For multiple applicability contexts attached to the same conditional
primitive, forward contexts precede restoration contexts and the exact
`RtssDependencyApplicabilityContext` enum order breaks any remaining tie; all
save contexts therefore precede all activation contexts.

##### Legally constructible diagnostic-order oracle groups

There is no all-category fixture. Structural failure, absent observation,
unusable observation, current evidence evaluation, name-rule evaluation,
namespace evaluation, range evaluation, and success have mutually exclusive or
short-circuited states. The following groups are the complete ordering oracles.
Every tuple is literal and normative; tests do not build expected order from
the evaluator.

**Group A - structural raw-name failures**

| Fixture | Why the reasons can coexist | Literal expected tuple | Leading reason / terminal status | Suppressed categories |
| --- | --- | --- | --- | --- |
| A1: raw application name `\\?\C:\..\game.exe:stream\u0000\u0001` | One non-empty string contains NUL and another control plus device, UNC, drive-qualified/rooted/full-path, dot-segment, separator, ADS, and generic-colon forms. | `(NUL_IN_NAME, CONTROL_CHARACTER, DEVICE_PATH, UNC_PATH, DRIVE_QUALIFIED_PATH, ROOTED_PATH, FULL_PATH, DOT_PATH_SEGMENT, PATH_SEPARATOR, ALTERNATE_DATA_STREAM, COLON_PATH_CONFUSION)` | `NUL_IN_NAME` / `UNSUPPORTED` | Current identity, capability, applicability, primitive, range, name-rule, and namespace evaluation |
| A2: raw name `""` | Empty cannot coexist with any content-dependent reason. | `(EMPTY_NAME,)` | `EMPTY_NAME` / `UNSUPPORTED` | Every later category |
| A3: raw name `"\t"` | The input is both whitespace-only and a control character; it cannot also be empty or a path form. | `(WHITESPACE_ONLY_NAME, CONTROL_CHARACTER)` | `WHITESPACE_ONLY_NAME` / `UNSUPPORTED` | Every later category |

In A1 and A3, the displayed escapes denote the actual U+0000, U+0001, and
U+0009 code points in the in-memory fixture; no NUL byte is written to a
tracked file.

The A1 positive control is exact `game.exe`; it has no classifier reason and
continues. A2 and A3 are required exclusive controls, not omissions from an
aggregate fixture.

**Group B - evaluation-context mismatch**

One current, valid, consistent, fully supporting observation is paired with a
context whose expected observation identity, backend generation, capability
generation, profile kind, and policy scope all differ. Those public context
dimensions can legally differ simultaneously. The literal tuple is
`(FOREIGN_OBSERVATION, BACKEND_GENERATION_MISMATCH,
CAPABILITY_GENERATION_MISMATCH, PROFILE_KIND_MISMATCH,
POLICY_SCOPE_MISMATCH)`, led by `FOREIGN_OBSERVATION`, with terminal
`UNKNOWN`. Missing observation, observation validity, primitive,
applicability, range, name-rule, and namespace reasons are suppressed. The
positive control is a structurally equal matching context and otherwise
identical evidence.

**Group C - unusable admitted observation**

The factory forbids combining these states, so each is a separate fixture:

| Fixture | Literal expected tuple | Leading reason / terminal status | Suppressed categories |
| --- | --- | --- | --- |
| C1: matching admitted `STALE` observation | `(STALE_EVIDENCE,)` | `STALE_EVIDENCE` / `UNKNOWN` | Applicability, primitive, range, name-rule, namespace |
| C2: matching admitted `INVALID` observation | `(INVALID_EVIDENCE,)` | `INVALID_EVIDENCE` / `UNKNOWN` | Applicability, primitive, range, name-rule, namespace |
| C3: matching current `CONTRADICTORY` observation with no selectable records | `(CONTRADICTORY_EVIDENCE,)` | `CONTRADICTORY_EVIDENCE` / `UNKNOWN` | Applicability, primitive, range, name-rule, namespace |
| C4: current valid foreign observation only | `(FOREIGN_OBSERVATION,)` | `FOREIGN_OBSERVATION` / `UNKNOWN` | Later context and evidence categories |
| C5: current valid observation with only backend generation mismatched | `(BACKEND_GENERATION_MISMATCH,)` | `BACKEND_GENERATION_MISMATCH` / `UNKNOWN` | Capability generation and later evidence categories |
| C6: current valid observation with only capability generation mismatched | `(CAPABILITY_GENERATION_MISMATCH,)` | `CAPABILITY_GENERATION_MISMATCH` / `UNKNOWN` | Later evidence categories |

The C-group positive control is current, consistent, matching, fully
supporting evidence. Missing observation is a separate single-category fixture
with exactly `(CAPABILITY_EVIDENCE_MISSING,)`; it is never combined with C4-C6.

**Group D - current consistent primitive and conditional-dependency failures**

D1 uses one existing fractional-mutation requirement and one current, valid,
consistent observation. Distinct exact keys carry: unsupported existence;
temporarily unavailable numerator read; unknown denominator read; unsupported
numerator write; temporarily unavailable denominator write; an incomplete
derived coordinated-write bundle; observed-unknown forward save
applicability; missing-source forward activation applicability;
observed-unknown restoration save applicability; and missing-source
restoration activation applicability. These states coexist because each
belongs to a different primitive or applicability-context key. Its literal
tuple is:

`(DERIVED_DEPENDENCY_INCOMPLETE,
PROFILE_EXISTENCE_LOOKUP_UNSUPPORTED,
FRACTIONAL_NUMERATOR_READ_TEMPORARILY_UNAVAILABLE,
FRACTIONAL_DENOMINATOR_READ_UNKNOWN,
FRACTIONAL_NUMERATOR_WRITE_UNSUPPORTED,
FRACTIONAL_DENOMINATOR_WRITE_TEMPORARILY_UNAVAILABLE,
FRACTIONAL_FORWARD_SAVE_APPLICABILITY_UNKNOWN,
FRACTIONAL_RESTORATION_SAVE_APPLICABILITY_UNKNOWN,
FRACTIONAL_FORWARD_ACTIVATION_APPLICABILITY_EVIDENCE_MISSING,
FRACTIONAL_RESTORATION_ACTIVATION_APPLICABILITY_EVIDENCE_MISSING)`.

`DERIVED_DEPENDENCY_INCOMPLETE` is the evaluator's diagnostic derivation from
the incomplete internal bundle; it is not a selectable support record or a
terminal internal-bundle decision.

The leading reason is `DERIVED_DEPENDENCY_INCOMPLETE`; terminal status is
`UNSUPPORTED` because the current explicitly unsupported active primitives
dominate unknown/unavailable dependencies. Save/activation primitive reasons
are suppressed for every `UNKNOWN` or missing-source applicability context.
Range and name evidence is supporting and contributes no reason. A missing
primitive manifest key is not legal in a consistent admitted observation and
has a separate factory-rejection test; a factory-materialized missing-source
save or activation primitive record is legal and uses exactly
`(SAVE_PERSIST_EVIDENCE_MISSING,)` or
`(ACTIVATE_RELOAD_EVIDENCE_MISSING,)` in its single-dependency fixture.

D2 fixtures vary one conditional slot while every other active dependency is
current and supported: `REQUIRED` plus supported primitive succeeds;
save `REQUIRED` plus unsupported primitive yields exactly
`(SAVE_PERSIST_UNSUPPORTED,)`; save `REQUIRED` plus missing-source primitive
yields exactly `(SAVE_PERSIST_EVIDENCE_MISSING,)`; activation `REQUIRED` plus
unsupported primitive yields exactly `(ACTIVATE_RELOAD_UNSUPPORTED,)`; and
activation `REQUIRED` plus missing-source primitive yields exactly
`(ACTIVATE_RELOAD_EVIDENCE_MISSING,)`. `NOT_REQUIRED` succeeds while the
corresponding unsupported or missing primitive is ignored. Observed `UNKNOWN`
and missing-source applicability use the exact context-specific one-element
tuples defined above. Separate forward/restoration fixtures prove their records
may differ. The D-group positive control marks each actually active slot
`REQUIRED` with supported primitive evidence and marks each deliberately
omitted slot `NOT_REQUIRED`.

**Group E - name-rule and namespace failures**

| Fixture | Why/split rule | Literal expected tuple | Leading reason / terminal status | Suppressed categories |
| --- | --- | --- | --- | --- |
| E1: one current rule set with foreign rule identity plus mismatched parent, backend generation, capability generation, profile kind, namespace scope, mechanism, operation, and name context | These matching dimensions can all differ simultaneously. | `(FOREIGN_NAME_RULE_SET, NAME_RULE_PARENT_OBSERVATION_MISMATCH, NAME_RULE_BACKEND_GENERATION_MISMATCH, NAME_RULE_CAPABILITY_GENERATION_MISMATCH, NAME_RULE_PROFILE_KIND_MISMATCH, NAME_RULE_NAMESPACE_SCOPE_MISMATCH, NAME_RULE_MECHANISM_MISMATCH, NAME_RULE_OPERATION_MISMATCH, NAME_RULE_CONTEXT_MISMATCH)` | `FOREIGN_NAME_RULE_SET` / `UNKNOWN` | Rule contents and namespace |
| E2: invalid rule set | Invalid, stale, and contradictory are factory-exclusive. | `(INVALID_NAME_RULES,)` | `INVALID_NAME_RULES` / `UNKNOWN` | Namespace |
| E3: stale rule set | Separate factory-legal state. | `(STALE_NAME_RULES,)` | `STALE_NAME_RULES` / `UNKNOWN` | Namespace |
| E4: current contradictory rule set, no selectable rules | Separate factory-legal state. | `(CONTRADICTORY_NAME_RULES,)` | `CONTRADICTORY_NAME_RULES` / `UNKNOWN` | Namespace |
| E5: usable rules plus incomplete namespace evidence | Completeness must pass before collision/normalization evaluation. | `(NAMESPACE_COMPLETENESS_MISSING,)` | `NAMESPACE_COMPLETENESS_MISSING` / `UNKNOWN` | Case, normalization, encoding collision, canonical collision |
| E6: usable rules and complete namespace proving one peer collides by case, named normalization, encoding, and current canonical key | Complete evidence can prove all four colliders for the same peer. | `(CASE_COLLISION, NORMALIZATION_COLLISION, ENCODING_COLLISION, CANONICAL_COLLISION)` | `CASE_COLLISION` / `UNSUPPORTED` | No later name category |
| E7: usable complete namespace with unknown normalization mode | Mutually exclusive with named-compatible/incompatible modes. | `(NORMALIZATION_UNKNOWN,)` | `NORMALIZATION_UNKNOWN` / `UNKNOWN` | Normalization mapping and later collision derivation |
| E8: named normalization with incomplete one-to-one proof | Complete proof, incomplete proof, and proved incompatibility are exclusive. | `(NORMALIZATION_PROOF_INCOMPLETE,)` | `NORMALIZATION_PROOF_INCOMPLETE` / `UNKNOWN` | Collision conclusions requiring that proof |
| E9: named normalization proving a many-to-one external-to-current ownership mapping | This is a proved incompatibility, not incomplete evidence. | `(IDENTITY_MODEL_INCOMPATIBLE,)` | `IDENTITY_MODEL_INCOMPATIBLE` / `UNSUPPORTED` | Later collision categories |

Each E fixture uses a structurally valid currently representable identity and
fully supporting capability/range evidence. The positive control uses a
matching current consistent rule set and complete current namespace evidence
proving one-to-one mapping and no collision.

**Group F - range failures**

F1 uses one valid fractional request with current usable evidence: numerator
`-129` against signed 8-bit `[-128, 127]`, denominator `256` against unsigned
8-bit `[0, 255]`, and a requested effective-rational representability range
whose evidence is explicitly unsupported. Distinct domains make the reasons
co-applicable. The literal tuple is
`(RANGE_UNSUPPORTED, RANGE_UNDERFLOW, RANGE_OVERFLOW,
BIT_WIDTH_OVERFLOW)`, led by `RANGE_UNSUPPORTED`, with terminal
`UNSUPPORTED`. Name categories are supporting and suppressed. The range
within-category order is missing, invalid evidence, unsupported, underflow,
overflow, bit-width overflow, then empty discrete intersection after
request-structural invalid/empty checks.

States that cannot coexist for the same range key use separate literal
fixtures:

- F2 missing required range:
  `(RANGE_EVIDENCE_MISSING,)` / leading `RANGE_EVIDENCE_MISSING` /
  `UNKNOWN`;
- F3 typed invalid observed range:
  `(INVALID_RANGE_EVIDENCE,)` / leading `INVALID_RANGE_EVIDENCE` /
  `UNKNOWN`;
- F4 reversed configured request:
  `(INVALID_RANGE_REQUEST,)` / leading `INVALID_RANGE_REQUEST` /
  `UNSUPPORTED`, with evidence evaluation suppressed;
- F5 equal configured endpoints with either exclusive:
  `(EMPTY_CONFIGURED_RANGE,)` / leading `EMPTY_CONFIGURED_RANGE` /
  `UNSUPPORTED`, with evidence evaluation suppressed; and
- F6 converted or intersected lower greater than upper:
  `(EMPTY_DISCRETE_INTERSECTION,)` / leading
  `EMPTY_DISCRETE_INTERSECTION` / `UNSUPPORTED`.

The F-group positive control uses the same domains with current supported
ranges containing each requested value and a non-empty exact intersection.

**Separate success and single-category controls**

Success is one entirely separate fixture with current matching evidence,
resolved applicability, all active primitives supported, valid non-empty
ranges, usable rules, and complete collision-free namespace evidence. It
expects exactly `(SUPPORTED_REQUIREMENT,)`. No failing fixture contains that
reason. Missing observation, raw/direct untrusted evidence, each single
applicability mismatch, each required save/activation primitive state, and any
other reason that cannot legally coexist with its group are tested as explicit
single-category fixtures with their literal one-element tuple.

Derived support is not a new assertion. A derived record is evaluated from its
complete direct-source DAG: contradiction yields the typed contradictory
observation and `UNKNOWN`; any current unsupported source yields
`UNSUPPORTED`; otherwise any missing, foreign, mismatched, unavailable,
stale, invalid, or unknown source yields `UNKNOWN`; only all current supported
sources yield `SUPPORTED`. Cycles and duplicate/foreign source identities are
typed derivation contradictions. The source tuple is stored in canonical
source-identity order.

##### Primitive operations, compounds, and postconditions

The primitive enum contains only indivisible adapter calls. Compound
requirements are policy bundles. Required postconditions describe what a later
runtime transaction must verify; item 2 evaluates capability to attempt their
proof but never asserts that a runtime result occurred.

| Terminal compound requirement | Ordered dependency expansion | Required future postconditions |
| --- | --- | --- |
| Exact readback | requested integer/numerator/denominator/flag reads | exact requested fields observed |
| Exact restoration | reads and writes for every captured applicable field; for a fractional pair, `COORDINATED_FRACTIONAL_WRITE`; restoration-context save if `REQUIRED`; restoration-context activation if `REQUIRED`; exact-readback expansion | restored state equals captured state; save confirmed only when restoration save is `REQUIRED`; activation confirmed only when restoration activation is `REQUIRED` |
| Existing read | existence lookup; requested integer/numerator/denominator/flag reads | profile exists; exact requested fields observed |
| Existing integer mutation | existence lookup; capture integer read; integer write; forward-integer save if `REQUIRED`; forward-integer activation if `REQUIRED`; exact integer readback; exact integer restoration using its separate restoration applicability | profile exists; exact requested value observed; save confirmed only when forward save is `REQUIRED`; activation confirmed only when forward activation is `REQUIRED`; exact restoration remains possible |
| Existing fractional mutation | existence lookup; capture numerator read; capture denominator read; `COORDINATED_FRACTIONAL_WRITE`; forward-fractional save if `REQUIRED`; forward-fractional activation if `REQUIRED`; exact numerator-and-denominator readback; exact numerator-and-denominator restoration using its separate restoration applicability | profile exists; exact requested pair observed; save confirmed only when forward save is `REQUIRED`; activation confirmed only when forward activation is `REQUIRED`; exact restoration remains possible |
| Verified absence | verify absence | profile absent |
| Deletion restoration | delete; verified-absence expansion | profile absent |
| Profile creation transaction | existence lookup; create; required integer or fractional capture/read and write expansion; creation-context save if `REQUIRED`; creation-context activation if `REQUIRED`; exact-readback expansion; deletion-restoration expansion | profile exists after create; exact value observed; save/activation confirmed only when each is `REQUIRED`; profile absent after restoration |

`COORDINATED_FRACTIONAL_WRITE` is the sole internal bundle. It expands in a
mechanism-declared order to exactly one numerator-write primitive and one
denominator-write primitive for the same observation, generations, profile
kind, mechanism, field scope, and transaction policy scope. Static capability
evidence proves only that the two supported primitive writes can be serialized
in that declared order while retaining responsibility for both fields. It does
not prove backend atomicity, that either write succeeds, that save or activation
succeeds, that readback matches, or that restoration occurs. Those are later
runtime postconditions.

The dependency graph is acyclic: terminal requirements expand only to
primitives, the one internal bundle, or earlier non-recursive readback,
restoration, and absence expansions. Exact restoration never depends on the
mutation requirement that consumes it. The static evaluator flattens and
deduplicates active primitive leaves in canonical phase order while retaining
phase labels and distinct forward/restoration applicability contexts for
diagnostics. Removing any active required leaf has an independent result:
a current explicit `UNSUPPORTED` leaf makes the terminal requirement
`UNSUPPORTED`; a missing, unknown, stale, invalid, or temporarily unavailable
leaf makes it `UNKNOWN`; only all current supported leaves allow `SUPPORTED`.
Numerator-only or denominator-only read/write applicability therefore never
supports existing fractional mutation. Unknown or missing save/activation
applicability prevents support; a matching `NOT_REQUIRED` record omits that
primitive without failure. A save/activation primitive that is `REQUIRED` but
missing or unusable prevents support, as do missing exact readback or exact
restoration.

The terminal capability result is still not mutation admission. Item 4 must
later provide the mutation journal, rollback interfaces, degraded-state
construction, and unresolved-ownership guard before item 5 can consume an
otherwise supported mutation requirement. Those coordinator/runtime
prerequisites are not fabricated as item-2 capability records.

`SAVE_CONFIRMED`, `ACTIVATION_CONFIRMED`, `EXACT_VALUE_OBSERVED`,
`PROFILE_EXISTS`, `PROFILE_ABSENT`, and
`RESTORED_STATE_EQUALS_CAPTURED_STATE` are deterministic future requirements,
not capability claims. Their actual pass/fail values are runtime results in
items 3, 5, and 6. `SAVE_CONFIRMED` and `ACTIVATION_CONFIRMED` enter a
particular future graph only when the matching applicability record is
`REQUIRED`; `NOT_REQUIRED` omits both primitive and postcondition, while
`UNKNOWN` cannot support the compound. No item-2 record may claim that
readback or restoration has already succeeded.

##### Domain-specific exact range contracts

Ranges use immutable `RtssExactBound(value, inclusive)` endpoints and an
explicit domain. A missing endpoint is an intentional open bound only inside an
otherwise admitted current range record; absence of a required range record is
`UNKNOWN / RANGE_EVIDENCE_MISSING`. `UNSUPPORTED` range evidence is explicit
and returns `UNSUPPORTED / RANGE_UNSUPPORTED`. An invalid observed range is
retained only as typed invalid observation evidence and returns `UNKNOWN /
INVALID_RANGE_EVIDENCE`. Every range record inherits the admitted observation
identity, backend and capability generations, mechanism, primitive, profile
kind, field domain, origin, complete derived-source references, validity, and
provenance; a bare numeric interval is not capability evidence.

| Range domain | Exact numeric type and construction rules |
| --- | --- |
| Integer FPS limit | Plain integer; zero is representable unless admitted signedness/range says otherwise. A controller request may separately require a positive target. |
| Fractional numerator | Plain integer, independently applicable; zero is representable, sign requires explicit mechanism evidence. |
| Fractional denominator | Positive plain integer, independently applicable; zero is always construction-invalid. |
| Effective rational FPS | Existing reduced `RationalCap`; compared by exact cross multiplication. It is optional backend representability evidence only, never a controller tuning range and never a substitute for exact stored numerator/denominator support. |
| Stored-field bit width | Positive plain integer plus field domain and exactly one representation: `UNSIGNED`, `TWOS_COMPLEMENT_SIGNED`, or `UNKNOWN`. For width `w > 0`, unsigned derives `[0, 2^w - 1]`; two's complement derives `[-2^(w-1), 2^(w-1) - 1]`. `UNKNOWN` or any future representation cannot derive an interval and evaluates `UNKNOWN / BIT_WIDTH_REPRESENTATION_UNKNOWN`. |
| Configured controller bound | Exact `int`, finite `Decimal`, or `RationalCap` policy input converted without float approximation. It restricts a request but does not prove backend capability or generate allowed cap values. |

Stored integer, numerator, and denominator observations and requested stored
values accept exact plain integers only; Boolean values and non-integral stored
values are construction errors. Denominator values are strictly positive.
There is no rational substitution between a stored field and an effective cap.
Bit-width intersection occurs only inside the same stored-field domain.

Configured policy endpoints may be non-integral because their conversion to a
discrete stored-field interval is exact. First convert a finite `Decimal` to
the exact rational represented by its sign, coefficient, and base-10 exponent;
an `int` becomes `n/1`; and a `RationalCap` uses its existing reduced numerator
and positive denominator. No float is accepted or produced. For exact lower
endpoint `L`, the discrete inclusive lower bound is `ceil(L)` when `L` is
inclusive and `floor(L) + 1` when `L` is exclusive. For exact upper endpoint
`U`, the discrete inclusive upper bound is `floor(U)` when `U` is inclusive
and `ceil(U) - 1` when `U` is exclusive. Open endpoints remain open. The
converted denominator lower bound is additionally intersected with `1`.
Conversion provenance retains the original endpoint, inclusivity, exact
rational value, converted integer, and rule used.

The independent negative conversion oracle is literal:

| Bound type | Exact input | Exact converted inclusive discrete bound |
| --- | ---: | ---: |
| Inclusive lower | `-60.5` | `-60` |
| Exclusive lower | `-60` | `-59` |
| Exclusive lower | `-60.5` | `-60` |
| Inclusive upper | `-59.5` | `-60` |
| Exclusive upper | `-60` | `-61` |
| Exclusive upper | `-59.5` | `-60` |

These values follow `ceil(L)`, `floor(L) + 1`, `floor(U)`, and
`ceil(U) - 1` exactly; no expected value is derived from future
implementation code. The review request's candidate `-59` for exclusive upper
`-59.5` is not adopted because `ceil(-59.5) - 1 = -59 - 1 = -60`, and `-59`
does not satisfy the strict upper bound. Required interval controls are also
literal:

- lower `-60.5` inclusive and upper `-58.5` exclusive convert to `-60`
  and `-59`, so the discrete set is exactly `{-60, -59}`;
- lower `-60` exclusive and upper `-59.5` inclusive convert to `-59`
  and `-60`, so the result is exactly
  `UNSUPPORTED / EMPTY_DISCRETE_INTERSECTION`;
- mixed-sign lower `-1.5` inclusive and upper `1.5` exclusive convert to
  `-1` and `1`, so the set is exactly `{-1, 0, 1}`;
- exact negative inclusive lower and upper `-60` convert to `-60` and
  produce exactly `{-60}`; making either equal endpoint exclusive is exactly
  `UNSUPPORTED / EMPTY_CONFIGURED_RANGE`;
- `Decimal("-0")` converts exactly to rational `0/1` and discrete `0`; the
  policy has no distinct negative-zero value; and
- for signed two's-complement width 8, request `-129` is one below `-128` and
  yields the ordered range reasons
  `(RANGE_UNDERFLOW, BIT_WIDTH_OVERFLOW)`.

Effective-rational bounds use canonical reduced numerator/denominator pairs
with a positive denominator and compare only by exact cross multiplication.
Finite `Decimal` policy bounds use the exact base-10 conversion above.
Numerator/denominator ranges never substitute for an effective-rational range,
or vice versa. Sequence item 2 validates one requested stored value or
configured interval against admitted RTSS evidence; it does not derive or tune
a controller cap ladder.

Public request construction rejects wrong types, Boolean integers, non-finite
`Decimal` values, denominator zero, and non-positive bit width. A reversed
configured range is a reachable structural policy failure:
`UNSUPPORTED / INVALID_RANGE_REQUEST`; equal configured endpoints with either
exclusive are `UNSUPPORTED / EMPTY_CONFIGURED_RANGE`. After exact discrete
conversion or backend/bit-width intersection, lower greater than upper is
`UNSUPPORTED / EMPTY_DISCRETE_INTERSECTION`. A raw adapter report with reversed
bounds, an invalid endpoint, or a denominator bound below one cannot construct
selectable range evidence; admission retains only typed
`INVALID_RANGE_EVIDENCE`, which evaluates `UNKNOWN`.

Large integers remain arbitrary-precision during policy evaluation. A stored
field request one step below or above an admitted or derived interval is
`UNSUPPORTED / RANGE_UNDERFLOW` or `UNSUPPORTED / RANGE_OVERFLOW`;
bit-width-derived overflow additionally retains `BIT_WIDTH_OVERFLOW`. Parser
resource limits are separate denial-of-service bounds and are never reported
as backend capability.

Intersection takes the exact greater lower endpoint and lesser upper endpoint.
When equal exact values come from multiple inputs, inclusivity is the logical
AND of their flags. Equal inclusive continuous bounds form one point; equal
exclusive continuous bounds are empty. Discrete intersections operate on the
already converted inclusive integer endpoints. Open lower or upper endpoints
remain open. Numerator and denominator intersections are computed
independently and both must succeed when the terminal compound requires both.
Missing admitted range evidence is `UNKNOWN / RANGE_EVIDENCE_MISSING`;
explicitly unsupported range evidence is `UNSUPPORTED / RANGE_UNSUPPORTED`;
typed invalid observed evidence is `UNKNOWN / INVALID_RANGE_EVIDENCE`.

Every range decision records exact provenance: request domain and original
configured endpoints, conversion rules and converted endpoints, admitted range
observation identity and backend/capability generations, mechanism/operation/
field scope, explicit range support state, bit width and representation when
used, each intersection operand, and the final exact intersection. No
floating-point approximation, silent rounding, rational-equivalence
substitution, or cross-domain reuse is permitted.

#### Planned supported-name policy model

`RtssSupportedNameRequest` is a public untrusted immutable request containing:

- the exact original name and explicit `ProfileKind`;
- exact requested access mechanism and primitive or compound requirement;
- exact name context `EXISTING_LOOKUP`, `EXISTING_MUTATION`, or
  `CREATE_PROFILE` (intent only; sequence item 3 later verifies existence); and
- references to the capability evaluation context and required admitted
  name-rule and namespace snapshot identities.

The request contains no claimed canonical identity, encoded representation,
peer-name set, collision result, completeness assertion, backend generation, or
capability generation. The policy derives canonical identity from the exact raw
name after minimal structural checks. Matching expectations belong to
`RtssCapabilityEvaluationContext`; authoritative derivations and peer
completeness belong only to admitted evidence.

Name rules do not live inside the capability observation. The separate
factory-controlled admitted rule-set contract below contains mechanism- and
kind-specific immutable evidence:

- encoding identifier and exact encoded representation/round-trip evidence;
- character and encoded-byte component limits;
- character and encoded-byte total-target limits, including known suffix
  expansion when applicable;
- explicit admitted/disallowed character evidence;
- explicit case-comparison behavior;
- explicit normalization behavior or an explicit no-normalization rule;
- a reference to admitted namespace/collision evidence for the exact rule and
  target namespace; and
- separate applicability to existing lookup, read, mutation, and creation.

Absent evidence is not replaced by ASCII, ANSI, UTF-8, UTF-16, a locale code
page, Windows path limits, filename limits, reserved-name lists, case folding,
or Unicode normalization guesses.

##### Raw-name and current-identity boundary

The raw classifier accepts one string and computes every matching reason
without rewriting it. A non-string is rejected by request construction. The
classifier aggregates reasons, deduplicates them, sorts them by the closed
order below, and uses the first reason as the leading reason. It completes all
structural checks in layers 1-4 for diagnostics; any match then short-circuits
before the current-model and evidence layers. If structure passes, it completes
all current-model checks in layer 5; any match then short-circuits before
evidence. Capability or namespace evidence is never consulted after a
structural or current-model failure.

The closed layers and within-layer reason order are:

1. impossible scalar/content: `EMPTY_NAME`, `WHITESPACE_ONLY_NAME`,
   `NUL_IN_NAME`, `CONTROL_CHARACTER`;
2. path form: `DEVICE_PATH`, `UNC_PATH`, `DRIVE_QUALIFIED_PATH`,
   `ROOTED_PATH`, `FULL_PATH`;
3. traversal/component form: `DOT_PATH_SEGMENT`, `PATH_SEPARATOR`;
4. stream/colon form: `ALTERNATE_DATA_STREAM`, `COLON_PATH_CONFUSION`;
5. current canonical-model representability, led by
   `IDENTITY_MODEL_INCOMPATIBLE`, then detail reasons:
   `EDGE_WHITESPACE`, `TRAILING_DOT`, `TRAILING_SPACE`,
   `PROFILE_KIND_SHAPE_INCOMPATIBLE`,
   `NON_ASCII_CURRENT_MODEL`, `MISSING_EXECUTABLE_SUFFIX`,
   `EMPTY_EXECUTABLE_STEM`, `RESERVED_STEM_CURRENT_MODEL`,
   `WINDOWS_CHARACTER_CURRENT_MODEL`;
6. applicable capability name-rule evidence in encoding, character, and length
   reason order; and
7. namespace evidence in completeness, case, normalization, encoding-collision,
   and canonical-collision order.

Path predicates are lexical and platform-independent: device prefixes include
`\\?\` and `\\.\`; UNC means two leading separators; drive-qualified means an
ASCII letter plus colon at the beginning or immediately after a recognized
device prefix; rooted means a leading separator or drive-qualified absolute
form; full path means any multi-component or rooted path form; dot segment
means an exact `.` or `..` component separated by either slash; ADS means a
colon outside the drive designator followed by stream text; and the generic
colon reason matches every remaining colon. Both slash directions count as
separators.

Layers 1-4 are structural injection/path-confusion failures and return
`UNSUPPORTED` with the first aggregated structural reason. Layer 5 contains
limitations of the accepted `CanonicalProfileIdentity` model rather than
universal RTSS facts. Names matching it return `UNSUPPORTED` with
`IDENTITY_MODEL_INCOMPATIBLE` as the leading terminal reason and the ordered
classifier details after it. Missing, stale, invalid, contradictory, or
otherwise-supporting name-rule evidence cannot change that result and is not
evaluated. This includes non-ASCII: all such evidence variants have the same
terminal result until a separately accepted identity migration exists.

Only after those checks does policy attempt exact current canonical
construction. It does not insert `.exe`, strip whitespace or dots, replace
characters, change case, normalize, or extract a basename. A name rejected by
the accepted constructor cannot proceed to capability or namespace evaluation
and can never be `SUPPORTED` or `UNKNOWN`. Broader support requires a separate
proposed identity migration, independent review, explicit acceptance, and
corresponding changes to `RtssGeneration` and `RtssOwnershipToken` before item
3 can consume the identity. No migration is part of item 2.

The exhaustive classification of current and required rules is:

| Raw-name case | Current constructor behavior | Planned category / raw invariant | Terminal result | Evidence override? | Later phase and required test |
| --- | --- | --- | --- | --- | --- |
| Empty string | Reject | Structural invalid | `UNSUPPORTED / EMPTY_NAME` | No | Item 2 positive non-empty and negative empty |
| Whitespace-only | Reject through edge-whitespace rule | Structural invalid | `UNSUPPORTED / WHITESPACE_ONLY_NAME` | No | Item 2 exact whitespace variants |
| Leading/trailing whitespace | Reject | Current identity-model invariant and path-confusion guard | `UNSUPPORTED / IDENTITY_MODEL_INCOMPATIBLE` | No in current model | Migration review; leading/trailing controls |
| NUL | Reject as control | Structural invalid | `UNSUPPORTED / NUL_IN_NAME` | No | Item 2 embedded NUL |
| Other control characters, including DEL | Reject | Structural invalid | `UNSUPPORTED / CONTROL_CHARACTER` | No | Item 2 each boundary class |
| `/` or `\` separator | Reject | Structural invalid | `UNSUPPORTED / PATH_SEPARATOR` | No | Item 2 both separators |
| Rooted path | Reject through separator/colon | Structural invalid | `UNSUPPORTED / ROOTED_PATH` | No | Item 2 rooted forms |
| UNC form | Reject through separator | Structural invalid | `UNSUPPORTED / UNC_PATH` | No | Item 2 UNC form |
| Drive-qualified form | Reject through colon/separator | Structural invalid | `UNSUPPORTED / DRIVE_QUALIFIED_PATH` | No | Item 2 drive-relative and absolute |
| Alternate data stream | Reject through colon | Structural invalid | `UNSUPPORTED / ALTERNATE_DATA_STREAM` | No | Item 2 ADS form |
| Device path | Reject through separator/colon | Structural invalid | `UNSUPPORTED / DEVICE_PATH` | No | Item 2 device namespaces |
| `.` or `..` path segment, including embedded segment form | Reject direct dot forms; separators reject embedded forms | Structural invalid | `UNSUPPORTED / DOT_PATH_SEGMENT` | No | Item 2 current/parent segments |
| Missing `.exe` | Reject | Current identity-model invariant, not universal RTSS truth | `UNSUPPORTED / IDENTITY_MODEL_INCOMPATIBLE` | No in item 2 | Identity migration/item 12; positive `.exe`, negative missing |
| Non-ASCII | Reject | Current identity-model invariant; backend encoding capability-dependent beyond current model | always `UNSUPPORTED / IDENTITY_MODEL_INCOMPATIBLE`, before name-rule evidence | No in item 2 | Migration plus item 12 encoding; missing/stale/supporting-rule controls |
| Trailing dot | Reject | Current identity-model invariant and Windows-context ambiguity | `UNSUPPORTED / IDENTITY_MODEL_INCOMPATIBLE` | No in current model | Migration/item 12; trailing-dot test |
| Trailing space | Reject through edge-whitespace | Current identity-model invariant and Windows-context ambiguity | `UNSUPPORTED / IDENTITY_MODEL_INCOMPATIBLE` | No in current model | Migration/item 12; trailing-space test |
| Windows reserved stem | Reject | Current identity-model invariant; capability-dependent RTSS fact is deferred | `UNSUPPORTED / IDENTITY_MODEL_INCOMPATIBLE` | No in current model | Migration/item 12; every reserved family |
| Invalid Windows filename characters `< > " \| ? *` | Reject | Current identity-model invariant; actual RTSS character support is capability-dependent | `UNSUPPORTED / IDENTITY_MODEL_INCOMPATIBLE` | No in current model | Migration/item 12; character matrix |
| Colon | Reject | Structural invalid because of drive/ADS ambiguity | `UNSUPPORTED / COLON_PATH_CONFUSION` unless a higher path/ADS reason leads | No | Item 2 colon forms |
| Global profile shape | Only canonical name `Global` constructs directly | Current identity-model invariant | exact `Global` may proceed; other raw shape is `UNSUPPORTED / IDENTITY_MODEL_INCOMPATIBLE` | No in current model | Item 2 Global positive and altered-shape negatives |
| Application profile shape | Basename with non-empty stem and `.exe` | Current identity-model invariant | exact representable shape may proceed | No in current model | Item 2 application positive and empty-stem negatives |
| Basename versus full path | Basename only; paths reject | Structural invalid for raw request; external namespace fact remains context-dependent | `UNSUPPORTED` with the first applicable path-form reason | No | Item 2 path controls; identity design/item 12 |
| Case-only spelling | Constructible; equality case-folds | Current ownership invariant plus capability/collision-dependent namespace fact | result from namespace table below | Evidence cannot create distinct current owners | Item 2 case matrix; item 12 live behavior |
| Unicode normalization | No normalization performed; non-ASCII rejects | Deferred capability fact and current identity-model invariant | representable ASCII may use the namespace table; non-ASCII remains `IDENTITY_MODEL_INCOMPATIBLE` | No implicit override | Migration/item 12 normalization matrix |

Representative overlaps have these independent expected ordered reasons:

| Raw input | Leading reason | Complete ordered classifier reasons before short-circuit |
| --- | --- | --- |
| `C:\game.exe` | `DRIVE_QUALIFIED_PATH` | `DRIVE_QUALIFIED_PATH`, `ROOTED_PATH`, `FULL_PATH`, `PATH_SEPARATOR`, `COLON_PATH_CONFUSION` |
| `\\server\share\game.exe` | `UNC_PATH` | `UNC_PATH`, `ROOTED_PATH`, `FULL_PATH`, `PATH_SEPARATOR` |
| `\\?\C:\game.exe` | `DEVICE_PATH` | `DEVICE_PATH`, `UNC_PATH`, `DRIVE_QUALIFIED_PATH`, `ROOTED_PATH`, `FULL_PATH`, `PATH_SEPARATOR`, `COLON_PATH_CONFUSION` |
| `..\game.exe` | `FULL_PATH` | `FULL_PATH`, `DOT_PATH_SEGMENT`, `PATH_SEPARATOR` |
| `folder\..\game.exe` | `FULL_PATH` | `FULL_PATH`, `DOT_PATH_SEGMENT`, `PATH_SEPARATOR` |
| `game.exe:stream` | `ALTERNATE_DATA_STREAM` | `ALTERNATE_DATA_STREAM`, `COLON_PATH_CONFUSION` |
| `/game.exe` | `ROOTED_PATH` | `ROOTED_PATH`, `FULL_PATH`, `PATH_SEPARATOR` |
| `é.exe` with missing, stale, or supporting rules | `IDENTITY_MODEL_INCOMPATIBLE` | `IDENTITY_MODEL_INCOMPATIBLE`, `NON_ASCII_CURRENT_MODEL` |
| `game` with missing or supporting rules | `IDENTITY_MODEL_INCOMPATIBLE` | `IDENTITY_MODEL_INCOMPATIBLE`, `MISSING_EXECUTABLE_SUFFIX` |
| `game.exe` | none | no classifier failure; continue to capability/name-rule evidence |

##### Factory-controlled admitted name-rule evidence

`RtssAdmittedNameRuleSet` is the sole authoritative name-rule owner. It is a
separate immutable factory-controlled (`init=False`) object, not a nested
capability-observation field and not a raw request field. It contains:

- one opaque structural rule-set identity and the exact parent admitted
  capability-observation identity;
- exact backend and capability generations;
- profile-kind and namespace scope;
- complete applicability keys for mechanism, primitive or terminal compound,
  and `EXISTING_LOOKUP`, `EXISTING_MUTATION`, or `CREATE_PROFILE`;
- exact encoding and round-trip rules, character and encoded-byte component/
  total limits, character admission rules, case/comparison rules, and
  normalization rules;
- immutable provenance and source references;
- validity `CURRENT`, `STALE`, or `INVALID`;
- diagnostic state `CONSISTENT` or `CONTRADICTORY`; and
- an explicit complete-applicability manifest.

The deterministic admission factory is the only constructor. Tests feed it
untrusted `RtssRawNameRuleReport` records; item 3 or item 12 later owns trusted
admission. Raw reports, caller-created mappings, and values copied from a rule
set cannot prove support. A consistent rule set contains exactly one rule for
each declared applicability key and complete coverage for the evaluated key.
Name-rule applicability has one literal complete canonical key:

```text
(
    rule_set_identity,
    parent_observation_identity,
    backend_generation,
    capability_generation,
    profile_kind,
    namespace_scope,
    mechanism,
    tagged_subject_kind,
    exact_subject,
    name_context,
)
```

`tagged_subject_kind` is exactly `PRIMITIVE` or `TERMINAL_COMPOUND`, and
`exact_subject` is exactly one member of that taxonomy; the tag prevents a
primitive and compound with similar values from colliding. All other
dimensions are exact. Wildcard, prefix, range, all-mechanisms, all-primitives,
all-compounds, all-contexts, or untagged primitive/compound-polymorphic
applicability is malformed and produces a current contradictory rule set with
typed `NAME_RULE_SCOPE_NOT_EXACT`. Rule content may contain the already-planned
exact character/length/encoding policy, but broad applicability scope may not.
A later adapter must expand broad source scope into exact records before
admission.

One aggregate rule record owns each complete key. Two legal records are exact
duplicates iff their complete canonical keys are equal; because every
dimension is exact and no wildcard is admitted, legal name-rule applicability
overlaps iff those complete keys are equal. A second record with that key,
whether content-equal or content-conflicting, produces
`NAME_RULE_EXACT_DUPLICATE`; there is no first/last-wins merge or silent
deduplication. Different complete keys do not overlap and may coexist.
Canonical key comparison uses the same structural-value and enum-declaration
ordering as capability admission. Duplicate conflict pairs and diagnostics are
sorted by diagnostic declaration order, lesser key, greater key, then
provenance/source reference, so reverse input order is invariant.

Any duplicate or non-exact applicability report produces one current
`CONTRADICTORY` admitted rule set with a canonical non-empty conflict tuple and
no selectable rules. Its public result is exactly `UNKNOWN /
CONTRADICTORY_NAME_RULES`; the factory-only duplicate/scope diagnostic is not a
public evaluator reason. Contradictory stale/invalid combinations, missing
coverage, or selectable rules inside a contradictory set are construction
errors.

Every reconstruction path, including `dataclasses.replace()`, must re-enter the
same invariant validator. An unchanged structurally equal factory copy is
equivalent; object identity is never required. Changing the rule-set identity,
parent identity, generations, scope, applicability, rule content, provenance,
validity, contradiction state, or nested source references either fails
construction or yields non-matching evidence and cannot retain admission.

The evaluator matches, in order: rule-set identity requested by the public
request; parent capability-observation identity; backend generation;
capability generation; profile kind; namespace scope; mechanism; exact
primitive or terminal compound; and name context. Missing or raw rules are
`UNKNOWN / NAME_RULE_EVIDENCE_MISSING`; for one present rule set, all legally
co-applicable foreign-identity, parent, generation, kind, scope, mechanism,
operation, and context mismatches are aggregated in that order before
returning `UNKNOWN`; invalid then stale rule sets are `UNKNOWN`; and a current
contradictory rule set is
`UNKNOWN / CONTRADICTORY_NAME_RULES`. Only a current consistent complete
matching rule set may continue. A structurally equal admitted copy is a
positive control.

##### Factory-controlled namespace and collision evidence

`RtssAdmittedNamespaceObservation` is immutable and factory-controlled
(`init=False`). It contains namespace snapshot identity, parent capability
observation identity, backend generation, capability generation, profile kind,
  mechanism, operation and exact lookup/mutation/creation scope, namespace identifier,
comparison mode, normalization mode, encoding context when relevant,
completeness mode `COMPLETE_ENUMERATION` or `AUTHORITATIVE_EXACT_QUERY`, the
immutable exact-name enumeration or authoritative exact-query/collision result,
provenance, validity/freshness, and typed diagnostic state. Complete enumeration
records the proof source and all exact names in canonical evidence order.
Authoritative exact query records query semantics, queried exact name and
canonical/encoding keys, and a definitive collision/no-collision result.

Comparison mode is the closed enum `CASE_SENSITIVE`, `CASE_INSENSITIVE`, or
`UNKNOWN`. Normalization mode is `EXACT_NONE`, `NAMED`, or `UNKNOWN`; `NAMED`
requires a non-empty exact algorithm identifier and the observed normalized
keys, without asking policy code to perform normalization. Encoding context
contains an exact encoding identifier, immutable parameters, encoded bytes,
round-trip result, and encoded collision key. Unknown enum additions fail
closed. Namespace scope is an opaque immutable identifier whose equality is
structural; it is not inferred from a filesystem path.

The normalization compatibility vocabulary is exact:

- the **external exact key** is the unchanged original profile name;
- the **external normalized key** is the exact key supplied by an admitted
  named normalization observation, never computed or rewritten by policy;
- the **current canonical ownership key** is
  `CanonicalProfileIdentity.canonical_key`, including its accepted ASCII
  `casefold()` behavior; and
- the **external identity** is the authoritative namespace identity to which
  the external exact and normalized keys resolve.

`EXACT_NONE` is compatible only when the admitted normalized key equals the
external exact key and complete namespace evidence proves no case, encoding,
or canonical-key collider. `NAMED` is compatible for an existing exact lookup
or existing mutation only when current, complete evidence proves: the exact
input resolves to exactly one external identity; its normalized key resolves
to that same and only identity; that identity maps to exactly one representable
current canonical ownership key; no other external exact, normalized, encoded,
case, or canonical key maps to that ownership key; and the unchanged exact
original remains in the audit record.

For creation, the same rule is prospective: authoritative complete enumeration
or exact-query semantics must prove the requested external exact key, external
normalized key, encoded key, case variants, and current canonical ownership key
are all absent; the predicted created external identity must map to exactly one
representable current canonical ownership key; and no other key may map to it.
A known named algorithm and a Boolean "no collision" assertion are
insufficient without this complete mapping proof.

A proved collider or many-to-one external-to-current mapping is
`UNSUPPORTED / NORMALIZATION_COLLISION` or
`UNSUPPORTED / IDENTITY_MODEL_INCOMPATIBLE`, respectively. Incomplete proof is
`UNKNOWN / NORMALIZATION_PROOF_INCOMPLETE`; `UNKNOWN` normalization is
`UNKNOWN / NORMALIZATION_UNKNOWN`. Missing, stale, invalid, foreign, or
generation-mismatched rule/namespace evidence is `UNKNOWN` before the
compatibility predicate. A current-model-unrepresentable name was already
short-circuited as `UNSUPPORTED` and can never become supported by a named
normalization rule.

The public request references the snapshot identity only. It cannot supply,
filter, or claim a peer set, which closes omitted-collider attacks. Namespace
evidence is mandatory whenever the decision depends on existing exact lookup,
mutation, creation, canonical case-folding, non-trivial normalization, encoding
round trip, or a derived encoded/canonical key. An exact lookup may use an
authoritative exact-query proof; creation and any operation that could create a
new ownership key require complete enumeration or an authoritative query that
proves absence for the exact external name and every current canonical,
normalization, and encoding collision key.

| Namespace state | Exact terminal result |
| --- | --- |
| Missing, stale, invalid, incomplete, foreign snapshot, or backend/capability generation mismatch | `UNKNOWN` with the matching evidence reason |
| Complete/current exact no-collision query | Continue evaluation; may become `SUPPORTED` |
| Case-sensitive single name with complete proof and no case-distinct peer | Existing exact lookup/mutation may continue; creation also needs authoritative canonical-key absence |
| Admitted case-distinct pair collapsing under current case-folded identity | `UNSUPPORTED / CASE_COLLISION` |
| Case-insensitive canonical-key collision | `UNSUPPORTED / CASE_COLLISION` |
| Unknown normalization behavior | `UNKNOWN / NORMALIZATION_UNKNOWN` |
| `EXACT_NONE`, complete proof, no collision | Continue evaluation; may become `SUPPORTED` |
| `NAMED`, complete one-to-one proof, no collision | Continue evaluation; may become `SUPPORTED` |
| `NAMED`, incomplete proof | `UNKNOWN / NORMALIZATION_PROOF_INCOMPLETE` |
| `NAMED`, incompatible many-to-one ownership mapping | `UNSUPPORTED / IDENTITY_MODEL_INCOMPATIBLE` |
| Proven normalization-equivalent collision | `UNSUPPORTED / NORMALIZATION_COLLISION` |
| Lossy or colliding encoding round trip | `UNSUPPORTED / ENCODING_COLLISION` |
| Proven current canonical-key collision | `UNSUPPORTED / CANONICAL_COLLISION`; may coexist diagnostically with case, normalization, or encoding collision |
| Existing exact lookup with authoritative exact no-collision proof | Continue against exact lookup dependencies |
| New profile creation without complete collision-key absence proof | `UNKNOWN / NAMESPACE_COMPLETENESS_MISSING` |

`RtssSupportedNameDecision` returns:

- `SUPPORTED`, `UNSUPPORTED`, or `UNKNOWN`;
- the unchanged exact original name and profile kind;
- the exact requested mechanism, primitive/compound requirement, and exact
  lookup/mutation/creation context;
- the canonical identity and encoded representation only when their evidence
  is admitted and unambiguous;
- observation identity, backend generation, and capability generation when
  evidence is present;
- all typed reasons in deterministic order; and
- an auditable collision/derivation summary that cannot mutate the name.

No decision silently truncates, replaces, strips, normalizes, changes case, or
selects a different identity. Existing case-insensitive ownership equality
remains an accepted constraint. If admitted evidence says names are
case-sensitive, the policy preserves exact spellings in diagnostics. One exact
name may proceed only with the complete no-collision proof specified above. A
case-distinct pair that collapses under current ownership always returns
`UNSUPPORTED / CASE_COLLISION`; it is never alternatively `UNKNOWN`.
Supporting both names as distinct owners would require a separately planned,
reviewed, and accepted identity-model migration.

#### Exact fail-closed evaluation rules

The exact name-policy signature is:

`evaluate_supported_name(request, context, admitted_capability_observation, admitted_name_rule_set, admitted_namespace_observation) -> decision`

The arguments have exact types `RtssSupportedNameRequest`,
`RtssCapabilityEvaluationContext`,
`RtssAdmittedCapabilityObservation | None`,
`RtssAdmittedNameRuleSet | None`, and
`RtssAdmittedNamespaceObservation | None`. No nested or alternate rule owner is
accepted.

Capability and name decisions use the same context-matching and stable-reason
algebra. Caller-authored context and request fields remain intent only.

Policy evaluation follows this deterministic order:

1. Run the complete raw classifier without live access or name rewriting.
   Aggregate all reasons across structural layers 1-4, or across current-model
   layer 5 only when structure passes. Structural failure or current
   canonical-model incompatibility returns `UNSUPPORTED` immediately, before
   capability, name-rule, or namespace evidence.
2. If no admitted observation exists, return `UNKNOWN /
   CAPABILITY_EVIDENCE_MISSING`. A raw report or current public capability
   object does not substitute for it.
3. Match observation identity, backend generation, capability generation,
   profile kind, and policy scope against context. Foreign, mismatched,
   stale/invalid, untrusted, or contradictory evidence is `UNKNOWN` under the
   closed algebra above. There is no observation-unavailable branch; temporary
   unavailability is evaluated only on a current selected primitive record.
4. Select only the exact requested mechanism, primitive/compound requirement,
   profile kind, and exact-field applicability records. Aggregate the canonical
   dependency bundle using current unsupported before unknown; no other
   mechanism is tried.
5. Require every active dependency for the requested operation. Read never
   implies write; write never implies readback; readback never implies
   restoration; profile-file access never implies API support.
6. Before evaluating each save or activation primitive, match its exact
   mechanism/compound/phase applicability record. `UNKNOWN`, missing-source,
   foreign, stale, invalid, contradictory, or mismatched applicability makes
   the compound `UNKNOWN`; `NOT_REQUIRED` omits that primitive and
   postcondition; `REQUIRED` activates the primitive support check. A
   mutation-capability decision requires current support for every active
   write, save, activation, exact-readback, and exact-restoration dependency
   for every applicable field. A current explicit unsupported active
   dependency makes it `UNSUPPORTED`; a missing or unknown active dependency
   makes it `UNKNOWN`. No mutation is admitted.
7. A fractional operation requiring both exact numerator and denominator is
   supported only when both field reads, writes, readback, and restoration are
   supported through the admitted mechanism. Numerator-only support,
   denominator-only support, or an unavailable denominator uses the closed
   dependency algebra with a partial-field or denominator reason.
8. Existing-profile read may be supported independently of write or creation.
   Existing-profile mutation requires its complete mutation dependency set.
   Creation additionally requires explicit creation, deletion, verified
   absence, and created-profile restoration capability. Any current explicit
   unsupported dependency makes creation `UNSUPPORTED`; otherwise any missing,
   unknown, unavailable, stale, or invalid dependency makes it `UNKNOWN`.
9. Deletion requests require explicit deletion plus verify-absence primitives.
   Current unsupported absence verification is `UNSUPPORTED`; missing or
   unknown verification is `UNKNOWN`.
10. Match the one admitted name-rule set to its requested identity, parent
    capability observation, backend/capability generations, profile kind,
    namespace scope, exact mechanism, operation, and exact
    lookup/mutation/creation context.
    Missing, stale, invalid, foreign, mismatched, incomplete, replaced, or
    contradictory rules follow the exact rule-set outcomes above. A name
    supported for existing lookup is not thereby supported for creation or
    mutation.
11. Unknown encoding, required unknown character/byte limit, unknown
    case/normalization rule, or missing collision evidence is `UNKNOWN`.
    Explicitly unsupported encoding, a value above a known maximum, a
    character rejected by admitted rules, or a proven collision is
    `UNSUPPORTED`.
12. Exact boundary values are accepted only when every other requirement is
    supported. Under the current identity boundary, non-ASCII and every other
    constructor-incompatible name always return
    `UNSUPPORTED / IDENTITY_MODEL_INCOMPATIBLE` before missing, stale, or
    otherwise-supporting rule evidence is considered. No Unicode support is
    claimed.
13. Structurally equal immutable admitted evidence produces the same decision.
    Foreign snapshots, direct construction, replacement, enum aliases, or
    changed nested generations cannot acquire trust.

These decisions occur before capture or mutation. They do not return
`RtssApplyResult`, create ownership, or classify operation, conflict, rollback,
or degraded state.

#### Interaction with sequence item 1

The pure policy reuses `ProfileKind`, `RtssStoredFieldKind`,
`RtssDenominatorStrategy`, `CanonicalProfileIdentity`, `RtssGeneration`,
`RtssCapabilityEvidence`, and typed diagnostics where semantics already match.
It does not broaden `RtssOutcome` or `RtssFailureStep` merely to represent
policy internals; a later coordinator maps a terminal policy decision to the
existing structured transaction outcome.

The admitted observation must match the item-1 ownership/capture context before
a later coordinator may bind it. The existing captured backend generation and
capability marker remain anchors. Item 2 introduces no way to assert that a
higher generation is trusted and no path for a caller-created graph to become
authoritative. Exact requested, canonical, captured, operation, conflict, and
restoration identity remain unchanged.

Item 2 creates no single-use registry, transaction admission registry,
serialization lease, ownership holder, handoff recipient, capture, readback
binding, operation evidence, conflict evidence, mutation journal, rollback, or
release. Those existing or later responsibilities remain outside policy.

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
13. Save the admitted profile only when the exact forward-context
    applicability record is `REQUIRED`; skip it only when that record is
    `NOT_REQUIRED`. `UNKNOWN` never reaches mutation admission.
14. Request update/activation only when the exact forward-context
    applicability record is `REQUIRED`; skip it only when that record is
    `NOT_REQUIRED`.
15. Read back profile existence, stored numerator/denominator, effective cap,
    owned flags, document/revision evidence, and backend generation.
16. Compare exact requested state and return `VERIFIED`; only then may a
    controller commit logical cap state. Retain session ownership needed for
    later restore.
17. On any false return, exception, cancellation, stale generation, backend
    restart, or mismatch after possible mutation, run rollback while still
    holding serialization.
18. Rollback restores the complete captured document or exact fields according
    to the approved mechanism, restores only owned limiter bits, evaluates the
    separate exact-restoration save and activation applicability records,
    performs only the restoration operations marked `REQUIRED`, and performs
    exact readback. A transaction-created profile is deleted and verified
    absent; deletion restoration currently has no save/activation dependency.
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
applicable save/update, and exact-readback phases, using restoration-context
applicability rather than copying forward-mutation applicability. Repeated
restore after verified release returns an idempotent verified
no-change/released result and performs no mutation.

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

For the sequence items material to this policy, the allocation is exact:

| Sequence item | Included | Excluded |
| --- | --- | --- |
| 2 - capability/name policy | Immutable enums, raw request/report contracts, factory-controlled admitted-observation shape, mechanism-operation requirements, name-rule evidence, pure decisions/reasons, deterministic policy, and its tests. | Trusted live admission, capture, registry, mutation, adapters, files, and ownership transitions. |
| 3 - coordinator admission/capture | Trust/admit a current observation for one transaction, recheck backend/capability generations, serialize, verify requested existence context, capture exact state, and support verified no-change only. | Mutation and rollback execution. |
| 4 - rollback foundations | Mutation journal/operation record, rollback interfaces, degraded-state construction, and failure classification while mutation remains disabled. | First apply and production adapters. |
| 5 - first mutation | One existing-profile exact-cap operation through one item-2-admitted exact reversible mechanism with complete save/activation/readback/rollback coverage. | Creation, deletion, flags, switching, additional mechanisms, and production wiring. |
| 6 - creation/restoration | Creation admission, created-profile ownership, deletion on restore, verified absence, repeated restore, degradation, and handoff. | Limiter flags, switching, and production mechanism discovery. |
| 12 - production adapters | Versioned observation/discovery, trusted adapter provenance, live mechanism selection, DLL/profile-file behavior, filesystem containment, caller wiring, disposable-profile/manual validation, and support claims only for passed rows. | Changing deterministic policy to guess around missing evidence. |

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

### Authoritative unresolved-decision table

This is the authoritative detailed table referenced by `DECISIONS.md`.
Corrected planning semantics - context matching, legal observation states,
decision precedence, failure-only reason ordering, contradiction
representation, internal fractional dependency expansion, bit-width and exact
bound conversion including literal negative oracles, mechanism-specific
save/activation applicability semantics, the parent-only evaluator boundary,
canonical applicability keys and literal duplicate/overlap predicates,
legally constructible diagnostic groups, aggregating raw-name classification,
identity fail-closed behavior, exact-scope name-rule ownership,
named-normalization compatibility, and namespace completeness - are resolved
proposed design pending independent review; they are not live-fact questions
and do not appear as open rows.

The item-2 planning correction leaves only these real-world or later-lifecycle
decisions explicit:

| ID | Question | Current evidence | Fail-closed interim rule | Owner / phase | Blocks item-2 implementation? | Blocks later mutation or production support? |
| --- | --- | --- | --- | --- | --- | --- |
| `S2-CAP-OPEN-001` | Which RTSS versions are supported? | No versioned capability/restoration matrix is accepted. | Version labels are diagnostic only; no real observation is supported. | Item 12 adapter/manual matrix | No | Yes, for every support claim |
| `S2-CAP-OPEN-002` | Which exact operations and fields does each API mechanism support? | Current code exposes partial DLL methods and guessed Booleans, not admitted evidence. | Unknown per operation/field; never infer from general API availability. | Item 12 adapters | No | Yes, for affected operations |
| `S2-CAP-OPEN-003` | Is fractional denominator access API-backed or profile-file-backed? | Existing production paths split mechanisms; `RTSS-008` remains Likely/Open. | No fallback; denominator-dependent operations remain unknown. | Items 8 and 12 | No | Yes, for fractional mutation |
| `S2-CAP-OPEN-004` | When applicable, can write, save, activation, and exact readback be relied on independently? | Item 1 models results but provides no live capability proof. | Require explicit support for every active primitive; missing readback rejects mutation. | Items 5 and 12 | No | Yes |
| `S2-CAP-OPEN-005` | Are create, delete, and verified absence supported and reversible? | No accepted versioned disposable-profile evidence. | Existing read may remain eligible; creation/deletion remain unknown. | Items 6 and 12 | No | Yes, for creation/deletion |
| `S2-CAP-OPEN-007` | For each real mechanism and compound/phase context, is save or activation required, proved not required, or unknown? | No accepted versioned mechanism evidence establishes applicability, and forward/restoration behavior may differ. | Admit `UNKNOWN`; omit a dependency only on factory-admitted exact-context `NOT_REQUIRED`; never infer omission from primitive absence or lack of support. | Items 5, 6, 8, and 12 | No | Yes, for every affected mutation/restoration graph |
| `S2-NAME-OPEN-001` | Which encoding(s) are lossless for each mechanism? | Current identity uses ASCII; that is not universal RTSS evidence. | Encoding-dependent names are unknown without exact admitted evidence. | Item 12 adapters/manual matrix | No | Yes, for affected names |
| `S2-NAME-OPEN-002` | What character and encoded-byte component/total limits apply? | No accepted RTSS limit evidence; current parser has no capability limits. | A required unknown limit yields `UNKNOWN`; do not truncate. | Item 12 adapters/manual matrix | No | Yes, for support beyond proven bounds |
| `S2-NAME-OPEN-003` | Which characters or reserved forms are invalid for DLL lookup and profile files? | Current validation uses Windows filename rules; RTSS equivalence is unproven. | Structural injection/path-confusion rules are fixed; other constructor restrictions remain current identity-model constraints and no universal RTSS rule is claimed. | Item 12 evidence; separate identity migration if broader support is proposed | No | Yes, for names outside proven rules |
| `S2-NAME-OPEN-004` | Are comparison and canonicalization case-sensitive or insensitive? | Accepted ownership identity is case-insensitive; live RTSS behavior is unverified. | Preserve exact spelling; evidence incompatible with current ownership identity fails closed. | Architectural review plus item 12 matrix | No | Yes, for incompatible namespaces |
| `S2-NAME-OPEN-005` | What Unicode normalization, if any, occurs? | No accepted evidence. | Do not normalize; reject/unknown on required normalization or collision ambiguity. | Item 12 adapters/manual matrix | No | Yes, for Unicode support |
| `S2-NAME-OPEN-006` | Is identity executable basename, full path, or another RTSS namespace? | Current contract accepts executable names only; production sources disagree. | Support only the admitted profile kind/name form; no path-to-basename rewriting. | Profile identity design and item 12 validation | No | Yes, for other forms |
| `S2-NAME-OPEN-007` | Should the accepted canonical identity model support names it rejects or distinguish case/normalization forms it collapses? | Item-1 generation and ownership contracts require the current canonical model. | Item 2 never supports an unrepresentable identity; propose a separate migration before item 3 consumption. | Separate identity-model planning and review | No | Yes, for broader or incompatible namespaces |
| `S2-CAP-OPEN-006` | How is a current or advanced backend/capability observation trusted? | Item 1 intentionally anchors to captured evidence and provides no advancement seam. | Item 2 has no production trust source; raw/caller-created observations cannot support. | Item 3 admission and item 12 adapters | No | Yes, before coordinator use |
| `S2-CAP-OPEN-008` | How are restart/re-enumeration generation changes handled? | Item 1 rejects generation advancement; no reacquisition design exists. | Prior admission becomes stale; reacquisition cannot be inferred. | Items 10 and 12 | No | Yes, after restart |
| `S2-CAP-OPEN-009` | Can external revisions/cross-process writers be detected or serialized? | Deterministic conflict model exists; live token/lock behavior is unknown. | Detect and fail closed where evidence exists; never overwrite silently. | Items 4, 10, and 12 | No | Yes, for safe restoration |
| `S2-CAP-OPEN-010` | Which document digest schemes beyond complete bytes/SHA-256 are approved? | Item 1 accepts complete bytes or SHA-256 only. | Preserve the accepted set; no other digest proves restoration. | Later contract review | No | Only if another scheme is required |
| `S2-CAP-OPEN-011` | How does degraded ownership persist across process restart? | No durable recipient/storage design exists. | Do not claim release or restart recovery. | Production lifecycle integration | No | Yes, for restart-safe support |

The deterministic Stage 2 model must account for every unresolved owned field
and retain or explicitly hand off ownership. It does not claim that
restart-persistent storage has been designed. No Stage 2 plan selects an RTSS
version, fractional mechanism, overwrite policy, cross-process lock, restart
recovery mechanism, universal component limit, or compatibility claim.

### Accepted small implementation commits

The independently verified and explicitly accepted implementation sequence is:

1. **Prerequisite contract correction - complete and independently approved**
   - restrict `RtssReadback` to read-only outcome/failure-step allowlists;
   - add the exhaustive readback matrix and a justified exhaustive apply
     matrix;
   - add exact stored-field evidence types; and
   - add the immutable degraded-state and retained-ownership schema.
   - the first implementation and all three reviewed commits did not pass
     independent review; the third focused corrective slice changes only the
     remaining forged-future-generation defect, tests, and related
     documentation;
   - completed without transaction coordination, mutation, or production
     integration; independent review approved the third correction with
     non-blocking test-quality observations.
2. **Capability and supported-name policy - four planning reviews rejected;
   fourth correction completed locally; independent review and later explicit
   acceptance required; implementation unauthorized**
   - future unit 2a: add unique status, support, validity, origin, mechanism,
     primitive-operation, terminal compound-requirement, internal-dependency,
     postcondition, dependency-applicability/context, contradiction, and
     typed-reason enums plus immutable evaluation context and raw/admitted
     capability and applicability evidence contracts with the closed legal
     observation-state factory;
   - future unit 2b: add the closed applicability/primitive/derived decision
     algebra, conditional canonical dependency bundles, stable reason ordering,
     and pure evaluator;
   - future unit 2c: add domain-specific integer, numerator, denominator,
     rational, and bit-width range contracts, the unsigned/two's-complement
     formulas, exact discrete configured-bound conversion, and exact
     intersection policy;
   - future unit 2d: add the raw supported-name request, structural
     classification, canonical-identity boundary, and exact-name-preserving
     decision contracts;
   - future unit 2e: add the separate parent-bound factory-controlled admitted
     name-rule set and complete namespace/collision evidence contracts;
   - future unit 2f: add pure supported-name evaluation for encoding, length,
     character, case, normalization, existing/creation, and exact collision
     outcomes;
   - future unit 2g: add deterministic factory/admission, public-path,
     direct-construction/replacement, applicability, legally co-applicable
     diagnostic-group, omitted-collider, negative-range, and full truth-table
     regressions;
   - future unit 2h: reconcile tracked documentation after tests pass;
   - each unit remains contract/policy-only and must be independently
     reviewable; none creates trusted live evidence, a coordinator registry,
     capture, mutation, or adapter integration.
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
     with exact-context save/activation applicability, every active
     save/activation primitive, exact readback, rollback, degraded-state,
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
for capture, mutation, every save or update/activation dependency proved
`REQUIRED`, readback, rollback, and exact restoration verification. Every
conditional dependency must have exact-context applicability evidence;
`UNKNOWN` or missing applicability fails admission, and only admitted
`NOT_REQUIRED` omits the primitive.

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
recording, mechanism- and phase-specific save and activation applicability and
semantics, exact readback, every applicable false and exception path, rollback,
degraded-state construction, ownership retention, and deterministic tests.
Stage 5 may be split into smaller commits if numerator and denominator
handling, save/update activation, or rollback cannot remain independently
reviewable as one slice. Smaller mutation slices are preferred over combining
mechanisms.

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

The planning-review and explicit-acceptance gates are satisfied. Sequence item
1 is independently approved and complete with no admitted mutation after three
failed implementation reviews and three focused corrections. The separate
focused sequence-item-2 planning and design work has received three rejected
planning reviews. This third documentation-only correction is complete
locally, but its commit requires independent read-only review and a later
explicit acceptance documentation step.
Sequence item 2 implementation and each later mutation-bearing slice remain
unauthorized and gated by their applicable review, rollback,
degraded-state, ownership, and failure-matrix requirements. No mutation is
admitted before item 5 and its prerequisites, and production integration
remains item 12. The accepted 12-item focused sequence above is unchanged.
Push and pull-request creation require separate explicit approval.

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
  prerequisite contract/test sequence item was corrected locally a third time
  after three implementation reviews failed, passes all 181 deterministic
  tests, and is independently approved and complete. Sequence item 2 planning
  and design are complete locally but require independent read-only review and
  explicit acceptance; implementation remains unauthorized.
  No coordinator or mutation exists, no production caller uses the contracts,
  and production integration remains item 12.
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
