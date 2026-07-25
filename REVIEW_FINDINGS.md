# Review Findings

## Review baseline

- Repository: `Drakenliger/DynamicFPSLimiter`
- Reviewed branch: `main`
- Reviewed commit: `5f89c49a9e18612b4645bb46a3b6a6e875612e04`
Review provenance consists of these local, ignored review inputs, which are not
tracked in Git:

- `review-input/DynamicFPSLimiter_Main_Branch_Deep_Technical_Review.md`
- `review-input/codex-results/01_controller_hardware_p0_verification.md`
- `review-input/codex-results/02_rtss_security_p0_verification.md`
- `review-input/codex-results/03_lifecycle_autopilot_p0_verification.md`

These names are retained for provenance only. A fresh clone or future session
does not need access to the local reports. `REVIEW_FINDINGS.md` is the durable
active ledger and contains all accepted findings, classifications, wording
refinements, priorities, and test links needed to continue the work.

## Release gate

Release is blocked for unattended RX 7900 XTX/Autopilot use. All open P0 and P1
findings must have an accepted disposition, automated coverage where possible,
and applicable Windows/RTSS/hardware evidence. Hardware- or version-dependent
effects are not Confirmed merely because code changes or unit tests pass.

## Definitions

Severity:

- **Critical:** immediate risk of severe compromise, data loss, or uncontrolled
  persistent external state.
- **High:** release-blocking correctness, safety, security, or lifecycle defect.
- **Medium:** material defect or design gap with narrower conditions or impact.
- **Low:** limited or dormant defect.
- **Informational:** documentation, maintenance, or release-quality concern.

Status:

- **Confirmed:** established by source control flow or an applicable interface
  contract.
- **Likely:** source establishes a credible path; external runtime behavior
  determines manifestation.
- **Possible:** a required environment, version, hardware, or deployment
  precondition is unverified.
- **Informational:** an observed quality gap, not asserted as a runtime defect.
- **Improvement:** a beneficial change without a demonstrated defect.
- **Rejected:** evidence does not support the proposed finding.

State:

- **Open:** correction or disposition is outstanding.
- **In progress:** work exists on the named branch or draft pull request.
- **Validation:** implementation exists but required evidence is incomplete.
- **Closed:** correction and required evidence are accepted.
- **Deferred:** explicitly accepted for a later release with rationale.

## Finding-count reconciliation

| Source | Stable findings | Result |
| --- | ---: | --- |
| Deep technical review | 48 | All retained |
| Controller/hardware verification | +1 | `HW-013` accepted |
| RTSS/security verification | +1 | `RTSS-009` accepted |
| Lifecycle/Autopilot verification | +0 | Consequential paths folded into existing roots |
| Active ledger | 50 | 48 original plus 2 new |

No separate identifiers are assigned to consequential paths already explained
by a root finding.

Across the three verification batches, 24 existing findings were independently
reverified. Twenty-three were Confirmed. `RTSS-008` remained Medium / Likely
because compatibility depends on the supported RTSS version and
fractional-limit mechanism. The batches also accepted `HW-013` as High /
Confirmed and `RTSS-009` as Low / Confirmed. `GUI-003` was upgraded to Medium /
Confirmed for its static design root cause while retaining its
environment-dependent runtime qualification.

## Accepted verification refinements

- `CTRL-002`: `get_fps_for_active_window()` returns `(None, None)` when no fresh
  matching RTSS sample exists. The previous `fps_mean` and `last_process_name`
  remain stale, while an unknown current identity does not veto controller
  evaluation.
- `HW-011`: PDH reinitialization is triggered by monitoring start and fresh
  RTSS-reported process-identity changes, not necessarily every raw Windows
  foreground-window change.
- `HW-012`: the permanent worker return specifically occurs when
  `usage_by_luid` is empty, normally following an empty usable handle map.
  Invalid formatted reads generally retain a LUID with a zero value; they do
  not directly take that exact return path. Other failures can still leave
  stale state exposed.
- `RTSS-001`: missing numerator or denominator keys deterministically fail after
  a successful read; the original wording understated this.
- `RTSS-003`: a missing application profile is created from loaded Global state,
  not as a numerator-only profile; the requested denominator still may not be
  applied.
- `RTSS-004`: retain Confirmed status, with the active loaded-profile caller
  inventory narrowed by the verification.
- `RTSS-008`: retain Likely; both the API denominator property and direct
  `Limit=`/profile-file behavior require a supported-version decision.
- `SEC-002`: bare `..` alone does not escape because of the appended suffix;
  parent-plus-target, rooted, UNC, mixed-separator, ADS, and reparse cases remain
  within the validated security finding.
- `THR-001`: explicitly covers duplicate monitoring and plotting generations.
- `THR-003`: normal stop/start clears controller confirmation arrays but not
  legacy percentiles; in-session transitions can immediately use mixed evidence.
- `THR-004`: includes tray helpers and the plotting update reachable after
  cancellation but before the loop condition is checked again.
- `GUI-002`: the idle flag is global, while the saved prior cap is local to a
  monitoring loop and can be reused against another profile.
- `GUI-003`: **Medium / Confirmed** for the inconsistent, unnormalized, and
  case-sensitive identity design. Runtime manifestations remain dependent on
  Windows, RTSS, and Lossless Scaling behavior.
- `GUI-004`: the undeclared `GetTickCount64` return failure is cyclic at the low
  32-bit sign bit and distinct from the 32-bit input-tick epoch mismatch.
- `GUI-005`: missing argument prototypes are included; not every affected return
  type is pointer-sized.

## RTSS Stage 1 independent-review findings

RTSS Stage 1 is limited to deterministic contracts and tests. The corrections
below were published in draft pull request #3 at
`42a4485c6d6b078d442e57061e745a2ea43e3d89`
(`test: add deterministic RTSS transaction contracts`). Two independent
read-only reviews were completed, and the final independent review found no
remaining Stage 1 blockers or regressions. This verification does not close the
production RTSS findings in the active ledger.

### `S1-FINAL-001` - corrected and independently verified

- **Original severity:** Blocking.
- **Original root cause:** Application-profile equality and hashing retained
  display spelling, so case-only variants of the same canonical
  case-insensitive RTSS identity could compare or hash differently across
  generations, requests, captures, readbacks, sets, and dictionaries.
- **Implemented correction:** Equality and hashing now use the canonical
  case-insensitive profile key. Display spelling remains diagnostic metadata
  and is not ownership identity.
- **Regression tests:** Case-only equality and hash equality; set and
  dictionary collision behavior; generation equality; and request, capture,
  and readback matching across case variants.
- **Independent-review result:** Corrected and independently verified; the
  final review found no blocker or regression.
- **Commit:** `42a4485c6d6b078d442e57061e745a2ea43e3d89`.

### `S1-FINAL-002` - corrected and independently verified

- **Original severity:** Blocking.
- **Original root cause:** A request could mutate limiter-flag bits without
  proving exact captured prior ownership, and a non-verified rollback could
  omit owned bits whose restoration remained unresolved.
- **Implemented correction:** Flag mutation requires complete captured prior
  ownership. Non-verified rollback outcomes must account for every unresolved
  owned bit through an exact `unrestored_flag_mask`, while unowned and
  unrequested bits remain outside ownership reporting.
- **Regression tests:** Complete captured flag ownership; owned and unowned
  readback bits; requested subsets; partial and unresolved rollback masks;
  missing backend epoch; cap-only operations; and the exhaustive apply/rollback
  outcome matrix.
- **Independent-review result:** Corrected and independently verified; the
  final review found no blocker or regression.
- **Commit:** `42a4485c6d6b078d442e57061e745a2ea43e3d89`.

### `S1-FINAL-003` - corrected and independently verified

- **Original severity:** Blocking.
- **Original root cause:** Ordinary `FAILED` could ambiguously describe a
  post-mutation or changed-state result, and restore results did not form a
  closed, non-recursive state machine that separated exact restoration from
  unresolved post-mutation state.
- **Implemented correction:** Ordinary apply `FAILED` is restricted to
  pre-mutation failure or exact verified no-change. Exact restoration uses
  `VERIFIED`; unresolved post-mutation restoration uses an explicit unresolved
  disposition; and apply and restore outcomes and failure steps are closed and
  exhaustively validated.
- **Regression tests:** Pre-capture state-free failure; exact no-change proof;
  mismatched readback rejection; degraded rollback graphs; non-recursive
  restore phases; exact restoration classification; and exhaustive apply,
  restore, outcome, and failure-step matrices.
- **Independent-review result:** Corrected and independently verified; the
  final review found no blocker or regression.
- **Commit:** `42a4485c6d6b078d442e57061e745a2ea43e3d89`.

### `S1-FINAL-004` - corrected and independently verified

- **Original severity:** Blocking.
- **Original root cause:** Document and revision evidence could be absent or
  ambiguous while a result still attempted to claim exact restoration.
- **Implemented correction:** Document and revision evidence now carry explicit
  availability states. Document verification requires immutable complete bytes
  or an approved immutable SHA-256 digest, and revision evidence must exactly
  match when it is part of captured ownership.
- **Regression tests:** Matching and mismatching document bytes and SHA-256
  digests; matching and mismatching revision evidence; cap-only restoration;
  unsupported and read-failed evidence; and verified absence.
- **Independent-review result:** Corrected and independently verified; the
  final review found no blocker or regression.
- **Commit:** `42a4485c6d6b078d442e57061e745a2ea43e3d89`.

### `S1-FINAL-002-R1` - corrected and independently verified

- **Original severity:** Blocking follow-up.
- **Original root cause:** Cross-object apply invariants could admit mismatched
  capture identity or generations, success mixed with rollback or failure
  details, or `FAILED_ROLLED_BACK` without a verified exact matching restore.
- **Implemented correction:** Apply results now enforce request, capture,
  readback, generation, rollback, failure-detail, and outcome consistency.
  Verified apply excludes rollback and failure state, while
  `FAILED_ROLLED_BACK` requires a verified matching restore.
- **Regression tests:** Mismatched capture identity and generations; forbidden
  rollback or failure details on verified apply; verified matching rollback;
  required failure details; and state-free pre-capture failure.
- **Independent-review result:** Corrected and independently verified; the
  final review found no blocker or regression.
- **Commit:** `42a4485c6d6b078d442e57061e745a2ea43e3d89`.

### `S1-FINAL-003-R1` - corrected and independently verified

- **Original severity:** Blocking follow-up.
- **Original root cause:** Capture/readback presence combinations could be
  internally impossible, verified absence could be conflated with failed
  evidence acquisition, and conflict, created-profile deletion, or ambiguous
  mutation intent was not fully constrained.
- **Implemented correction:** Capture and readback models reject impossible
  presence combinations, distinguish verified absence from unavailable or
  failed evidence, enforce conflict and created-profile restoration rules, and
  reject unresolved or ambiguous mutation intent.
- **Regression tests:** Impossible captured presence states; absence versus
  failure; external-edit conflicts; created-profile deletion; and unresolved or
  ambiguous mutation requests.
- **Independent-review result:** Corrected and independently verified; the
  final review found no blocker or regression.
- **Commit:** `42a4485c6d6b078d442e57061e745a2ea43e3d89`.

The following final-review items remain explicitly deferred and non-blocking:

- `S1-FINAL-005` - deferred; no Stage 1 contract or regression blocker.
- `S1-FINAL-006` - deferred; no Stage 1 contract or regression blocker.
- `S1-FINAL-007` - deferred; no Stage 1 contract or regression blocker.

No physical RTSS, profile-file, Windows runtime, RX 7900 XTX, Lossless Scaling,
LibreHardwareMonitor, PDH, GUI, or lifecycle integration testing was performed
for Stage 1.

## Draft PR #3 independent review

Draft pull request #3 was independently reviewed in full at published head
`afd43e0373001a9f471573bbfb3535ae0b3c1ac3`. The review reran all 95
deterministic tests, confirmed that production RTSS callers remained unchanged,
and found no code or RTSS-safety merge blocker. GitHub reported no automated
checks. The review recommendation was to approve after the documentation-only
correction recorded below.

These supplemental Stage 1 review findings preserve the existing 50-item active
ledger and its identifiers; they are not duplicate ledger entries.

### `S1-DOC-001` - Medium / Confirmed / corrected and published

- **Location:** `CURRENT_STATUS.md` and `IMPLEMENTATION_PLAN.md`.
- **Problem:** Tracked documentation continued to describe the pre-publication
  state after the Stage 1 branch had been pushed and draft PR #3 had been
  created.
- **Effect:** A future session could repeat publication work, use the wrong
  branch head, or apply the wrong phase gate.
- **Original disposition:** Fix before merge through a documentation-only
  correction.
- **Correction:** Commit
  `e002045a0285a03706b5560969b8a9f1c9ac8b31`
  (`docs: record RTSS Stage 1 publication review`) corrected the original
  pre-publication inconsistency.
- **Verification and publication:** `e002045` passed independent read-only
  review and was pushed successfully to the existing Stage 1 branch and draft
  PR #3.
- **Final merge-gate maintenance:** Publication exposed self-referential
  transition wording in the correction. The present follow-up replaces it with
  a dated pre-merge snapshot and explicit post-creation and post-publication
  verification requirements. This is documentation maintenance, not a
  production defect. The commit containing this follow-up must be verified
  through Git after creation and through GitHub after any approved publication.

### `S1-READBACK-001` - Low / Confirmed / deferred

- **Location:** `RtssReadback.__post_init__`.
- **Problem:** The readback contract accepts mutation-only outcomes and failure
  steps, including rollback states, without a read-only outcome/step allowlist.
- **Effect:** A future adapter could construct a semantically impossible
  read-only result.
- **Current reachability:** No production caller uses the Stage 1 contracts.
- **Required correction:** Restrict `RtssReadback` to an explicit set of valid
  read-only outcomes and failure steps.
- **Disposition:** Deferred Stage 2 prerequisite before production adapters rely
  on the contract.

### `S1-TEST-001` - Low / Confirmed / deferred

- **Location:** Readback contract tests.
- **Problem:** The deterministic suite has no exhaustive readback
  outcome/failure-step matrix.
- **Required correction:** Add an exhaustive readback outcome/failure-step
  matrix and retain fail-closed coverage when outcomes or steps change.
- **Disposition:** Deferred with `S1-READBACK-001` before production
  integration.

### `S1-DESIGN-001` - Low / Improvement / deferred

- **Location:** Application-profile-name validation and derived profile
  filename construction.
- **Problem:** The Stage 1 identity contract has no explicit component-length
  boundary for the DLL name or derived profile filename.
- **Required correction:** Define capability-driven application and profile
  component-length limits before filesystem integration.
- **Disposition:** Deferred to the Stage 2 capability and supported-name
  policy.

## RTSS Stage 2 planning-review findings

These supplemental findings record the independent read-only review of local
planning commit `7adfb5406b091ccd8c55872fc1b75036029fee8a`. They do not alter,
renumber, close, or replace any entry in the original 50-item active technical
review ledger.

A second independent, read-only review assessed correction commit
`15a3774eb0ff10741e6684bf3414b4fdde61ae72`. Its overall recommendation was
**Not approved; further correction required**. It independently verified
`S2-NAME-001`, `S1-PROVENANCE-001`, `S2-STATUS-001`, and `S2-DECISION-001` as
corrected, while finding `S2-DEGRADED-001`, `S2-SEQUENCE-001`, and
`S2-INVENTORY-001` only partially corrected. The latter three dispositions
below record the further correction and remain pending another independent
verification.

### `S2-DEGRADED-001` - High / Confirmed / corrected pending another independent verification

- **Location:** Stage 1 restoration-result contracts and the Stage 2
  degraded-state, rollback, restoration, and ownership plan.
- **Problem:** The current Stage 1 schema explicitly accounts for unresolved
  owned limiter bits but does not unambiguously represent every other unresolved
  owned field.
- **Required correction:** Stage 2 must unconditionally define an immutable
  degraded-state representation covering, where owned or applicable, exact
  stored numerator and denominator, effective rational cap, profile existence
  or deletion state, complete profile-document evidence, revision evidence,
  limiter-flag bits, save uncertainty, update/activation uncertainty, backend
  generation or epoch, ownership retained after failure, unavailable or
  unreadable evidence, and conflicts caused by external edits.
- **Required distinctions:** Exact verified restoration, partial restoration,
  unresolved post-mutation state, external-edit conflict, unavailable evidence,
  read failure, retained ownership, and ownership transferred through an
  explicit degraded handoff must be distinct. Silent ownership release is
  invalid.
- **Gate:** The coordinator must not be implemented until this contract
  extension and its deterministic tests are defined. Persistence across a
  complete application-process restart may remain a later production-
  integration decision, but deterministic Stage 2 ownership and degraded
  classification are mandatory.
- **Second independent-review result:** Partially corrected. The first
  correction covered unresolved owned fields but did not bind every degraded
  result and handoff explicitly to complete immutable profile identity,
  request/transaction identity, requested/captured/readback generation
  evidence, backend epoch, and capability snapshot.
- **Further correction:** The plan now requires canonical identity, profile
  kind, diagnostic spelling where retained, exact requested, captured, and
  readback/restoration identities, the Stage 1 application, session, profile,
  and `source_generation` dimensions for each applicable evidence snapshot,
  immutable transaction identity, backend epoch, and capability-generation or
  snapshot identity. A handoff must also preserve every unresolved field and
  failed/unavailable evidence state, current holder, defined recipient,
  explicit responsibility-transfer status, and the reason normal release is
  impossible. Omitted, inconsistent, stale, ambiguous, or unavailable
  attribution evidence is rejected fail closed.
- **Ownership release correction:** Ownership remains retained unless exact
  restoration is verified against the same canonical identity and generations,
  or the defined recipient accepts a complete explicit handoff preserving all
  identity, generation, unresolved-state, and responsibility evidence.
- **Status:** Corrected pending another independent verification; not closed or
  independently verified.

### `S2-NAME-001` - Medium / Confirmed / corrected and independently verified

- **Location:** Canonical identity, capability, supported-name, encoding, and
  component-length planning.
- **Problem:** Encoding support must not become a permanent ASCII-only identity
  invariant.
- **Required correction:** Canonical identity must always reject lexically or
  path-unsafe names independently of capabilities. The policy must separately
  represent names unsupported by the selected backend and names permitted only
  when exact encoding and supported-name capabilities prove lossless handling.
- **Default policy:** Non-ASCII names remain rejected by default. Future Unicode
  acceptance requires explicit capability and policy evidence, exact lossless
  encoding, defined canonicalization behavior, and applicable encoded-byte and
  character limits. No Unicode support is claimed.
- **Second independent-review result:** Corrected and independently verified.

### `S2-SEQUENCE-001` - High / Confirmed / corrected pending another independent verification

- **Location:** Proposed Stage 2 implementation commits.
- **Problem:** A mutation-bearing intermediate commit was planned before
  complete rollback handling, while the following commit combined too many
  failure, restoration, conflict, cancellation, and ownership concerns.
- **Required correction:** Prerequisite contracts and matrices must precede
  policy and evidence contracts; admission, serialization, capture, and
  verified no-change must initially enable no mutation; rollback foundations
  and degraded classification must exist before mutation admission; every
  mutation slice must arrive with save, update, readback, rollback, and its
  complete applicable failure matrix; restoration/deletion and then
  conflict/cancellation/generation work must remain focused later units.
- **Gate:** No intermediate implementation commit may admit a mutation without
  complete rollback or degraded-state handling for every mutation it can
  perform. Production adapters remain separate.
- **Second independent-review result:** Partially corrected. Rollback and
  degraded prerequisites were moved before mutation, but the first
  mutation-bearing Stage 5 operation and its exclusions remained too broad to
  review independently.
- **Further correction:** Stage 5 now admits only an exact-cap change to an
  already existing application or Global profile through one already-admitted
  mechanism that supports complete exact capture, mutation, save,
  update/activation, readback, rollback, and restoration verification. It
  excludes missing-profile creation, deletion, Global-derived creation, flags,
  startup flag changes, production document replacement, conflict resolution
  beyond fail-closed detection, switching, ownership transfer, cross-process
  serialization, production callers, live adapters, unsupported fractional
  fallback, and mechanisms without exact readback and rollback evidence.
- **Reviewability correction:** Each mutation-bearing commit must include
  ordered recording, all applicable false/exception paths, rollback,
  degradation, ownership retention, and deterministic tests. Numerator and
  denominator handling, activation, or rollback must be split further when
  they cannot remain independently reviewable. Creation/deletion restoration,
  flags, additional mechanisms, switching, cancellation/generation
  transitions, and production adapters remain separate later slices.
- **Status:** Corrected pending another independent verification; not closed or
  independently verified.

### `S1-PROVENANCE-001` - Medium / Confirmed / corrected and independently verified

- **Location:** Treatment of `S1-FINAL-005`, `S1-FINAL-006`, and
  `S1-FINAL-007`.
- **Problem:** Durable tracked sources define these only as deferred identifiers
  and do not support a test-maintenance, provenance-cleanup, coordinator, or
  other technical allocation.
- **Required correction:** Their technical definitions require provenance
  recovery before disposition. They are not closed and are not treated as
  coordinator prerequisites unless recovered evidence proves that they are.
  Ignored local reports must not be required by a fresh clone.
- **Evidence rule:** Any recovered requirement must be added durably and receive
  appropriate regression coverage before technical allocation or closure. No
  content is inferred for these identifiers.
- **Second independent-review result:** Corrected and independently verified.

### `S2-STATUS-001` - Low / Confirmed / corrected and independently verified

- **Location:** `CURRENT_STATUS.md`.
- **Problem:** Self-referential wording described committed planning work as
  “the current planning task.”
- **Correction:** Use stable historical wording identifying the local Stage 2
  planning commit and its exact scope.
- **Second independent-review result:** Corrected and independently verified.

### `S2-INVENTORY-001` - Low / Confirmed / corrected pending another independent verification

- **Location:** Production inventory for
  `RTSSController.set_fractional_framerate`.
- **Problem:** The inventory described the denominator profile-file rewrite as
  optional.
- **First correction:** The method calculates a positive denominator, always
  attempts the direct denominator rewrite through `set_limit_denominator`, then
  writes the numerator through the RTSS property path.
- **Second independent-review result:** Partially corrected. The first
  correction correctly made the denominator file rewrite unconditional but
  described the method too broadly as having one eventual update, overlooking
  the non-default branch.
- **Further correction:** All identified active production callers use the
  default `update=False` path. It calls the denominator and numerator helpers
  with updates disabled and then performs one final `UpdateProfiles`. In the
  non-default `update=True` path, the denominator helper performs one update and
  the numerator property helper performs another, for two update activations.
  The denominator file rewrite remains unconditional in both paths; update
  count and timing differ. A later ordered-fake characterization test is
  planned for each branch.
- **Status:** Corrected pending another independent verification; not closed or
  independently verified.

### `S2-DECISION-001` - Medium / Improvement / corrected and independently verified

- **Location:** Stage 2 planning status and decision provenance.
- **Problem:** Accepted repository decisions, proposed Stage 2 design, and
  unresolved evidence-dependent decisions were not distinguished clearly
  enough.
- **Correction:** Stage 2-specific architecture and sequencing remain
  **Proposed Stage 2 design pending independent verification and explicit
  acceptance.** They become accepted only after the complete corrected plan is
  independently verified, the user explicitly accepts it, and accepted
  decisions are durably recorded before implementation where needed. Existing
  accepted decisions in `DECISIONS.md` remain unchanged.
- **Second independent-review result:** Corrected and independently verified.

## Active finding ledger

`Owner` names the responsible workstream, not an assigned individual.
`Automated tests` and `Manual evidence` identify required evidence. The initial
deterministic harness passes on `test/controller-and-adapter-harness`; physical
and integration evidence remains outstanding.

| Pri | ID | Severity / status | Active finding | Owner | Target branch / PR | Automated tests | Manual evidence | State |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P0 | CTRL-001 | High / Confirmed | Normal one-step cap decrease is unreachable | Controller | `test/controller-and-adapter-harness` -> `fix/controller-validity-and-delays` | Passing differential cap-selection characterization; defect preserved | RX 7900 XTX sustained overload trace | Open |
| P0 | CTRL-002 | High / Confirmed | Stale FPS and process identity can drive decisions | Controller | `fix/controller-validity-and-delays` | Fake clock/freshness | Menus, Alt-Tab, RTSS restart | Open |
| P1 | CTRL-003 | Medium / Confirmed | No settling period follows an RTSS cap change | Controller | `fix/controller-validity-and-delays` | Fake clock/controller | Cap timing and frametime trace | Open |
| P1 | CTRL-004 | Medium / Confirmed design gap | No explicit CPU-bound suppression policy | Controller | `fix/controller-validity-and-delays` | Controller sensor-role policy | CPU/GPU-bound LS traces | Open |
| P1 | CTRL-005 | Medium / Confirmed | Runtime configuration validation is incomplete | Controller/config | `test/controller-and-adapter-harness` -> `fix/controller-validity-and-delays` | Passing pure cap-ladder validator tests; validator unwired | Invalid-input Windows UI run | Open |
| P0 | CTRL-006 | High / Confirmed | LibreHM ignores configured decision delays | Controller | `fix/controller-validity-and-delays` | Fake clock/sensors | Brief versus sustained bursts | Open |
| P0 | HW-001 | High / Confirmed | LibreHM decisions are gated by legacy PDH | Backend isolation | `fix/backend-isolation-and-pdh` | Fake backend isolation | LHM valid with PDH zero/unavailable | Open |
| P1 | HW-002 | High / Confirmed | LHM selections use positional, ambiguous identities | LHM | `fix/lhm-identity-health` | Fake LHM identity | Multi-GPU identifier inventory | Open |
| P1 | HW-003 | High / Confirmed | LHM has no freshness, invalid-state, or recovery model | LHM | `fix/lhm-identity-health` | Fake clock/LHM recovery | Driver reset and sleep/resume | Open |
| P0 | HW-004 | High / Confirmed | PDH queries leak and reinitialization is unsynchronized | PDH | `fix/backend-isolation-and-pdh` | PDH handle lifecycle | Reinit and handle-count run | Open |
| P1 | HW-005 | Medium / Likely | PDH aggregation can select or measure the wrong GPU | PDH | `fix/backend-isolation-and-pdh` | Fake PDH identity/aggregation | LUID mapping with LS | Open |
| P1 | HW-006 | Medium / Confirmed | LHM runtime/asset selection is ineffective | LHM | `fix/lhm-identity-health` | Loader/runtime selection | Packaged runtime inspection | Open |
| P3 | HW-007 | Low / Confirmed | Sensor discovery leaves its LHM `Computer` open | LHM | `fix/lhm-identity-health` | LHM lifecycle | Repeated discovery resource run | Open |
| P3 | HW-008 | Low / Confirmed | Percentile upper boundary reads unsorted data | PDH/controller | `fix/backend-isolation-and-pdh` | Percentile boundary | Not required beyond Windows smoke | Open |
| P0 | HW-009 | High / Confirmed | Missing enabled LHM sensors do not veto an increase | LHM/controller | `fix/lhm-identity-health` | Sensor quorum | Disconnect/re-enumerate sensor | Open |
| P1 | HW-010 | Medium / Confirmed | LHM control reads are not an atomic snapshot | LHM | `fix/lhm-identity-health` | Snapshot consistency | Poll/load stress | Open |
| P0 | HW-011 | High / Confirmed | LibreHM mode has a hard PDH startup/reinit dependency | Backend isolation | `fix/backend-isolation-and-pdh` | Fake backend startup | LHM-only Windows start | Open |
| P1 | HW-012 | High / Confirmed | PDH worker can stop while leaving stale data valid | PDH | `fix/backend-isolation-and-pdh` | PDH health/freshness | Counter loss and driver reset | Open |
| P1 | HW-013 | High / Confirmed | Legacy mode has a hard LibreHardwareMonitor startup dependency | Backend isolation | `fix/backend-isolation-and-pdh` | Fake backend startup | Legacy-only Windows start without LHM | Open |
| P0 | RTSS-001 | High / Confirmed | Direct RTSS writer uses uninitialized flags | RTSS | `fix/rtss-transaction-and-restore` | Fake RTSS/parser | Disposable malformed profiles | Open |
| P0 | RTSS-002 | High / Confirmed | Previous RTSS caps are not captured or restored | RTSS | `fix/rtss-transaction-and-restore` | RTSS restoration | Exact profile/flag restoration matrix | Open |
| P0 | RTSS-003 | High / Confirmed | RTSS cap updates are partial, non-atomic, and unverified | RTSS | `fix/rtss-transaction-and-restore` | RTSS failure/readback | Versioned disposable profiles | Open |
| P0 | RTSS-004 | High / Confirmed | Loaded-profile transactions are not serialized | RTSS | `fix/rtss-transaction-and-restore` | Transaction interleavings | Concurrent profile exercise | Open |
| P1 | RTSS-005 | Medium / Confirmed | Controller state advances after failed RTSS writes | RTSS/controller | `fix/rtss-transaction-and-restore` | Write acknowledgment | Forced RTSS failure | Open |
| P3 | RTSS-006 | Low / Confirmed | RTSS profile APIs reject Unicode names | RTSS | `fix/rtss-transaction-and-restore` | Canonical identity validation | Supported-name matrix | Open |
| P0 | RTSS-007 | High / Confirmed | Startup unconditionally enables the global limiter | RTSS | `fix/rtss-transaction-and-restore` | Flag ownership/restoration | Open/close RTSS flag check | Open |
| P1 | RTSS-008 | Medium / Likely | Fractional denominator compatibility is not established | RTSS | `fix/rtss-transaction-and-restore` | Rational/capability tests | Supported RTSS matrix | Open |
| P3 | RTSS-009 | Low / Confirmed | Dormant `disable_limiter()` toggles instead of idempotently disabling | RTSS | `fix/rtss-transaction-and-restore` | Flag idempotence | Versioned flag smoke test | Open |
| P0 | THR-001 | High / Confirmed | Stop/start can create duplicate monitoring and plotting loops | Lifecycle | `fix/session-lifecycle` | Lifecycle barriers | Rapid start/stop stress | Open |
| P1 | THR-002 | Medium / Likely | Independent application threads call Dear PyGui concurrently | GUI/lifecycle | `fix/session-lifecycle` | GUI queue/generation | DPG stress and shutdown | Open |
| P1 | THR-003 | Medium / Confirmed | Legacy sample windows persist between sessions | Lifecycle/sensors | `fix/session-lifecycle` | Session warm-up/reset | Cross-profile/backend transitions | Open |
| P1 | THR-004 | Medium / Confirmed | Exit does not join all workers before destroying DPG | Lifecycle | `fix/session-lifecycle` | Ordered shutdown | Repeated Windows exit stress | Open |
| P0 | THR-005 | High / Confirmed | Autopilot self-stop can be followed by another cap write | Lifecycle | `fix/session-lifecycle` | No post-cancel write | Autopilot self-stop trace | Open |
| P0 | GUI-001 | High / Confirmed | Autopilot retains the previous profile cap model | Profiles/Autopilot | `fix/profile-autopilot-idle` | Transactional profile switch | Game A -> B trace | Open |
| P1 | GUI-002 | High / Confirmed | Idle state and prior active cap are shared across profiles | Profiles/idle | `fix/profile-autopilot-idle` | Per-generation idle | Idle A -> B -> input | Open |
| P1 | GUI-003 | Medium / Confirmed design; runtime-dependent effects | Autopilot process identity is inconsistent, unnormalized, and case-sensitive | Profiles/Autopilot | `fix/profile-autopilot-idle` | Canonical identity | Game/LS/desktop identity matrix | Open |
| P1 | GUI-004 | Medium / Confirmed | Idle calculation fails on long-uptime systems | Win32/idle | `fix/profile-autopilot-idle` | Tick-wrap arithmetic | Long-uptime Windows simulation/smoke | Open |
| P1 | GUI-005 | Medium / Confirmed | Required Win32 return and argument types are undeclared | Win32 | `fix/profile-autopilot-idle` | Win32 ABI tests | 64-bit handle/process run | Open |
| P3 | GUI-006 | Low / Confirmed | Quick Load can fail before Quick Save | Profiles/GUI | `fix/profile-autopilot-idle` | Config defaults | First-run Quick Load | Open |
| P1 | SEC-001 | High / Possible | Elevated process trusts a potentially writable application tree | Security/packaging | `hardening/config-packaging-logging` | Install-integrity policy | ACL/install-layout audit | Open |
| P0 | SEC-002 | High / Confirmed | Profile traversal enables privileged file rewrite | RTSS/security | `fix/rtss-transaction-and-restore` | Profile/path matrix | Elevated containment harness | Open |
| P2 | SEC-003 | Medium / Possible | Autostart uses elevated shell command strings | Security | `hardening/config-packaging-logging` | Argument construction | Task Scheduler smoke | Open |
| P2 | SEC-004 | Medium / Informational | Release and dependency integrity are not enforced | Packaging | `hardening/config-packaging-logging` | Manifest/build checks | Release artifact audit | Open |
| P2 | SEC-005 | Medium / Confirmed | First launch recursively strips Mark of the Web | Security | `hardening/config-packaging-logging` | Pre-launch policy | Downloaded artifact audit | Open |
| P1 | TEST-001 | High / Confirmed | No automated test suite or CI exists | QA | `test/controller-and-adapter-harness` | Standard-library discovery and import-isolation suite passes; CI absent | Not applicable | In progress |
| P1 | TEST-002 | High / Confirmed | Controller logic lacks deterministic seams | QA/controller | `test/controller-and-adapter-harness` | Initial fake clock, FPS/process, sensor, RTSS, and generation contracts pass | Not applicable | In progress |
| P1 | MAINT-001 | Medium / Confirmed | Errors and worker failures are obscured | Diagnostics | `hardening/config-packaging-logging` | Error/worker reporting | No-console failure capture | Open |
| P3 | MAINT-002 | Low / Confirmed | `backup_snippets.py` is syntactically invalid | Maintenance | `docs/rx7900xtx-acceptance` | AST/packaging inventory | Not applicable | Open |
| P3 | MAINT-003 | Low / Informational | Documentation, versions, and dependency declarations diverge | Documentation | `docs/rx7900xtx-acceptance` | Documentation/version check | Release review | Open |
| P2 | MAINT-004 | Medium / Confirmed | Configuration rewrites are non-atomic | Config | `hardening/config-packaging-logging` | Atomic persistence/recovery | Interrupted-write run | Open |

### Notes on new identifiers

- `HW-013` - **High / Confirmed / Open**. Legacy mode has a hard
  LibreHardwareMonitor startup dependency. Verification provenance:
  `01_controller_hardware_p0_verification.md` (local ignored input). Target:
  backend isolation and LHM lifecycle.
- `RTSS-009` - **Low / Confirmed / Open**. The dormant
  `disable_limiter()` helper toggles flag bit 4 rather than idempotently
  disabling it. It has **no active caller at the reviewed commit**.
  Verification provenance: `02_rtss_security_p0_verification.md` (local ignored
  input). Target: RTSS transaction and flag ownership.

### Priority triage decisions

Priority is a project sequencing decision separate from severity and
confirmation status.

- `HW-013` is assigned P1 because selected-backend isolation must be corrected
  before unattended use, but it is scheduled in the backend-isolation phase
  after the test, RTSS, lifecycle, controller, and LHM foundations.
- `RTSS-009` is assigned P3 because the helper is dormant and has no active
  caller at the reviewed commit. It remains included in
  `fix/rtss-transaction-and-restore` so it cannot later be reused as an
  idempotent disable or restoration operation.

## Pending decisions

- Supported RTSS versions.
- Fractional denominator API versus profile-file fallback.
- Stop policy when a session-owned profile was externally edited.
- Exact LHM version and runtime.
- Required control-sensor roles and quorum.
- CPU-bound policy while preserving thermal and power safety actions.
- Physical settle and confirmation-delay values.

`DECISIONS.md` records the evidence and phase needed for each decision.

## Physical validation requirements

Every physical run must record Windows, Adrenalin, RTSS, LHM/runtime, game,
display, and Lossless Scaling versions/settings, plus:

- controller and lifecycle generation trace;
- RTSS profile/flags before, requested, read back, restored, and after;
- LHM hardware/sensor identifier dump with type, name, value, freshness, and
  health;
- PDH full-LUID mapping and selected engine instances;
- FPS/frametime capture and cap-write timestamps;
- worker/thread/handle counts where lifecycle or resource ownership is tested.

Required scenarios include native rendering and LSFG; menus/loading/Alt-Tab;
game A -> game B -> desktop; missing/stale sensors; iGPU enabled/disabled;
driver reset; RTSS/LS restart; sleep/resume; long uptime; repeated start/stop;
normal exit; and handled apply/restoration failures.
