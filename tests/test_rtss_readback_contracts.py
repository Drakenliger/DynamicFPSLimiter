"""RTSS Stage 2 prerequisite readback, evidence, and ownership contracts."""

from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError, replace
from enum import Enum

from src.core import rtss_contracts
from src.core.rtss_contracts import (
    RTSS_READBACK_FAILURE_STEPS,
    RTSS_READBACK_OUTCOMES,
    RTSS_STORED_CAP_NOT_REQUESTED,
    CanonicalProfileIdentity,
    CapturedProfileState,
    ProfileKind,
    RationalCap,
    RtssApplyRequest,
    RtssApplyResult,
    RtssCapabilityEvidence,
    RtssConflictEvidence,
    RtssDegradedClassification,
    RtssDegradedFieldAccounting,
    RtssDegradedHandoff,
    RtssDegradedState,
    RtssDenominatorStrategy,
    RtssDiagnostic,
    RtssExactRestorationProof,
    RtssFailureStep,
    RtssFieldAvailability,
    RtssGeneration,
    RtssHandoffDecision,
    RtssHandoffResult,
    RtssOperationEvidence,
    RtssOperationState,
    RtssOutcome,
    RtssOwnedField,
    RtssOwnershipRelease,
    RtssOwnershipReleaseReason,
    RtssOwnershipToken,
    RtssReadback,
    RtssRestoreResult,
    RtssReadFailureDiagnostic,
    RtssStoredCapEvidence,
    RtssStoredCapStatus,
    RtssStoredFieldEvidence,
    RtssStoredFieldKind,
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


def _operation_evidence(
    operation: RtssOwnedField,
    generation: RtssGeneration,
    *,
    backend_generation: int,
    result: bool | None,
) -> RtssOperationEvidence:
    return RtssOperationEvidence(
        operation,
        generation,
        backend_generation,
        True,
        result,
        None if result is True else RtssDiagnostic(
            f"{operation.value}_uncertain",
            f"{operation.value} result was not verified",
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
        asymmetric = RtssStoredCapEvidence(
            RtssStoredFieldEvidence(
                RtssFieldAvailability.AVAILABLE,
                120,
            ),
            RtssStoredFieldEvidence(
                RtssFieldAvailability.READ_FAILED,
                diagnostic=RtssReadFailureDiagnostic(
                    RtssStoredFieldKind.DENOMINATOR,
                    "denominator_read_failed",
                ),
            ),
        )
        self.assertIs(asymmetric.status, RtssStoredCapStatus.INCONSISTENT)
        self.assertTrue(asymmetric.requested)
        self.assertTrue(asymmetric.unresolved)
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


class StoredEvidenceDiagnosticTests(unittest.TestCase):
    def test_S2_EVIDENCE_IMPL_001_read_failure_requires_typed_diagnostic(self):
        with self.assertRaisesRegex(ValueError, "typed diagnostic"):
            RtssStoredFieldEvidence(RtssFieldAvailability.READ_FAILED)
        with self.assertRaisesRegex(ValueError, "must not be empty"):
            RtssReadFailureDiagnostic(RtssStoredFieldKind.NUMERATOR, "")
        with self.assertRaisesRegex(ValueError, "must not be empty"):
            RtssReadFailureDiagnostic(
                RtssStoredFieldKind.NUMERATOR,
                "read_failed",
                "",
            )

    def test_S2_EVIDENCE_IMPL_001_diagnostic_is_prohibited_when_incompatible(self):
        diagnostic = RtssReadFailureDiagnostic(
            RtssStoredFieldKind.NUMERATOR,
            "read_failed",
        )
        for availability in (
            RtssFieldAvailability.AVAILABLE,
            RtssFieldAvailability.NOT_REQUESTED,
            RtssFieldAvailability.UNSUPPORTED,
            RtssFieldAvailability.VERIFIED_ABSENT,
        ):
            with self.subTest(availability=availability):
                value = 1 if availability is RtssFieldAvailability.AVAILABLE else None
                with self.assertRaisesRegex(ValueError, "only valid"):
                    RtssStoredFieldEvidence(
                        availability,
                        value,
                        diagnostic,
                    )

    def test_S2_EVIDENCE_IMPL_001_failures_are_field_specific_and_immutable(self):
        evidence = RtssStoredCapEvidence.read_failed(
            numerator_code="api_num",
            denominator_code="file_den",
            numerator_message="numerator API read failed",
            denominator_message="denominator file read failed",
        )

        self.assertIs(
            evidence.numerator.diagnostic.field,
            RtssStoredFieldKind.NUMERATOR,
        )
        self.assertIs(
            evidence.denominator.diagnostic.field,
            RtssStoredFieldKind.DENOMINATOR,
        )
        self.assertNotEqual(
            evidence.numerator.diagnostic.code,
            evidence.denominator.diagnostic.code,
        )
        with self.assertRaises(FrozenInstanceError):
            evidence.numerator.diagnostic.code = "changed"

    def test_S2_EVIDENCE_IMPL_001_failed_evidence_rejects_value_and_raw_types(self):
        diagnostic = RtssReadFailureDiagnostic(
            RtssStoredFieldKind.NUMERATOR,
            "read_failed",
        )
        with self.assertRaisesRegex(ValueError, "must not contain"):
            RtssStoredFieldEvidence(
                RtssFieldAvailability.READ_FAILED,
                120,
                diagnostic,
            )
        with self.assertRaises(TypeError):
            RtssReadFailureDiagnostic("numerator", "read_failed")
        with self.assertRaises(TypeError):
            RtssStoredFieldEvidence("read_failed")
        with self.assertRaises(TypeError):
            RtssStoredFieldEvidence(RtssFieldAvailability.AVAILABLE, True)
        failed = RtssStoredFieldEvidence(
            RtssFieldAvailability.READ_FAILED,
            diagnostic=diagnostic,
        )
        with self.assertRaisesRegex(ValueError, "typed diagnostic"):
            replace(failed, diagnostic=None)


class OwnershipProofRegressionTests(unittest.TestCase):
    def setUp(self):
        self.transaction = RtssTransactionIdentity("tx-a")
        self.identity = CanonicalProfileIdentity.application("game.exe")
        self.generation = RtssGeneration(1, 2, 3, self.identity, 4)
        self.capture = CapturedProfileState(
            self.generation,
            7,
            True,
            RationalCap(60, 1),
            stored_cap=RtssStoredCapEvidence.available(120, 2),
        )
        self.readback = RtssReadback(
            RtssOutcome.VERIFIED,
            self.generation,
            True,
            RationalCap(60, 1),
            backend_generation=7,
            stored_cap=RtssStoredCapEvidence.available(120, 2),
        )
        self.restore = RtssRestoreResult(
            RtssOutcome.VERIFIED,
            self.generation,
            readback=self.readback,
            captured_state=self.capture,
            transaction_identity=self.transaction,
        )
        self.capability = RtssCapabilityEvidence(
            self.transaction,
            self.generation,
            7,
            11,
        )
        self.owner = RtssOwnershipToken(
            self.transaction,
            self.capture,
            self.capability,
            "session-owner",
        )
        self.proof = RtssExactRestorationProof(self.owner, self.restore)

    def _owner_for_capture(
        self,
        capture: CapturedProfileState,
        *,
        transaction: RtssTransactionIdentity | None = None,
        capability_generation: int = 11,
    ) -> RtssOwnershipToken:
        transaction = transaction or self.transaction
        capability = RtssCapabilityEvidence(
            transaction,
            capture.generation,
            capture.backend_generation,
            capability_generation,
        )
        return RtssOwnershipToken(
            transaction,
            capture,
            capability,
            "session-owner",
        )

    def test_S2_OWNERSHIP_IMPL_001_restore_result_cannot_release_two_transactions(self):
        other_transaction = RtssTransactionIdentity("tx-b")
        other_owner = self._owner_for_capture(
            self.capture,
            transaction=other_transaction,
        )

        with self.assertRaisesRegex(ValueError, "transaction identity"):
            RtssExactRestorationProof(other_owner, self.restore)
        release = RtssOwnershipRelease(
            self.owner,
            RtssOwnershipReleaseReason.EXACT_RESTORATION,
            restoration_proof=self.proof,
        )
        self.assertIs(release.restoration, self.restore)

    def test_S2_OWNERSHIP_IMPL_001_same_generations_different_capture_rejected(self):
        different_capture = replace(
            self.capture,
            cap=RationalCap(61, 1),
            stored_cap=RtssStoredCapEvidence.available(122, 2),
        )
        different_owner = self._owner_for_capture(different_capture)

        with self.assertRaisesRegex(ValueError, "exact captured state"):
            RtssExactRestorationProof(different_owner, self.restore)

    def test_S2_OWNERSHIP_IMPL_001_copied_capability_marker_rejected(self):
        other_transaction = RtssTransactionIdentity("tx-b")
        with self.assertRaisesRegex(ValueError, "match the transaction"):
            RtssOwnershipToken(
                other_transaction,
                self.capture,
                self.capability,
                "session-owner",
            )
        different_capability_owner = self._owner_for_capture(
            self.capture,
            capability_generation=12,
        )
        with self.assertRaisesRegex(ValueError, "different ownership"):
            RtssOwnershipRelease(
                different_capability_owner,
                RtssOwnershipReleaseReason.EXACT_RESTORATION,
                restoration_proof=self.proof,
            )

    def test_S2_OWNERSHIP_IMPL_001_proof_from_another_owner_is_not_reusable(self):
        other_owner = replace(self.owner, holder="other-holder")
        with self.assertRaisesRegex(ValueError, "different ownership"):
            RtssOwnershipRelease(
                other_owner,
                RtssOwnershipReleaseReason.EXACT_RESTORATION,
                restoration_proof=self.proof,
            )

    def test_S2_OWNERSHIP_IMPL_001_profile_identity_and_kind_mismatch_rejected(self):
        identities = (
            CanonicalProfileIdentity.application("other.exe"),
            CanonicalProfileIdentity.global_profile(),
        )
        for identity in identities:
            with self.subTest(identity=identity):
                generation = replace(
                    self.generation,
                    profile_identity=identity,
                )
                capture = replace(self.capture, generation=generation)
                owner = self._owner_for_capture(capture)
                with self.assertRaisesRegex(ValueError, "exact captured state"):
                    RtssExactRestorationProof(owner, self.restore)

    def test_S2_OWNERSHIP_IMPL_001_each_generation_mismatch_rejected(self):
        for dimension in (
            "application_generation",
            "session_generation",
            "profile_generation",
            "source_generation",
        ):
            with self.subTest(dimension=dimension):
                generation = replace(
                    self.generation,
                    **{dimension: 99},
                )
                capture = replace(self.capture, generation=generation)
                owner = self._owner_for_capture(capture)
                with self.assertRaisesRegex(ValueError, "exact captured state"):
                    RtssExactRestorationProof(owner, self.restore)

    def test_S2_OWNERSHIP_IMPL_001_backend_epoch_and_representation_are_exact(self):
        stale_capture = replace(self.capture, backend_generation=8)
        stale_owner = self._owner_for_capture(stale_capture)
        with self.assertRaisesRegex(ValueError, "exact captured state"):
            RtssExactRestorationProof(stale_owner, self.restore)

        normalized = replace(
            self.readback,
            stored_cap=RtssStoredCapEvidence.available(60, 1),
        )
        with self.assertRaisesRegex(ValueError, "representation"):
            RtssRestoreResult(
                RtssOutcome.VERIFIED,
                self.generation,
                readback=normalized,
                captured_state=self.capture,
                transaction_identity=self.transaction,
            )

    def test_S2_OWNERSHIP_IMPL_001_incomplete_or_marker_only_release_rejected(self):
        with self.assertRaisesRegex(ValueError, "immutable proof"):
            RtssOwnershipRelease(
                self.owner,
                RtssOwnershipReleaseReason.EXACT_RESTORATION,
            )
        with self.assertRaises(TypeError):
            RtssOwnershipRelease(
                self.owner,
                "exact_restoration",
                restoration_proof=self.proof,
            )
        with self.assertRaises(TypeError):
            RtssCapabilityEvidence(
                self.transaction,
                self.generation,
                True,
                11,
            )


class ExactApplicabilityRegressionTests(unittest.TestCase):
    def setUp(self):
        self.transaction = RtssTransactionIdentity("tx-applicability")
        self.generation = RtssGeneration(
            1,
            2,
            3,
            CanonicalProfileIdentity.application("game.exe"),
            4,
        )
        self.request = RtssApplyRequest(
            self.generation,
            RationalCap(59, 1),
            RtssDenominatorStrategy.PROFILE_FILE,
            reason="applicability regression",
        )

    def _state(
        self,
        stored_cap: RtssStoredCapEvidence,
        classification: RtssDegradedClassification,
    ) -> RtssDegradedState:
        capture = CapturedProfileState(
            self.generation,
            7,
            True,
            RationalCap(60, 1),
            stored_cap=stored_cap,
        )
        capability = RtssCapabilityEvidence(
            self.transaction,
            self.generation,
            7,
            11,
        )
        owner = RtssOwnershipToken(
            self.transaction,
            capture,
            capability,
            "session-owner",
        )
        return RtssDegradedState(
            self.transaction,
            self.request,
            capture,
            self.generation,
            owner,
            classification,
            "exact applicability regression",
        )

    def test_S2_DEGRADED_IMPL_001_failed_requested_pair_remains_applicable(self):
        state = self._state(
            RtssStoredCapEvidence.read_failed(
                numerator_code="num_failed",
                denominator_code="den_failed",
            ),
            RtssDegradedClassification.READ_FAILURE,
        )
        self.assertTrue(
            {
                RtssOwnedField.EXACT_STORED_NUMERATOR,
                RtssOwnedField.EXACT_STORED_DENOMINATOR,
            }
            <= state.accounting.unresolved_fields
        )
        with self.assertRaisesRegex(ValueError, "complete pre-mutation capture"):
            state.captured_state.require_pre_mutation_capture()

    def test_S2_DEGRADED_IMPL_001_unsupported_requested_pair_remains_applicable(self):
        state = self._state(
            RtssStoredCapEvidence.unavailable(
                RtssFieldAvailability.UNSUPPORTED
            ),
            RtssDegradedClassification.EVIDENCE_UNAVAILABLE,
        )
        self.assertTrue(
            {
                RtssOwnedField.EXACT_STORED_NUMERATOR,
                RtssOwnedField.EXACT_STORED_DENOMINATOR,
            }
            <= state.accounting.unresolved_fields
        )
        self.assertFalse(state.captured_state.pre_mutation_capture_admissible)

    def test_S2_DEGRADED_IMPL_001_asymmetric_pair_keeps_both_responsibilities(self):
        asymmetric = RtssStoredCapEvidence(
            RtssStoredFieldEvidence(RtssFieldAvailability.AVAILABLE, 120),
            RtssStoredFieldEvidence(
                RtssFieldAvailability.READ_FAILED,
                diagnostic=RtssReadFailureDiagnostic(
                    RtssStoredFieldKind.DENOMINATOR,
                    "den_failed",
                ),
            ),
        )
        state = self._state(
            asymmetric,
            RtssDegradedClassification.READ_FAILURE,
        )
        self.assertIs(asymmetric.status, RtssStoredCapStatus.INCONSISTENT)
        self.assertTrue(
            {
                RtssOwnedField.EXACT_STORED_NUMERATOR,
                RtssOwnedField.EXACT_STORED_DENOMINATOR,
            }
            <= state.accounting.applicable_fields
        )
        self.assertFalse(state.captured_state.pre_mutation_capture_admissible)

    def test_S2_DEGRADED_IMPL_001_not_requested_and_captured_are_distinct(self):
        unrequested = self._state(
            RTSS_STORED_CAP_NOT_REQUESTED,
            RtssDegradedClassification.UNRESOLVED_MUTATION,
        )
        captured = self._state(
            RtssStoredCapEvidence.available(120, 2),
            RtssDegradedClassification.UNRESOLVED_MUTATION,
        )

        self.assertNotIn(
            RtssOwnedField.EXACT_STORED_NUMERATOR,
            unrequested.accounting.applicable_fields,
        )
        self.assertIn(
            RtssOwnedField.EXACT_STORED_NUMERATOR,
            captured.accounting.applicable_fields,
        )
        self.assertTrue(captured.captured_state.pre_mutation_capture_admissible)


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
        self.capability = RtssCapabilityEvidence(
            self.transaction,
            self.generation,
            7,
            11,
        )
        self.owner = RtssOwnershipToken(
            self.transaction,
            self.captured,
            self.capability,
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
            "current_owner": self.owner,
            "classification": RtssDegradedClassification.READ_FAILURE,
            "reason": "readback failed after possible mutation",
            "save_evidence": _operation_evidence(
                RtssOwnedField.SAVE,
                self.generation,
                backend_generation=8,
                result=None,
            ),
            "activation_evidence": _operation_evidence(
                RtssOwnedField.ACTIVATION,
                self.generation,
                backend_generation=8,
                result=None,
            ),
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
        absent_capability = replace(
            self.capability,
            generation=absent_capture.generation,
        )
        absent_owner = RtssOwnershipToken(
            self.transaction,
            absent_capture,
            absent_capability,
            "session-owner",
        )
        absent = self.state(
            captured_state=absent_capture,
            current_owner=absent_owner,
            classification=RtssDegradedClassification.UNRESOLVED_MUTATION,
            save_evidence=None,
            activation_evidence=None,
        )

        represented = (
            existing.accounting.applicable_fields
            | absent.accounting.applicable_fields
        )
        self.assertEqual(represented, frozenset(RtssOwnedField))

    def test_stage2_degraded_accounting_rejects_incomplete_and_double_states(self):
        with self.assertRaises(TypeError):
            RtssDegradedFieldAccounting(
                frozenset(self.applicable),
                frozenset(),
                (),
            )
        with self.assertRaises(TypeError):
            RtssUnresolvedFieldEvidence(
                RtssOwnedField.EFFECTIVE_CAP,
                RtssFieldAvailability.AVAILABLE,
                "fabricated observation",
            )

    def test_stage2_degraded_state_rejects_claimed_resolution_without_evidence(self):
        state = self.state()
        with self.assertRaises(TypeError):
            replace(
                state.accounting,
                resolved_fields=state.accounting.applicable_fields,
            )

    def test_stage2_unowned_and_unrequested_fields_do_not_become_unresolved(self):
        capture = CapturedProfileState(
            self.generation,
            7,
            True,
            RationalCap(60, 1),
        )
        capability = replace(self.capability, generation=capture.generation)
        owner = RtssOwnershipToken(
            self.transaction,
            capture,
            capability,
            "session-owner",
        )
        state = self.state(
            captured_state=capture,
            current_owner=owner,
            classification=RtssDegradedClassification.UNRESOLVED_MUTATION,
            save_evidence=None,
            activation_evidence=None,
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
                save_evidence = _operation_evidence(
                    RtssOwnedField.SAVE,
                    self.generation,
                    backend_generation=7,
                    result=(
                        True
                        if save_state is RtssOperationState.VERIFIED
                        else None
                    ),
                )
                activation_evidence = _operation_evidence(
                    RtssOwnedField.ACTIVATION,
                    self.generation,
                    backend_generation=7,
                    result=(
                        True
                        if activation_state is RtssOperationState.VERIFIED
                        else None
                    ),
                )
                state = self.state(
                    save_evidence=save_evidence,
                    activation_evidence=activation_evidence,
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
        with self.assertRaisesRegex(ValueError, "captured generation"):
            self.state(
                captured_state=replace(
                    self.captured,
                    generation=replace(
                        self.generation,
                        profile_generation=99,
                    ),
                )
            )
        with self.assertRaisesRegex(ValueError, "evidence generation"):
            self.state(
                evidence_generation=replace(
                    self.generation,
                    source_generation=99,
                )
            )
        different_capture = replace(
            self.captured,
            cap=RationalCap(61, 1),
            stored_cap=RtssStoredCapEvidence.available(122, 2),
        )
        different_owner = RtssOwnershipToken(
            self.transaction,
            different_capture,
            self.capability,
            "session-owner",
        )
        with self.assertRaisesRegex(ValueError, "exact captured state"):
            self.state(current_owner=different_owner)
        with self.assertRaisesRegex(ValueError, "capability evidence"):
            replace(
                self.owner,
                transaction_identity=RtssTransactionIdentity("transaction-2"),
            )

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
        recipient = replace(self.owner, holder="lifecycle-owner")
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
                capture = replace(self.captured, generation=generation)
                capability = RtssCapabilityEvidence(
                    self.transaction,
                    generation,
                    7,
                    11,
                )
                recipient = RtssOwnershipToken(
                    self.transaction,
                    capture,
                    capability,
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
        wrong_backend_capture = replace(self.captured, backend_generation=99)
        wrong_backend = RtssOwnershipToken(
            self.transaction,
            wrong_backend_capture,
            replace(self.capability, backend_generation=99),
            "lifecycle-owner",
        )
        wrong_capability = RtssOwnershipToken(
            self.transaction,
            self.captured,
            replace(self.capability, capability_generation=99),
            "lifecycle-owner",
        )
        wrong_transaction = RtssTransactionIdentity("transaction-2")
        wrong_transaction_owner = RtssOwnershipToken(
            wrong_transaction,
            self.captured,
            replace(
                self.capability,
                transaction_identity=wrong_transaction,
            ),
            "lifecycle-owner",
        )
        changes = (
            (wrong_backend, "exact owned capture"),
            (wrong_capability, "capability evidence"),
            (replace(self.owner, holder="other-owner"), "defined recipient"),
            (wrong_transaction_owner, "transaction identity"),
        )
        for recipient, message in changes:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    RtssHandoffResult(
                        handoff,
                        RtssHandoffDecision.ACCEPTED,
                        "invalid recipient attribution",
                        recipient,
                    )

    def test_S2_DEGRADED_IMPL_002_external_conflict_requires_evidence(self):
        with self.assertRaisesRegex(ValueError, "not justified"):
            self.state(
                classification=RtssDegradedClassification.EXTERNAL_CONFLICT
            )
        conflict = RtssConflictEvidence(
            RtssOwnedField.PROFILE_REVISION,
            self.generation,
            8,
            "revision-1",
            "revision-2",
        )
        with self.assertRaisesRegex(ValueError, "not justified"):
            self.state(
                conflict_evidence=conflict,
                classification=RtssDegradedClassification.READ_FAILURE,
            )
        state = self.state(
            conflict_evidence=conflict,
            classification=RtssDegradedClassification.EXTERNAL_CONFLICT,
        )
        self.assertIs(state.conflict_evidence, conflict)

    def test_S2_DEGRADED_IMPL_002_latest_backend_is_derived_from_observations(self):
        with self.assertRaises(TypeError):
            self.state(latest_backend_generation=99)
        stale_save = _operation_evidence(
            RtssOwnedField.SAVE,
            self.generation,
            backend_generation=6,
            result=None,
        )
        with self.assertRaisesRegex(ValueError, "cannot predate"):
            self.state(save_evidence=stale_save)
        self.assertEqual(self.state().latest_backend_generation, 8)

    def test_S2_DEGRADED_IMPL_002_operation_success_requires_operation_evidence(self):
        for operation in (
            RtssOwnedField.SAVE,
            RtssOwnedField.ACTIVATION,
        ):
            with self.subTest(operation=operation):
                with self.assertRaisesRegex(ValueError, "cannot claim"):
                    RtssOperationEvidence(
                        operation,
                        self.generation,
                        7,
                        False,
                        True,
                    )
        with self.assertRaises(TypeError):
            self.state(save_state=RtssOperationState.VERIFIED)
        with self.assertRaises(TypeError):
            self.state(activation_state=RtssOperationState.VERIFIED)

    def test_S2_DEGRADED_IMPL_002_false_verified_absence_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "must not have a cap"):
            RtssReadback(
                RtssOutcome.VERIFIED,
                self.generation,
                False,
                RationalCap(60, 1),
                backend_generation=7,
            )

    def test_S2_DEGRADED_IMPL_002_requested_fields_cannot_be_omitted(self):
        state = self.state()
        self.assertTrue(
            {
                RtssOwnedField.EXACT_STORED_NUMERATOR,
                RtssOwnedField.EXACT_STORED_DENOMINATOR,
            }
            <= state.accounting.applicable_fields
        )
        with self.assertRaises(TypeError):
            replace(
                state.accounting,
                applicable_fields=(
                    state.accounting.applicable_fields
                    - {RtssOwnedField.EXACT_STORED_NUMERATOR}
                ),
            )

    def test_S2_DEGRADED_IMPL_002_empty_degraded_state_is_rejected(self):
        readback = RtssReadback(
            RtssOutcome.VERIFIED,
            self.generation,
            True,
            RationalCap(60, 1),
            limiter_flags=4,
            profile_revision="revision-1",
            backend_generation=7,
            profile_revision_availability=RtssFieldAvailability.AVAILABLE,
            profile_document_availability=RtssFieldAvailability.AVAILABLE,
            profile_document=b"Limit=120\nLimitDenominator=2\n",
            stored_cap=RtssStoredCapEvidence.available(120, 2),
        )
        with self.assertRaisesRegex(ValueError, "at least one unresolved"):
            self.state(
                readback=readback,
                save_evidence=None,
                activation_evidence=None,
                classification=RtssDegradedClassification.UNRESOLVED_MUTATION,
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
            transaction_identity=self.transaction,
        )
        capability = RtssCapabilityEvidence(
            self.transaction,
            self.generation,
            7,
            11,
        )
        owner = RtssOwnershipToken(
            self.transaction,
            capture,
            capability,
            "session-owner",
        )
        proof = RtssExactRestorationProof(owner, restore)
        release = RtssOwnershipRelease(
            owner,
            RtssOwnershipReleaseReason.EXACT_RESTORATION,
            restoration_proof=proof,
        )

        self.assertIs(release.restoration, restore)
        with self.assertRaisesRegex(ValueError, "different ownership"):
            RtssOwnershipRelease(
                self.owner,
                RtssOwnershipReleaseReason.EXACT_RESTORATION,
                restoration_proof=proof,
            )


class EnumAliasHardeningTests(unittest.TestCase):
    def test_S1_READBACK_ALIAS_001_members_and_iteration_are_both_exhaustive(self):
        relevant_enums = (
            ProfileKind,
            RtssDenominatorStrategy,
            RtssOutcome,
            RtssFailureStep,
            RtssFieldAvailability,
            RtssOwnedField,
            RtssOperationState,
            RtssDegradedClassification,
            RtssHandoffDecision,
            RtssOwnershipReleaseReason,
            RtssStoredFieldKind,
            RtssStoredCapStatus,
        )
        for enum_type in relevant_enums:
            with self.subTest(enum_type=enum_type.__name__):
                members = enum_type.__members__
                self.assertEqual(len(members), len(list(enum_type)))
                self.assertEqual(list(members.values()), list(enum_type))
                self.assertEqual(
                    len({member.value for member in members.values()}),
                    len(members),
                )

    def test_S1_READBACK_ALIAS_001_members_check_detects_iteration_alias_gap(self):
        class AliasProbe(Enum):
            VALUE = "value"
            VALUE_ALIAS = "value"

        self.assertEqual(len(list(AliasProbe)), 1)
        self.assertEqual(len(AliasProbe.__members__), 2)
        self.assertNotEqual(
            list(AliasProbe.__members__.values()),
            list(AliasProbe),
        )


if __name__ == "__main__":
    unittest.main()
