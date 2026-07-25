"""RTSS Stage 2 prerequisite readback, evidence, and ownership contracts."""

from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError, replace

from src.core import rtss_contracts
from src.core.rtss_contracts import (
    RTSS_READBACK_FAILURE_STEPS,
    RTSS_READBACK_OUTCOMES,
    RTSS_STORED_CAP_NOT_REQUESTED,
    CanonicalProfileIdentity,
    CapturedProfileState,
    RationalCap,
    RtssApplyRequest,
    RtssApplyResult,
    RtssDegradedClassification,
    RtssDegradedFieldAccounting,
    RtssDegradedHandoff,
    RtssDegradedState,
    RtssDenominatorStrategy,
    RtssFailureStep,
    RtssFieldAvailability,
    RtssGeneration,
    RtssHandoffDecision,
    RtssHandoffResult,
    RtssOperationState,
    RtssOutcome,
    RtssOwnedField,
    RtssOwnershipRelease,
    RtssOwnershipReleaseReason,
    RtssOwnershipToken,
    RtssReadback,
    RtssRestoreResult,
    RtssStoredCapEvidence,
    RtssStoredFieldEvidence,
    RtssTransactionIdentity,
    RtssUnresolvedFieldEvidence,
)


READBACK_STEPS_BY_OUTCOME = {
    RtssOutcome.VERIFIED: {RtssFailureStep.NONE},
    RtssOutcome.REJECTED_VALIDATION: {RtssFailureStep.VALIDATE},
    RtssOutcome.STALE_GENERATION: {RtssFailureStep.GENERATION},
    RtssOutcome.UNSUPPORTED_CAPABILITY: {RtssFailureStep.CAPABILITY},
    RtssOutcome.POLICY_REQUIRED: {RtssFailureStep.CAPABILITY},
    RtssOutcome.CONFLICT: {RtssFailureStep.CONFLICT},
    RtssOutcome.FAILED: {RtssFailureStep.READBACK},
}


def _accounting(
    applicable: set[RtssOwnedField],
    resolved: set[RtssOwnedField],
) -> RtssDegradedFieldAccounting:
    unresolved = applicable - resolved
    return RtssDegradedFieldAccounting(
        frozenset(applicable),
        frozenset(resolved),
        tuple(
            RtssUnresolvedFieldEvidence(
                field,
                RtssFieldAvailability.READ_FAILED,
                f"{field.value} remains unresolved",
            )
            for field in sorted(unresolved, key=lambda item: item.value)
        ),
    )


class RtssReadbackAllowlistTests(unittest.TestCase):
    def setUp(self):
        identity = CanonicalProfileIdentity.application("game.exe")
        self.generation = RtssGeneration(1, 2, 3, identity, 4)

    def test_S1_READBACK_001_allowlists_are_explicit_and_fail_closed(self):
        expected_outcomes = frozenset(READBACK_STEPS_BY_OUTCOME)
        expected_steps = frozenset().union(*READBACK_STEPS_BY_OUTCOME.values())
        rejected_outcomes = frozenset(
            {
                RtssOutcome.FAILED_ROLLED_BACK,
                RtssOutcome.DEGRADED,
            }
        )
        rejected_steps = frozenset(
            {
                RtssFailureStep.CAPTURE,
                RtssFailureStep.APPLY,
                RtssFailureStep.SAVE,
                RtssFailureStep.UPDATE,
                RtssFailureStep.ROLLBACK,
                RtssFailureStep.RESTORE,
                RtssFailureStep.DELETE,
            }
        )

        self.assertEqual(RTSS_READBACK_OUTCOMES, expected_outcomes)
        self.assertEqual(RTSS_READBACK_FAILURE_STEPS, expected_steps)
        self.assertEqual(
            set(rtss_contracts._READBACK_FAILURE_STEPS_BY_OUTCOME),
            set(RTSS_READBACK_OUTCOMES),
        )
        self.assertEqual(
            set(RTSS_READBACK_OUTCOMES) | set(rejected_outcomes),
            set(RtssOutcome),
        )
        self.assertFalse(set(RTSS_READBACK_OUTCOMES) & set(rejected_outcomes))
        self.assertEqual(
            set(RTSS_READBACK_FAILURE_STEPS) | set(rejected_steps),
            set(RtssFailureStep),
        )
        self.assertFalse(
            set(RTSS_READBACK_FAILURE_STEPS) & set(rejected_steps)
        )

    def test_S1_TEST_001_readback_outcome_and_step_matrix_is_exhaustive(self):
        self.assertEqual(
            set(READBACK_STEPS_BY_OUTCOME),
            set(RTSS_READBACK_OUTCOMES),
        )
        for outcome in RtssOutcome:
            for step in RtssFailureStep:
                with self.subTest(outcome=outcome, step=step):
                    kwargs = {"failure_step": step}
                    if outcome is not RtssOutcome.VERIFIED:
                        kwargs["error"] = "classified read-only failure"
                    try:
                        RtssReadback(
                            outcome,
                            self.generation,
                            False,
                            None,
                            **kwargs,
                        )
                    except ValueError:
                        accepted = False
                    else:
                        accepted = True
                    self.assertEqual(
                        accepted,
                        step in READBACK_STEPS_BY_OUTCOME.get(outcome, set()),
                    )

    def test_S1_READBACK_001_rejects_all_mutation_and_rollback_states(self):
        for outcome in (RtssOutcome.FAILED_ROLLED_BACK, RtssOutcome.DEGRADED):
            with self.subTest(outcome=outcome):
                with self.assertRaisesRegex(ValueError, "read-only"):
                    RtssReadback(
                        outcome,
                        self.generation,
                        False,
                        None,
                        failure_step=RtssFailureStep.READBACK,
                        error="mutation-only outcome",
                    )

        rejected_steps = set(RtssFailureStep) - set(
            RTSS_READBACK_FAILURE_STEPS
        )
        self.assertEqual(
            rejected_steps,
            {
                RtssFailureStep.CAPTURE,
                RtssFailureStep.APPLY,
                RtssFailureStep.SAVE,
                RtssFailureStep.UPDATE,
                RtssFailureStep.ROLLBACK,
                RtssFailureStep.RESTORE,
                RtssFailureStep.DELETE,
            },
        )
        for step in rejected_steps:
            with self.subTest(step=step):
                with self.assertRaisesRegex(ValueError, "read-only"):
                    RtssReadback(
                        RtssOutcome.FAILED,
                        self.generation,
                        False,
                        None,
                        failure_step=step,
                        error="mutation-only failure step",
                    )

    def test_S1_TEST_001_apply_outcome_and_step_matrix_remains_exhaustive(self):
        cap = RationalCap(60, 1)
        request = RtssApplyRequest(
            self.generation,
            cap,
            RtssDenominatorStrategy.PROFILE_FILE,
            reason="apply matrix",
        )
        captured = CapturedProfileState(self.generation, 7, True, cap)
        exact_readback = RtssReadback(
            RtssOutcome.VERIFIED,
            self.generation,
            True,
            cap,
            backend_generation=7,
        )
        verified_restore = RtssRestoreResult(
            RtssOutcome.VERIFIED,
            self.generation,
            readback=exact_readback,
            captured_state=captured,
        )
        degraded_restore = RtssRestoreResult(
            RtssOutcome.DEGRADED,
            self.generation,
            captured_state=captured,
            failure_step=RtssFailureStep.ROLLBACK,
            error="rollback evidence unavailable",
        )
        post_mutation_steps = {
            RtssFailureStep.APPLY,
            RtssFailureStep.SAVE,
            RtssFailureStep.UPDATE,
            RtssFailureStep.READBACK,
        }
        expected = {
            RtssOutcome.VERIFIED: {RtssFailureStep.NONE},
            RtssOutcome.REJECTED_VALIDATION: {RtssFailureStep.VALIDATE},
            RtssOutcome.STALE_GENERATION: {RtssFailureStep.GENERATION},
            RtssOutcome.UNSUPPORTED_CAPABILITY: {
                RtssFailureStep.CAPABILITY
            },
            RtssOutcome.POLICY_REQUIRED: {RtssFailureStep.CAPABILITY},
            RtssOutcome.CONFLICT: {RtssFailureStep.CONFLICT},
            RtssOutcome.FAILED: {
                RtssFailureStep.VALIDATE,
                RtssFailureStep.GENERATION,
                RtssFailureStep.CAPABILITY,
                RtssFailureStep.CAPTURE,
                *post_mutation_steps,
            },
            RtssOutcome.FAILED_ROLLED_BACK: post_mutation_steps,
            RtssOutcome.DEGRADED: post_mutation_steps,
        }
        self.assertEqual(set(expected), set(RtssOutcome))

        for outcome in RtssOutcome:
            for step in RtssFailureStep:
                with self.subTest(outcome=outcome, step=step):
                    kwargs = {"failure_step": step}
                    if outcome is RtssOutcome.VERIFIED:
                        kwargs.update(
                            readback=exact_readback,
                            captured_state=captured,
                        )
                    else:
                        kwargs["error"] = "classified apply result"
                    if outcome is RtssOutcome.FAILED and step in post_mutation_steps:
                        kwargs.update(
                            readback=exact_readback,
                            captured_state=captured,
                        )
                    elif outcome is RtssOutcome.FAILED_ROLLED_BACK:
                        kwargs.update(
                            captured_state=captured,
                            rollback=verified_restore,
                        )
                    elif outcome is RtssOutcome.DEGRADED:
                        kwargs.update(
                            captured_state=captured,
                            rollback=degraded_restore,
                        )
                    try:
                        RtssApplyResult(outcome, request, **kwargs)
                    except ValueError:
                        accepted = False
                    else:
                        accepted = True
                    self.assertEqual(accepted, step in expected[outcome])


class ExactStoredRepresentationTests(unittest.TestCase):
    def setUp(self):
        self.generation = RtssGeneration(
            1,
            2,
            3,
            CanonicalProfileIdentity.application("game.exe"),
            4,
        )

    def test_stage2_exact_stored_pair_preserves_unreduced_representation(self):
        stored = RtssStoredCapEvidence.available(120, 2)

        self.assertEqual(stored.numerator.value, 120)
        self.assertEqual(stored.denominator.value, 2)
        self.assertEqual(stored.effective_cap, RationalCap(60, 1))
        self.assertNotEqual(stored, RtssStoredCapEvidence.available(60, 1))

    def test_stage2_exact_stored_pair_rejects_partial_or_invalid_evidence(self):
        with self.assertRaisesRegex(ValueError, "coherent paired"):
            RtssStoredCapEvidence(
                RtssStoredFieldEvidence(
                    RtssFieldAvailability.AVAILABLE,
                    120,
                ),
                RtssStoredFieldEvidence(RtssFieldAvailability.READ_FAILED),
            )
        with self.assertRaisesRegex(ValueError, "must not contain"):
            RtssStoredFieldEvidence(
                RtssFieldAvailability.UNSUPPORTED,
                1,
            )
        with self.assertRaisesRegex(ValueError, "positive"):
            RtssStoredCapEvidence.available(60, 0)

    def test_stage2_exact_stored_pair_distinguishes_all_evidence_states(self):
        states = {
            availability: RtssStoredCapEvidence.unavailable(availability)
            for availability in RtssFieldAvailability
            if availability is not RtssFieldAvailability.AVAILABLE
        }

        self.assertEqual(set(states), set(RtssFieldAvailability) - {
            RtssFieldAvailability.AVAILABLE
        })
        self.assertEqual(len(set(states.values())), len(states))
        for availability, evidence in states.items():
            with self.subTest(availability=availability):
                self.assertIs(evidence.availability, availability)
                self.assertIsNone(evidence.numerator.value)
                self.assertIsNone(evidence.denominator.value)

    def test_stage2_exact_pair_is_not_inferred_from_reduced_cap(self):
        captured = CapturedProfileState(
            self.generation,
            7,
            True,
            RationalCap(60, 1),
        )
        readback = RtssReadback(
            RtssOutcome.VERIFIED,
            self.generation,
            True,
            RationalCap(60, 1),
            backend_generation=7,
        )

        self.assertIs(captured.stored_cap, RTSS_STORED_CAP_NOT_REQUESTED)
        self.assertIs(readback.stored_cap, RTSS_STORED_CAP_NOT_REQUESTED)

    def test_stage2_exact_pair_must_match_effective_cap_mathematically(self):
        with self.assertRaisesRegex(ValueError, "mathematically"):
            CapturedProfileState(
                self.generation,
                7,
                True,
                RationalCap(60, 1),
                stored_cap=RtssStoredCapEvidence.available(119, 2),
            )
        with self.assertRaisesRegex(ValueError, "mathematically"):
            RtssReadback(
                RtssOutcome.VERIFIED,
                self.generation,
                True,
                RationalCap(60, 1),
                backend_generation=7,
                stored_cap=RtssStoredCapEvidence.available(119, 2),
            )

    def test_stage2_mathematically_equal_representation_mismatch_is_not_exact(self):
        captured = CapturedProfileState(
            self.generation,
            7,
            True,
            RationalCap(60, 1),
            stored_cap=RtssStoredCapEvidence.available(120, 2),
        )
        normalized_readback = RtssReadback(
            RtssOutcome.VERIFIED,
            self.generation,
            True,
            RationalCap(60, 1),
            backend_generation=7,
            stored_cap=RtssStoredCapEvidence.available(60, 1),
        )

        with self.assertRaisesRegex(ValueError, "representation"):
            RtssRestoreResult(
                RtssOutcome.VERIFIED,
                self.generation,
                readback=normalized_readback,
                captured_state=captured,
            )

    def test_stage2_identical_stored_representation_can_verify_exact_restore(self):
        stored = RtssStoredCapEvidence.available(120, 2)
        captured = CapturedProfileState(
            self.generation,
            7,
            True,
            RationalCap(60, 1),
            stored_cap=stored,
        )
        readback = RtssReadback(
            RtssOutcome.VERIFIED,
            self.generation,
            True,
            RationalCap(60, 1),
            backend_generation=7,
            stored_cap=stored,
        )

        result = RtssRestoreResult(
            RtssOutcome.VERIFIED,
            self.generation,
            readback=readback,
            captured_state=captured,
        )
        self.assertTrue(result.succeeded)

    def test_stage2_unavailable_captured_storage_cannot_claim_exact_restore(self):
        for availability in (
            RtssFieldAvailability.READ_FAILED,
            RtssFieldAvailability.UNSUPPORTED,
        ):
            with self.subTest(availability=availability):
                captured = CapturedProfileState(
                    self.generation,
                    7,
                    True,
                    RationalCap(60, 1),
                    stored_cap=RtssStoredCapEvidence.unavailable(availability),
                )
                readback = RtssReadback(
                    RtssOutcome.VERIFIED,
                    self.generation,
                    True,
                    RationalCap(60, 1),
                    backend_generation=7,
                    stored_cap=RtssStoredCapEvidence.available(60, 1),
                )
                with self.assertRaisesRegex(ValueError, "unavailable captured"):
                    RtssRestoreResult(
                        RtssOutcome.VERIFIED,
                        self.generation,
                        readback=readback,
                        captured_state=captured,
                    )


class DegradedOwnershipContractTests(unittest.TestCase):
    def setUp(self):
        self.transaction = RtssTransactionIdentity("transaction-1")
        self.identity = CanonicalProfileIdentity.application("Game.exe")
        self.generation = RtssGeneration(1, 2, 3, self.identity, 4)
        self.request = RtssApplyRequest(
            self.generation,
            RationalCap(59, 1),
            RtssDenominatorStrategy.PROFILE_FILE,
            limiter_flag_mask=4,
            reason="degraded contract fixture",
        )
        self.captured = CapturedProfileState(
            RtssGeneration(
                1,
                2,
                3,
                CanonicalProfileIdentity.application("game.EXE"),
                4,
            ),
            7,
            True,
            RationalCap(60, 1),
            limiter_flags=4,
            profile_revision="revision-1",
            profile_document=b"Limit=120\nLimitDenominator=2\n",
            owned_flag_mask=4,
            profile_revision_availability=RtssFieldAvailability.AVAILABLE,
            profile_document_availability=RtssFieldAvailability.AVAILABLE,
            stored_cap=RtssStoredCapEvidence.available(120, 2),
        )
        self.owner = RtssOwnershipToken(
            self.transaction,
            self.generation,
            7,
            11,
            "session-owner",
        )
        self.applicable = {
            RtssOwnedField.EXACT_STORED_NUMERATOR,
            RtssOwnedField.EXACT_STORED_DENOMINATOR,
            RtssOwnedField.EFFECTIVE_CAP,
            RtssOwnedField.PROFILE_EXISTENCE,
            RtssOwnedField.PROFILE_DOCUMENT,
            RtssOwnedField.PROFILE_REVISION,
            RtssOwnedField.LIMITER_FLAGS,
            RtssOwnedField.SAVE,
            RtssOwnedField.ACTIVATION,
            RtssOwnedField.BACKEND_EPOCH,
            RtssOwnedField.RETAINED_OWNERSHIP,
        }
        self.resolved = {RtssOwnedField.RETAINED_OWNERSHIP}

    def state(self, **changes) -> RtssDegradedState:
        values = {
            "transaction_identity": self.transaction,
            "request": self.request,
            "captured_state": self.captured,
            "evidence_generation": self.generation,
            "latest_backend_generation": 8,
            "capability_generation": 11,
            "current_owner": self.owner,
            "accounting": _accounting(self.applicable, self.resolved),
            "classification": RtssDegradedClassification.READ_FAILURE,
            "reason": "readback failed after possible mutation",
            "save_state": RtssOperationState.UNCERTAIN,
            "activation_state": RtssOperationState.UNCERTAIN,
        }
        values.update(changes)
        return RtssDegradedState(**values)

    def test_stage2_degraded_state_accounts_for_every_supported_field(self):
        existing = self.state()
        absent_capture = CapturedProfileState(
            self.generation,
            7,
            False,
            None,
            stored_cap=RtssStoredCapEvidence.unavailable(
                RtssFieldAvailability.VERIFIED_ABSENT
            ),
        )
        absent_applicable = {
            RtssOwnedField.PROFILE_DELETION,
            RtssOwnedField.VERIFIED_PROFILE_ABSENCE,
            RtssOwnedField.BACKEND_EPOCH,
            RtssOwnedField.RETAINED_OWNERSHIP,
        }
        absent = self.state(
            captured_state=absent_capture,
            accounting=_accounting(
                absent_applicable,
                {RtssOwnedField.RETAINED_OWNERSHIP},
            ),
            save_state=RtssOperationState.NOT_APPLICABLE,
            activation_state=RtssOperationState.NOT_APPLICABLE,
        )

        represented = (
            existing.accounting.applicable_fields
            | absent.accounting.applicable_fields
        )
        self.assertEqual(represented, frozenset(RtssOwnedField))

    def test_stage2_degraded_accounting_rejects_incomplete_and_double_states(self):
        with self.assertRaisesRegex(ValueError, "classify every"):
            RtssDegradedFieldAccounting(
                frozenset(self.applicable),
                frozenset(),
                (),
            )
        field = RtssOwnedField.EFFECTIVE_CAP
        with self.assertRaisesRegex(ValueError, "also be listed"):
            RtssDegradedFieldAccounting(
                frozenset({field}),
                frozenset({field}),
                (
                    RtssUnresolvedFieldEvidence(
                        field,
                        RtssFieldAvailability.READ_FAILED,
                        "duplicate resolution",
                    ),
                ),
            )

    def test_stage2_degraded_state_rejects_claimed_resolution_without_evidence(self):
        falsely_resolved = set(self.resolved)
        falsely_resolved.add(RtssOwnedField.EFFECTIVE_CAP)
        with self.assertRaisesRegex(ValueError, "without matching evidence"):
            self.state(
                accounting=_accounting(self.applicable, falsely_resolved)
            )

    def test_stage2_unowned_and_unrequested_fields_do_not_become_unresolved(self):
        capture = CapturedProfileState(
            self.generation,
            7,
            True,
            RationalCap(60, 1),
        )
        applicable = {
            RtssOwnedField.EFFECTIVE_CAP,
            RtssOwnedField.PROFILE_EXISTENCE,
            RtssOwnedField.BACKEND_EPOCH,
            RtssOwnedField.RETAINED_OWNERSHIP,
        }
        state = self.state(
            captured_state=capture,
            save_state=RtssOperationState.NOT_APPLICABLE,
            activation_state=RtssOperationState.NOT_APPLICABLE,
            accounting=_accounting(
                applicable,
                {RtssOwnedField.RETAINED_OWNERSHIP},
            ),
        )

        self.assertNotIn(
            RtssOwnedField.EXACT_STORED_NUMERATOR,
            state.accounting.applicable_fields,
        )
        self.assertNotIn(
            RtssOwnedField.PROFILE_DOCUMENT,
            state.accounting.applicable_fields,
        )
        self.assertNotIn(
            RtssOwnedField.LIMITER_FLAGS,
            state.accounting.applicable_fields,
        )

    def test_stage2_save_and_activation_uncertainty_are_independent(self):
        for save_state, activation_state, unresolved_field in (
            (
                RtssOperationState.UNCERTAIN,
                RtssOperationState.VERIFIED,
                RtssOwnedField.SAVE,
            ),
            (
                RtssOperationState.VERIFIED,
                RtssOperationState.UNCERTAIN,
                RtssOwnedField.ACTIVATION,
            ),
        ):
            with self.subTest(
                save_state=save_state,
                activation_state=activation_state,
            ):
                resolved = set(self.resolved)
                resolved.add(RtssOwnedField.BACKEND_EPOCH)
                resolved.add(
                    RtssOwnedField.ACTIVATION
                    if activation_state is RtssOperationState.VERIFIED
                    else RtssOwnedField.SAVE
                )
                state = self.state(
                    latest_backend_generation=7,
                    save_state=save_state,
                    activation_state=activation_state,
                    accounting=_accounting(self.applicable, resolved),
                )
                self.assertIn(
                    unresolved_field,
                    state.accounting.unresolved_fields,
                )

    def test_stage2_degraded_state_requires_retained_immutable_ownership(self):
        state = self.state()
        self.assertTrue(state.ownership_retained)
        with self.assertRaises(FrozenInstanceError):
            state.ownership_retained = False
        with self.assertRaisesRegex(ValueError, "retain ownership"):
            self.state(ownership_retained=False)

    def test_stage2_degraded_state_rejects_incomplete_attribution(self):
        mismatches = (
            (
                "captured generation",
                {"captured_state": replace(
                    self.captured,
                    generation=replace(
                        self.generation,
                        profile_generation=99,
                    ),
                )},
            ),
            (
                "evidence generation",
                {"evidence_generation": replace(
                    self.generation,
                    source_generation=99,
                )},
            ),
            (
                "owner generation",
                {"current_owner": replace(
                    self.owner,
                    generation=replace(
                        self.generation,
                        session_generation=99,
                    ),
                )},
            ),
            (
                "owner backend epoch",
                {"current_owner": replace(
                    self.owner,
                    backend_generation=99,
                )},
            ),
            (
                "capability generation",
                {"current_owner": replace(
                    self.owner,
                    capability_generation=99,
                )},
            ),
            (
                "transaction identity",
                {"current_owner": replace(
                    self.owner,
                    transaction_identity=RtssTransactionIdentity(
                        "transaction-2"
                    ),
                )},
            ),
        )
        for message, changes in mismatches:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    self.state(**changes)

    def test_stage2_case_only_identity_variation_preserves_canonical_ownership(self):
        state = self.state()
        self.assertEqual(
            state.profile_identity,
            state.captured_state.generation.profile_identity,
        )
        self.assertIs(state.profile_kind, self.identity.kind)
        self.assertEqual(state.requested_generation, self.generation)
        self.assertEqual(state.captured_generation, self.generation)
        self.assertIsNone(state.readback_generation)
        self.assertNotEqual(
            state.request.generation.profile_identity.name,
            state.captured_state.generation.profile_identity.name,
        )

    def test_stage2_degraded_classifications_are_closed_and_immutable(self):
        self.assertEqual(
            set(RtssDegradedClassification),
            {
                RtssDegradedClassification.PARTIAL_RESTORATION,
                RtssDegradedClassification.UNRESOLVED_MUTATION,
                RtssDegradedClassification.EXTERNAL_CONFLICT,
                RtssDegradedClassification.EVIDENCE_UNAVAILABLE,
                RtssDegradedClassification.READ_FAILURE,
            },
        )
        with self.assertRaises(TypeError):
            self.state(classification="read_failure")

    def test_stage2_complete_matching_handoff_is_explicitly_accepted(self):
        state = self.state()
        handoff = RtssDegradedHandoff(state, "lifecycle-owner")
        recipient = RtssOwnershipToken(
            self.transaction,
            self.generation,
            8,
            11,
            "lifecycle-owner",
        )
        result = RtssHandoffResult(
            handoff,
            RtssHandoffDecision.ACCEPTED,
            "recipient accepted complete unresolved responsibility",
            recipient,
        )
        release = RtssOwnershipRelease(
            self.owner,
            RtssOwnershipReleaseReason.ACCEPTED_HANDOFF,
            handoff=result,
        )

        self.assertTrue(result.ownership_released)
        self.assertIs(release.handoff, result)

    def test_stage2_rejected_handoff_retains_ownership_and_cannot_release(self):
        handoff = RtssDegradedHandoff(self.state(), "lifecycle-owner")
        result = RtssHandoffResult(
            handoff,
            RtssHandoffDecision.REJECTED,
            "recipient rejected responsibility",
        )

        self.assertFalse(result.ownership_released)
        self.assertTrue(handoff.degraded_state.ownership_retained)
        with self.assertRaisesRegex(ValueError, "cannot release"):
            RtssOwnershipRelease(
                self.owner,
                RtssOwnershipReleaseReason.ACCEPTED_HANDOFF,
                handoff=result,
            )

    def test_stage2_handoff_requires_defined_recipient_and_explicit_decision(self):
        with self.assertRaisesRegex(ValueError, "must not be empty"):
            RtssDegradedHandoff(self.state(), "")
        handoff = RtssDegradedHandoff(self.state(), "lifecycle-owner")
        with self.assertRaises(TypeError):
            RtssHandoffResult(
                handoff,
                None,
                "missing explicit acceptance",
            )
        with self.assertRaisesRegex(ValueError, "recipient ownership"):
            RtssHandoffResult(
                handoff,
                RtssHandoffDecision.ACCEPTED,
                "acceptance without ownership proof",
            )

    def test_stage2_handoff_rejects_cross_profile_and_generation_transfer(self):
        handoff = RtssDegradedHandoff(self.state(), "lifecycle-owner")
        generation_changes = (
            replace(
                self.generation,
                profile_identity=CanonicalProfileIdentity.application(
                    "other.exe"
                ),
            ),
            replace(self.generation, application_generation=99),
            replace(self.generation, session_generation=99),
            replace(self.generation, profile_generation=99),
            replace(self.generation, source_generation=99),
        )
        for generation in generation_changes:
            with self.subTest(generation=generation):
                recipient = RtssOwnershipToken(
                    self.transaction,
                    generation,
                    8,
                    11,
                    "lifecycle-owner",
                )
                with self.assertRaisesRegex(ValueError, "generation"):
                    RtssHandoffResult(
                        handoff,
                        RtssHandoffDecision.ACCEPTED,
                        "invalid cross-generation acceptance",
                        recipient,
                    )

    def test_stage2_handoff_rejects_backend_capability_and_recipient_mismatch(self):
        handoff = RtssDegradedHandoff(self.state(), "lifecycle-owner")
        changes = (
            ({"backend_generation": 99}, "backend epoch"),
            ({"capability_generation": 99}, "capability generation"),
            ({"holder": "other-owner"}, "defined recipient"),
            (
                {
                    "transaction_identity": RtssTransactionIdentity(
                        "transaction-2"
                    )
                },
                "transaction identity",
            ),
        )
        for token_changes, message in changes:
            with self.subTest(message=message):
                recipient = replace(
                    RtssOwnershipToken(
                        self.transaction,
                        self.generation,
                        8,
                        11,
                        "lifecycle-owner",
                    ),
                    **token_changes,
                )
                with self.assertRaisesRegex(ValueError, message):
                    RtssHandoffResult(
                        handoff,
                        RtssHandoffDecision.ACCEPTED,
                        "invalid recipient attribution",
                        recipient,
                    )

    def test_stage2_exact_matching_restoration_can_release_ownership(self):
        capture = CapturedProfileState(
            self.generation,
            7,
            True,
            RationalCap(60, 1),
            stored_cap=RtssStoredCapEvidence.available(120, 2),
        )
        readback = RtssReadback(
            RtssOutcome.VERIFIED,
            self.generation,
            True,
            RationalCap(60, 1),
            backend_generation=7,
            stored_cap=RtssStoredCapEvidence.available(120, 2),
        )
        restore = RtssRestoreResult(
            RtssOutcome.VERIFIED,
            self.generation,
            readback=readback,
            captured_state=capture,
        )
        release = RtssOwnershipRelease(
            self.owner,
            RtssOwnershipReleaseReason.EXACT_RESTORATION,
            restoration=restore,
            restoration_capability_generation=11,
        )

        self.assertIs(release.restoration, restore)
        with self.assertRaisesRegex(ValueError, "capability generation"):
            RtssOwnershipRelease(
                self.owner,
                RtssOwnershipReleaseReason.EXACT_RESTORATION,
                restoration=restore,
                restoration_capability_generation=99,
            )


if __name__ == "__main__":
    unittest.main()
