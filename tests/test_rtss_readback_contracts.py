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
    RtssReadbackEvidence,
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
    ownership: RtssOwnershipToken,
    *,
    result: bool | None,
    readback_evidence: RtssReadbackEvidence | None = None,
) -> RtssOperationEvidence:
    if result is True:
        if readback_evidence is None:
            raise ValueError("verified helper evidence requires readback")
        return RtssOperationEvidence.verified(
            operation,
            ownership,
            readback_evidence,
        )
    return RtssOperationEvidence.uncertain(
        operation,
        ownership,
        RtssDiagnostic(
            f"{operation.value}_uncertain",
            f"{operation.value} result was not verified",
        ),
        readback_evidence=readback_evidence,
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
        state = RtssDegradedState(
            self.request,
            owner,
            "exact applicability regression",
        )
        self.assertIs(state.classification, classification)
        return state

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
        owner = changes.get("current_owner", self.owner)
        values = {
            "request": self.request,
            "current_owner": owner,
            "reason": "readback failed after possible mutation",
            "save_evidence": _operation_evidence(
                RtssOwnedField.SAVE,
                owner,
                result=None,
            ),
            "activation_evidence": _operation_evidence(
                RtssOwnedField.ACTIVATION,
                owner,
                result=None,
            ),
        }
        values.update(changes)
        return RtssDegradedState(**values)

    def matching_readback_evidence(
        self,
        ownership: RtssOwnershipToken | None = None,
    ) -> RtssReadbackEvidence:
        ownership = ownership or self.owner
        captured = ownership.captured_state
        readback = RtssReadback(
            RtssOutcome.VERIFIED,
            captured.generation,
            captured.profile_existed,
            captured.cap,
            limiter_flags=captured.limiter_flags,
            profile_revision=captured.profile_revision,
            backend_generation=captured.backend_generation,
            profile_revision_availability=(
                captured.profile_revision_availability
            ),
            profile_document_availability=(
                captured.profile_document_availability
            ),
            profile_document=captured.profile_document,
            profile_document_sha256=captured.profile_document_sha256,
            stored_cap=captured.stored_cap,
        )
        return RtssReadbackEvidence.bind(ownership, readback)

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
            current_owner=absent_owner,
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
            current_owner=owner,
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
                readback_evidence = self.matching_readback_evidence()
                save_evidence = _operation_evidence(
                    RtssOwnedField.SAVE,
                    self.owner,
                    result=(
                        True
                        if save_state is RtssOperationState.VERIFIED
                        else None
                    ),
                    readback_evidence=(
                        readback_evidence
                        if save_state is RtssOperationState.VERIFIED
                        else None
                    ),
                )
                activation_evidence = _operation_evidence(
                    RtssOwnedField.ACTIVATION,
                    self.owner,
                    result=(
                        True
                        if activation_state is RtssOperationState.VERIFIED
                        else None
                    ),
                    readback_evidence=(
                        readback_evidence
                        if activation_state is RtssOperationState.VERIFIED
                        else None
                    ),
                )
                state = self.state(
                    readback_evidence=readback_evidence,
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
        with self.assertRaises((FrozenInstanceError, TypeError)):
            state.ownership_retained = False
        with self.assertRaises(TypeError):
            self.state(ownership_retained=False)

    def test_stage2_degraded_state_rejects_incomplete_attribution(self):
        changed_generation = replace(
            self.generation,
            profile_generation=99,
        )
        changed_capture = replace(
            self.captured,
            generation=changed_generation,
        )
        changed_capability = RtssCapabilityEvidence(
            self.transaction,
            changed_generation,
            7,
            11,
        )
        changed_owner = RtssOwnershipToken(
            self.transaction,
            changed_capture,
            changed_capability,
            "session-owner",
        )
        with self.assertRaisesRegex(ValueError, "match the request"):
            self.state(
                current_owner=changed_owner,
                save_evidence=None,
                activation_evidence=None,
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
        readback_evidence = self.matching_readback_evidence()
        with self.assertRaisesRegex(ValueError, "exact transaction owner"):
            self.state(
                current_owner=different_owner,
                readback_evidence=readback_evidence,
                save_evidence=None,
                activation_evidence=None,
            )
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
        with self.assertRaises(TypeError):
            self.state(
                classification=RtssDegradedClassification.EXTERNAL_CONFLICT
            )
        matching = self.matching_readback_evidence()
        conflict_readback = replace(
            matching.readback,
            profile_revision="revision-2",
        )
        conflict_observation = RtssReadbackEvidence.bind(
            self.owner,
            conflict_readback,
        )
        conflict = RtssConflictEvidence.from_readback(
            RtssOwnedField.PROFILE_REVISION,
            self.owner,
            conflict_observation,
        )
        with self.assertRaisesRegex(ValueError, "must be identical"):
            self.state(
                conflict_evidence=conflict,
            )
        state = self.state(
            readback_evidence=conflict_observation,
            conflict_evidence=conflict,
        )
        self.assertIs(state.conflict_evidence, conflict)
        self.assertIs(
            state.classification,
            RtssDegradedClassification.EXTERNAL_CONFLICT,
        )
        with self.assertRaises(TypeError):
            replace(conflict, captured_value="invented")
        with self.assertRaises(TypeError):
            replace(conflict, backend_generation=999)

    def test_S2_DEGRADED_IMPL_002_latest_backend_is_derived_from_observations(self):
        with self.assertRaises(TypeError):
            self.state(latest_backend_generation=99)
        stale_readback = RtssReadback(
            RtssOutcome.FAILED,
            self.generation,
            False,
            None,
            backend_generation=6,
            failure_step=RtssFailureStep.READBACK,
            error="stale observation",
            stored_cap=RtssStoredCapEvidence.read_failed(
                numerator_code="num-failed",
                denominator_code="den-failed",
            ),
        )
        with self.assertRaisesRegex(ValueError, "cannot predate"):
            RtssReadbackEvidence.bind(self.owner, stale_readback)

        future_readback = replace(stale_readback, backend_generation=8)
        future_capability = RtssCapabilityEvidence(
            self.transaction,
            self.generation,
            8,
            12,
        )
        future_observation = RtssReadbackEvidence.bind(
            self.owner,
            future_readback,
            capability_evidence=future_capability,
        )
        state = self.state(
            readback_evidence=future_observation,
            save_evidence=None,
            activation_evidence=None,
        )
        self.assertEqual(state.latest_backend_generation, 8)
        self.assertEqual(state.latest_capability_evidence, future_capability)

    def test_S2_DEGRADED_IMPL_002_operation_success_requires_operation_evidence(self):
        for operation in (
            RtssOwnedField.SAVE,
            RtssOwnedField.ACTIVATION,
        ):
            with self.subTest(operation=operation):
                with self.assertRaises(TypeError):
                    RtssOperationEvidence(
                        operation,
                        self.generation,
                        7,
                        False,
                        True,
                    )
                readback_evidence = self.matching_readback_evidence()
                evidence = RtssOperationEvidence.verified(
                    operation,
                    self.owner,
                    readback_evidence,
                )
                self.assertIs(evidence.state, RtssOperationState.VERIFIED)
                self.assertEqual(evidence.ownership, self.owner)
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
                readback_evidence=RtssReadbackEvidence.bind(
                    self.owner,
                    readback,
                ),
                save_evidence=None,
                activation_evidence=None,
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


class DegradedEvidenceProvenanceRegressionTests(unittest.TestCase):
    def setUp(self):
        self.transaction = RtssTransactionIdentity("tx-provenance-a")
        self.other_transaction = RtssTransactionIdentity("tx-provenance-b")
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
            reason="provenance regression",
        )
        self.capture = CapturedProfileState(
            self.generation,
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
            self.capture,
            self.capability,
            "session-owner",
        )

    def owner_for(
        self,
        transaction: RtssTransactionIdentity,
        *,
        generation: RtssGeneration | None = None,
        capture: CapturedProfileState | None = None,
        capability_generation: int = 11,
        holder: str = "session-owner",
    ) -> RtssOwnershipToken:
        generation = generation or self.generation
        capture = capture or replace(self.capture, generation=generation)
        capability = RtssCapabilityEvidence(
            transaction,
            generation,
            capture.backend_generation,
            capability_generation,
        )
        return RtssOwnershipToken(
            transaction,
            capture,
            capability,
            holder,
        )

    def matching_readback(
        self,
        *,
        generation: RtssGeneration | None = None,
        backend_generation: int = 7,
        revision: str = "revision-1",
    ) -> RtssReadback:
        generation = generation or self.generation
        return RtssReadback(
            RtssOutcome.VERIFIED,
            generation,
            True,
            RationalCap(60, 1),
            limiter_flags=4,
            profile_revision=revision,
            backend_generation=backend_generation,
            profile_revision_availability=RtssFieldAvailability.AVAILABLE,
            profile_document_availability=RtssFieldAvailability.AVAILABLE,
            profile_document=b"Limit=120\nLimitDenominator=2\n",
            stored_cap=RtssStoredCapEvidence.available(120, 2),
        )

    def failed_readback(
        self,
        stored_cap: RtssStoredCapEvidence,
        *,
        backend_generation: int = 7,
    ) -> RtssReadback:
        return RtssReadback(
            RtssOutcome.FAILED,
            self.generation,
            False,
            None,
            backend_generation=backend_generation,
            failure_step=RtssFailureStep.READBACK,
            error="read failed",
            profile_revision_availability=RtssFieldAvailability.READ_FAILED,
            profile_document_availability=RtssFieldAvailability.READ_FAILED,
            stored_cap=stored_cap,
        )

    def state(
        self,
        *,
        owner: RtssOwnershipToken | None = None,
        readback_evidence: RtssReadbackEvidence | None = None,
        save_evidence: RtssOperationEvidence | None = None,
        activation_evidence: RtssOperationEvidence | None = None,
        conflict_evidence: RtssConflictEvidence | None = None,
    ) -> RtssDegradedState:
        return RtssDegradedState(
            self.request,
            owner or self.owner,
            "provenance regression",
            readback_evidence=readback_evidence,
            save_evidence=save_evidence,
            activation_evidence=activation_evidence,
            conflict_evidence=conflict_evidence,
        )

    def test_S2_DEGRADED_IMPL_002_A_failed_complete_pair_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "complete available"):
            self.failed_readback(
                RtssStoredCapEvidence.available(120, 2)
            )

    def test_S2_DEGRADED_IMPL_002_A_unsupported_complete_pair_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "complete available"):
            RtssReadback(
                RtssOutcome.UNSUPPORTED_CAPABILITY,
                self.generation,
                False,
                None,
                backend_generation=7,
                failure_step=RtssFailureStep.CAPABILITY,
                error="unsupported",
                stored_cap=RtssStoredCapEvidence.available(120, 2),
            )

    def test_S2_DEGRADED_IMPL_002_A_verified_complete_pair_is_accepted(self):
        readback = self.matching_readback()

        self.assertTrue(readback.verified)
        self.assertIs(
            readback.stored_cap.status,
            RtssStoredCapStatus.CAPTURED,
        )

    def test_S2_DEGRADED_IMPL_002_A_partial_numerator_remains_partial(self):
        partial = RtssStoredCapEvidence(
            RtssStoredFieldEvidence(RtssFieldAvailability.AVAILABLE, 120),
            RtssStoredFieldEvidence(
                RtssFieldAvailability.READ_FAILED,
                diagnostic=RtssReadFailureDiagnostic(
                    RtssStoredFieldKind.DENOMINATOR,
                    "denominator-failed",
                ),
            ),
        )
        observation = RtssReadbackEvidence.bind(
            self.owner,
            self.failed_readback(partial),
        )
        state = self.state(readback_evidence=observation)
        unresolved = {
            item.field: item.availability
            for item in state.accounting.unresolved_evidence
        }

        self.assertIs(
            unresolved[RtssOwnedField.EXACT_STORED_NUMERATOR],
            RtssFieldAvailability.AVAILABLE,
        )
        self.assertIs(
            unresolved[RtssOwnedField.EXACT_STORED_DENOMINATOR],
            RtssFieldAvailability.READ_FAILED,
        )

    def test_S2_DEGRADED_IMPL_002_A_partial_denominator_remains_partial(self):
        partial = RtssStoredCapEvidence(
            RtssStoredFieldEvidence(
                RtssFieldAvailability.READ_FAILED,
                diagnostic=RtssReadFailureDiagnostic(
                    RtssStoredFieldKind.NUMERATOR,
                    "numerator-failed",
                ),
            ),
            RtssStoredFieldEvidence(RtssFieldAvailability.AVAILABLE, 2),
        )
        observation = RtssReadbackEvidence.bind(
            self.owner,
            self.failed_readback(partial),
        )
        state = self.state(readback_evidence=observation)
        unresolved = {
            item.field: item.availability
            for item in state.accounting.unresolved_evidence
        }

        self.assertIs(
            unresolved[RtssOwnedField.EXACT_STORED_NUMERATOR],
            RtssFieldAvailability.READ_FAILED,
        )
        self.assertIs(
            unresolved[RtssOwnedField.EXACT_STORED_DENOMINATOR],
            RtssFieldAvailability.AVAILABLE,
        )

    def test_S2_DEGRADED_IMPL_002_A_aggregate_failure_controls_other_fields(self):
        failed = self.failed_readback(
            RtssStoredCapEvidence.read_failed(
                numerator_code="numerator-failed",
                denominator_code="denominator-failed",
            )
        )
        state = self.state(
            readback_evidence=RtssReadbackEvidence.bind(self.owner, failed)
        )
        unresolved = {
            item.field: item.availability
            for item in state.accounting.unresolved_evidence
        }

        self.assertIs(
            unresolved[RtssOwnedField.EFFECTIVE_CAP],
            RtssFieldAvailability.READ_FAILED,
        )
        self.assertIs(
            state.classification,
            RtssDegradedClassification.READ_FAILURE,
        )

    def test_S2_DEGRADED_IMPL_002_B_cross_transaction_readback_is_rejected(self):
        observation = RtssReadbackEvidence.bind(
            self.owner,
            self.failed_readback(
                RtssStoredCapEvidence.read_failed(
                    numerator_code="numerator-failed",
                    denominator_code="denominator-failed",
                )
            ),
        )
        other_owner = self.owner_for(self.other_transaction)

        with self.assertRaisesRegex(ValueError, "exact transaction owner"):
            self.state(
                owner=other_owner,
                readback_evidence=observation,
            )

    def test_S2_DEGRADED_IMPL_002_B_replace_cannot_change_readback_transaction(self):
        observation = RtssReadbackEvidence.bind(
            self.owner,
            self.matching_readback(),
        )
        other_owner = self.owner_for(self.other_transaction)

        with self.assertRaises(TypeError):
            replace(observation, ownership=other_owner)

    def test_S2_DEGRADED_IMPL_002_B_readback_binding_mismatches_are_rejected(self):
        wrong_generation = replace(
            self.generation,
            source_generation=99,
        )
        with self.assertRaisesRegex(ValueError, "generation and profile"):
            RtssReadbackEvidence.bind(
                self.owner,
                self.matching_readback(generation=wrong_generation),
            )
        with self.assertRaisesRegex(ValueError, "requires a backend epoch"):
            RtssReadbackEvidence.bind(
                self.owner,
                replace(self.matching_readback(), backend_generation=None),
            )
        with self.assertRaisesRegex(ValueError, "exact owner capability"):
            RtssReadbackEvidence.bind(
                self.owner,
                self.matching_readback(),
                capability_evidence=replace(
                    self.capability,
                    capability_generation=12,
                ),
            )
        advanced_readback = self.failed_readback(
            RtssStoredCapEvidence.read_failed(
                numerator_code="numerator-failed",
                denominator_code="denominator-failed",
            ),
            backend_generation=8,
        )
        capability_mismatches = (
            replace(
                self.capability,
                transaction_identity=self.other_transaction,
                backend_generation=8,
            ),
            replace(
                self.capability,
                generation=wrong_generation,
                backend_generation=8,
            ),
            replace(self.capability, backend_generation=9),
        )
        for capability in capability_mismatches:
            with self.subTest(capability=capability):
                with self.assertRaises(ValueError):
                    RtssReadbackEvidence.bind(
                        self.owner,
                        advanced_readback,
                        capability_evidence=capability,
                    )

    def test_S2_DEGRADED_IMPL_002_B_direct_boolean_operation_is_impossible(self):
        with self.assertRaises(TypeError):
            RtssOperationEvidence(
                RtssOwnedField.SAVE,
                self.generation,
                7,
                True,
                True,
            )

    def test_S2_DEGRADED_IMPL_002_B_trusted_operation_result_is_accepted(self):
        observation = RtssReadbackEvidence.bind(
            self.owner,
            self.matching_readback(),
        )
        operation = RtssOperationEvidence.verified(
            RtssOwnedField.SAVE,
            self.owner,
            observation,
        )
        state = self.state(
            readback_evidence=observation,
            save_evidence=operation,
            activation_evidence=RtssOperationEvidence.uncertain(
                RtssOwnedField.ACTIVATION,
                self.owner,
                RtssDiagnostic("activation-uncertain"),
            ),
        )

        self.assertIs(operation.state, RtssOperationState.VERIFIED)
        self.assertIs(state.save_state, RtssOperationState.VERIFIED)

    def test_S2_DEGRADED_IMPL_002_B_operation_provenance_mismatches_rejected(self):
        observation = RtssReadbackEvidence.bind(
            self.owner,
            self.matching_readback(),
        )
        owners = (
            self.owner_for(self.other_transaction),
            self.owner_for(
                self.transaction,
                generation=replace(
                    self.generation,
                    profile_identity=CanonicalProfileIdentity.application(
                        "other.exe"
                    ),
                ),
            ),
            self.owner_for(
                self.transaction,
                generation=replace(
                    self.generation,
                    profile_identity=CanonicalProfileIdentity.global_profile(),
                ),
            ),
            self.owner_for(
                self.transaction,
                generation=replace(
                    self.generation,
                    session_generation=99,
                ),
            ),
            self.owner_for(
                self.transaction,
                capability_generation=12,
            ),
        )
        for owner in owners:
            with self.subTest(owner=owner):
                with self.assertRaisesRegex(ValueError, "exact owner"):
                    RtssOperationEvidence.verified(
                        RtssOwnedField.SAVE,
                        owner,
                        observation,
                    )

    def test_S2_DEGRADED_IMPL_002_B_operation_type_mismatch_is_rejected(self):
        operation = RtssOperationEvidence.uncertain(
            RtssOwnedField.ACTIVATION,
            self.owner,
            RtssDiagnostic("activation-uncertain"),
        )

        with self.assertRaisesRegex(ValueError, "wrong field"):
            self.state(save_evidence=operation)

    def test_S2_DEGRADED_IMPL_002_B_operation_epoch_cannot_be_injected(self):
        operation = RtssOperationEvidence.uncertain(
            RtssOwnedField.SAVE,
            self.owner,
            RtssDiagnostic("save-uncertain"),
        )

        self.assertEqual(operation.backend_generation, 7)
        with self.assertRaises(TypeError):
            replace(operation, backend_generation=999)

    def test_S2_DEGRADED_IMPL_002_B_unrequested_conflict_is_rejected(self):
        unrequested_capture = replace(
            self.capture,
            stored_cap=RTSS_STORED_CAP_NOT_REQUESTED,
        )
        owner = self.owner_for(
            self.transaction,
            capture=unrequested_capture,
        )
        conflicting_readback = replace(
            self.matching_readback(),
            cap=RationalCap(61, 1),
            stored_cap=RtssStoredCapEvidence.available(122, 2),
        )
        observation = RtssReadbackEvidence.bind(owner, conflicting_readback)

        with self.assertRaisesRegex(ValueError, "requested, applicable, and owned"):
            RtssConflictEvidence.from_readback(
                RtssOwnedField.EXACT_STORED_NUMERATOR,
                owner,
                observation,
            )

    def test_S2_DEGRADED_IMPL_002_B_unowned_conflict_is_rejected(self):
        unowned_capture = replace(
            self.capture,
            profile_revision=None,
            profile_revision_availability=(
                RtssFieldAvailability.NOT_REQUESTED
            ),
        )
        owner = self.owner_for(
            self.transaction,
            capture=unowned_capture,
        )
        observation = RtssReadbackEvidence.bind(
            owner,
            self.matching_readback(revision="revision-2"),
        )

        with self.assertRaisesRegex(ValueError, "requested, applicable, and owned"):
            RtssConflictEvidence.from_readback(
                RtssOwnedField.PROFILE_REVISION,
                owner,
                observation,
            )

    def test_S2_DEGRADED_IMPL_002_B_invented_conflict_value_is_impossible(self):
        with self.assertRaises(TypeError):
            RtssConflictEvidence(
                RtssOwnedField.PROFILE_REVISION,
                self.generation,
                999,
                "invented",
                "revision-2",
            )

    def test_S2_DEGRADED_IMPL_002_B_correct_conflict_is_derived_and_accepted(self):
        observation = RtssReadbackEvidence.bind(
            self.owner,
            self.matching_readback(revision="revision-2"),
        )
        conflict = RtssConflictEvidence.from_readback(
            RtssOwnedField.PROFILE_REVISION,
            self.owner,
            observation,
        )
        state = self.state(
            readback_evidence=observation,
            conflict_evidence=conflict,
        )

        self.assertEqual(conflict.captured_value, "revision-1")
        self.assertEqual(conflict.observed_value, "revision-2")
        self.assertNotIn(
            RtssOwnedField.PROFILE_REVISION,
            state.accounting.resolved_fields,
        )
        self.assertIs(
            state.classification,
            RtssDegradedClassification.EXTERNAL_CONFLICT,
        )

    def test_S2_DEGRADED_IMPL_002_B_conflict_provenance_mismatch_is_rejected(self):
        observation = RtssReadbackEvidence.bind(
            self.owner,
            self.matching_readback(revision="revision-2"),
        )
        owners = (
            self.owner_for(self.other_transaction),
            self.owner_for(
                self.transaction,
                generation=replace(
                    self.generation,
                    profile_identity=CanonicalProfileIdentity.global_profile(),
                ),
            ),
            self.owner_for(
                self.transaction,
                generation=replace(
                    self.generation,
                    source_generation=99,
                ),
            ),
            self.owner_for(
                self.transaction,
                capability_generation=12,
            ),
        )
        for owner in owners:
            with self.subTest(owner=owner):
                with self.assertRaisesRegex(
                    ValueError,
                    "exact transaction owner",
                ):
                    RtssConflictEvidence.from_readback(
                        RtssOwnedField.PROFILE_REVISION,
                        owner,
                        observation,
                    )

    def test_S2_DEGRADED_IMPL_002_B_conflict_and_readback_must_be_coherent(self):
        conflict_observation = RtssReadbackEvidence.bind(
            self.owner,
            self.matching_readback(revision="revision-2"),
        )
        conflict = RtssConflictEvidence.from_readback(
            RtssOwnedField.PROFILE_REVISION,
            self.owner,
            conflict_observation,
        )
        resolving_observation = RtssReadbackEvidence.bind(
            self.owner,
            self.matching_readback(),
        )

        with self.assertRaisesRegex(ValueError, "must be identical"):
            self.state(
                readback_evidence=resolving_observation,
                conflict_evidence=conflict,
            )
        with self.assertRaisesRegex(ValueError, "differing"):
            RtssConflictEvidence.from_readback(
                RtssOwnedField.PROFILE_REVISION,
                self.owner,
                resolving_observation,
            )

    def test_S2_DEGRADED_IMPL_002_B_latest_epoch_requires_bound_observation(self):
        failed = self.failed_readback(
            RtssStoredCapEvidence.read_failed(
                numerator_code="numerator-failed",
                denominator_code="denominator-failed",
            ),
            backend_generation=8,
        )
        capability = RtssCapabilityEvidence(
            self.transaction,
            self.generation,
            8,
            12,
        )
        observation = RtssReadbackEvidence.bind(
            self.owner,
            failed,
            capability_evidence=capability,
        )
        state = self.state(readback_evidence=observation)

        self.assertEqual(state.latest_backend_generation, 8)
        with self.assertRaises(TypeError):
            replace(state, latest_backend_generation=999)

    def test_S2_DEGRADED_IMPL_002_B_state_replace_revalidates_provenance(self):
        observation = RtssReadbackEvidence.bind(
            self.owner,
            self.failed_readback(
                RtssStoredCapEvidence.read_failed(
                    numerator_code="numerator-failed",
                    denominator_code="denominator-failed",
                )
            ),
        )
        state = self.state(readback_evidence=observation)
        other_owner = self.owner_for(self.other_transaction)

        with self.assertRaisesRegex(ValueError, "exact transaction owner"):
            replace(state, current_owner=other_owner)
        with self.assertRaises(ValueError):
            replace(state, reason=" ")

    def test_structural_ownership_copy_is_the_same_logical_token(self):
        owner_copy = replace(self.owner)
        observation = RtssReadbackEvidence.bind(
            owner_copy,
            self.matching_readback(),
        )
        operation = RtssOperationEvidence.verified(
            RtssOwnedField.SAVE,
            self.owner,
            observation,
        )

        self.assertIsNot(owner_copy, self.owner)
        self.assertEqual(owner_copy, self.owner)
        self.assertEqual(operation.ownership, self.owner)

    def test_modified_structural_ownership_copy_is_a_different_token(self):
        observation = RtssReadbackEvidence.bind(
            self.owner,
            self.matching_readback(),
        )
        changed_owner = replace(self.owner, holder="other-holder")

        with self.assertRaisesRegex(ValueError, "exact owner"):
            RtssOperationEvidence.verified(
                RtssOwnedField.SAVE,
                changed_owner,
                observation,
            )

    def test_duplicate_release_prevention_remains_a_future_registry_concern(self):
        readback = self.matching_readback()
        restore = RtssRestoreResult(
            RtssOutcome.VERIFIED,
            self.generation,
            readback=readback,
            captured_state=self.capture,
            transaction_identity=self.transaction,
        )
        proof = RtssExactRestorationProof(self.owner, restore)

        first = RtssOwnershipRelease(
            self.owner,
            RtssOwnershipReleaseReason.EXACT_RESTORATION,
            restoration_proof=proof,
        )
        second = RtssOwnershipRelease(
            replace(self.owner),
            RtssOwnershipReleaseReason.EXACT_RESTORATION,
            restoration_proof=proof,
        )
        self.assertEqual(first, second)


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
