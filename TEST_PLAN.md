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
It also covers the RTSS Stage 1 contract and deterministic-fake validation plus
the RTSS Stage 2 sequence item 1 prerequisite contracts and focused review
corrections recorded below. The complete suite contains 181 passing
deterministic tests. It performs no live
RTSS, GUI, sensor, process, registry, profile, or hardware interaction. CI and
later production adapters remain outstanding.

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

## RTSS Stage 2 deterministic coordinator tests

The prerequisite contract matrices and exact stored/degraded ownership tests
for sequence item 1 are implemented, passing, independently approved, and
complete. The first
implementation at `c83aa281d961222eeeb70dbb994c4f33aef46381` and first
correction at `c323ddeb5cd62636a608d312af873a1552142f67` did not pass
independent review. Second correction
`ee9d0c7526861aeb999e1b410b3d2b21b71a6c23` also did not pass independent
review because caller-forged future backend and capability generations remained
trusted. The third focused corrective regressions below pass, and independent
read-only review approved source commit
`4011d7e1e29fc2a4bbe901d184c53774b33e7baa` with non-blocking findings.
Coordinator, capability/name-policy, mutation, production-adapter, and physical
tests in later subsections remain **planned** and must not be described as
passing.

The corrected Stage 2 test plan at
`677b6b5750ac52953fd1581efbc658adbc171b22` was independently verified and
explicitly accepted on 25 July 2026. The separately authorized first
implementation gate is complete and independently approved: the prerequisite
contract matrices and exact stored/degraded-state coverage remain
contract/test-only and enable no mutation. Later planned tests remain
unimplemented.

The Stage 2 tests will use only pure contracts, an in-memory fake backend, a
fake lifecycle/admission owner, deterministic barriers, and an ordered
operation log. They must run on any supported development platform without
RTSS, Windows, a GPU, a game, Dear PyGui, LibreHardwareMonitor, PDH, or Lossless
Scaling.

### Implemented prerequisite contract matrices

- **Implemented `S1-READBACK-001` / `S1-TEST-001`:** iterate every
  `RtssOutcome`/`RtssFailureStep` pair and assert the explicit read-only
  acceptance table. Verify `VERIFIED/NONE`, permitted validation, generation,
  capability, conflict, and readback failures, and reject mutation-only apply,
  save, update, rollback, restore, and delete states. Assert the table covers
  every enum member so additions fail closed.
- **Implemented apply matrix:** iterate every
  `RtssOutcome`/`RtssFailureStep` pair with the minimum valid supporting state
  for that pair. Accept only the defined pre-mutation, exact no-change,
  verified apply, verified rollback, conflict, and degraded graphs; reject all
  other pairs.
- **Planned restore matrix:** retain the Stage 1 exhaustive matrix and extend
  it for any new non-flag unresolved-state accounting without weakening the
  existing exact-restoration and closed-state assertions.
- **Planned capability-name prerequisite (`S1-DESIGN-001`):** test zero,
  one-below, exact, and one-above boundaries for DLL-name bytes and derived
  profile-filename components, including the `.cfg` suffix and Global mapping.

### First implementation sequence item 1 evidence and ownership regressions

- Exact stored numerator and denominator remain unreduced independent evidence;
  partial pairs and invalid availability/value combinations fail closed.
- `NOT_REQUESTED`, `AVAILABLE`, `READ_FAILED`, `UNSUPPORTED`, and
  `VERIFIED_ABSENT` stored evidence remain distinct.
- Captured `120/2` and readback `60/1` are mathematically equal effective caps
  but fail representation-exact restoration; `120/2` matched by `120/2`
  verifies when all other evidence matches.
- Exact stored representation is not inferred from `RationalCap`.
- Degraded accounting partitions every applicable field exactly once and
  covers stored numerator/denominator, effective cap, profile
  existence/deletion/verified absence, document, revision, owned limiter flags,
  save, activation, backend epoch, and retained ownership.
- Incomplete accounting, false resolution, unavailable evidence, and
  unrequested/unowned-field inflation fail closed; save and activation
  uncertainty are independent.
- Typed transaction, canonical profile, profile-kind, request, capture,
  evidence, application/session/profile/source, backend, and capability
  attribution are immutable and generation checked.
- Case-only display spelling preserves canonical ownership; cross-profile,
  cross-generation, backend-epoch, capability-generation, recipient, and
  transaction mismatches are rejected.
- Complete explicit handoff acceptance can release ownership; rejection,
  missing acceptance, incomplete attribution, or a wrong recipient retains
  ownership. Exact verified restoration is the only other admitted release
  proof.
- These original 27 focused tests raised the complete deterministic result from
  95 to 122. They continue to pass, but independent review found that they did
  not prove the five correction items below.

### Implemented sequence item 1 corrective regressions

- **Foreign exact-restoration proof:** reject reuse of one restore result across
  transaction owners, a proof from another owner, proof reuse after holder or
  capability change, same generations with different captures, canonical
  profile or profile-kind mismatch, each application/session/profile/source
  generation mismatch, backend-epoch mismatch, copied capability markers,
  incomplete proof, and marker-only or raw-string substitutes.
- **Exact stored-field applicability:** keep requested numerator and denominator
  applicable after paired `READ_FAILED`, paired `UNSUPPORTED`, or asymmetric
  evidence; distinguish not-requested and conclusively captured pairs; require
  both responsibilities in degraded accounting; and fail closed through the
  pre-mutation capture contract when requested exact evidence is incomplete.
- **Derived degraded evidence:** reject caller-authored unresolved accounting,
  fabricated `AVAILABLE`, classification without its required evidence,
  conflict evidence with the wrong classification, stale backend observations,
  false save or activation success, false verified absence, omitted requested
  fields, resolved/unresolved rewriting through `dataclasses.replace()`, and
  empty degraded accounting with retained ownership.
- **Typed read-failure diagnostics:** require non-empty field-specific typed
  diagnostics for `READ_FAILED`; reject missing, empty, incompatible, mutable,
  raw-string, Boolean-integer, and value-bearing failed evidence; preserve
  distinct numerator and denominator failure codes.
- **Enum aliases:** assert both ordinary enum iteration and `Enum.__members__`
  for all relevant enums, enforce unique values, and demonstrate with a
  synthetic enum that iteration alone omits aliases.
- The 24 corrective tests raise the complete deterministic result from 122 to
  146 passing tests with zero failures, errors, or unexpected skips.

### Implemented sequence item 1 second corrective regressions

- **Non-verified complete-pair rejection:** independently reject failed and
  unsupported readbacks whose exact numerator and denominator are both
  `AVAILABLE`; accept a verified complete pair; retain numerator-only and
  denominator-only transaction-bound partial evidence; and prove aggregate
  failure controls unresolved fields without conclusive field observation.
- **Transaction-bound readback:** bind readback to the exact structural owner,
  transaction, canonical profile and kind, all generation dimensions, backend
  epoch, and capability evidence. Reject cross-transaction reuse, profile or
  generation mismatch, stale backend evidence, missing backend evidence,
  capability mismatch, and `dataclasses.replace()` transaction substitution.
- **Trusted operation evidence:** make direct Boolean-result construction
  impossible. Accept verified save or activation evidence only from a matching
  verified bound observation; reject transaction, profile, kind, generation,
  capability, operation-type, owner, and arbitrary-epoch mismatches.
- **Conflict provenance:** derive the captured value from
  `CapturedProfileState` and the observed value and backend epoch from the same
  transaction-bound readback. Reject unrequested or unowned fields, invented
  captured values, wrong transaction/profile/kind/generation/capability,
  arbitrary epochs, another transaction's observation, and contradictory
  resolving readback.
- **Derived degraded truth:** derive classification, resolved/unresolved
  accounting, ownership retention, latest backend epoch, and latest capability
  evidence. Reject raw readback, fabricated operation success, cross-owner
  evidence, direct derived-field construction, and `dataclasses.replace()`
  bypass.
- **Structural token-copy semantics:** prove an unchanged immutable token copy
  is the same logical owner, while modified transaction, capture, profile,
  generation, backend, capability, or holder evidence is a different token.
  Duplicate-release prevention remains a future coordinator-registry
  responsibility and is deliberately not implemented.
- These 25 second-correction tests raise the complete deterministic result from
  146 to 171 passing tests with zero failures, errors, or unexpected skips.

### Implemented sequence item 1 third corrective regressions

- **Captured-generation anchoring:** reject readback backend generations before
  or after the ownership token's captured backend generation, even when a
  caller-created capability object agrees with the forged epoch.
- **Exact capability anchoring:** reject caller-created future capability
  generations and require accepted capability evidence to equal the owner's
  captured immutable capability evidence.
- **Nested substitution:** reject future backend and capability generations
  introduced through nested `dataclasses.replace()` calls or copied into an
  otherwise structurally equal ownership token.
- **Downstream fail-closed paths:** reject verified and uncertain operation
  evidence, conflict evidence, direct degraded-state construction, and
  degraded-state replacement when their supporting graph attempts to introduce
  a future generation.
- **Valid controls:** accept exact-current bound readback, verified operation,
  same-generation conflict, and degraded-state derivation; retain verified
  complete-pair, numerator-only partial, denominator-only partial, failed-pair,
  and unsupported-pair behavior from the prior matrices.
- These 10 third-correction tests raise the complete deterministic result from
  171 to 181 passing tests with zero failures, errors, skips, or warnings.
  They add no trusted advanced-generation observation mechanism.

These tests remain pure contract tests. They do not provide coordinator
admission, capture execution, mutation, save, activation, rollback,
restoration, production-adapter, or live-system coverage; that work remains in
the later planned sections.

### Sequence item 1 independent approval record

Independent review reran the complete deterministic suite with
`PYTHONDONTWRITEBYTECODE=1` and passed all 181 tests. It recorded two
non-blocking observations:

- `TEST-S2-PREFIX-COUNT-001`: replaying the targeted parent prefix produced 35
  tests with 9 failures, not the historically reported 8. Eight newly added
  rejection tests and one modified existing latest-epoch test failed against
  the parent. This corrects historical count accuracy only.
- `TEST-S2-DOWNSTREAM-PATH-001`: several operation, conflict, and
  degraded-state rejection tests combine readback binding and downstream
  construction in one `assertRaises` block. Binding rejects first, so the
  downstream constructor is not separately executed. The tests still prove
  forged evidence cannot reach those downstream public paths, and public
  factory-only construction provides no separately invalid already-bound
  evidence object.

Neither observation requires a source or test change now, and neither reopens
sequence item 1. Test restructuring is deferred until a legitimate trusted
advanced-generation observation seam exists. The second corrected
sequence-item-2 plan was rejected by a third planning review for
`S2-CAP-PLAN-003-R2`, `S2-TEST-PLAN-002-R2`, and
`S2-TEST-PLAN-001-R2`. The third corrected plan was rejected by a fourth
planning review for `S2-CAP-PLAN-004-R3` and `S2-CAP-PLAN-005-R3`. The fourth
corrected commit `b59187343ce775013dfcdbaf899a819cc53409cf` was rejected by a
fifth planning review with exact verdict **Not approved — blocking planning
findings require correction**, exactly five blockers
(`S2-CAP-TRUST-001-R4`, `S2-CAP-PLAN-004-R4`,
`S2-CAP-PLAN-005-R4-A`, `S2-TEST-PLAN-003-R4`, and
`S2-DOC-STATUS-002-R4`), and no non-blocking findings. Thus the initial plan and
four subsequent corrections through `b591873` received five rejected planning
reviews.

### Sequence item 2 planning approval and acceptance record

The fifth corrected plan at reviewed source commit
`c3047fc37248392b74255f36844120fc0f6fef82` defines the matrix below.
Independent read-only review, with bytecode creation disabled, ran exactly
`python -m unittest discover -s tests -t . -v`: 181 tests ran in 0.315 seconds;
181 passed with zero failures, errors, skips, or warnings. It closed
`S2-CAP-TRUST-001-R4`, `S2-CAP-PLAN-004-R4`,
`S2-CAP-PLAN-005-R4-A`, `S2-TEST-PLAN-003-R4`, and
`S2-DOC-STATUS-002-R4`; no blocking or non-blocking findings remained. The
review ended exactly **Approved — Stage 2 sequence item 2 planning is
complete**, and the user explicitly accepted that exact reviewed planning scope
in this documentation-only step.

The deterministic sequence-item-2 matrix is accepted planning authority, but
its tests remain planned until sequence-item-2 source implementation is added.
This acceptance step changes no source or test and performs no live RTSS,
filesystem, Windows, hardware, GPU, display, or Lossless Scaling validation.
Focused sequence-item-2 implementation is the next separately executable item
only after publication topology is settled and a separate instruction is given;
sequence item 3 and later work remain unauthorized.

Every corrected item-2 test below must use a public or realistically reachable
policy path, a test-only factory/admission fixture, an independently specified
expected status/reason tuple, and a positive control. Tests must not construct
the decision under test as their oracle. A later separately instructed focused
sequence-item-2 implementation must add and pass these tests before its own
acceptance.

### Corrected sequence item 2 context and decision-algebra matrix

- **Matching context:** a current admitted parent plus a structurally equal
  `RtssCapabilityEvaluationContext` copy returns the positive-control
  `SUPPORTED`; object identity is never asserted. The context is intent only
  and carries no evidence authority.
- **Context mismatch:** independently test foreign observation identity,
  backend-generation mismatch, capability-generation mismatch, profile-kind
  mismatch, and source/policy-scope mismatch. Each uses otherwise fully
  supporting admitted evidence and expects exact `UNKNOWN` status and the
  designated leading reason.
- **One parent-factory reconstruction boundary:** the test admission factory
  consumes an expected immutable parent header, a declared complete manifest,
  provenance/source constraints, and untrusted value candidates. It validates
  every field and reconstructs fresh canonical children and one complete
  parent; it never retains or trusts a submitted child instance. Production
  authenticity remains item 3/item 12 work.
- **Copy and reconstruction:** original, shallow-copy, deep-copy, exact-value
  reconstruction, unchanged `dataclasses.replace()`, fully populated exact
  `object.__new__`, copied-provenance, and caller-authored equal-value child
  candidates have one result when submitted through that same boundary. If all
  values match, admission is `CONSISTENT` with `()` diagnostics and the exact
  positive fixture returns `SUPPORTED / (SUPPORTED_REQUIREMENT,)`. Equality
  alone does not bypass admission; no token, marker, registry, or undocumented
  object-identity distinction exists.
- **Changed replacements:** changing a bound child field creates a new
  untrusted value candidate. Against the unchanged parent header and manifest,
  each isolated change produces the literal mismatch diagnostic specified in
  the applicability or name-rule authority table below. An unchanged nested
  replacement is equivalent only after the same reconstruction boundary.
- **Caller-authored context and evidence:** a perfectly matching public context
  with absent evidence returns `UNKNOWN / (CAPABILITY_EVIDENCE_MISSING,)`.
  Raw or standalone child evidence is not a parent and is rejected by the
  evaluator type boundary. A caller-authored equal child submitted through the
  parent factory is not distinguished by origin and receives the same result as
  every other equal candidate.
- **Primitive truth table:** exact tests cover current supported ->
  `SUPPORTED`; current unsupported -> `UNSUPPORTED`; current unknown ->
  `UNKNOWN`; stale supported -> `UNKNOWN`; stale unsupported -> `UNKNOWN` with
  stale then reported-unsupported reasons; invalid supported -> `UNKNOWN`;
  invalid unsupported -> `UNKNOWN` with invalid then reported-unsupported
  reasons; current primitive temporarily unavailable -> `UNKNOWN`; missing ->
  `UNKNOWN`; foreign/backend/capability mismatch -> `UNKNOWN`.
- **Whole-observation availability:** absence is the only missing-observation
  representation and expects `UNKNOWN / (CAPABILITY_EVIDENCE_MISSING,)`.
  Current, stale, and invalid consistent snapshots are admitted; stale and
  invalid snapshots expect their exact `UNKNOWN` reasons. A current
  contradictory snapshot with no selectable records expects
  `UNKNOWN / (CONTRADICTORY_EVIDENCE,)`. No observation-unavailable fixture,
  branch, or expected result exists.
- **Observation factory invariants:** reject contradictory plus stale/invalid,
  contradictory with selectable records, consistent snapshots with missing or
  incomplete applicability manifests, stale/invalid primitive unavailability,
  and any attempted observation-availability field. A separate unreachable
  private invariant rejects an attempt to force already-duplicate or overlapping
  applicability material into an object labelled `CONSISTENT`. The public raw
  admission factory never uses that guard as the outcome for raw duplicates; it
  constructs the current contradictory parent described below. Admit current
  primitive unavailability only inside a current consistent complete snapshot.
- **One contradiction policy:** the test admission factory converts
  contradictory direct or derived sources into the typed contradictory
  observation with no selectable records. It evaluates exactly `UNKNOWN /
  (CONTRADICTORY_EVIDENCE,)`; tests do not also expect constructor rejection for
  that semantic state. Duplicate identical primitive keys remain separate
  structural construction errors.
- **Mixed dependencies:** current unsupported plus current unknown ->
  `UNSUPPORTED`; current unsupported plus stale dependency -> `UNSUPPORTED`
  while retaining the stale reason; all current supported -> `SUPPORTED`.
  Reverse input order produces the identical status and reason tuple.
- **Stable failure reasons:** use only the explicit maximal legally
  co-applicable groups and literal tuples in the next subsection. There is no
  all-category fixture. Duplicates collapse without changing the stated order,
  and `SUPPORTED_REQUIREMENT` is absent from every failing tuple.
- **Separate success reason:** one fully supporting input expects `SUPPORTED`
  and exactly `(SUPPORTED_REQUIREMENT,)`; success is never aggregated with
  failures.
- **Derived sources:** all direct current supported sources -> supported
  derived record; a current unsupported source -> `UNSUPPORTED`; missing,
  foreign, mismatched, unavailable, stale, invalid, or unknown source ->
  `UNKNOWN`; contradictory or cyclic sources -> typed contradictory
  observation and `UNKNOWN`. Source tuple order does not affect results.

### Corrected sequence item 2 legally co-applicable reason-order groups

No test requests an impossible all-category input. Every fixture below asserts
the literal tuple, leading reason, terminal status, and suppressed categories
without deriving its oracle from implementation order.

**Group A - structural request failures**

- **A1 maximal non-empty structural fixture:** raw application name
  `\\?\C:\..\game.exe:stream\u0000\u0001`. The one string legally combines
  NUL and another control with device, UNC, drive-qualified/rooted/full-path,
  dot-segment, separator, ADS, and generic-colon forms. Expect terminal
  `UNSUPPORTED`, leading `NUL_IN_NAME`, and exactly
  `(NUL_IN_NAME, CONTROL_CHARACTER, DEVICE_PATH, UNC_PATH,
  DRIVE_QUALIFIED_PATH, ROOTED_PATH, FULL_PATH, DOT_PATH_SEGMENT,
  PATH_SEPARATOR, ALTERNATE_DATA_STREAM, COLON_PATH_CONFUSION)`.
  Suppress identity, capability, applicability, primitive, range, rule, and
  namespace evaluation.
- **A2 empty exclusive fixture:** raw `""`; expect `UNSUPPORTED`, leading
  `EMPTY_NAME`, exactly `(EMPTY_NAME,)`, and suppress every later category.
  Empty cannot coexist with content-dependent reasons.
- **A3 whitespace/control fixture:** raw `"\t"`; expect `UNSUPPORTED`, leading
  `WHITESPACE_ONLY_NAME`, exactly
  `(WHITESPACE_ONLY_NAME, CONTROL_CHARACTER)`, and suppress every later
  category. It cannot also be empty or a path form.
- The displayed A1/A3 escapes denote actual U+0000, U+0001, and U+0009 code
  points in the in-memory fixtures; tracked documentation contains no NUL byte.
- **A positive control:** exact `game.exe` has no classifier reason and
  continues to usable supporting evidence.

**Group B - evaluation-context mismatch**

- Use one current valid consistent fully supporting observation and a context
  whose observation identity, backend generation, capability generation,
  profile kind, and policy scope all differ. These public dimensions can
  legally mismatch together. Expect `UNKNOWN`, leading
  `FOREIGN_OBSERVATION`, and exactly
  `(FOREIGN_OBSERVATION, BACKEND_GENERATION_MISMATCH,
  CAPABILITY_GENERATION_MISMATCH, PROFILE_KIND_MISMATCH,
  POLICY_SCOPE_MISMATCH)`.
- Missing observation, observation validity, applicability, primitive, range,
  name-rule, and namespace categories are suppressed.
- The positive control uses a structurally equal matching context and otherwise
  identical evidence.

**Group C - unusable admitted observation**

Factory-exclusive states use separate fixtures:

| Fixture | Exact expected tuple | Leading reason | Terminal | Suppressed |
| --- | --- | --- | --- | --- |
| C1 matching stale observation | `(STALE_EVIDENCE,)` | `STALE_EVIDENCE` | `UNKNOWN` | Applicability through namespace |
| C2 matching invalid observation | `(INVALID_EVIDENCE,)` | `INVALID_EVIDENCE` | `UNKNOWN` | Applicability through namespace |
| C3 current contradictory observation with no selectable records | `(CONTRADICTORY_EVIDENCE,)` | `CONTRADICTORY_EVIDENCE` | `UNKNOWN` | Applicability through namespace |
| C4 current valid foreign observation only | `(FOREIGN_OBSERVATION,)` | `FOREIGN_OBSERVATION` | `UNKNOWN` | Later context/evidence |
| C5 only backend generation mismatched | `(BACKEND_GENERATION_MISMATCH,)` | `BACKEND_GENERATION_MISMATCH` | `UNKNOWN` | Capability generation and later evidence |
| C6 only capability generation mismatched | `(CAPABILITY_GENERATION_MISMATCH,)` | `CAPABILITY_GENERATION_MISMATCH` | `UNKNOWN` | Later evidence |

Missing observation is a separate fixture expecting exactly
`(CAPABILITY_EVIDENCE_MISSING,)`; it is never combined with foreign or
generation-mismatched evidence. The C positive control is current,
consistent, matching, and fully supporting.

**Group D - current consistent primitive/dependency failures**

- **D1 maximal legal fixture:** use existing fractional mutation with current
  valid consistent evidence. Different exact keys provide unsupported
  existence; temporarily unavailable numerator read; unknown denominator
  read; unsupported numerator write; temporarily unavailable denominator
  write; incomplete derived coordinated write; observed-unknown forward save
  applicability; missing-source forward activation applicability;
  observed-unknown restoration save applicability; and missing-source
  restoration activation applicability. Expect leading
  `DERIVED_DEPENDENCY_INCOMPLETE`, terminal `UNSUPPORTED`, and exactly:

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

  `DERIVED_DEPENDENCY_INCOMPLETE` is derived from the incomplete internal
  bundle for diagnostics; it is not a selectable record or terminal bundle
  decision.

  Explicit unsupported active primitives dominate the unknown/unavailable
  states. Save/activation primitive reasons are suppressed wherever
  applicability is unknown or missing-source. Supporting range/name evidence
  contributes nothing.
- A missing primitive manifest key is factory-illegal and gets a construction-
  rejection test. A legal factory-materialized missing-source primitive record
  gets exactly `(SAVE_PERSIST_EVIDENCE_MISSING,)` for save or
  `(ACTIVATE_RELOAD_EVIDENCE_MISSING,)` for activation.
- **D2 conditional-slot fixtures:** with every other dependency current and
  supported, assert independently: `REQUIRED` plus supported succeeds;
  save `REQUIRED` plus unsupported is exactly
  `(SAVE_PERSIST_UNSUPPORTED,)`; save `REQUIRED` plus missing-source is exactly
  `(SAVE_PERSIST_EVIDENCE_MISSING,)`; activation `REQUIRED` plus unsupported
  is exactly `(ACTIVATE_RELOAD_UNSUPPORTED,)`; activation `REQUIRED` plus
  missing-source is exactly `(ACTIVATE_RELOAD_EVIDENCE_MISSING,)`;
  `NOT_REQUIRED` succeeds while an unsupported or missing matching primitive
  is ignored; and observed-unknown/missing-source applicability uses the exact
  context-specific one-element tuples listed below.
- The positive control marks only actually active slots `REQUIRED` with
  supported primitives and deliberately omitted slots `NOT_REQUIRED`.

**Group E - name-rule and namespace failures**

All fixtures use a structurally valid currently representable identity and
fully supporting capability/range evidence.

| Fixture and coexistence rule | Exact expected tuple | Leading / terminal | Suppressed |
| --- | --- | --- | --- |
| E1 current rule set with foreign identity plus mismatched parent, backend generation, capability generation, kind, namespace scope, mechanism, operation, and name context; all matching dimensions may differ together | `(FOREIGN_NAME_RULE_SET, NAME_RULE_PARENT_OBSERVATION_MISMATCH, NAME_RULE_BACKEND_GENERATION_MISMATCH, NAME_RULE_CAPABILITY_GENERATION_MISMATCH, NAME_RULE_PROFILE_KIND_MISMATCH, NAME_RULE_NAMESPACE_SCOPE_MISMATCH, NAME_RULE_MECHANISM_MISMATCH, NAME_RULE_OPERATION_MISMATCH, NAME_RULE_CONTEXT_MISMATCH)` | `FOREIGN_NAME_RULE_SET` / `UNKNOWN` | Rule contents and namespace |
| E2 invalid rule set; exclusive of stale/contradictory | `(INVALID_NAME_RULES,)` | `INVALID_NAME_RULES` / `UNKNOWN` | Namespace |
| E3 stale rule set; separate legal state | `(STALE_NAME_RULES,)` | `STALE_NAME_RULES` / `UNKNOWN` | Namespace |
| E4 current contradictory rule set with no selectable rules | `(CONTRADICTORY_NAME_RULES,)` | `CONTRADICTORY_NAME_RULES` / `UNKNOWN` | Namespace |
| E5 usable rules plus incomplete namespace; completeness precedes later checks | `(NAMESPACE_COMPLETENESS_MISSING,)` | `NAMESPACE_COMPLETENESS_MISSING` / `UNKNOWN` | Case, normalization, encoding/canonical collision |
| E6 complete namespace proves the same peer collides by case, named normalization, encoding, and canonical key | `(CASE_COLLISION, NORMALIZATION_COLLISION, ENCODING_COLLISION, CANONICAL_COLLISION)` | `CASE_COLLISION` / `UNSUPPORTED` | Later name categories |
| E7 unknown normalization mode; exclusive of named modes | `(NORMALIZATION_UNKNOWN,)` | `NORMALIZATION_UNKNOWN` / `UNKNOWN` | Mapping/collision derivation |
| E8 named normalization with incomplete one-to-one proof | `(NORMALIZATION_PROOF_INCOMPLETE,)` | `NORMALIZATION_PROOF_INCOMPLETE` / `UNKNOWN` | Conclusions requiring complete proof |
| E9 named normalization proves many-to-one external/current ownership mapping | `(IDENTITY_MODEL_INCOMPATIBLE,)` | `IDENTITY_MODEL_INCOMPATIBLE` / `UNSUPPORTED` | Later collision categories |

The E positive control uses matching current consistent rules and complete
one-to-one collision-free namespace evidence.

**Group F - range failures**

- **F1 maximal cross-domain fixture:** a valid fractional request uses
  numerator `-129` against signed 8-bit `[-128, 127]`, denominator `256`
  against unsigned 8-bit `[0, 255]`, and requires an effective-rational
  representability range whose evidence is explicitly unsupported. The
  distinct domains allow co-applicability.
  Expect `UNSUPPORTED`, leading `RANGE_UNSUPPORTED`, and exactly
  `(RANGE_UNSUPPORTED, RANGE_UNDERFLOW, RANGE_OVERFLOW,
  BIT_WIDTH_OVERFLOW)`. Supporting name evidence contributes no reason.
- **F2 missing required range:** exactly `(RANGE_EVIDENCE_MISSING,)`, leading
  `RANGE_EVIDENCE_MISSING`, terminal `UNKNOWN`.
- **F3 typed invalid observed range:** exactly
  `(INVALID_RANGE_EVIDENCE,)`, leading `INVALID_RANGE_EVIDENCE`, terminal
  `UNKNOWN`.
- **F4 reversed configured request:** exactly `(INVALID_RANGE_REQUEST,)`,
  leading `INVALID_RANGE_REQUEST`, terminal `UNSUPPORTED`; evidence evaluation
  is suppressed.
- **F5 equal configured endpoints with either exclusive:** exactly
  `(EMPTY_CONFIGURED_RANGE,)`, leading `EMPTY_CONFIGURED_RANGE`, terminal
  `UNSUPPORTED`; evidence evaluation is suppressed.
- **F6 converted/intersected lower greater than upper:** exactly
  `(EMPTY_DISCRETE_INTERSECTION,)`, leading
  `EMPTY_DISCRETE_INTERSECTION`, terminal `UNSUPPORTED`.
- The F positive control uses current supported same-domain ranges containing
  the requested values and a non-empty exact intersection.

**Separate success and single-category fixtures**

The only success fixture has matching current evidence, resolved
applicability, supported active primitives, valid non-empty ranges, usable
rules, and complete collision-free namespace evidence. It expects exactly
`(SUPPORTED_REQUIREMENT,)`. Every failure fixture excludes that reason.
Raw/direct untrusted evidence, each single applicability mismatch, each
required save/activation primitive state, and every reason not legally
co-applicable above receives an explicit literal one-element tuple test.

### Corrected sequence item 2 taxonomy and range matrix

- Assert unique, disjoint membership for `RtssPrimitiveOperation`,
  terminal `RtssCompoundRequirement`, internal
  `RtssInternalDependencyBundle`, `RtssRequiredPostcondition`,
  `RtssDependencyApplicability`, and
  `RtssDependencyApplicabilityContext`. Applicability membership is exactly
  `REQUIRED`, `NOT_REQUIRED`, and `UNKNOWN`. No internal bundle,
  postcondition, or applicability context is publicly selectable as a
  primitive or terminal compound.
- For every primitive operation, factory-admit supported, unsupported, unknown,
  stale, and wrong-kind records through the public evaluator.
- For existing read, existing integer mutation, existing fractional mutation,
  exact readback, exact restoration, profile creation, deletion restoration,
  and verified absence, test the complete flattened ordered dependency bundle
  and remove each active dependency one at a time. Remove-one matrices remove
  only primitives whose exact-context applicability is `REQUIRED`; a
  `NOT_REQUIRED` primitive is absent from the graph and is never reported as a
  removed failure.
- Assert `COORDINATED_FRACTIONAL_WRITE` is an internal ordered reversible
  numerator-write/denominator-write expansion, not an atomic primitive or
  terminal requirement. There is no public evaluator request for it.
- Existing fractional mutation positive control independently supplies:
  existence lookup; exact current numerator and denominator reads; both
  coordinated writes; exact forward save and activation applicability; each
  forward primitive marked `REQUIRED`; exact pair readback; exact pair
  restoration capability; and separate restoration save and activation
  applicability/primitives. Removing each active leaf once yields
  `UNSUPPORTED` for a current explicitly unsupported leaf and `UNKNOWN` for
  missing, unknown, stale, invalid, or temporarily unavailable evidence.
- Independently expect failure for numerator-only support, denominator-only
  support, `REQUIRED` save with missing primitive, `REQUIRED` activation with
  missing primitive, unknown or missing applicability, missing exact readback,
  and missing exact restoration. Add positive controls where save and/or
  activation is factory-proved `NOT_REQUIRED`; unsupported or missing omitted
  primitive evidence contributes no failure. Static capability output must
  contain no claim that a write, readback, save, activation, rollback, or
  restoration actually occurred.
- For exact-value-observed, save-confirmed, activation-confirmed,
  profile-exists, profile-absent, and restored-equals-captured postconditions,
  verify that item 2 returns capability requirements only and never fabricates
  a later runtime success. Save-confirmed and activation-confirmed appear only
  for exact contexts marked `REQUIRED`.
- **Save applicability matrix:** for integer forward, fractional forward,
  integer restoration, fractional restoration, and both profile-creation
  forward contexts, independently test save `REQUIRED` with current supported,
  current unsupported, and missing-source primitive; save
  `NOT_REQUIRED` with unsupported and missing primitive positive controls;
  observed `UNKNOWN`; and missing-source applicability. Expected statuses are
  respectively `SUPPORTED`, `UNSUPPORTED`, `UNKNOWN`, `SUPPORTED`,
  `UNKNOWN`, and `UNKNOWN` when all other dependencies support. The exact
  single reasons are `SAVE_PERSIST_UNSUPPORTED`,
  `SAVE_PERSIST_EVIDENCE_MISSING`, context-specific
  `*_SAVE_APPLICABILITY_UNKNOWN`, and context-specific
  `*_SAVE_APPLICABILITY_EVIDENCE_MISSING` where applicable.
- **Activation applicability matrix:** repeat the same contexts for activation
  `REQUIRED` with current supported, current unsupported, and missing-source
  primitive; activation `NOT_REQUIRED` with unsupported and missing primitive
  positive controls; observed `UNKNOWN`; and missing-source applicability.
  Exact failure reasons are `ACTIVATE_RELOAD_UNSUPPORTED`,
  `ACTIVATE_RELOAD_EVIDENCE_MISSING`, context-specific
  `*_ACTIVATION_APPLICABILITY_UNKNOWN`, and context-specific
  `*_ACTIVATION_APPLICABILITY_EVIDENCE_MISSING`.
- **Forward/restoration independence:** one positive fixture proves forward
  save `REQUIRED` with supported save while restoration save is
  `NOT_REQUIRED`; another proves forward activation `NOT_REQUIRED` while
  restoration activation is `REQUIRED` with supported activation. Reverse
  each pair and vary integer/fractional contexts. No evaluator copies a
  forward record into restoration or vice versa.
- **Applicability authority and public path:** applicability children are
  immutable value inputs and never independent support proof. The sole
  authority boundary is reconstruction of the complete parent by the admission
  factory. The public
  `evaluate_capability(requirement, context, admitted_observation)` signature
  accepts only `None` or the complete parent and has no standalone-child
  overload. Passing a child in the parent position must raise `TypeError` and
  produce no `RtssCapabilityDecision`; no child-admission diagnostic is exposed
  as a public reason.
- **Parent entry validation:** original and exact shallow/deep copies of an
  admitted complete parent undergo the same total parent-invariant validation
  before selection and return the same decision. A completely populated
  field-for-field parent reconstruction, caller-authored equal parent, copied
  equal provenance/source values, fully populated equal `object.__new__`, or
  unchanged `dataclasses.replace(parent)` cannot be distinguished by origin and
  has the same result after reconstruction. An incomplete parent created with
  `object.__new__` raises `TypeError` before a decision. A top-level binding
  changed without changing its nested children reconstructs a contradictory
  parent; a fully consistently changed parent remains structurally valid and
  fails the unchanged evaluator context with its literal public mismatch.
- **Child reconstruction:** the factory treats a valid original child, shallow
  copy, deep copy, exact reconstruction, unchanged replacement, copied exact
  provenance/source tuple, fully populated exact constructor-bypass candidate,
  and caller-authored equal-value child identically. It reconstructs a fresh
  canonical child, admits a consistent complete parent with `()` diagnostics,
  and the otherwise-supporting positive fixture returns exactly `SUPPORTED /
  (SUPPORTED_REQUIREMENT,)`.
- **Child failures:** an incomplete constructor-bypass candidate, raw enum,
  Boolean, or wrong child type produces one current contradictory parent with
  no selectable records and exact factory tuple
  `(APPLICABILITY_EVIDENCE_UNTRUSTED,)`; the public result is exactly `UNKNOWN /
  (CONTRADICTORY_EVIDENCE,)`. A changed bound value is diagnosed only from its
  structural mismatch, never from whether the candidate originated in another
  object. A missing raw source is reconstructed as the exact keyed `UNKNOWN`
  record with `APPLICABILITY_EVIDENCE_MISSING` provenance. Every declared
  save/activation slot has exact records; no record covers two mechanisms,
  compounds, phases, primitives, profile kinds, or field scopes.
- Every observed-unknown and missing-source applicability case asserts its
  literal one-element tuple from this table:

  | Context | Save unknown | Save missing | Activation unknown | Activation missing |
  | --- | --- | --- | --- | --- |
  | Integer forward | `(INTEGER_FORWARD_SAVE_APPLICABILITY_UNKNOWN,)` | `(INTEGER_FORWARD_SAVE_APPLICABILITY_EVIDENCE_MISSING,)` | `(INTEGER_FORWARD_ACTIVATION_APPLICABILITY_UNKNOWN,)` | `(INTEGER_FORWARD_ACTIVATION_APPLICABILITY_EVIDENCE_MISSING,)` |
  | Fractional forward | `(FRACTIONAL_FORWARD_SAVE_APPLICABILITY_UNKNOWN,)` | `(FRACTIONAL_FORWARD_SAVE_APPLICABILITY_EVIDENCE_MISSING,)` | `(FRACTIONAL_FORWARD_ACTIVATION_APPLICABILITY_UNKNOWN,)` | `(FRACTIONAL_FORWARD_ACTIVATION_APPLICABILITY_EVIDENCE_MISSING,)` |
  | Integer restoration | `(INTEGER_RESTORATION_SAVE_APPLICABILITY_UNKNOWN,)` | `(INTEGER_RESTORATION_SAVE_APPLICABILITY_EVIDENCE_MISSING,)` | `(INTEGER_RESTORATION_ACTIVATION_APPLICABILITY_UNKNOWN,)` | `(INTEGER_RESTORATION_ACTIVATION_APPLICABILITY_EVIDENCE_MISSING,)` |
  | Fractional restoration | `(FRACTIONAL_RESTORATION_SAVE_APPLICABILITY_UNKNOWN,)` | `(FRACTIONAL_RESTORATION_SAVE_APPLICABILITY_EVIDENCE_MISSING,)` | `(FRACTIONAL_RESTORATION_ACTIVATION_APPLICABILITY_UNKNOWN,)` | `(FRACTIONAL_RESTORATION_ACTIVATION_APPLICABILITY_EVIDENCE_MISSING,)` |
  | Profile creation integer forward | `(PROFILE_CREATION_INTEGER_SAVE_APPLICABILITY_UNKNOWN,)` | `(PROFILE_CREATION_INTEGER_SAVE_APPLICABILITY_EVIDENCE_MISSING,)` | `(PROFILE_CREATION_INTEGER_ACTIVATION_APPLICABILITY_UNKNOWN,)` | `(PROFILE_CREATION_INTEGER_ACTIVATION_APPLICABILITY_EVIDENCE_MISSING,)` |
  | Profile creation fractional forward | `(PROFILE_CREATION_FRACTIONAL_SAVE_APPLICABILITY_UNKNOWN,)` | `(PROFILE_CREATION_FRACTIONAL_SAVE_APPLICABILITY_EVIDENCE_MISSING,)` | `(PROFILE_CREATION_FRACTIONAL_ACTIVATION_APPLICABILITY_UNKNOWN,)` | `(PROFILE_CREATION_FRACTIONAL_ACTIVATION_APPLICABILITY_EVIDENCE_MISSING,)` |

- Applicability authority tests use baseline value candidate
  `A=(O1,B1,C1,M1,APPLICATION,EXISTING_FRACTIONAL_MUTATION,
  FRACTIONAL_FORWARD_MUTATION,SAVE_PERSIST,(NUMERATOR,DENOMINATOR),
  REQUIRED,P1,(S1,))`, where the final three components are applicability,
  provenance, and canonical source references. The fixed factory header and
  manifest expect those literal values. `O2`, `B2`, `C2`, `M2`, `GLOBAL`,
  `EXACT_RESTORATION`, `FRACTIONAL_EXACT_RESTORATION`, `ACTIVATE_RELOAD`,
  `(NUMERATOR,)`, `P2`, and `(S2,)` are distinct valid values in their
  corresponding dimensions. Unless a row says otherwise, contradictory means
  one current admitted contradictory parent with no selectable records, and
  every such row has the literal public result `UNKNOWN /
  (CONTRADICTORY_EVIDENCE,)`.

  | Candidate and path through the one parent factory | Admission result | Exact ordered factory diagnostics | Exact public evaluator result |
  | --- | --- | --- | --- |
  | Original complete parent `P` returned by the factory | current consistent parent | `()` | `SUPPORTED / (SUPPORTED_REQUIREMENT,)` |
  | `copy.copy(P)` | current consistent parent after entry validation | `()` | `SUPPORTED / (SUPPORTED_REQUIREMENT,)` |
  | `copy.deepcopy(P)` | current consistent parent after entry validation | `()` | `SUPPORTED / (SUPPORTED_REQUIREMENT,)` |
  | Exact field-for-field, caller-authored equal, or fully populated equal `object.__new__` reconstruction of `P` | current consistent parent after entry reconstruction | `()` | `SUPPORTED / (SUPPORTED_REQUIREMENT,)` |
  | `P` with independently copied but equal provenance/source values | current consistent parent after entry reconstruction | `()` | `SUPPORTED / (SUPPORTED_REQUIREMENT,)` |
  | Incomplete `object.__new__` reconstruction of `P` | parent boundary raises `TypeError` | no diagnostic tuple; `TypeError` precedes reconstruction | no `RtssCapabilityDecision` and no reason tuple |
  | Unchanged `dataclasses.replace(P)` | current consistent parent after entry reconstruction | `()` | `SUPPORTED / (SUPPORTED_REQUIREMENT,)` |
  | `dataclasses.replace(P, observation_identity=O2)` while nested children remain bound to `O1` | current contradictory parent after entry reconstruction | `(APPLICABILITY_PARENT_OBSERVATION_MISMATCH,)` | `UNKNOWN / (CONTRADICTORY_EVIDENCE,)` |
  | Whole `P` consistently replaced to `O2`, including every nested parent binding | current consistent parent after entry reconstruction | `()` | `UNKNOWN / (FOREIGN_OBSERVATION,)` against the unchanged `O1` context |
  | Original candidate `A` | consistent parent | `()` | `SUPPORTED / (SUPPORTED_REQUIREMENT,)` |
  | `copy.copy(A)` | consistent parent | `()` | `SUPPORTED / (SUPPORTED_REQUIREMENT,)` |
  | `copy.deepcopy(A)` | consistent parent | `()` | `SUPPORTED / (SUPPORTED_REQUIREMENT,)` |
  | Exact field-for-field value reconstruction of `A` | consistent parent | `()` | `SUPPORTED / (SUPPORTED_REQUIREMENT,)` |
  | Unchanged `dataclasses.replace(A)` | consistent parent | `()` | `SUPPORTED / (SUPPORTED_REQUIREMENT,)` |
  | Caller-authored child with every value equal to `A` | consistent parent | `()` | `SUPPORTED / (SUPPORTED_REQUIREMENT,)` |
  | `A` with independently shallow/deep-copied but equal `P1` and `(S1,)` | consistent parent | `()` | `SUPPORTED / (SUPPORTED_REQUIREMENT,)` |
  | Fully populated exact `object.__new__` or equivalent reconstruction of `A` | consistent parent | `()` | `SUPPORTED / (SUPPORTED_REQUIREMENT,)` |
  | Incomplete `object.__new__` candidate, raw enum, Boolean, or wrong child type | contradictory parent | `(APPLICABILITY_EVIDENCE_UNTRUSTED,)` | `UNKNOWN / (CONTRADICTORY_EVIDENCE,)` |
  | Canonical child from an `O2` parent, differing only as structurally shown by `parent_observation_identity=O2` | contradictory parent | `(APPLICABILITY_PARENT_OBSERVATION_MISMATCH,)` | `UNKNOWN / (CONTRADICTORY_EVIDENCE,)` |
  | Same `O2` candidate with both `parent_observation_identity=O2` and source `(S2,)` | contradictory parent | `(APPLICABILITY_PARENT_OBSERVATION_MISMATCH, APPLICABILITY_SOURCE_REFERENCE_MISMATCH)` | `UNKNOWN / (CONTRADICTORY_EVIDENCE,)` |
  | `dataclasses.replace(A, parent_observation_identity=O2)` | contradictory parent | `(APPLICABILITY_PARENT_OBSERVATION_MISMATCH,)` | `UNKNOWN / (CONTRADICTORY_EVIDENCE,)` |
  | `dataclasses.replace(A, backend_generation=B2)` | contradictory parent | `(APPLICABILITY_BACKEND_GENERATION_MISMATCH,)` | `UNKNOWN / (CONTRADICTORY_EVIDENCE,)` |
  | `dataclasses.replace(A, capability_generation=C2)` | contradictory parent | `(APPLICABILITY_CAPABILITY_GENERATION_MISMATCH,)` | `UNKNOWN / (CONTRADICTORY_EVIDENCE,)` |
  | `dataclasses.replace(A, mechanism=M2)` | contradictory parent | `(APPLICABILITY_MECHANISM_MISMATCH,)` | `UNKNOWN / (CONTRADICTORY_EVIDENCE,)` |
  | `dataclasses.replace(A, profile_kind=GLOBAL)` | contradictory parent | `(APPLICABILITY_PROFILE_KIND_MISMATCH,)` | `UNKNOWN / (CONTRADICTORY_EVIDENCE,)` |
  | `dataclasses.replace(A, terminal_compound_requirement=EXACT_RESTORATION)` | contradictory parent | `(APPLICABILITY_COMPOUND_MISMATCH,)` | `UNKNOWN / (CONTRADICTORY_EVIDENCE,)` |
  | `dataclasses.replace(A, dependency_phase_context=FRACTIONAL_EXACT_RESTORATION)` | contradictory parent | `(APPLICABILITY_REQUIREMENT_CONTEXT_MISMATCH,)` | `UNKNOWN / (CONTRADICTORY_EVIDENCE,)` |
  | `dataclasses.replace(A, canonical_exact_field_set=(NUMERATOR,))` | contradictory parent | `(APPLICABILITY_FIELD_SET_MISMATCH,)` | `UNKNOWN / (CONTRADICTORY_EVIDENCE,)` |
  | `dataclasses.replace(A, primitive_dependency=ACTIVATE_RELOAD)` | contradictory parent | `(APPLICABILITY_PRIMITIVE_MISMATCH,)` | `UNKNOWN / (CONTRADICTORY_EVIDENCE,)` |
  | `dataclasses.replace(A, applicability=NOT_REQUIRED)` as a distinct legal payload in the same slot | consistent parent | `()` | `SUPPORTED / (SUPPORTED_REQUIREMENT,)` for the otherwise-complete fixture; the changed payload is evaluated, not treated as origin failure |
  | `dataclasses.replace(A, provenance=P2)` | contradictory parent | `(APPLICABILITY_PROVENANCE_MISMATCH,)` | `UNKNOWN / (CONTRADICTORY_EVIDENCE,)` |
  | `dataclasses.replace(A, source_references=(S2,))` | contradictory parent | `(APPLICABILITY_SOURCE_REFERENCE_MISMATCH,)` | `UNKNOWN / (CONTRADICTORY_EVIDENCE,)` |
  | Standalone canonical child passed as `admitted_observation` | parent boundary raises `TypeError` | no diagnostic tuple; parent factory is not a child overload | no `RtssCapabilityDecision` and no reason tuple |
  | Exact complete-parent positive control reconstructed from `A` and all other supporting records | consistent parent | `()` | `SUPPORTED / (SUPPORTED_REQUIREMENT,)` |

  There is deliberately no copied-authority-material case: this model has no
  authority field, marker, token, registry, or origin flag. A proposed such
  field is a wrong input shape and follows the untrusted-input row. Equal copied
  provenance is ordinary data; changed provenance or sources use only the two
  literal structural mismatch rows above.

### Corrected sequence item 2 applicability duplicate/overlap matrix

The literal canonical key is
`(parent, backend_generation, capability_generation, mechanism, profile_kind,
terminal_compound, phase_context, primitive, canonical_exact_field_set)`.
The baseline base key is
`K=(O1,B1,C1,M1,APPLICATION,EXISTING_FRACTIONAL_MUTATION,
FRACTIONAL_FORWARD_MUTATION,SAVE_PERSIST)`. `N` is `NUMERATOR` and `D` is
`DENOMINATOR`. The admitted production universe is exactly `(N,D)`, so its only
non-empty field sets are `{N}`, `{D}`, and `{N,D}`. A non-empty unequal partial
intersection is mathematically unreachable at the real boundary. The separately
named pure relation-classifier oracle uses abstract `frozenset({0,1})` and
`frozenset({1,2})`; those integers are predicate tokens only and are never raw
children, `RtssStoredFieldKind` values, or admitted evidence. `GLOBAL`, `EXACT_RESTORATION`,
`FRACTIONAL_EXACT_RESTORATION`, and `ACTIVATE_RELOAD` differ from `K` only in
the dimension named by the row.

For every "contradictory" row, construction succeeds as one current
contradictory parent with no selectable records, the listed tuple is the exact
factory-only ordered admission diagnostic tuple, the evaluator may be called,
and its exact public result is `UNKNOWN / (CONTRADICTORY_EVIDENCE,)`. For every
"consistent" row, construction succeeds as a consistent parent, diagnostics
are `()`, and direct evaluation of either otherwise fully supported exact key
returns `SUPPORTED / (SUPPORTED_REQUIREMENT,)`.

| Case | Exact candidate keys or raw scope | Construction | Exact ordered admission diagnostics | Evaluator |
| --- | --- | --- | --- | --- |
| Raw exact duplicate | `K+(N,D)@SA`, then `K+(N,D)@SB` | contradictory | `(APPLICABILITY_EXACT_DUPLICATE,)` | contradictory-parent result |
| Reversed raw duplicate input | the same occurrences in order `@SB`, then `@SA` | contradictory | `(APPLICABILITY_EXACT_DUPLICATE,)` | identical canonical source tuple and contradictory-parent result |
| Equal field set in different raw member order | `K+(N,D)@SA` and raw `K+(D,N)@SB` | contradictory | `(APPLICABILITY_EXACT_DUPLICATE,)` | contradictory-parent result |
| Strict subset | `K+(N)` and `K+(N,D)` | contradictory | `(APPLICABILITY_FIELD_SET_OVERLAP,)` | contradictory-parent result |
| Strict superset | `K+(N,D)` and `K+(D)` | contradictory | `(APPLICABILITY_FIELD_SET_OVERLAP,)` | contradictory-parent result |
| Isolated pure partial-intersection oracle | abstract `frozenset({0,1})` and `frozenset({1,2})` | no parent construction; pure classifier only | no factory diagnostic tuple | exactly `PARTIAL_INTERSECTION` in either argument order; no evaluator call |
| Disjoint field sets | `K+(N)` and `K+(D)` | consistent | `()` | either exact-key positive control |
| Same fields, different mechanism | `K+(N,D)` and `K[mechanism=M2]+(N,D)` | consistent | `()` | either exact-key positive control |
| Same fields, different profile kind | `K+(N,D)` and `K[profile_kind=GLOBAL]+(N,D)` | consistent | `()` | either exact-key positive control |
| Same fields, different compound | `K+(N,D)` and valid restoration key `K[compound=EXACT_RESTORATION,phase=FRACTIONAL_EXACT_RESTORATION]+(N,D)` | consistent | `()` | either exact-key positive control |
| Same fields, different phase | `K+(N,D)` and `K[phase=FRACTIONAL_EXACT_RESTORATION]+(N,D)` | consistent | `()` | either exact-key positive control |
| Same fields, different primitive | `K+(N,D)` and `K[primitive=ACTIVATE_RELOAD]+(N,D)` | consistent | `()` | either exact-key positive control |
| Illegal missing primitive | `K[primitive=None]+(N,D)` | contradictory | `(APPLICABILITY_PRIMITIVE_MISSING,)` | contradictory-parent result |
| Illegal missing compound | `K[compound=None]+(N,D)` | contradictory | `(APPLICABILITY_COMPOUND_MISSING,)` | contradictory-parent result |
| Wildcard primitive | `K[primitive=ALL_PRIMITIVES]+(N,D)` | contradictory | `(APPLICABILITY_PRIMITIVE_SCOPE_NOT_EXACT,)` | contradictory-parent result |
| Wildcard field scope | `K+(ALL_FIELDS)` | contradictory | `(APPLICABILITY_FIELD_SCOPE_NOT_EXACT,)` | contradictory-parent result |
| Reversed subset input order | `K+(N,D)`, then `K+(N)` | contradictory | `(APPLICABILITY_FIELD_SET_OVERLAP,)` | identical contradiction sources and parent result |
| Valid coexistence | `K+(N)` and `K+(D)` supplied in both orders | consistent | `()` | identical positive controls |
| Evaluator boundary control | raw-duplicate contradictory parent passed directly; no child argument | contradictory | `(APPLICABILITY_EXACT_DUPLICATE,)` | exactly `UNKNOWN / (CONTRADICTORY_EVIDENCE,)` |

The duplicate oracle uses independently authored immutable fixture values
`P0=("fixture-provenance","r4")`, `SA=("fixture-source","A")`, and
`SB=("fixture-source","B")`. Let `DUP_A` and `DUP_B` be the complete canonical
occurrence identities for `K+(N,D)@SA` and `K+(N,D)@SB`, respectively, authored
directly in the fixture rather than returned by the production normalizer. In
both raw orders, the complete expected contradiction-source tuple is literally

```text
((APPLICABILITY_EXACT_DUPLICATE, DUP_A, DUP_B, EQUAL),)
```

and the complete unique factory-diagnostic tuple is literally
`(APPLICABILITY_EXACT_DUPLICATE,)`. The resulting parent is current and
contradictory, has `primitive_records=()` and `applicability_records=()`, and
evaluates exactly `UNKNOWN / (CONTRADICTORY_EVIDENCE,)`; no competing rejection
assertion exists.

The mandatory combined-conflict fixture independently fixes every raw and
canonical value. Its expected parent header is

```text
K1=(O1,B1,C1,M1,APPLICATION,EXISTING_FRACTIONAL_MUTATION,
    FRACTIONAL_FORWARD_MUTATION,SAVE_PERSIST)
```

and its mismatched but value-shaped base is

```text
K2=(O2,B2,C1,M1,APPLICATION,EXISTING_FRACTIONAL_MUTATION,
    FRACTIONAL_FORWARD_MUTATION,SAVE_PERSIST)
```

`O1 != O2`, `B1 != B2`, and every other same-named value is exactly equal. The
declared test manifest contains the exact slots `K1+(N)` and `K1+(N,D)`. Thus
`C` and the two duplicate candidates each match a declared field slot before
binding checks; the intentionally overlapping slots cannot form a consistent
parent and are reduced semantically. An empty field tuple is structurally
non-comparable and `FIELD_SET_EMPTY` is mutually exclusive with a manifest
field-set mismatch. A missing primitive is likewise mutually exclusive with a
primitive mismatch.

The fixture-local raw scalar representation is a closed literal pair
`(tag,payload)` with ranks `CANONICAL=0`, `MISSING=1`,
`NON_EXACT_SCOPE=2`, and `UNTRUSTED=3`; a sentinel has payload `()`. These ranks
are fixture data, not calls to the production normalizer. In addition to `P0`,
define `SC=("fixture-source","C")` and `SD=("fixture-source","D")`, with
canonical order `SA < SB < SC < SD`. The four raw audit tuples are written
literally as:

```text
RAW_A=((0,O2),(0,B2),(0,C1),(0,M1),(0,APPLICATION),
       (0,EXISTING_FRACTIONAL_MUTATION),(0,FRACTIONAL_FORWARD_MUTATION),
       (0,SAVE_PERSIST),(0,(N,D)),(0,REQUIRED),(0,P0),(0,(SA,)))
RAW_B=((0,O2),(0,B2),(0,C1),(0,M1),(0,APPLICATION),
       (0,EXISTING_FRACTIONAL_MUTATION),(0,FRACTIONAL_FORWARD_MUTATION),
       (0,SAVE_PERSIST),(0,(D,N)),(0,REQUIRED),(0,P0),(0,(SB,)))
RAW_C=((0,O2),(0,B2),(0,C1),(0,M1),(0,APPLICATION),
       (0,EXISTING_FRACTIONAL_MUTATION),(0,FRACTIONAL_FORWARD_MUTATION),
       (0,SAVE_PERSIST),(0,(N,)),(0,REQUIRED),(0,P0),(0,(SC,)))
RAW_BAD=((0,O2),(0,B2),(0,C1),(0,M1),(0,APPLICATION),
         (0,EXISTING_FRACTIONAL_MUTATION),(0,FRACTIONAL_FORWARD_MUTATION),
         (1,()),(0,()),(0,REQUIRED),(0,P0),(0,(SD,)))
```

Accordingly `A=K2+(N,D)@SA`, raw `B=K2+(D,N)@SB`, `C=K2+(N)@SC`, and
`BAD=K2[primitive=MISSING]+()@SD`. Their complete expected canonical occurrence
identities are independently authored as:

```text
RN=(0,K2+(N),
    (APPLICABILITY_PARENT_OBSERVATION_MISMATCH,
     APPLICABILITY_BACKEND_GENERATION_MISMATCH),
    P0,(SC,),RAW_C,0)
RNDA=(0,K2+(N,D),
      (APPLICABILITY_PARENT_OBSERVATION_MISMATCH,
       APPLICABILITY_BACKEND_GENERATION_MISMATCH),
      P0,(SA,),RAW_A,0)
RNDB=(0,K2+(N,D),
      (APPLICABILITY_PARENT_OBSERVATION_MISMATCH,
       APPLICABILITY_BACKEND_GENERATION_MISMATCH),
      P0,(SB,),RAW_B,0)
RBAD=(1,(),
      (APPLICABILITY_PARENT_OBSERVATION_MISMATCH,
       APPLICABILITY_BACKEND_GENERATION_MISMATCH,
       APPLICABILITY_FIELD_SET_EMPTY,
       APPLICABILITY_PRIMITIVE_MISSING),
      P0,(SD,),RAW_BAD,0)
```

The complete expected contradiction-source tuple is exactly and literally:

```text
(
    (APPLICABILITY_PARENT_OBSERVATION_MISMATCH, RN),
    (APPLICABILITY_PARENT_OBSERVATION_MISMATCH, RNDA),
    (APPLICABILITY_PARENT_OBSERVATION_MISMATCH, RNDB),
    (APPLICABILITY_PARENT_OBSERVATION_MISMATCH, RBAD),
    (APPLICABILITY_BACKEND_GENERATION_MISMATCH, RN),
    (APPLICABILITY_BACKEND_GENERATION_MISMATCH, RNDA),
    (APPLICABILITY_BACKEND_GENERATION_MISMATCH, RNDB),
    (APPLICABILITY_BACKEND_GENERATION_MISMATCH, RBAD),
    (APPLICABILITY_EXACT_DUPLICATE, RNDA, RNDB, EQUAL),
    (APPLICABILITY_FIELD_SET_OVERLAP, RN, RNDA, STRICT_SUBSET),
    (APPLICABILITY_FIELD_SET_OVERLAP, RN, RNDB, STRICT_SUBSET),
    (APPLICABILITY_FIELD_SET_EMPTY, RBAD),
    (APPLICABILITY_PRIMITIVE_MISSING, RBAD),
)
```

The complete expected unique factory-diagnostic tuple is exactly and literally:

```text
(
    APPLICABILITY_PARENT_OBSERVATION_MISMATCH,
    APPLICABILITY_BACKEND_GENERATION_MISMATCH,
    APPLICABILITY_EXACT_DUPLICATE,
    APPLICABILITY_FIELD_SET_OVERLAP,
    APPLICABILITY_FIELD_SET_EMPTY,
    APPLICABILITY_PRIMITIVE_MISSING,
)
```

For every one of the 24 raw permutations of `(A,B,C,BAD)` and the independently
simulated detector schedules binding-then-pair, pair-then-binding,
reverse-detector, and interleaved, assert that exact source tuple and diagnostic
tuple. Also assert the exact parent fields
`header=K1`, `declared_manifest=(K1+(N),K1+(N,D))`, `provenance=P0`,
`validity=CURRENT`, `diagnostic_state=CONTRADICTORY`, the literal source and
diagnostic tuples above, `primitive_records=()`, and
`applicability_records=()`, followed by public result exactly
`UNKNOWN / (CONTRADICTORY_EVIDENCE,)`. The expected identities and tuples are
test constants; the test must not call the production normalizer, occurrence
sorter, conflict reducer, or diagnostic projector to build them.

The real-boundary relation cases above assert equal, strict subset, strict
superset, and disjoint using only `N` and `D`. The pure abstract-set oracle is
the only current partial-intersection test. An enum-expansion guard asserts that
the admitted `RtssStoredFieldKind` universe is exactly `(N,D)` and that real
partial intersection is unreachable. If the enum ever has at least three unique
legal members, the guard fails with literal message
`add an explicit legal real-boundary partial-intersection fixture` until a named
new-member raw fixture passes through the actual parent factory and expects
`(APPLICABILITY_FIELD_SET_OVERLAP,)`, the current contradictory parent with
empty selectable records, and exactly
`UNKNOWN / (CONTRADICTORY_EVIDENCE,)`. No production field is synthesized.

Additional exact-scope cases assert `K+()` produces
`(APPLICABILITY_FIELD_SET_EMPTY,)`; raw `K+(N,N)` produces
`(APPLICABILITY_FIELD_MEMBER_DUPLICATE,)` and cannot be silently deduplicated;
a primitive-only record missing its exact terminal compound and phase uses the
missing-compound diagnostic; and a compound-only record missing its exact
primitive uses the missing-primitive diagnostic. Each produces the same
admitted contradictory-parent/public-evaluator boundary defined above. No
primitive report covers another compound, and no compound report creates
values for its primitives. Candidate keys, conflict pairs, provenance, and
diagnostics are asserted in canonical order under all input permutations.
- Exercise integer-limit, fractional-numerator, fractional-denominator,
  optional exact-rational, and stored-bit-width domains separately. A range
  from one domain cannot satisfy another.
- Bit-width oracle values are explicit: unsigned width 8 is exactly
  `[0, 255]`; two's-complement signed width 8 is exactly `[-128, 127]`;
  unsigned width 1 is `[0, 1]`; signed width 1 is `[-1, 0]`. Test both extrema,
  one-step underflow/overflow, and arbitrarily large positive widths. Unknown,
  sign-magnitude, ones'-complement, or future representations expect
  `UNKNOWN / BIT_WIDTH_REPRESENTATION_UNKNOWN`, never a guessed interval.
- Per domain, cover inclusive lower/upper boundaries, exclusive boundaries,
  equal inclusive bounds, missing lower/open upper, open lower/missing upper,
  equal-exclusive configured failure, reversed configured failure, an
  intersection that becomes discrete-empty, other empty intersections, and
  arbitrarily large exact integers. Invalid raw backend bounds become typed
  invalid observation evidence rather than selectable contracts.
- Cover exact configured-bound conversion without implementation-derived
  expectations: integer-domain inclusive lower `59.5` -> `60`; exclusive lower
  `60` -> `61`; inclusive upper `60.5` -> `60`; exclusive upper `60` -> `59`.
  Use finite `Decimal` and `RationalCap` forms that denote the same exact
  rationals and require identical converted bounds. Open endpoints remain open.
- Assert this literal negative conversion oracle independently:

  | Bound type | Exact input | Exact converted discrete bound |
  | --- | ---: | ---: |
  | Inclusive lower | `-60.5` | `-60` |
  | Exclusive lower | `-60` | `-59` |
  | Exclusive lower | `-60.5` | `-60` |
  | Inclusive upper | `-59.5` | `-60` |
  | Exclusive upper | `-60` | `-61` |
  | Exclusive upper | `-59.5` | `-60` |

  The oracle uses inclusive lower `ceil(L)`, exclusive lower `floor(L) + 1`,
  inclusive upper `floor(U)`, and exclusive upper `ceil(U) - 1`. The review
  request's candidate `-59` for exclusive upper `-59.5` is explicitly rejected:
  `ceil(-59.5) - 1 = -60`, and `-59` violates the strict bound.
- **Negative non-integral non-empty intersection:** configured lower `-60.5`
  inclusive and upper `-58.5` exclusive convert literally to lower `-60` and
  upper `-59`; expect exactly `{-60, -59}`.
- **Negative empty intersection:** configured lower `-60` exclusive and upper
  `-59.5` inclusive convert literally to lower `-59` and upper `-60`; expect
  terminal exactly `UNSUPPORTED / EMPTY_DISCRETE_INTERSECTION`.
- **Mixed-sign control:** lower `-1.5` inclusive and upper `1.5` exclusive
  convert to `-1` and `1`; expect exactly `{-1, 0, 1}`.
- **Exact-negative-integer control:** inclusive lower and upper `-60` both
  convert to `-60`; expect exactly `{-60}`. With either equal endpoint
  exclusive, expect exactly `UNSUPPORTED / EMPTY_CONFIGURED_RANGE`.
- **Negative zero:** construct `Decimal("-0")` exactly, obtain rational `0/1`
  and discrete `0`, and assert there is no separate negative-zero policy
  value.
- **Signed minimum underflow:** two's-complement width 8 derives
  `[-128, 127]`; request `-129` expects `UNSUPPORTED` and exactly
  `(RANGE_UNDERFLOW, BIT_WIDTH_OVERFLOW)`.
- Every positive and negative conversion fixture uses only exact `int`,
  finite `Decimal`, or `RationalCap` construction; importing, accepting,
  producing, or comparing a float fails the test.
- Equal inclusive discrete bounds form one value. Equal configured endpoints
  with either exclusive are `UNSUPPORTED / EMPTY_CONFIGURED_RANGE`.
  Non-integral endpoints whose ceiling/floor conversion crosses, and otherwise
  disjoint discrete intersections, are
  `UNSUPPORTED / EMPTY_DISCRETE_INTERSECTION`. Reversed configured bounds are
  `UNSUPPORTED / INVALID_RANGE_REQUEST`.
- Cover bit-width one-step overflow/underflow, Boolean rejection, non-positive
  width, and missing/unknown representation. Parser bit limits must not appear
  as backend capability evidence.
- Denominator zero is construction-invalid; denominator one is a positive
  control. Numerator zero and denominator evidence are independently
  applicable, and one never fills the other's missing range.
- Missing required range record -> `UNKNOWN / RANGE_EVIDENCE_MISSING`;
  explicit unsupported range -> `UNSUPPORTED / RANGE_UNSUPPORTED`; typed
  invalid observed range -> `UNKNOWN / INVALID_RANGE_EVIDENCE`; empty
  continuous configured range -> `UNSUPPORTED / EMPTY_CONFIGURED_RANGE`; empty
  converted/intersected stored domain ->
  `UNSUPPORTED / EMPTY_DISCRETE_INTERSECTION`.
- If effective rational range is present, compare large exact
  `RationalCap` values and exact finite `Decimal` endpoints without float
  conversion. Independently assert exact endpoint comparisons, inclusivity,
  and reduction; prove rational range never substitutes for exact stored
  numerator/denominator bounds. Controller target bounds restrict one request
  but do not create backend support or derive cap-ladder values.
- Assert range decision provenance contains the original configured endpoints,
  exact rational conversion, discrete conversion rule/result, admitted
  observation/generations, exact backend and bit-width operands, and final
  same-domain intersection.

### Corrected sequence item 2 raw-name and namespace matrix

- Table-drive every raw classification in `IMPLEMENTATION_PLAN.md`: empty;
  whitespace-only; leading/trailing whitespace; NUL; other controls/DEL; both
  separators; rooted; UNC; drive-qualified; ADS; device path; current/parent
  segments; missing `.exe`; non-ASCII; trailing dot; trailing space; every
  reserved-stem family; each invalid Windows filename character; colon; Global
  shape; application shape/empty stem; basename versus full path; case-only;
  and normalization forms. Each row asserts its exact terminal status/reason
  and has a simple representable application-name control.
- Assert the closed overlap oracle exactly: `C:\game.exe` leads with
  `DRIVE_QUALIFIED_PATH`; `\\server\share\game.exe` with `UNC_PATH`;
  `\\?\C:\game.exe` with `DEVICE_PATH`; `..\game.exe` and
  `folder\..\game.exe` with `FULL_PATH`; `game.exe:stream` with
  `ALTERNATE_DATA_STREAM`; and `/game.exe` with `ROOTED_PATH`. Each assertion
  includes the full ordered reason tuple from the plan, not a set assembled by
  the implementation.
- Reverse raw-check registration/input order and require the identical leading
  reason and ordered tuple. Multiple matched reasons are retained across all
  structural layers, or across the current-model layer when structure passes;
  capability and namespace reasons are not evaluated after either group fails.
- Feed a raw name rejected by `CanonicalProfileIdentity` together with admitted
  backend evidence that otherwise fully supports it. Expect
  `UNSUPPORTED` led by `IDENTITY_MODEL_INCOMPATIBLE`, never `SUPPORTED` or
  `UNKNOWN`; also test the representable application name, exact Global name,
  and construction of compatible `RtssGeneration` and `RtssOwnershipToken`
  context.
- For non-ASCII and missing-suffix current-model failures, independently supply
  missing name rules, stale rules, and current fully supporting rules. Every
  input has the same current-model `UNSUPPORTED` result and no capability or
  namespace reason, proving the identity boundary wins before evidence.
- Prove a case-sensitive external namespace cannot create two distinct owners
  that collapse under current case-folded identity. A complete single-name
  exact lookup may proceed; a proved case-distinct pair is exactly
  `UNSUPPORTED / CASE_COLLISION`.
- Construct namespace evidence only through the test admission factory and
  cover snapshot identity, parent observation identity, backend/capability
  generations, kind, scope, comparison, normalization, encoding, provenance,
  freshness, diagnostic state, and both completeness modes.
- Missing, stale, invalid, incomplete, foreign, or generation-mismatched
  namespace evidence is exact `UNKNOWN`; complete authoritative no-collision
  evidence proceeds. A public request omitting a collider cannot affect the
  factory's complete enumeration, and an incomplete enumeration never supports
  the request.
- Test authoritative exact lookup, existing mutation, and new creation
  separately. Creation without absence proof for exact, canonical,
  normalization, and encoding collision keys is
  `UNKNOWN / NAMESPACE_COMPLETENESS_MISSING`.
- Case-insensitive collision -> `UNSUPPORTED / CASE_COLLISION`; unknown
  normalization -> `UNKNOWN / NORMALIZATION_UNKNOWN`; normalization mode
  incompatible with current ownership ->
  `UNSUPPORTED / IDENTITY_MODEL_INCOMPATIBLE`; proved normalization collision
  -> `UNSUPPORTED / NORMALIZATION_COLLISION`; encoding collision or lossy
  round trip -> `UNSUPPORTED / ENCODING_COLLISION`.
- Prove exact original text remains unchanged through success and every failure
  path. No `.exe`/`.cfg` insertion, basename extraction, truncation,
  replacement, case-folding, normalization, or encoded substitution occurs.

### Corrected sequence item 2 admitted name-rule trust matrix

- Name-rule children use the same parent-factory reconstruction model as
  applicability children. `RtssRawNameRuleReport` values, canonical child
  values extracted from an earlier set, copies, replacements, reconstructions,
  and caller-authored values are all untrusted factory inputs. The factory
  validates the fixed rule-set header and complete manifest, reconstructs fresh
  canonical children, and is the only route to a complete
  `RtssAdmittedNameRuleSet` supplied to `evaluate_supported_name`.
- The evaluator accepts only the complete rule-set parent. Passing a raw or
  canonical child as `admitted_name_rule_set` raises `TypeError`, produces no
  name decision, and does not emit a factory diagnostic as a public reason.
  Direct child construction therefore cannot directly produce support, while a
  caller-authored equal child submitted through the parent factory is
  intentionally equivalent to every other equal value candidate.
- Missing rules expect `UNKNOWN / NAME_RULE_EVIDENCE_MISSING`. Invalid then
  stale rules expect their exact validity reasons. Equal complete canonical
  keys or a prohibited non-exact scope produce one current contradictory
  admitted rule set with no selectable rules and expect
  `UNKNOWN / (CONTRADICTORY_NAME_RULES,)`.
- Name-rule applicability uses the literal key
  `(rule_set_identity,parent_observation_identity,backend_generation,
  capability_generation,profile_kind,namespace_scope,mechanism,
  tagged_subject_kind,exact_subject,name_context)`. Baseline
  `R=(R1,O1,B1,C1,APPLICATION,NAMESPACE1,M1,PRIMITIVE,
  SAVE_PERSIST,EXISTING_MUTATION,RULE_CONTENT1,P1,(S1,))` is exact, where the
  final three components are rule content, provenance, and canonical source
  references. Two `R` reports in one factory input, including content-equal
  copies, produce the current contradictory rule set with ordered factory
  diagnostic `(NAME_RULE_EXACT_DUPLICATE,)` and public result exactly `UNKNOWN /
  (CONTRADICTORY_NAME_RULES,)`. In a separate manifest that declares both keys,
  `R` plus a key differing in any one exact dimension succeeds as a consistent
  set with `()` diagnostics. A
  wildcard/prefix/range/all-subject/all-context applicability scope or an
  untagged primitive/compound subject produces the contradictory rule set with
  `(NAME_RULE_SCOPE_NOT_EXACT,)`; rule-content character ranges remain governed
  by the existing aggregate exact-key rule and are not applicability wildcards.
  `RULE_CONTENT2` is a distinct valid legal payload that still supports the
  exact positive-control name; changing to it proves that legal payload changes
  are evaluated on their new semantics rather than diagnosed by origin.
  Reversing either duplicate/conflict input or two legal distinct-key inputs
  preserves the same canonically ordered conflict tuple, diagnostics, and
  evaluator result. No first-wins, last-wins, or silent deduplication is tested
  or permitted.
- A separate name-rule reducer-order fixture uses expected header
  `H1=(R1,O1,B1,C1,APPLICATION,NAMESPACE1,M1,PRIMITIVE,SAVE_PERSIST,
  EXISTING_MUTATION)` and mismatched key
  `H2=(R1,O2,B1,C1,APPLICATION,NAMESPACE1,M1,PRIMITIVE,SAVE_PERSIST,
  EXISTING_MUTATION)`. Define literal sources
  `SRA=("fixture-name-source","A")`,
  `SRB=("fixture-name-source","B")`, and
  `SRC=("fixture-name-source","C")`, ordered `SRA < SRB < SRC`. `RA` and `RB`
  have equal complete key `H2`, legal `RULE_CONTENT1`, `P0`, and sources `SRA`
  and `SRB`; `RC` has the same value fields except its tagged subject scope is
  the literal `NON_EXACT_SCOPE` tag and source `SRC`, so it is non-comparable.
  Using the same independently authored raw tag ranks as the applicability
  fixture, define these exact occurrence identities, without a production
  normalizer:

  ```text
  NRA=(0,H2,(NAME_RULE_PARENT_OBSERVATION_MISMATCH,),
       P0,(SRA,),RAW_NRA,0)
  NRB=(0,H2,(NAME_RULE_PARENT_OBSERVATION_MISMATCH,),
       P0,(SRB,),RAW_NRB,0)
  NRC=(1,(),
       (NAME_RULE_PARENT_OBSERVATION_MISMATCH,NAME_RULE_SCOPE_NOT_EXACT),
       P0,(SRC,),RAW_NRC,0)
  ```

  The raw tuples are also literal and list, in order, rule-set identity, parent
  identity, backend generation, capability generation, profile kind, namespace
  scope, mechanism, tagged subject kind, exact subject, name context, rule
  content, provenance, and source references:

  ```text
  RAW_NRA=((0,R1),(0,O2),(0,B1),(0,C1),(0,APPLICATION),(0,NAMESPACE1),
           (0,M1),(0,PRIMITIVE),(0,SAVE_PERSIST),(0,EXISTING_MUTATION),
           (0,RULE_CONTENT1),(0,P0),(0,(SRA,)))
  RAW_NRB=((0,R1),(0,O2),(0,B1),(0,C1),(0,APPLICATION),(0,NAMESPACE1),
           (0,M1),(0,PRIMITIVE),(0,SAVE_PERSIST),(0,EXISTING_MUTATION),
           (0,RULE_CONTENT1),(0,P0),(0,(SRB,)))
  RAW_NRC=((0,R1),(0,O2),(0,B1),(0,C1),(0,APPLICATION),(0,NAMESPACE1),
           (0,M1),(2,()),(0,SAVE_PERSIST),(0,EXISTING_MUTATION),
           (0,RULE_CONTENT1),(0,P0),(0,(SRC,)))
  ```

  The independently written complete expected source and diagnostic tuples are
  exactly:

  ```text
  (
      (NAME_RULE_PARENT_OBSERVATION_MISMATCH, NRA),
      (NAME_RULE_PARENT_OBSERVATION_MISMATCH, NRB),
      (NAME_RULE_PARENT_OBSERVATION_MISMATCH, NRC),
      (NAME_RULE_EXACT_DUPLICATE, NRA, NRB),
      (NAME_RULE_SCOPE_NOT_EXACT, NRC),
  )

  (
      NAME_RULE_PARENT_OBSERVATION_MISMATCH,
      NAME_RULE_EXACT_DUPLICATE,
      NAME_RULE_SCOPE_NOT_EXACT,
  )
  ```

  Assert both tuples for all six permutations of `(RA,RB,RC)` and
  binding-first, duplicate-first, scope-first, reverse, and interleaved detector
  schedules. Every case asserts the exact parent fields `header=H1`,
  `declared_manifest=(H1,)`, `provenance=P0`,
  `source_references=(SRA,SRB,SRC)`, `validity=CURRENT`,
  `diagnostic_state=CONTRADICTORY`, the literal stored source and diagnostic
  tuples above, and `rules=()`. That current contradictory rule-set parent
  evaluates exactly
  `UNKNOWN / (CONTRADICTORY_NAME_RULES,)`. The oracle never calls the production
  occurrence normalizer, sorter, reducer, or diagnostic projector.
- The literal authority and copy oracle, with every other capability/name input
  supporting, is:

  | Candidate and path through the one name-rule parent factory | Admission result | Exact ordered factory diagnostics | Exact public evaluator result |
  | --- | --- | --- | --- |
  | Original complete rule-set parent `Q` returned by the factory | current consistent rule set | `()` | `SUPPORTED / (SUPPORTED_REQUIREMENT,)` |
  | `copy.copy(Q)` | current consistent rule set after entry validation | `()` | `SUPPORTED / (SUPPORTED_REQUIREMENT,)` |
  | `copy.deepcopy(Q)` | current consistent rule set after entry validation | `()` | `SUPPORTED / (SUPPORTED_REQUIREMENT,)` |
  | Exact field-for-field, caller-authored equal, or fully populated equal `object.__new__` reconstruction of `Q` | current consistent rule set after entry reconstruction | `()` | `SUPPORTED / (SUPPORTED_REQUIREMENT,)` |
  | `Q` with independently copied but equal provenance/source values | current consistent rule set after entry reconstruction | `()` | `SUPPORTED / (SUPPORTED_REQUIREMENT,)` |
  | Incomplete `object.__new__` reconstruction of `Q` | parent boundary raises `TypeError` | no diagnostic tuple; `TypeError` precedes reconstruction | no name decision and no reason tuple |
  | Unchanged `dataclasses.replace(Q)` | current consistent rule set after entry reconstruction | `()` | `SUPPORTED / (SUPPORTED_REQUIREMENT,)` |
  | `dataclasses.replace(Q, rule_set_identity=R2)` while nested rules remain bound to `R1` | current contradictory rule set after entry reconstruction | `(NAME_RULE_SET_IDENTITY_MISMATCH,)` | `UNKNOWN / (CONTRADICTORY_NAME_RULES,)` |
  | Whole `Q` consistently replaced to `R2`, including every nested rule binding | current consistent rule set after entry reconstruction | `()` | `UNKNOWN / (FOREIGN_NAME_RULE_SET,)` against the unchanged `R1` request |
  | Original candidate `R` | consistent rule set | `()` | `SUPPORTED / (SUPPORTED_REQUIREMENT,)` |
  | `copy.copy(R)` | consistent rule set | `()` | `SUPPORTED / (SUPPORTED_REQUIREMENT,)` |
  | `copy.deepcopy(R)` | consistent rule set | `()` | `SUPPORTED / (SUPPORTED_REQUIREMENT,)` |
  | Exact field-for-field reconstruction of `R` | consistent rule set | `()` | `SUPPORTED / (SUPPORTED_REQUIREMENT,)` |
  | Unchanged `dataclasses.replace(R)` | consistent rule set | `()` | `SUPPORTED / (SUPPORTED_REQUIREMENT,)` |
  | Caller-authored child with every value equal to `R` | consistent rule set | `()` | `SUPPORTED / (SUPPORTED_REQUIREMENT,)` |
  | `R` with independently copied but equal `P1` and `(S1,)` | consistent rule set | `()` | `SUPPORTED / (SUPPORTED_REQUIREMENT,)` |
  | Fully populated exact `object.__new__` or equivalent reconstruction of `R` | consistent rule set | `()` | `SUPPORTED / (SUPPORTED_REQUIREMENT,)` |
  | Incomplete constructor-bypass candidate or wrong child type | contradictory rule set | `(NAME_RULE_EVIDENCE_UNTRUSTED,)` | `UNKNOWN / (CONTRADICTORY_NAME_RULES,)` |
  | `dataclasses.replace(R, rule_set_identity=R2)` against the fixed `R1` header | contradictory rule set | `(NAME_RULE_SET_IDENTITY_MISMATCH,)` | `UNKNOWN / (CONTRADICTORY_NAME_RULES,)` |
  | `dataclasses.replace(R, parent_observation_identity=O2)` | contradictory rule set | `(NAME_RULE_PARENT_OBSERVATION_MISMATCH,)` | `UNKNOWN / (CONTRADICTORY_NAME_RULES,)` |
  | `dataclasses.replace(R, backend_generation=B2)` | contradictory rule set | `(NAME_RULE_BACKEND_GENERATION_MISMATCH,)` | `UNKNOWN / (CONTRADICTORY_NAME_RULES,)` |
  | `dataclasses.replace(R, capability_generation=C2)` | contradictory rule set | `(NAME_RULE_CAPABILITY_GENERATION_MISMATCH,)` | `UNKNOWN / (CONTRADICTORY_NAME_RULES,)` |
  | `dataclasses.replace(R, profile_kind=GLOBAL)` | contradictory rule set | `(NAME_RULE_PROFILE_KIND_MISMATCH,)` | `UNKNOWN / (CONTRADICTORY_NAME_RULES,)` |
  | `dataclasses.replace(R, namespace_scope=NAMESPACE2)` | contradictory rule set | `(NAME_RULE_NAMESPACE_SCOPE_MISMATCH,)` | `UNKNOWN / (CONTRADICTORY_NAME_RULES,)` |
  | `dataclasses.replace(R, mechanism=M2)` | contradictory rule set | `(NAME_RULE_MECHANISM_MISMATCH,)` | `UNKNOWN / (CONTRADICTORY_NAME_RULES,)` |
  | `dataclasses.replace(R, tagged_subject_kind=TERMINAL_COMPOUND)` | contradictory rule set | `(NAME_RULE_SUBJECT_KIND_MISMATCH,)` | `UNKNOWN / (CONTRADICTORY_NAME_RULES,)` |
  | `dataclasses.replace(R, exact_subject=ACTIVATE_RELOAD)` | contradictory rule set | `(NAME_RULE_OPERATION_MISMATCH,)` | `UNKNOWN / (CONTRADICTORY_NAME_RULES,)` |
  | `dataclasses.replace(R, name_context=CREATE_PROFILE)` | contradictory rule set | `(NAME_RULE_CONTEXT_MISMATCH,)` | `UNKNOWN / (CONTRADICTORY_NAME_RULES,)` |
  | `dataclasses.replace(R, rule_content=RULE_CONTENT2)` | consistent rule set | `()` | `SUPPORTED / (SUPPORTED_REQUIREMENT,)` because this distinct legal payload supports the exact target |
  | `dataclasses.replace(R, provenance=P2)` | contradictory rule set | `(NAME_RULE_PROVENANCE_MISMATCH,)` | `UNKNOWN / (CONTRADICTORY_NAME_RULES,)` |
  | `dataclasses.replace(R, source_references=(S2,))` | contradictory rule set | `(NAME_RULE_SOURCE_REFERENCE_MISMATCH,)` | `UNKNOWN / (CONTRADICTORY_NAME_RULES,)` |
  | Standalone raw or canonical `R` child passed as `admitted_name_rule_set` | parent boundary raises `TypeError` | no diagnostic tuple; parent factory is not a child overload | no name decision and no reason tuple |
  | Exact complete-rule-set positive control reconstructed from `R` and its manifest | consistent rule set | `()` | `SUPPORTED / (SUPPORTED_REQUIREMENT,)` |

- Original, shallow-copy, deep-copy, and exact complete-parent reconstruction
  of the admitted rule set have the same result after total parent validation,
  as does unchanged `dataclasses.replace(rule_set)`. An incomplete complete-
  parent `object.__new__` bypass raises `TypeError` before evaluation. A changed
  whole parent follows the two explicit structural-inconsistency versus
  fully-consistent-foreign rows above; unchanged replacement coverage also
  applies to child value `R` through the real parent boundary.
- There is no copyable name-rule authority material. Exact copied provenance is
  ordinary equal data; invented authority fields are wrong input shape. Reject
  missing applicability coverage, selectable rules in a contradictory set,
  contradictory stale/invalid state, mutable nested collections, foreign source
  references, or inconsistent parent generations through their literal
  structural rules rather than object origin.
- Existing lookup rules cannot prove mutation or creation, application rules
  cannot prove Global, and one mechanism/operation cannot prove another.
  A current consistent complete exact-scope rule set is the independent
  positive control.

### Corrected sequence item 2 normalization compatibility matrix

- Define oracle keys explicitly in fixtures: unchanged external exact key,
  admitted external normalized key, current
  `CanonicalProfileIdentity.canonical_key`, encoded key, and authoritative
  namespace identity. Policy code does not generate the expected keys.
- `EXACT_NONE` with normalized key equal to the exact key, complete current
  evidence, and no case/encoding/canonical collision may proceed to
  `SUPPORTED`. Any collider has its exact `UNSUPPORTED` reason.
- `NAMED` existing exact lookup and existing mutation each have a positive
  control proving one external exact identity, one normalized identity, one
  representable current ownership key, unchanged audit spelling, and no other
  exact/normalized/encoded/case/canonical mapping to that key.
- `NAMED` creation has a separate positive control with authoritative absence
  for the external exact, normalized, encoded, case, and canonical keys plus
  one unambiguous predicted ownership mapping.
- A named normalization collision expects
  `UNSUPPORTED / NORMALIZATION_COLLISION`; a many-to-one mapping into the
  current owner expects `UNSUPPORTED / IDENTITY_MODEL_INCOMPATIBLE`; incomplete
  mapping/no-collision proof expects
  `UNKNOWN / NORMALIZATION_PROOF_INCOMPLETE`; and unknown normalization expects
  `UNKNOWN / NORMALIZATION_UNKNOWN`.
- Missing, stale, invalid, foreign, parent-mismatched, backend-mismatched, and
  capability-mismatched rule or namespace evidence independently expect the
  exact `UNKNOWN` reason. A Boolean no-collision assertion never substitutes
  for the complete mapping proof.
- Existing exact lookup, existing mutation, and creation fixtures are not
  reused across contexts. Current-model-incompatible names remain
  `UNSUPPORTED` before every normalization fixture.

### Planned sequence item 2 capability/name contract tests

These tests are future deterministic work. They require no RTSS, Windows, GPU,
game, profile file, Dear PyGui, PDH, LHM, or live adapter.

- Assert unique complete membership with no aliases for every proposed policy
  status, support-state, validity, origin, mechanism, primitive-operation,
  compound-requirement, postcondition, dependency-applicability,
  dependency-context, name-context,
  comparison/normalization, completeness, diagnostic-state, and reason enum.
- Construct every immutable raw request/report with valid minimum data; reject
  wrong enums, Boolean integers, negative generations, duplicate mechanism
  records, duplicate source identities, mutable collections, empty diagnostic
  codes, and inconsistent profile kinds.
- Prove raw reports, `RtssCapabilityInfo`, caller-created
  `RtssCapabilityEvidence`, version labels, Boolean flags, and standalone child
  values cannot directly create a supported complete parent or `SUPPORTED`
  decision. This is a parent-boundary rule, not a claim that two exactly equal
  value candidates have different authority.
- Run the literal applicability and name-rule authority tables above through
  their real parent factories. Original, shallow copy, deep copy, exact value
  reconstruction, unchanged child `dataclasses.replace()`, caller-authored
  equal value, exact copied provenance/source material, and fully populated
  exact `object.__new__` candidates must each independently produce the stated
  consistent-parent `()` diagnostics and exact positive result. Do not derive
  one expected tuple from another candidate or from a production helper.
- Run every changed bound-field replacement separately with the unchanged
  parent header and manifest. Assert its literal one-element mismatch tuple,
  contradictory parent with no selectable records, and exact parent-level
  `UNKNOWN` result. The two explicitly combined applicability parent/source
  mismatches assert their literal two-element tuple in declaration order.
- Assert incomplete `object.__new__` child candidates use the literal untrusted
  factory diagnostic and contradictory-parent result. Unchanged complete-parent
  `dataclasses.replace()` candidates must traverse entry reconstruction and
  produce the exact positive result; header-only changed and fully consistently
  changed parents produce their two literal rows above. Incomplete complete-
  parent bypasses and standalone applicability or name-rule children passed in
  the complete-parent position raise `TypeError` and produce no decision or
  public reason tuple.
- Assert no authority/provenance token, marker, registry, copied-origin flag, or
  object-identity test exists. Exact copied provenance is ordinary immutable
  data; changed provenance and source references use their named structural
  mismatch diagnostics. A prior factory origin never changes the expected
  result of a completely equal candidate submitted through the same boundary.
- Bind every derived capability record to complete immutable source records.
  Missing, foreign, or generation-mismatched sources evaluate unknown; cyclic
  or contradictory sources create the sole typed contradictory observation.
- Keep `RtssCapabilitySupportState`, `RtssEvidenceValidity`, and
  `RtssEvidenceOrigin` orthogonal: direct/derived never implies supported,
  stale/invalid never becomes current, and a stale/invalid unsupported report
  remains diagnostically visible while its own terminal result is `UNKNOWN`.
- Preserve `ProfileKind`, `RtssStoredFieldKind`,
  `RtssDenominatorStrategy`, `RtssGeneration`, and item-1 capability/ownership
  invariants without changing item-1 accepted outcome matrices.
- Preserve exact original name bytes/text in requests and decisions; reject
  silent truncation, replacement, stripping, case change, normalization, or
  encoded-name substitution.

### Planned sequence item 2 capability policy tests

- Exact requested mechanism/operation/profile kind with current admitted direct
  support returns `SUPPORTED` and the exact selected mechanism.
- Explicitly unsupported mechanism returns `UNSUPPORTED`; missing mechanism
  evidence returns `UNKNOWN`; neither tries another mechanism.
- Missing observation, raw-only report, stale observation, invalid observation,
  current temporarily unavailable primitive, foreign observation,
  backend-generation mismatch, and capability-generation mismatch each return
  deterministic `UNKNOWN` with its own typed reason. There is no whole-
  observation unavailable case.
- The factory-admitted contradictory observation returns `UNKNOWN /
  CONTRADICTORY_EVIDENCE`, regardless of any supporting raw source; duplicate
  identical primitive keys remain construction errors.
- Direct and derived evidence with the same complete trusted sources produce
  the same decision; incomplete or foreign derivation does not.
- Supported read plus unsupported write allows only the exact read request.
- Supported write plus unsupported or unknown exact readback rejects mutation.
- Supported write/readback with `REQUIRED` save or activation but without the
  matching primitive rejects mutation with the exact deterministic primitive
  reason. `NOT_REQUIRED` is the only state that omits that primitive;
  `UNKNOWN`, missing, or binding/provenance/source-mismatched applicability
  returns `UNKNOWN`.
  Missing exact restoration rejects mutation independently.
- For save and activation separately, cover required/supported,
  required/unsupported, required/missing, proved not required,
  applicability unknown, and applicability missing. Repeat for integer forward,
  fractional forward, integer restoration, fractional restoration, and
  integer/fractional creation-forward contexts.
- Prove forward save required with restoration save not required, and forward
  activation not required with restoration activation required. No
  forward/restoration default or equality inference is permitted.
- Exact integer read/write capability does not imply fractional capability.
- Fractional numerator support with denominator unsupported or unknown rejects
  the complete fractional requirement; the inverse does likewise.
- A mechanism requiring a combined exact numerator/denominator operation
  rejects numerator-only or denominator-only applicability.
- Exact domain-specific configured and admitted numeric ranges follow the full
  corrected range matrix above. Parser bounds are not treated as backend
  bounds.
- Global-only evidence rejects application requests and application-only
  evidence rejects Global requests with `PROFILE_KIND_UNSUPPORTED`.
- Existing-profile read can be supported while existing mutation, creation,
  deletion, or verified absence remains unsupported.
- Profile creation is supported only with exact creation, deletion, verified
  absence, readback, and restoration support for the same mechanism/kind.
- Explicitly unsupported create, delete, or verified absence yields
  `UNSUPPORTED`; unknown/unavailable evidence yields `UNKNOWN`.
- Deletion without verified-absence support never produces `SUPPORTED`.
- A capability that names a general RTSS version or profile-file access but
  lacks the exact operation record is unknown, not implicitly supported.
- Reordering immutable records does not change the decision or diagnostic
  ordering; repeated evaluation is deterministic.

### Planned sequence item 2 supported-name policy tests

- Existing supported simple application name and supported Global identity
  return `SUPPORTED` only under exact mechanism/kind/existing-lookup evidence.
- Creation of a supported simple name requires separate creation name evidence
  plus complete creation capability dependencies.
- Existing lookup/read may be supported while creation or mutation of the same
  exact name is denied.
- Unknown encoding returns `UNKNOWN`; explicitly unsupported encoding returns
  `UNSUPPORTED`; neither guesses ASCII, ANSI, UTF-8, UTF-16, or a locale code
  page.
- Known exact character and encoded-byte maxima accept zero/one-below/exact
  boundary as structurally applicable and reject one-above. Test component and
  total limits separately, including evidence-backed suffix expansion.
- A required unknown component or total limit returns `UNKNOWN` rather than
  silently accepting or truncating.
- A character explicitly invalid under admitted mechanism/kind/operation rules
  returns `UNSUPPORTED`; a character with no applicable rule returns
  `UNKNOWN`.
- Non-ASCII exact names never return `SUPPORTED` or `UNKNOWN` under the current
  canonical identity model. Missing, stale, invalid, or otherwise complete
  lossless backend evidence all leave the leading result exactly
  `UNSUPPORTED / IDENTITY_MODEL_INCOMPATIBLE`.
- Non-ASCII with unknown encoding, lossy round trip, mismatched encoded bytes,
  unknown normalization, or missing collision evidence is never supported.
- Case-sensitive admitted evidence retains case-distinct exact names in the
  decision/audit record. A complete single-name exact lookup may proceed; a
  pair that collapses under current ownership returns exactly
  `UNSUPPORTED / CASE_COLLISION`.
- Case-insensitive evidence accepts one unambiguous spelling and rejects a
  proven case-only collision; exact original spelling remains unchanged.
- Normalization-equivalent exact names with a proven collision return exactly
  `UNSUPPORTED / NORMALIZATION_COLLISION`. Unknown normalization returns
  `UNKNOWN / NORMALIZATION_UNKNOWN`; an incompatible normalization mode returns
  `UNSUPPORTED / IDENTITY_MODEL_INCOMPATIBLE`; no normalization is performed.
- A known named normalization with the complete one-to-one proof and no
  collision has positive controls for existing lookup, existing mutation, and
  creation. Incomplete proof is exactly
  `UNKNOWN / NORMALIZATION_PROOF_INCOMPLETE`; many-to-one ownership mapping is
  exactly `UNSUPPORTED / IDENTITY_MODEL_INCOMPATIBLE`.
- Exact profile-kind mismatch, Global/application rule reuse, or
  executable-name/full-path rule reuse is rejected.
- An otherwise valid name is `UNSUPPORTED` for a current explicit unsupported
  dependency and `UNKNOWN` for a missing, unavailable, stale, invalid, or
  unknown dependency under the closed algebra.
- Stale name-rule evidence, foreign encoded evidence, backend/capability
  generation mismatch, or collision data from another namespace fails closed.
- No silent `.exe`, `.cfg`, separator, basename, path, case, or normalization
  rewrite occurs. Derived target evidence must preserve the exact audited
  source name.
- Identical input and admitted evidence always produce identical status,
  reason tuple, canonical/encoded output, and audit summary.

### Planned sequence item 2 regression and integrity tests

- Item-1 ownership generation anchoring remains enforced for direct and nested
  forged future backend/capability generations.
- Item-1 failed/unsupported complete-pair rejection, partial exact-field
  behavior, factory-only readback/operation/conflict evidence, structural token
  copy semantics, and enum uniqueness remain passing.
- Policy imports no production RTSS module, filesystem adapter, Dear PyGui,
  Win32/registry, LHM, PDH, GPU, game, or Lossless Scaling dependency.
- Policy creates no transaction registry, single-use token store,
  serialization lock, coordinator, ownership release, mutation journal,
  operation evidence, conflict evidence, rollback, or live adapter.
- Supported-name evaluation performs no filesystem access and opens no profile
  file.
- Tests assert no mutation or external operation appears in the deterministic
  operation log.
- Planning-correction integrity checks proved only the four task-authorized
  planning files changed, no absolute local path or compatibility claim was
  added, and no generated/cache/bytecode artifact remained. Documentation-only
  acceptance integrity checks prove exactly `CURRENT_STATUS.md`,
  `REVIEW_FINDINGS.md`, `DECISIONS.md`, `IMPLEMENTATION_PLAN.md`, `TEST_PLAN.md`,
  and `RELEASE_NOTES.md` changed. A whitespace-normalized cross-document status
  guard requires those six documents to record reviewed source
  `c3047fc37248392b74255f36844120fc0f6fef82`, the exact approved verdict,
  explicit user acceptance, completed planning, absent item-2 implementation,
  and unauthorized sequence item 3 and later work. Status and release documents
  also record separately authorized non-rewriting stacked publication as the
  next safe action. No absolute local path, compatibility or performance claim,
  or generated/cache/bytecode artifact may be added.
- The complete suite runs with `PYTHONDONTWRITEBYTECODE=1`; item-2
  implementation acceptance requires all existing and new tests to pass.

### Later adapter, manual, and physical capability/name validation

This evidence is required later and is not performed or claimed by the
deterministic item-2 implementation:

- record exact RTSS version/build and installed API/DLL surface;
- enumerate profile existence, exact field read/write, flags, save,
  activation, readback, restoration, creation, deletion, and verified-absence
  behavior independently;
- compare API and complete profile-file mechanisms and record exact file
  format, revision, atomicity, and unrelated-field preservation;
- test exact encoding, encoded bytes, round trip, component and total
  character/byte limits, suffix expansion, invalid/reserved characters, and
  non-ASCII behavior for DLL lookup and profile files separately;
- test Global versus application naming, executable basename versus full path,
  existing lookup, creation, case sensitivity, case-only collisions,
  normalization forms, and normalization collisions;
- test RTSS exit/restart, adapter re-enumeration, capability-generation
  transition, stale observations, and reacquisition;
- test deletion plus exact verified absence and restoration after every
  partially completed creation path;
- test conflicting external edits, revision/document changes, and any
  available cross-process serialization;
- use only disposable profiles for destructive/failure cases and record all
  environment/version details; and
- make no RTSS, Windows, RX 7900 XTX, Lossless Scaling, display, VRR, or
  frame-generation support claim until the complete applicable matrix passes.

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
- Characterize the existing Stage 1 structural rejection matrix for empty
  input, whitespace, controls, missing `.exe`, dot components, trailing
  dot/space, reserved Windows stems, separators, rooted/path/device/stream
  forms, and containment escapes. Item-2 policy tests separately prove that
  these current safeguards are not treated as universal evidence of RTSS DLL
  or profile-file rules.
- Reject unsupported Unicode under the current identity contract; any future
  policy support requires explicit admitted lossless encoding, defined
  comparison/normalization behavior, collision evidence, and satisfied
  character and encoded-byte limits.
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
  exact field and active operation required for capture, mutation, readback,
  rollback, and exact restoration verification; every save/activation slot
  must have exact-context applicability, every `REQUIRED` primitive must be
  supported, and only `NOT_REQUIRED` omits a primitive.
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
  pre-mutation recheck -> mutation -> each forward-context `REQUIRED` save then
  activation in phase order -> readback -> verify -> ownership retention ->
  unlock. `NOT_REQUIRED` operations are absent from the log.
- Successful rollback/restore uses the separate restoration applicability
  records; forward and restoration operation logs may differ exactly as those
  admitted records specify.
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
  owned limiter bits, then performs only restoration-context save/activation
  operations admitted as `REQUIRED`, and verifies. `NOT_REQUIRED` operations
  are absent; `UNKNOWN` could not have admitted the mutation.
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
