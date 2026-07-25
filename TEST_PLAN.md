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
sequence-item-2 plan defines the matrix below after two rejected planning
reviews. This correction commit must pass independent read-only review and a
later acceptance documentation step must explicitly authorize implementation;
implementation remains unauthorized.

Every corrected item-2 test below must use a public or realistically reachable
policy path, a test-only factory/admission fixture, an independently specified
expected status/reason tuple, and a positive control. Tests must not construct
the decision under test as their oracle. Sequence item 2 implementation remains
prohibited until this second corrected planning commit passes another
independent read-only review and a later acceptance documentation step
explicitly authorizes implementation.

### Corrected sequence item 2 context and decision-algebra matrix

- **Matching context:** current admitted observation plus a structurally equal
  `RtssCapabilityEvaluationContext` copy returns the positive-control
  `SUPPORTED`; object identity is never asserted.
- **Context mismatch:** independently test foreign observation identity,
  backend-generation mismatch, capability-generation mismatch, profile-kind
  mismatch, and source/policy-scope mismatch. Each uses otherwise fully
  supporting admitted evidence and expects exact `UNKNOWN` status and the
  designated leading reason.
- **Replacement attacks:** nested `dataclasses.replace()` of context,
  observation identity, primitive source, backend generation, or capability
  generation cannot retain trust; unchanged nested structural copies remain
  accepted.
- **Caller-authored context:** a perfectly matching public context with absent,
  raw, caller-created, directly constructed, or untrusted observation evidence
  returns `UNKNOWN`, never `SUPPORTED`. The positive control differs only by
  test-factory admission.
- **Primitive truth table:** exact tests cover current supported ->
  `SUPPORTED`; current unsupported -> `UNSUPPORTED`; current unknown ->
  `UNKNOWN`; stale supported -> `UNKNOWN`; stale unsupported -> `UNKNOWN` with
  stale then reported-unsupported reasons; invalid supported -> `UNKNOWN`;
  invalid unsupported -> `UNKNOWN` with invalid then reported-unsupported
  reasons; current primitive temporarily unavailable -> `UNKNOWN`; missing ->
  `UNKNOWN`; foreign/backend/capability mismatch -> `UNKNOWN`.
- **Whole-observation availability:** absence is the only missing-observation
  representation and expects `UNKNOWN / CAPABILITY_EVIDENCE_MISSING`.
  Current, stale, and invalid consistent snapshots are admitted; stale and
  invalid snapshots expect their exact `UNKNOWN` reasons. A current
  contradictory snapshot with no selectable records expects
  `UNKNOWN / CONTRADICTORY_EVIDENCE`. No observation-unavailable fixture,
  branch, or expected result exists.
- **Observation factory invariants:** reject contradictory plus stale/invalid,
  contradictory with selectable records, consistent snapshots with missing or
  duplicate applicability keys, stale/invalid primitive unavailability, and
  any attempted observation-availability field. Admit current primitive
  unavailability only inside a current consistent complete snapshot.
- **One contradiction policy:** the test admission factory converts
  contradictory direct or derived sources into the typed contradictory
  observation with no selectable records. It evaluates exactly `UNKNOWN /
  CONTRADICTORY_EVIDENCE`; tests do not also expect constructor rejection for
  that semantic state. Duplicate identical primitive keys remain separate
  structural construction errors.
- **Mixed dependencies:** current unsupported plus current unknown ->
  `UNSUPPORTED`; current unsupported plus stale dependency -> `UNSUPPORTED`
  while retaining the stale reason; all current supported -> `SUPPORTED`.
  Reverse input order produces the identical status and reason tuple.
- **Stable failure reasons:** construct one legally co-applicable failing input
  containing every failure category and
  assert request structure; identity; missing/foreign/generation/kind/scope;
  provenance; invalid then stale; contradiction/derivation; canonical primitive
  order with unsupported before temporary-unavailable before unknown; range;
  encoding/length/character; namespace; case; normalization; encoding
  collision; canonical collision. Duplicates collapse without changing order.
  `SUPPORTED_REQUIREMENT` is absent from every failing tuple.
- **Separate success reason:** one otherwise identical fully supporting input
  expects `SUPPORTED` and exactly `(SUPPORTED_REQUIREMENT,)`; success is never
  aggregated with failures. Categories that cannot legally coexist use
  separate single-category tests.
- **Derived sources:** all direct current supported sources -> supported
  derived record; a current unsupported source -> `UNSUPPORTED`; missing,
  foreign, mismatched, unavailable, stale, invalid, or unknown source ->
  `UNKNOWN`; contradictory or cyclic sources -> typed contradictory
  observation and `UNKNOWN`. Source tuple order does not affect results.

### Corrected sequence item 2 taxonomy and range matrix

- Assert unique, disjoint membership for `RtssPrimitiveOperation`,
  terminal `RtssCompoundRequirement`, internal
  `RtssInternalDependencyBundle`, and `RtssRequiredPostcondition`. No internal
  bundle or postcondition is publicly selectable or appears in the primitive
  or terminal compound enums.
- For every primitive operation, factory-admit supported, unsupported, unknown,
  stale, and wrong-kind records through the public evaluator.
- For existing read, existing integer mutation, existing fractional mutation,
  exact readback, exact restoration, profile creation, deletion restoration,
  and verified absence, test the complete flattened ordered dependency bundle
  and remove each dependency one at a time.
- Assert `COORDINATED_FRACTIONAL_WRITE` is an internal ordered reversible
  numerator-write/denominator-write expansion, not an atomic primitive or
  terminal requirement. There is no public evaluator request for it.
- Existing fractional mutation positive control independently supplies:
  existence lookup; exact current numerator and denominator reads; both
  coordinated writes; save; activation; exact pair readback; and exact pair
  restoration capability. Removing each leaf once yields `UNSUPPORTED` for a
  current explicitly unsupported leaf and `UNKNOWN` for missing, unknown,
  stale, invalid, or temporarily unavailable evidence.
- Independently expect failure for numerator-only support, denominator-only
  support, missing save, missing activation, missing exact readback, and
  missing exact restoration. Static capability output must contain no claim
  that a write, readback, save, activation, rollback, or restoration actually
  occurred.
- For exact-value-observed, save-confirmed, activation-confirmed,
  profile-exists, profile-absent, and restored-equals-captured postconditions,
  verify that item 2 returns capability requirements only and never fabricates
  a later runtime success.
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

- Direct construction and raw caller-authored `RtssRawNameRuleReport` objects
  cannot produce support. The positive control uses only the deterministic
  test admission factory and differs only by admission.
- Assert exact matching for rule-set identity, parent capability-observation
  identity, backend generation, capability generation, profile kind, namespace
  scope, mechanism, primitive/terminal operation, and
  existing-lookup/existing-mutation/creation context. Vary each dimension
  independently while all others support; expect the exact `UNKNOWN` mismatch
  reason.
- Missing rules expect `UNKNOWN / NAME_RULE_EVIDENCE_MISSING`. Invalid then
  stale rules expect their exact validity reasons. A raw duplicate or
  overlapping applicability report produces one current contradictory
  admitted rule set with no selectable rules and expects
  `UNKNOWN / CONTRADICTORY_NAME_RULES`.
- Reject factory inputs with missing applicability coverage, selectable rules
  in a contradictory set, contradictory stale/invalid state, mutable nested
  collections, foreign source references, or inconsistent parent generations.
- Attempt direct `dataclasses.replace()` and nested replacement of identity,
  parent, generations, scope, applicability, content, provenance, validity,
  and contradiction state. Each changed copy must rerun validation or lose
  matching trust; an unchanged structurally equal factory copy is accepted
  without object-identity assertions.
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
  compound-requirement, postcondition, name-context,
  comparison/normalization, completeness, diagnostic-state, and reason enum.
- Construct every immutable raw request/report with valid minimum data; reject
  wrong enums, Boolean integers, negative generations, duplicate mechanism
  records, duplicate source identities, mutable collections, empty diagnostic
  codes, and inconsistent profile kinds.
- Prove raw reports, `RtssCapabilityInfo`, caller-created
  `RtssCapabilityEvidence`, version labels, and Boolean flags cannot directly
  create a supported admitted observation or `SUPPORTED` decision.
- Prove admitted observations are factory-controlled: direct construction,
  `object.__new__` followed by ordinary initialization, public factory search,
  `dataclasses.replace()`, nested replacement, and copied future-generation
  attempts cannot acquire trust.
- Accept structurally equal immutable admitted-observation copies as the same
  logical evidence where the factory contract permits copying; reject any
  changed observation identity, content, validity, provenance, source,
  backend generation, or capability generation.
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
- Supported write/readback without save, activation, or exact restoration
  rejects mutation with the first deterministic missing dependency reason and
  retains all applicable reasons in stable order.
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
- Documentation/integrity checks prove only the approved planning/implementation
  files changed, no absolute local path was added, no compatibility claim was
  added, and no generated/cache/bytecode artifact remains.
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
