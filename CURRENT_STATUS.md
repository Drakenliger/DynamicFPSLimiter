# Current Status

## Repository

- Fork: `Drakenliger/DynamicFPSLimiter`
- Upstream reference: `SameSalamander5710/DynamicFPSLimiter`
- Default branch: `main`
- Current local branch: `feature/rtss-transaction-coordinator`
- Current phase: RTSS Stage 2 sequence item 1 deterministic contracts are
  independently approved and complete; sequence-item-2 deterministic planning
  at `c3047fc37248392b74255f36844120fc0f6fef82` is independently approved,
  explicitly accepted in this documentation-only step, and complete; no
  sequence-item-2 source implementation exists
- Independently approved and explicitly accepted sequence-item-2 planning
  source commit:
  `c3047fc37248392b74255f36844120fc0f6fef82`
  (`docs: resolve RTSS applicability planning conflicts`)
- Rejected fourth correction and reviewed parent:
  `b59187343ce775013dfcdbaf899a819cc53409cf`
  (`docs: close RTSS applicability contract gaps`)
- Current approved sequence-item-1 source commit:
  `4011d7e1e29fc2a4bbe901d184c53774b33e7baa`
  (`fix: anchor RTSS evidence generations`)
- Review baseline: `5f89c49a9e18612b4645bb46a3b6a6e875612e04`
- Stage 1 squash merge:
  `f8c4d4a2f7c6e1db39f3fd3c037ed98e07c39c95`
  (`Add deterministic RTSS transaction contracts (#3)`)
- Stage 2 planning baseline:
  `7adfb5406b091ccd8c55872fc1b75036029fee8a`
  (`docs: begin RTSS Stage 2 planning`)
- First Stage 2 planning correction:
  `15a3774eb0ff10741e6684bf3414b4fdde61ae72`
  (`docs: address RTSS Stage 2 planning review`)
- Final Stage 2 planning correction:
  `677b6b5750ac52953fd1581efbc658adbc171b22`
  (`docs: complete RTSS Stage 2 planning corrections`)
- Stage 2 acceptance record:
  `d10feead8a3707ee52a54f80e4e53c14945309d0`
  (`docs: accept RTSS Stage 2 coordinator design`)

## Verified Stage 1 merge state

On 25 July 2026, the repository and fork were independently checked before
this planning branch was created:

- local `main`, `origin/main`, and the initial `HEAD` all resolved to
  `f8c4d4a2f7c6e1db39f3fd3c037ed98e07c39c95`;
- local `main` was zero commits ahead of and zero commits behind
  `origin/main`;
- pull request #3 in `Drakenliger/DynamicFPSLimiter` was merged into `main`;
- GitHub reported the PR #3 merge commit as
  `f8c4d4a2f7c6e1db39f3fd3c037ed98e07c39c95`;
- the repository was clean and the index was empty;
- no local or `origin` branch named
  `feature/rtss-transaction-coordinator` existed; and
- the existing Stage 1 branch `fix/rtss-transaction-and-restore` was not
  switched to, reused, reset, deleted, or modified.

Only `origin` was fetched and queried. The upstream repository was not
contacted.

The deterministic command
`python -m unittest discover -s tests -t . -v`, with
`PYTHONDONTWRITEBYTECODE=1`, passed all 95 tests before this planning branch was
created. The repository remained clean and contained no `__pycache__`, `.pyc`,
or `.pyo` artifacts.

## Independent Stage 2 planning review

The local planning commit
`7adfb5406b091ccd8c55872fc1b75036029fee8a` changed exactly:

- `CURRENT_STATUS.md`;
- `IMPLEMENTATION_PLAN.md`; and
- `TEST_PLAN.md`.

An independent read-only review of that commit completed on 25 July 2026. Its
result was **Approved after specified documentation corrections**. During the
review, all 95 deterministic tests passed, the worktree and index remained
clean, and no cache or bytecode artifacts were produced.

The review confirmed that no Stage 2 source implementation exists, no
production caller uses the Stage 1 contracts, and no remote Stage 2 branch,
configured branch upstream, push, or pull request exists.

The accepted correction-required blockers are:

- `S2-DEGRADED-001`;
- `S2-NAME-001`;
- `S2-SEQUENCE-001`; and
- `S1-PROVENANCE-001`.

The smaller required corrections are:

- `S2-STATUS-001`;
- `S2-INVENTORY-001`; and
- `S2-DECISION-001`.

Correction commit `15a3774eb0ff10741e6684bf3414b4fdde61ae72` addressed those
findings; its second independent-review disposition is recorded below.

## Second independent Stage 2 correction review

The first documentation correction,
`15a3774eb0ff10741e6684bf3414b4fdde61ae72`, received a second independent,
read-only review on 25 July 2026. The review recommendation was **Not approved;
further correction required**. All 95 deterministic tests passed during that
review.

The second review found these findings fully corrected:

- `S2-NAME-001`;
- `S1-PROVENANCE-001`;
- `S2-STATUS-001`; and
- `S2-DECISION-001`.

It found these findings only partially corrected:

- `S2-DEGRADED-001`, because degraded results and handoffs did not yet bind all
  identity and generation evidence explicitly;
- `S2-SEQUENCE-001`, because the first mutation-bearing Stage 5 slice was not
  concretely bounded; and
- `S2-INVENTORY-001`, because the non-default `update=True` path and its two
  update activations were not recorded.

At that point, the subsequent documentation correction addressed those three
remaining planning items but still required another independent, read-only
review and explicit acceptance. Stage 2 implementation remained blocked. No
Stage 2 source implementation, production integration, remote branch,
configured branch upstream, or pull request existed.

## Final Stage 2 correction review and acceptance

Final planning correction
`677b6b5750ac52953fd1581efbc658adbc171b22` received an independent, strictly
read-only review on 25 July 2026. The result was **Approved for explicit user
acceptance**. The review found `S2-DEGRADED-001`, `S2-SEQUENCE-001`, and
`S2-INVENTORY-001` fully corrected and found no regression in `S2-NAME-001`,
`S1-PROVENANCE-001`, `S2-STATUS-001`, or `S2-DECISION-001`.

The review confirmed the original active ledger still contained exactly 50
unchanged, uniquely ordered findings. Both planning diffs were whitespace-clean,
all 95 deterministic tests passed, the worktree and index remained clean, and
no cache or bytecode artifacts were present. The branch had no configured
upstream, remote Stage 2 branch, or pull request; only the fork origin was
queried and the configured upstream repository was not contacted.

The user explicitly accepted the corrected RTSS Stage 2
transaction-coordinator plan at `677b6b5750ac52953fd1581efbc658adbc171b22` on
25 July 2026. Accepted Stage 2 architectural decisions are recorded in
`DECISIONS.md`. This acceptance does not authorize implementation, push,
pull-request creation, production integration, or live RTSS/hardware
interaction.

## RTSS Stage 2 sequence item 1 implementation

The accepted prerequisite contract correction was implemented locally after
the planning-review and explicit-acceptance gates completed at
`d10feead8a3707ee52a54f80e4e53c14945309d0`.

The focused deterministic change:

- restricts `RtssReadback` through explicit closed read-only outcome,
  failure-step, and outcome/step allowlists;
- preserves exact stored numerator and denominator evidence independently of
  reduced mathematical `RationalCap` equality;
- requires representation-exact restoration when exact stored evidence is
  owned;
- adds immutable complete degraded-field accounting, typed transaction and
  ownership attribution, save and activation uncertainty, retained ownership,
  explicit degraded handoff, and proof-gated ownership release; and
- adds exhaustive readback and apply matrices plus exact-representation,
  degraded-state, identity, generation, ownership, and handoff regressions.

The deterministic suite passes all 122 tests with
`PYTHONDONTWRITEBYTECODE=1`. No coordinator, transaction admission, capture
execution, mutation, rollback execution, production integration, live adapter,
dependency, or external-system behavior was added.

Independent read-only review of implementation commit
`c83aa281d961222eeeb70dbb994c4f33aef46381` did not approve the implementation.
It confirmed three blocking findings and two non-blocking findings:

- `S2-OWNERSHIP-IMPL-001`: exact restoration was not bound to the releasing
  transaction owner and used a separately copied capability-generation marker;
- `S2-DEGRADED-IMPL-001`: requested failed or unsupported exact stored fields
  could disappear from applicability and degraded accounting;
- `S2-DEGRADED-IMPL-002`: generic caller-authored unresolved, classification,
  operation, and backend claims were not proven by concrete evidence;
- `S2-EVIDENCE-IMPL-001`: exact-field read failures lacked required typed,
  field-specific diagnostics; and
- `S1-READBACK-ALIAS-001`: enum iteration alone did not guard exhaustive
  matrices against aliases.

A focused local correction binds ownership to exact captured state and
immutable transaction/capability evidence, requires a transaction-bound exact
restoration proof, keeps requested exact-pair responsibilities applicable
through failed, unsupported, and asymmetric evidence, derives degraded
accounting and classification from concrete observations, adds typed
field-specific read-failure diagnostics, and enforces/tests enum uniqueness
through `Enum.__members__`.

Independent read-only review of corrective commit
`c323ddeb5cd62636a608d312af873a1552142f67` did not approve the
implementation. It found that a failed or unsupported readback could still
carry a complete available exact pair (`S2-DEGRADED-IMPL-002-A`) and that
readback, operation, conflict, capability, and backend-epoch evidence remained
reusable or caller-authored without complete transaction provenance
(`S2-DEGRADED-IMPL-002-B`). It also found that the documentation overstated
the resulting protection (`DOC-S2-DEGRADED-COVERAGE-001`).

A second focused local correction rejects complete available exact pairs on
non-verified readback, requires transaction-bound readback evidence for
degraded construction, makes operation and conflict evidence factory-only and
owner-bound, derives conflict values and backend/capability epochs from bound
observations, and derives degraded classification and accounting. Structural
ownership-token equality is documented and tested without implementing
single-consumption coordinator behavior.

Independent read-only review of second corrective commit
`ee9d0c7526861aeb999e1b410b3d2b21b71a6c23` did not approve the
implementation. It confirmed `S2-DEGRADED-IMPL-002-A` corrected, but found
`S2-DEGRADED-IMPL-002-B` still open because mutually consistent caller-created
future backend and capability generations could be bound and then trusted by
operation, conflict, and degraded-state evidence. It also found
`DOC-S2-DEGRADED-COVERAGE-001` not corrected accurately.

A third focused local correction fails closed by requiring bound readback
backend generation and capability evidence to equal the ownership token's
captured evidence. No trusted advanced-generation observation mechanism is
introduced. Regressions cover direct construction, nested
`dataclasses.replace()` substitution, operation and conflict factories,
degraded latest-generation derivation, structural token copies, and valid
current-generation controls.

The complete deterministic suite passes all 181 tests with
`PYTHONDONTWRITEBYTECODE=1`. The third correction remains contract/test-only:
no coordinator, mutation, production integration, capability/name policy, or
live system behavior was added. It has not been pushed and has no pull request.
Display and Frame Generation Awareness remains future planning only and is not
implemented by this correction.

## RTSS Stage 2 sequence item 1 independent approval

Independent read-only review of approved source commit
`4011d7e1e29fc2a4bbe901d184c53774b33e7baa` ended **Approved with
non-blocking review findings**. The review found no remaining blocking
correctness, provenance, scope, documentation, or repository-integrity issue.
It independently confirmed:

- `S2-DEGRADED-IMPL-002-A` remained corrected;
- `S2-DEGRADED-IMPL-002-B` was corrected for the defined ownership trust
  boundary;
- `DOC-S2-DEGRADED-COVERAGE-001` was corrected accurately;
- `S2-OWNERSHIP-TOKEN-SEMANTICS-001` remains correctly deferred and
  non-blocking because single-use token consumption and duplicate-release
  prevention belong to a future coordinator registry;
- all 181 deterministic tests passed;
- the original production finding ledger remained exactly 50 rows with 50
  unique identifiers in its original order, with all nine production RTSS
  findings still Open; and
- the work remained within sequence item 1, local, clean, and unpublished,
  without sequence-item-2 or later operational behavior.

The review recorded two non-blocking findings:

- `TEST-S2-PREFIX-COUNT-001` corrects a historical implementation-session
  statement: replaying the targeted 35-test prefix against the parent produced
  9 failures, not 8. Eight new rejection tests and one modified existing
  latest-epoch test failed. This affects historical test-count accuracy only.
- `TEST-S2-DOWNSTREAM-PATH-001` observes that several operation, conflict, and
  degraded-state rejection tests combine readback binding and downstream
  construction in one `assertRaises` block. Binding rejects first, so the
  downstream constructor does not execute. The tests still prove that forged
  evidence cannot reach those public downstream paths, and the factory-only
  API cannot construct a separately invalid already-bound evidence object.

Neither finding requires a source or test correction now, and neither reopens
sequence item 1. RTSS Stage 2 sequence item 1 is complete and independently
approved as deterministic contract work only.

## RTSS Stage 2 sequence item 2 planning and design

The documentation-only sequence-item-2 planning session began from clean local
HEAD `fed6a33c79d7575c33ac5b4f1585fa536880896f`
(`docs: accept RTSS Stage 2 sequence item 1`) on
`feature/rtss-transaction-coordinator`. That starting commit had parent
`4011d7e1e29fc2a4bbe901d184c53774b33e7baa`, tree
`0cdb6411a5aa3ade33e7fed20f92ffc780ed251f`, and stable patch ID
`d1c2ee3590d606adfaf58b7383a360b15a388516`. Local `main` and the locally
recorded `origin/main` were both
`f8c4d4a2f7c6e1db39f3fd3c037ed98e07c39c95`; the branch was nine commits ahead,
zero behind, clean, unpublished, and had no configured upstream or
remote-tracking branch containing HEAD. No remote was contacted.
No push or Stage 2 pull request exists.

The first focused planning commit,
`fd7e3d8aeb57bf7b8cd8acb8bd51448673dc2f1d`
(`docs: plan RTSS capability and name policy`), received an independent,
read-only review. The exact verdict was **Not approved - blocking planning
findings require correction**. The review confirmed repository state, scope,
all 181 deterministic tests, the 50-row production ledger, sequence boundaries,
and the local unpublished state, but identified eight blocking planning
findings:

- `S2-CAP-PLAN-001`: no immutable evaluation context identified the expected
  observation and generations;
- `S2-CAP-PLAN-002`: evidence legality, terminal precedence, derived support,
  mixed dependencies, contradictions, and reason ordering were not closed;
- `S2-CAP-PLAN-003`: primitive operations, compound requirements, and verified
  postconditions were mixed;
- `S2-RANGE-PLAN-001`: exact range domains and intersection behavior were
  incomplete;
- `S2-NAME-PLAN-001`: policy could support a raw name that accepted item-1
  identity and ownership contracts cannot represent;
- `S2-NAME-PLAN-002`: structural safety, current identity-model constraints,
  capability rules, and deferred facts were not exhaustively separated;
- `S2-NAME-PLAN-003`: caller-supplied peer names could omit a collision and
  case/normalization outcomes were ambiguous; and
- `S2-TEST-PLAN-001`: the deterministic matrix did not cover those corrected
  semantics through non-self-confirming public paths.

The review also recorded non-blocking `S2-DOC-OPEN-001`: the detailed open
decision table and the shorter decision summary could diverge.

This focused local correction addresses those findings in the four planning
documents without amending or rewriting the rejected commit. It defines a
separate immutable matching context; a closed evidence and dependency algebra;
separate primitive, compound, and postcondition taxonomies; domain-specific
exact ranges; an exhaustive raw-name classification; the fail-closed current
canonical-identity boundary; and factory-controlled, generation-bound complete
namespace evidence. `IMPLEMENTATION_PLAN.md` is the authoritative detailed
open-decision table and `DECISIONS.md` now cross-references it.

The planning review and correction inspected the accepted item-1 contracts and
tests and record these central conclusions:

- existing `RtssCapabilityInfo` is a public range/Boolean description and
  existing `RtssCapabilityEvidence` is a public ownership provenance marker;
  neither is authoritative live mechanism support by itself;
- item-1 ownership, readback, operation, conflict, degraded-state, exact
  restoration, captured-generation, and structural-token boundaries remain
  unchanged;
- sequence item 2 will use a pure typed `SUPPORTED` / `UNSUPPORTED` /
  `UNKNOWN` policy over a factory-controlled admitted immutable capability
  observation;
- support is exact-mechanism, primitive-operation, exact-field, profile-kind,
  and generation specific; compound requirements are derived from acyclic
  primitive bundles, while verified postconditions remain distinct later
  runtime results;
- supported-name policy preserves the exact original name and admits no silent
  encoding, truncation, replacement, case change, normalization, collision, or
  mechanism fallback;
- no universal RTSS encoding, length, character, case, normalization, filename,
  or version rule is assumed from current Windows-oriented validation; and
- trusted live/current or advanced-generation observation remains a later
  coordinator/adaptor admission responsibility, not a caller-authored Boolean
  or generation.

The unresolved live evidence includes supported RTSS versions and exact APIs;
denominator mechanism; exact read/write/readback/restoration operation support;
creation, deletion, and verified absence; encoding and encoded representation;
component/total character and byte limits; invalid/reserved characters; case
and normalization behavior; executable-name versus full-path identity;
backend restart/re-enumeration; external edits/cross-process conflict evidence;
and durable degraded ownership after application restart. Each unresolved item
has a typed fail-closed interim rule and later owner in
`IMPLEMENTATION_PLAN.md`. These questions do not block implementing the pure
item-2 contracts after another independent review and explicit acceptance. A
name outside the current canonical identity model can be inspected but can
never return `SUPPORTED`; support requires a separately planned, reviewed, and
accepted identity-model migration. Deferred live facts continue to block
affected later mutation admission or production support.

The planned implementation is divided into small future units for capability
enums/evidence, pure mechanism policy, supported-name contracts, pure name
policy, diagnostics/hardening/tests, and documentation reconciliation. A
complete deterministic matrix is recorded in `TEST_PLAN.md`. No implementation
unit is authorized now.

This planning-only update changes exactly:

- `CURRENT_STATUS.md`;
- `DECISIONS.md`;
- `IMPLEMENTATION_PLAN.md`; and
- `TEST_PLAN.md`.

It changes no source, tests, configuration, workflow, dependency, packaging,
license, generated file, application behavior, RTSS/profile state, or other
external system. `REVIEW_FINDINGS.md` remains unchanged because the review
findings are planning-review records summarized here and must remain separate
from the unchanged production ledger.
`RELEASE_NOTES.md` remains unchanged because the repository convention records
implemented contract behavior there, while this change is planning only.

Independent read-only review of the first corrected planning commit
`88efe137be44b8be6f26da9b5982f045e6aa10f0` ended **Not approved - blocking
planning findings require correction**. The review confirmed
`S2-CAP-PLAN-001`, the original `S2-NAME-PLAN-001` defect, and
`S2-DOC-OPEN-001` remained corrected. It identified seven blocking findings:

- `S2-CAP-PLAN-002`: observation-level unavailability had no legal typed
  representation;
- `S2-CAP-PLAN-003`: coordinated fractional update had contradictory
  dependency and admission meanings;
- `S2-RANGE-PLAN-001`: bit-width formulas and cross-domain bound conversion
  remained incomplete;
- `S2-NAME-PLAN-002`: overlapping raw-name classes had no deterministic
  precedence or leading reason;
- `S2-NAME-PLAN-003`: named normalization had no closed compatibility
  predicate;
- `S2-NAME-RULE-PLAN-001`: admitted name-rule evidence had no single
  construction and trust boundary; and
- `S2-TEST-PLAN-001`: the affected matrices still could not serve as an
  independent oracle.

The review also recorded non-blocking `S2-TEST-PLAN-002`: a failing
reason-order input must not include the success reason.

This second documentation-only planning correction removes observation-level
unavailability; makes coordinated fractional update one internal ordered,
reversible dependency bundle; closes signed bit-width and exact discrete-bound
conversion rules; defines one aggregating raw-name classifier and leading
reason order; defines exact named-normalization compatibility; introduces one
factory-controlled, parent-bound admitted name-rule set; and rebuilds the
affected matrices with independently stated outcomes and separate failure and
success reason-order tests. These are proposed planning semantics pending
review, not implemented contracts.

At that point, the second corrected sequence-item-2 plan was complete locally
but had not been independently approved. No source or test file changed. No
push or pull request existed. Its next action was another independent read-only
review followed, only if approved, by a later explicit acceptance
documentation step. Sequence item 2 implementation and sequence item 3
remained unauthorized, as did every mutation, production integration, push,
and pull-request creation. No RTSS, Windows, RX 7900 XTX, Lossless Scaling,
display, VRR, or frame-generation compatibility claim was established.

Independent read-only review of the second corrected planning commit
`ae252ff8341570e2c55aa3c8555117dfb4e3db8c`
(`docs: complete RTSS capability policy corrections`) ended **Not approved —
blocking planning findings require correction**. The review found exactly
three remaining blocking planning defects:

- `S2-CAP-PLAN-003-R2`: save and activation were unconditional dependencies
  even though the pure model did not prove whether either operation was
  required, proved not required, or of unknown applicability for the exact
  mechanism and forward/restoration context;
- `S2-TEST-PLAN-002-R2`: the reason-order matrix requested one impossible
  all-category fixture containing mutually exclusive and short-circuited
  states; and
- `S2-TEST-PLAN-001-R2`: the discrete-bound oracle lacked literal negative
  floor/ceiling and negative-intersection expectations.

The review found no other blocking or non-blocking planning finding. It
confirmed that all other prior capability, range, raw-name, name-rule,
normalization, context, and ownership corrections remained intact; all 181
deterministic tests passed; source and tests were unchanged; and the 50-row
production ledger remained unchanged with all nine production RTSS findings
Open.

This third documentation-only correction defines factory-admitted,
mechanism- and context-specific save/activation applicability with exactly
`REQUIRED`, `NOT_REQUIRED`, and `UNKNOWN`; replaces the impossible aggregate
diagnostic fixture with literal maximal legally co-applicable groups and
separate exclusive-state/success fixtures; and adds literal negative
bound-conversion, intersection, negative-zero, equal-boundary, and signed
underflow oracles. All other corrected planning semantics and all sequence
boundaries are preserved.

It changes exactly `CURRENT_STATUS.md`, `DECISIONS.md`,
`IMPLEMENTATION_PLAN.md`, and `TEST_PLAN.md`. It changes no source, tests,
configuration, workflow, dependency, packaging, license, release note,
generated file, application behavior, or external state.

Independent read-only review of the third corrected planning commit
`2825a8fbed1b3bc1e10d42e3c5d73b352c57ab73`
(`docs: finalize RTSS capability policy plan`) ended **Not approved -
blocking planning findings require correction**. The review confirmed that
Groups A-F are legally constructible, the literal positive and negative
arithmetic oracles are correct, the 12-item sequence boundaries are preserved,
and the production ledger remains 50 uniquely identified rows with all nine
RTSS findings Open. It found exactly two remaining blockers:

- `S2-CAP-PLAN-004-R3`: child-specific applicability mismatch reasons were
  assigned to the public evaluator even though a mismatched child has no legal
  path into a consistent admitted parent; and
- `S2-CAP-PLAN-005-R3`: applicability and equivalent name-rule duplicate/
  overlap language lacked literal canonical keys and predicates.

This fourth documentation-only correction keeps the existing typed
contradictory-parent policy. Applicability-child invariants, exact-scope
requirements, duplicates, and overlaps are decided at factory admission. A
semantic conflict produces one current contradictory admitted parent with
canonically ordered admission diagnostics and no selectable records; the
parent-only public evaluator then returns exactly `UNKNOWN /
CONTRADICTORY_EVIDENCE`. It never accepts or diagnoses a standalone child.
The correction also defines the literal applicability key, immutable
field-set representation, exact duplicate and intersection predicates,
wildcard prohibition, primitive-versus-compound scope, deterministic ordering,
and the equivalent exact-scope rule for admitted name-rule sets.

At that point, the fourth corrected sequence-item-2 plan remained unapproved
pending another independent read-only review. No source or test file had
changed. No push or pull request existed. Its next authorized action was that
review followed, only if approved, by a later documentation-only acceptance
step. Sequence item 2 implementation, sequence item 3, push, and pull-request
creation remained unauthorized.

Independent read-only review of the fourth corrected planning commit
`b59187343ce775013dfcdbaf899a819cc53409cf`
(`docs: close RTSS applicability contract gaps`) ended exactly **Not approved —
blocking planning findings require correction**. It found exactly five blocking
findings and no non-blocking findings:

- `S2-CAP-TRUST-001-R4`: equal-value applicability and name-rule children had
  no defined authority discriminator or complete re-admission rule;
- `S2-CAP-PLAN-004-R4`: duplicate raw applicability keys still had conflicting
  factory-rejection and contradictory-parent outcomes;
- `S2-CAP-PLAN-005-R4-A`: simultaneous structural, binding, duplicate, and
  overlap conflicts had no complete order-independent reduction;
- `S2-TEST-PLAN-003-R4`: the admitted partial-intersection fixture used
  synthetic field `X`, which is not a production `RtssStoredFieldKind`; and
- `S2-DOC-STATUS-002-R4`: correction history, rejected-review count, current
  phase, and next-action wording remained stale.

This fifth documentation-only planning correction selects one parent-factory
reconstruction model for applicability and name-rule evidence. The complete
parent is the only public evaluator input. Its factory treats every nested
child as untrusted immutable value input, validates every field, and rebuilds
canonical children and a canonical parent; the evaluator re-runs that same
complete-parent boundary. Therefore shallow copies, deep copies, exact-value
reconstruction, unchanged `dataclasses.replace()`, copied provenance values,
and caller-authored equal values cannot differ in authority, while every
changed value is revalidated and a standalone child can never prove support.

Raw duplicate applicability keys now have one outcome only: the factory returns
one current `CONTRADICTORY` parent with no selectable primitive or applicability
records and exact diagnostic `(APPLICABILITY_EXACT_DUPLICATE,)`; the public
evaluator returns exactly `UNKNOWN / (CONTRADICTORY_EVIDENCE,)`. A separate
internal guard may reject an attempt to force conflicting records into an
already-labelled `CONSISTENT` object, but it is not an alternative raw-admission
outcome.

Combined conflicts use one retain-all, order-independent reduction. It retains
every raw occurrence and every per-record structural or binding source,
canonicalizes comparable keys, enumerates every unordered pair, and retains
every duplicate or overlap source. A duplicate pair emits only its duplicate
source, but each duplicate occurrence still pairs with third records; malformed
non-comparable records retain their own sources without pair analysis. Exact
repeated sources are set-deduplicated, sources and diagnostic enums use explicit
canonical ranks and value/source keys, and stable diagnostic precedence is
shape/trust and binding/provenance/source, exact duplicate, field overlap, then
structural/scope. Any source
produces one current contradictory parent with no selectable records and public
result exactly `UNKNOWN / (CONTRADICTORY_EVIDENCE,)`, independent of input or
detector order.

The current production field universe contains only `NUMERATOR` and
`DENOMINATOR`. Equal, strict-subset, strict-superset, and disjoint field-set
relations are reachable at the real admission boundary. Non-empty unequal
partial intersection is mathematically unreachable with two members, so no
synthetic field is admitted as evidence. A separately named pure set-relation
oracle may test generic partial-intersection mathematics; an enum-expansion
guard requires a legal real-boundary fixture when at least three unique
`RtssStoredFieldKind` members exist.

This fifth correction changes exactly:

- `CURRENT_STATUS.md`;
- `DECISIONS.md`;
- `IMPLEMENTATION_PLAN.md`; and
- `TEST_PLAN.md`.

It changes no source, test, workflow, dependency, configuration, packaging,
license, generated file, application behavior, or external state.
`AGENTS.md`, `REVIEW_FINDINGS.md`, and `RELEASE_NOTES.md` remain unchanged. No
RTSS or profile mutation, live Windows or hardware action, push, pull request,
merge, publication, or later pipeline-stage work occurred.

Independent read-only review of fifth planning-correction commit
`c3047fc37248392b74255f36844120fc0f6fef82`, whose sole parent is
`b59187343ce775013dfcdbaf899a819cc53409cf`, ended exactly **Approved — Stage 2
sequence item 2 planning is complete**. The reviewed commit's subject is
`docs: resolve RTSS applicability planning conflicts`, its tree is
`97e0c705e16da878870849e1c0feb4ec1d173504`, and its stable patch ID is
`a1836c15ff9ff4efdec3cf4b225305e8d553c45a`.

The review found no blocking or non-blocking planning findings and independently
confirmed closure of:

- `S2-CAP-TRUST-001-R4`;
- `S2-CAP-PLAN-004-R4`;
- `S2-CAP-PLAN-005-R4-A`;
- `S2-TEST-PLAN-003-R4`; and
- `S2-DOC-STATUS-002-R4`.

With `PYTHONDONTWRITEBYTECODE=1`, the review ran
`python -m unittest discover -s tests -t . -v`: all 181 tests passed in
0.315 seconds with zero failures, errors, skips, or warnings. It verified a
clean worktree and empty index, no ordinary untracked or generated artifacts,
local `main` and recorded `origin/main` at
`f8c4d4a2f7c6e1db39f3fd3c037ed98e07c39c95`, branch divergence zero behind
and 15 ahead, no configured upstream, no remote-tracking branch containing the
reviewed commit, and no publication or remote interaction.

By authorizing this documentation-only step after that approved review, the
user explicitly accepts the reviewed sequence-item-2 capability and
supported-name policy plan and its deterministic test expectations.
Sequence-item-2 planning is therefore accepted and complete. This acceptance
does not implement sequence item 2, authorize sequence item 3, admit mutation,
or establish live or physical compatibility.

This acceptance task changes exactly:

- `CURRENT_STATUS.md`;
- `REVIEW_FINDINGS.md`;
- `DECISIONS.md`;
- `IMPLEMENTATION_PLAN.md`;
- `TEST_PLAN.md`; and
- `RELEASE_NOTES.md`.

It changes no source, test, workflow, dependency, configuration, packaging,
license, generated file, application behavior, or external state. No push or
pull request exists. The documentation commit recording this acceptance is not
itself claimed to have received independent review.

The accepted 12-item sequence is unchanged: sequence item 1 is complete and
independently approved for deterministic contracts only; sequence item 2 is
capability and supported-name policy; sequence item 3 is coordinator admission
and capture without mutation; sequence item 4 is rollback foundations without
mutation; the first mutation remains sequence item 5; profile creation and
restoration remain sequence item 6; and production adapters plus live
evidence-backed support claims remain sequence item 12. The fifth correction is
independently approved and explicitly accepted, while remaining local and
unpublished. A later focused sequence-item-2 implementation session is
authorized only by separate instruction after publication topology is settled;
no implementation occurs here. Sequence item 3, every later sequence item,
enhancement-backlog work, merge, and release remain unauthorized. Mutation
remains gated until sequence item 5 and its prerequisites, and production
adapters remain sequence item 12.

## Current work

RTSS Stage 1 is complete and merged. It provides deterministic identity,
rational-cap, generation, capability, capture, readback, apply, restoration,
ownership, evidence, and result contracts with deterministic tests.

RTSS Stage 2 planning, its accepted corrections and review record, the
sequence-item-2 initial plan and four rejected corrections, the independently
approved fifth correction, and this explicit acceptance record are maintained
on `feature/rtss-transaction-coordinator`. The first Stage 2 contract/test-only
sequence item and its three focused corrections are implemented locally;
sequence item 1 is independently approved and complete. Sequence-item-2
planning is accepted and complete, but no transaction coordinator or
sequence-item-2 source implementation exists and no production caller uses the
planned contracts.

The initial local Stage 2 planning commit changed exactly:

- `CURRENT_STATUS.md`;
- `IMPLEMENTATION_PLAN.md`; and
- `TEST_PLAN.md`.

The planning corrections were documentation-only and limited to:

- `CURRENT_STATUS.md`;
- `REVIEW_FINDINGS.md`;
- `IMPLEMENTATION_PLAN.md`; and
- `TEST_PLAN.md`.

The acceptance record is also documentation-only and limited to
`CURRENT_STATUS.md`, `REVIEW_FINDINGS.md`, `DECISIONS.md`,
`IMPLEMENTATION_PLAN.md`, and `TEST_PLAN.md`. None of this planning or
acceptance work changes production source, tests, configuration, workflows,
ignored review inputs, or external state. The branch remains local only: no
Stage 2 push, remote branch, configured upstream for this branch, or pull
request exists.

This documentation-only sequence-item-1 approval update changes exactly:

- `CURRENT_STATUS.md`;
- `REVIEW_FINDINGS.md`;
- `IMPLEMENTATION_PLAN.md`;
- `TEST_PLAN.md`; and
- `RELEASE_NOTES.md`.

It changes no source, tests, configuration, workflow, dependency, packaging,
license, generated file, application behavior, or external system.
`DECISIONS.md` remains unchanged because no new architectural decision was
introduced. The documentation commit recording this approval is not itself
claimed to have received independent review.

## Design-review status

**Accepted Stage 2 design; sequence item 1 complete and independently approved;
sequence-item-2 deterministic planning independently approved, explicitly
accepted, and complete.**

The Stage 2 design review preserves the Stage 1 contract layer while planning
the focused prerequisites and extensions required by a deterministic
coordinator:

- correct `S1-READBACK-001` by restricting `RtssReadback` to read-only
  outcomes and failure steps;
- correct `S1-TEST-001` with an exhaustive readback outcome/failure-step
  acceptance and rejection matrix;
- correct `S1-DESIGN-001` with capability-driven DLL-name and derived-profile
  component limits;
- add exact stored numerator and denominator capture because the existing
  reduced `RationalCap` represents the effective value but cannot alone prove
  representation-exact restoration;
- require immutable degraded-state accounting for every unresolved owned field,
  save/update uncertainty, backend epoch, retained ownership, unavailable or
  unreadable evidence, and external conflicts;
- distinguish always-invalid lexical/path forms from capability-dependent,
  exactly encoded supported names, with non-ASCII rejected by default;
- add explicit transaction identity/admission around immutable Stage 1
  requests so duplicates and concurrent writers can be rejected; and
- keep deterministic coordination separate from later live DLL, profile-file,
  GUI, lifecycle, and production-caller integration.

The readback, exact stored-field, degraded-state, handoff, and retained-
ownership prerequisites in sequence item 1 are corrected, independently
approved, and complete. Capability-driven name policy is sequence item 2: its
initial plan and four corrections through `b591873` were rejected in five
independent reviews; fifth correction `c3047fc` is independently approved and
explicitly accepted. Its deterministic planning is complete. Source
implementation has not begun. A later focused item-2 implementation session is
the next implementation activity only after publication topology is settled.
Sequence item 3 and later work remain unauthorized. Coordinator logic,
mutation, production integration, and later tests remain unimplemented and
non-production-reachable. Trusted observation of an advanced backend or
capability generation remains a later admission/adapter concern.

The tracked ledger identifies `S1-FINAL-005`, `S1-FINAL-006`, and
`S1-FINAL-007` only as deferred identifiers and does not retain their
root-cause or acceptance text. No technical allocation or closure is permitted
without provenance recovery. They are not treated as coordinator prerequisites
unless recovered evidence proves that they are. Any recovered requirement must
be added to durable tracked documentation and receive appropriate regression
coverage before disposition; ignored local reports must never be required by a
fresh clone.

## Production status

The existing production RTSS paths remain unchanged and unsafe for unattended
use:

- `RTSSController` exposes separate, unserialized profile loads, property
  reads/writes, saves, updates, direct profile-file rewrites, deletion, and
  global flag mutation;
- application startup unconditionally enables the RTSS limiter;
- start and stop both initiate cap writes;
- the monitoring loop performs overload, headroom, idle-entry, and idle-exit
  writes and advances logical cap state before write verification;
- exit may write the Global cap without a captured prior state or verified
  restoration;
- profile deletion is initiated directly by `ConfigManager`; and
- Autopilot and monitoring profile changes are not transactional or
  generation-owned.

No physical RTSS, profile-file, Windows runtime, GPU, driver, game, GUI,
LibreHardwareMonitor, PDH, registry, or Lossless Scaling validation was
performed. No supported RTSS-version, RX 7900 XTX, or Lossless Scaling
compatibility claim is made.

## Release status

Not ready for unattended RX 7900 XTX or Autopilot use. Controller evidence can
be stale or backend-coupled, RTSS writes are not serialized or reversible, and
lifecycle races can permit stale generations to act.

No live RTSS, Windows, RX 7900 XTX, Lossless Scaling, display, VRR, or
frame-generation compatibility has been established.

## Next action and gates

The original Stage 2 architecture gates and the sequence-item-1 implementation
gates are satisfied. The sequence-item-2 initial plan and four corrections
through `b591873` received five rejected reviews. Fifth correction `c3047fc`
passed independent review with exact verdict **Approved — Stage 2 sequence item
2 planning is complete**, all five R4 blockers closed, and no blocking or
non-blocking findings. The user explicitly accepted that reviewed plan in this
documentation-only step.

The exact next safe action is a separately authorized, non-rewriting stacked
publication. No push or pull request is performed here. After publication
topology is settled, a separately instructed focused sequence-item-2
implementation session is authorized. No sequence-item-2 implementation exists
yet. Sequence item 3 coordinator admission/capture, sequence item 4 rollback
foundations, every mutation-bearing slice, production integration, merge,
release, and enhancement-backlog work remain separately unauthorized. No
mutation is admitted before sequence item 5 and its prerequisites; profile
creation/restoration remains sequence item 6; and production adapters and live
evidence-backed support claims remain sequence item 12.

## Physical validation still required

- Stable RX 7900 XTX LHM hardware/sensor identities and RX 7000 power-sensor
  behavior.
- PDH LUID and engine attribution with Lossless Scaling.
- Supported RTSS versions, fractional denominator behavior, readback, and exact
  restoration.
- Cap-write timing, settle delays, and frametime effects.
- Game, Lossless Scaling, desktop, and launcher identity transitions.
- Long-uptime idle behavior, Win32 ABI behavior, driver/RTSS restart, sleep, and
  shutdown resilience.

## Historical documentation scope

The seven durable project documents were introduced through pull request #1:

- `AGENTS.md`;
- `CURRENT_STATUS.md`;
- `REVIEW_FINDINGS.md`;
- `DECISIONS.md`;
- `IMPLEMENTATION_PLAN.md`;
- `TEST_PLAN.md`; and
- `RELEASE_NOTES.md`.

The Stage 1 branch and pull request #3 added the deterministic RTSS contracts,
tests, and synchronized documentation. PR #3 is now merged; its final squash
commit is
`f8c4d4a2f7c6e1db39f3fd3c037ed98e07c39c95`. Production RTSS behavior did not
change in Stage 1.
