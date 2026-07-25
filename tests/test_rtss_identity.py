"""Pure RTSS identity, rational-cap, and Stage 1 model tests."""

from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError
from decimal import Decimal
from hashlib import sha256

from src.core import rtss_contracts
from src.core.rtss_contracts import (
    CanonicalProfileIdentity,
    CapturedProfileState,
    ProfileKind,
    RationalCap,
    RtssApplyRequest,
    RtssApplyResult,
    RtssCapabilityInfo,
    RtssDenominatorStrategy,
    RtssFailureStep,
    RtssFieldAvailability,
    RtssGeneration,
    RtssOutcome,
    RtssReadback,
    RtssRestoreResult,
    canonicalize_profile_collection,
)


class CanonicalProfileIdentityTests(unittest.TestCase):
    def test_S1_FINAL_001_case_only_application_identities_are_equal_and_hash_equal(self):
        mixed_case = CanonicalProfileIdentity.application("Game.exe")
        other_case = CanonicalProfileIdentity.application("game.EXE")

        self.assertEqual(mixed_case, other_case)
        self.assertEqual(hash(mixed_case), hash(other_case))
        self.assertNotEqual(
            mixed_case,
            CanonicalProfileIdentity.application("other.exe"),
        )
        self.assertNotEqual(mixed_case, CanonicalProfileIdentity.global_profile())

    def test_S1_FINAL_001_case_only_identities_collapse_in_sets_and_dictionaries(self):
        mixed_case = CanonicalProfileIdentity.application("Game.exe")
        other_case = CanonicalProfileIdentity.application("game.EXE")

        self.assertEqual({mixed_case, other_case}, {mixed_case})
        identities = {mixed_case: "first"}
        identities[other_case] = "replacement"
        self.assertEqual(len(identities), 1)
        self.assertEqual(identities[mixed_case], "replacement")
        self.assertEqual(identities[other_case], "replacement")

    def test_S1_FINAL_001_generation_equality_uses_canonical_profile_identity(self):
        mixed_case = RtssGeneration(
            1,
            2,
            3,
            CanonicalProfileIdentity.application("Game.exe"),
            4,
        )
        other_case = RtssGeneration(
            1,
            2,
            3,
            CanonicalProfileIdentity.application("game.EXE"),
            4,
        )

        self.assertEqual(mixed_case, other_case)
        self.assertEqual(hash(mixed_case), hash(other_case))

    def test_RTSS_006_global_identity_is_explicit(self):
        identity = CanonicalProfileIdentity.global_profile()

        self.assertIs(identity.kind, ProfileKind.GLOBAL)
        self.assertEqual(identity.name, "Global")
        self.assertEqual(identity.canonical_key, "global")
        self.assertEqual(identity.dll_name, b"")
        self.assertEqual(identity.relative_profile_filename, "Global")

    def test_RTSS_006_legacy_global_translation_is_case_insensitive(self):
        for name in ("Global", "global", "GLOBAL", "gLoBaL"):
            with self.subTest(name=name):
                self.assertEqual(
                    CanonicalProfileIdentity.from_legacy_name(name),
                    CanonicalProfileIdentity.global_profile(),
                )

    def test_SEC_002_empty_input_never_means_global(self):
        with self.assertRaisesRegex(ValueError, "must not be empty"):
            CanonicalProfileIdentity.from_legacy_name("")
        with self.assertRaisesRegex(ValueError, "must not be empty"):
            CanonicalProfileIdentity.application("")
        with self.assertRaisesRegex(ValueError, "canonical name"):
            CanonicalProfileIdentity(ProfileKind.GLOBAL, "")

    def test_RTSS_006_valid_executable_names_derive_adapter_names(self):
        expected = (
            ("game.exe", b"game.exe", "game.exe.cfg"),
            ("Game.EXE", b"Game.EXE", "Game.EXE.cfg"),
            ("Game Name.ExE", b"Game Name.ExE", "Game Name.ExE.cfg"),
            ("game-name.exe", b"game-name.exe", "game-name.exe.cfg"),
            ("game_name.exe", b"game_name.exe", "game_name.exe.cfg"),
            ("game.release.v2.exe", b"game.release.v2.exe", "game.release.v2.exe.cfg"),
            ("12345.exe", b"12345.exe", "12345.exe.cfg"),
        )
        for name, dll_name, relative_filename in expected:
            with self.subTest(name=name):
                identity = CanonicalProfileIdentity.application(name)
                self.assertIs(identity.kind, ProfileKind.APPLICATION)
                self.assertEqual(identity.dll_name, dll_name)
                self.assertEqual(
                    identity.relative_profile_filename, relative_filename
                )

    def test_RTSS_006_rejects_unicode_without_lossy_conversion(self):
        for name in ("café.exe", "ゲーム.exe", "game\u00a0.exe"):
            with self.subTest(name=name):
                with self.assertRaisesRegex(ValueError, "ASCII"):
                    CanonicalProfileIdentity.application(name)

    def test_SEC_002_rejects_path_and_stream_forms(self):
        invalid_names = (
            "folder/game.exe",
            r"folder\game.exe",
            "./game.exe",
            r".\game.exe",
            "../game.exe",
            r"..\game.exe",
            "/game.exe",
            r"\game.exe",
            r"C:\game.exe",
            "C:game.exe",
            r"\\server\share\game.exe",
            "game.exe:stream",
            r"\\?\C:\game.exe",
            r"\\.\C:\game.exe",
            r"\??\C:\game.exe",
        )
        for name in invalid_names:
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    CanonicalProfileIdentity.application(name)

    def test_SEC_002_rejects_dot_components_and_missing_basenames(self):
        for name in (".", "..", ".exe", "..exe", "...exe"):
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    CanonicalProfileIdentity.application(name)

    def test_SEC_002_rejects_controls_whitespace_and_trailing_dots(self):
        invalid_names = (
            " game.exe",
            "game.exe ",
            "game.exe\t",
            "game\n.exe",
            "game\x00.exe",
            "game.exe.",
        )
        for name in invalid_names:
            with self.subTest(name=repr(name)):
                with self.assertRaises(ValueError):
                    CanonicalProfileIdentity.application(name)

    def test_SEC_002_rejects_windows_reserved_device_stems(self):
        invalid_names = (
            "CON.exe",
            "con.txt.exe",
            "PRN.EXE",
            "AUX.exe",
            "NUL.exe",
            "CLOCK$.exe",
            "CONIN$.exe",
            "CONOUT$.exe",
            "COM1.exe",
            "com9.ExE",
            "LPT1.exe",
            "lpt9.exe",
        )
        for name in invalid_names:
            with self.subTest(name=name):
                with self.assertRaisesRegex(ValueError, "reserved"):
                    CanonicalProfileIdentity.application(name)

    def test_RTSS_006_requires_an_executable_extension(self):
        for name in ("game", "game.cfg", "game.exe.cfg"):
            with self.subTest(name=name):
                with self.assertRaisesRegex(ValueError, "end with .exe"):
                    CanonicalProfileIdentity.application(name)

    def test_SEC_002_rejects_case_only_and_duplicate_collection_entries(self):
        with self.assertRaisesRegex(ValueError, "case-only"):
            canonicalize_profile_collection(("Game.exe", "game.EXE"))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            canonicalize_profile_collection(("game.exe", "game.exe"))
        with self.assertRaisesRegex(ValueError, "case-only"):
            canonicalize_profile_collection(("Global", "GLOBAL"))

    def test_SEC_002_collection_validation_returns_immutable_identities(self):
        identities = canonicalize_profile_collection(
            name for name in ("Global", "game.exe", "tool.EXE")
        )

        self.assertIsInstance(identities, tuple)
        self.assertEqual(
            tuple(identity.canonical_key for identity in identities),
            ("global", "application:game.exe", "application:tool.exe"),
        )
        with self.assertRaises(FrozenInstanceError):
            identities[1].name = "other.exe"


class RationalCapTests(unittest.TestCase):
    def test_RTSS_008_converts_exact_decimal_and_integer_values(self):
        expected = (
            (Decimal("59.94"), RationalCap(2997, 50)),
            (Decimal("117.5"), RationalCap(235, 2)),
            (Decimal("60.00"), RationalCap(60, 1)),
            (60, RationalCap(60, 1)),
        )
        for value, cap in expected:
            with self.subTest(value=value):
                converted = RationalCap.from_value(value)
                self.assertEqual(converted, cap)
                self.assertEqual(
                    (converted.numerator, converted.denominator),
                    (cap.numerator, cap.denominator),
                )
                self.assertFalse(hasattr(converted, "value"))

    def test_RTSS_008_reduces_ratios_using_integer_arithmetic(self):
        self.assertEqual(RationalCap(11750, 100), RationalCap(235, 2))
        self.assertEqual(RationalCap(-120, 2), RationalCap(-60, 1))
        self.assertEqual(RationalCap(0, 1000), RationalCap(0, 1))

    def test_RTSS_008_rejects_non_exact_input_types(self):
        for value in (True, False, "59.94", 59.94, None):
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    RationalCap.from_value(value)
        with self.assertRaises(TypeError):
            RationalCap(True, 1)
        with self.assertRaises(TypeError):
            RationalCap(60, False)

    def test_RTSS_008_rejects_non_finite_decimal_values(self):
        for value in (Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "finite"):
                    RationalCap.from_value(value)

    def test_RTSS_008_requires_a_positive_denominator(self):
        for denominator in (0, -1):
            with self.subTest(denominator=denominator):
                with self.assertRaisesRegex(ValueError, "positive"):
                    RationalCap(60, denominator)

    def test_RTSS_008_enforces_only_caller_supplied_ranges(self):
        cap = RationalCap.from_value(
            Decimal("117.5"),
            minimum_numerator=200,
            maximum_numerator=300,
            minimum_denominator=1,
            maximum_denominator=10,
        )
        self.assertEqual(cap, RationalCap(235, 2))

        with self.assertRaisesRegex(ValueError, "numerator exceeds"):
            RationalCap.from_value(Decimal("117.5"), maximum_numerator=200)
        with self.assertRaisesRegex(ValueError, "denominator exceeds"):
            RationalCap.from_value(Decimal("117.5"), maximum_denominator=1)
        with self.assertRaisesRegex(ValueError, "must not exceed"):
            RationalCap.from_value(60, minimum_numerator=100, maximum_numerator=50)
        with self.assertRaises(TypeError):
            RationalCap.from_value(60, maximum_numerator=True)

    def test_RTSS_008_preserves_high_precision_and_tiny_decimals_exactly(self):
        values = (
            Decimal("123456789012345678901234567890123456789"),
            Decimal("0.123456789012345678901234567890123456789"),
            Decimal("1E-1000"),
        )
        for value in values:
            with self.subTest(value=value):
                cap = RationalCap.from_value(value)
                self.assertEqual(
                    (cap.numerator, cap.denominator),
                    value.as_integer_ratio(),
                )

    def test_RTSS_008_enforces_decimal_parser_safety_limits_before_conversion(self):
        self.assertEqual(
            RationalCap.from_value(
                Decimal("1E+4"),
                maximum_absolute_exponent=4,
            ),
            RationalCap(10000, 1),
        )
        with self.assertRaisesRegex(ValueError, "exponent"):
            RationalCap.from_value(
                Decimal("1E+5"),
                maximum_absolute_exponent=4,
            )
        with self.assertRaisesRegex(ValueError, "exponent"):
            RationalCap.from_value(
                Decimal("1E-5"),
                maximum_absolute_exponent=4,
            )

        self.assertEqual(
            RationalCap.from_value(
                Decimal("1234"),
                maximum_significant_digits=4,
            ),
            RationalCap(1234, 1),
        )
        with self.assertRaisesRegex(ValueError, "significant digits"):
            RationalCap.from_value(
                Decimal("12345"),
                maximum_significant_digits=4,
            )

        self.assertEqual(
            RationalCap.from_value(255, maximum_numerator_bits=8),
            RationalCap(255, 1),
        )
        with self.assertRaisesRegex(ValueError, "numerator"):
            RationalCap.from_value(256, maximum_numerator_bits=8)
        self.assertEqual(
            RationalCap.from_value(
                Decimal("0.125"),
                maximum_denominator_bits=4,
            ),
            RationalCap(1, 8),
        )
        with self.assertRaisesRegex(ValueError, "denominator"):
            RationalCap.from_value(
                Decimal("0.125"),
                maximum_denominator_bits=3,
            )
        with self.assertRaisesRegex(ValueError, "numerator"):
            RationalCap.from_value(
                Decimal("1E+100000"),
                maximum_absolute_exponent=100000,
                maximum_numerator_bits=64,
            )
        with self.assertRaisesRegex(ValueError, "denominator"):
            RationalCap.from_value(
                Decimal("1E-100000"),
                maximum_absolute_exponent=100000,
                maximum_denominator_bits=64,
            )

    def test_RTSS_008_effective_cap_bounds_use_exact_rational_comparison(self):
        exact_boundary = RationalCap.from_value(
            Decimal("59.94"),
            minimum_effective_cap=Decimal("59.94"),
            maximum_effective_cap=RationalCap(2997, 50),
        )
        self.assertEqual(exact_boundary, RationalCap(2997, 50))

        with self.assertRaisesRegex(ValueError, "effective minimum"):
            RationalCap(59939, 1000).require_ranges(
                minimum_effective_cap=Decimal("59.94")
            )
        with self.assertRaisesRegex(ValueError, "effective maximum"):
            RationalCap(59941, 1000).require_ranges(
                maximum_effective_cap=Decimal("59.94")
            )
        with self.assertRaisesRegex(ValueError, "effective minimum"):
            exact_boundary.require_ranges(
                minimum_effective_cap=Decimal("59.94"),
                minimum_effective_cap_inclusive=False,
            )
        with self.assertRaisesRegex(ValueError, "effective maximum"):
            exact_boundary.require_ranges(
                maximum_effective_cap=Decimal("59.94"),
                maximum_effective_cap_inclusive=False,
            )
        with self.assertRaisesRegex(ValueError, "must not exceed"):
            exact_boundary.require_ranges(
                minimum_effective_cap=60,
                maximum_effective_cap=59,
            )
        with self.assertRaisesRegex(ValueError, "exclusive equal"):
            exact_boundary.require_ranges(
                minimum_effective_cap=60,
                maximum_effective_cap=60,
                minimum_effective_cap_inclusive=False,
            )

    def test_RTSS_008_negative_caps_require_an_explicit_permitting_range(self):
        negative = RationalCap(-1, 2)
        self.assertIs(
            negative.require_ranges(
                minimum_effective_cap=-1,
                maximum_effective_cap=0,
            ),
            negative,
        )
        with self.assertRaisesRegex(ValueError, "effective minimum"):
            negative.require_ranges(minimum_effective_cap=0)

    def test_RTSS_008_capability_ranges_are_explicit_not_universal(self):
        unconstrained = RtssCapabilityInfo(backend_generation=1)
        very_large_cap = RationalCap(10**100, 10**50)
        self.assertIs(unconstrained.validate_cap(very_large_cap), very_large_cap)

        constrained = RtssCapabilityInfo(
            backend_generation=2,
            denominator_strategies=(RtssDenominatorStrategy.PROFILE_FILE,),
            minimum_numerator=0,
            maximum_numerator=5000,
            minimum_denominator=1,
            maximum_denominator=100,
            maximum_numerator_bits=16,
            maximum_denominator_bits=8,
            minimum_effective_cap=Decimal("30"),
            maximum_effective_cap=Decimal("120"),
        )
        self.assertEqual(
            constrained.validate_cap(RationalCap(2997, 50)),
            RationalCap(2997, 50),
        )
        with self.assertRaisesRegex(ValueError, "numerator exceeds"):
            constrained.validate_cap(RationalCap(5001, 1))
        with self.assertRaisesRegex(ValueError, "effective minimum"):
            constrained.validate_cap(RationalCap(2999, 100))
        with self.assertRaisesRegex(ValueError, "effective maximum"):
            constrained.validate_cap(RationalCap(121, 1))
        self.assertEqual(
            constrained.minimum_effective_cap,
            RationalCap(30, 1),
        )
        self.assertEqual(
            constrained.maximum_effective_cap,
            RationalCap(120, 1),
        )

    def test_RTSS_008_cap_and_capability_models_are_immutable(self):
        cap = RationalCap.from_value(Decimal("59.94"))
        capability = RtssCapabilityInfo(
            backend_generation=1,
            denominator_strategies=[RtssDenominatorStrategy.PROFILE_FILE],
        )

        self.assertEqual(
            capability.denominator_strategies,
            (RtssDenominatorStrategy.PROFILE_FILE,),
        )
        with self.assertRaises(FrozenInstanceError):
            cap.numerator = 60
        with self.assertRaises(FrozenInstanceError):
            capability.backend_generation = 2

    def test_RTSS_008_unresolved_is_a_policy_state_not_a_capability(self):
        self.assertEqual(
            set(RtssDenominatorStrategy),
            {
                RtssDenominatorStrategy.UNRESOLVED,
                RtssDenominatorStrategy.PROFILE_FILE,
                RtssDenominatorStrategy.RTSS_API,
            },
        )
        self.assertEqual(RtssDenominatorStrategy.UNRESOLVED.value, "unresolved")
        self.assertEqual(RtssDenominatorStrategy.PROFILE_FILE.value, "profile_file")
        self.assertEqual(RtssDenominatorStrategy.RTSS_API.value, "rtss_api")
        with self.assertRaisesRegex(ValueError, "not an observed"):
            RtssCapabilityInfo(
                backend_generation=1,
                denominator_strategies=(RtssDenominatorStrategy.UNRESOLVED,),
            )


class RtssModelContractTests(unittest.TestCase):
    def setUp(self):
        self.identity = CanonicalProfileIdentity.application("game.exe")
        self.generation = RtssGeneration(1, 2, 3, self.identity)
        self.cap = RationalCap.from_value(Decimal("59.94"))
        self.request = RtssApplyRequest(
            self.generation,
            self.cap,
            RtssDenominatorStrategy.PROFILE_FILE,
            allow_profile_creation=True,
            limiter_flag_mask=4,
            limiter_flag_values=0,
            reason="controller decrease",
        )
        self.readback = RtssReadback(
            RtssOutcome.VERIFIED,
            self.generation,
            True,
            self.cap,
            limiter_flags=0,
            profile_revision="revision-2",
            backend_generation=5,
            profile_revision_availability=RtssFieldAvailability.AVAILABLE,
        )
        self.captured = CapturedProfileState(
            self.generation,
            5,
            True,
            RationalCap(60, 1),
            limiter_flags=4,
            profile_revision="revision-1",
            profile_document=b"Limit=60\nLimitDenominator=1\n",
            owned_flag_mask=4,
            profile_revision_availability=RtssFieldAvailability.AVAILABLE,
            profile_document_availability=RtssFieldAvailability.AVAILABLE,
        )

    def restored_readback(
        self,
        *,
        limiter_flags=4,
        profile_revision="revision-1",
        profile_document=b"Limit=60\nLimitDenominator=1\n",
    ):
        return RtssReadback(
            RtssOutcome.VERIFIED,
            self.generation,
            True,
            self.captured.cap,
            limiter_flags=limiter_flags,
            profile_revision=profile_revision,
            backend_generation=5,
            profile_revision_availability=RtssFieldAvailability.AVAILABLE,
            profile_document_availability=RtssFieldAvailability.AVAILABLE,
            profile_document=profile_document,
        )

    def test_RTSS_001_through_RTSS_005_models_are_immutable(self):
        restore = RtssRestoreResult(
            RtssOutcome.CONFLICT,
            self.generation,
            readback=self.readback,
            captured_state=self.captured,
            failure_step=RtssFailureStep.CONFLICT,
            error="external edit detected",
            unrestored_flag_mask=4,
        )
        result = RtssApplyResult(
            RtssOutcome.VERIFIED,
            self.request,
            readback=self.readback,
            captured_state=self.captured,
        )

        for model, attribute, value in (
            (self.generation, "session_generation", 4),
            (self.request, "reason", "changed"),
            (self.readback, "profile_exists", False),
            (self.captured, "profile_revision", "changed"),
            (restore, "error", None),
            (result, "outcome", RtssOutcome.FAILED),
        ):
            with self.subTest(model=type(model).__name__):
                with self.assertRaises(FrozenInstanceError):
                    setattr(model, attribute, value)

        self.assertTrue(result.succeeded)
        self.assertFalse(restore.succeeded)
        self.assertIs(restore.captured_state, self.captured)

    def test_RTSS_005_verified_apply_requires_exact_readback(self):
        with self.assertRaisesRegex(ValueError, "requires verified readback"):
            RtssApplyResult(
                RtssOutcome.VERIFIED,
                self.request,
                captured_state=self.captured,
            )

        mismatched_readback = RtssReadback(
            RtssOutcome.VERIFIED,
            self.generation,
            True,
            RationalCap(60, 1),
            limiter_flags=0,
            backend_generation=5,
        )
        with self.assertRaisesRegex(ValueError, "cap must match"):
            RtssApplyResult(
                RtssOutcome.VERIFIED,
                self.request,
                readback=mismatched_readback,
                captured_state=self.captured,
            )

        missing_flags = RtssReadback(
            RtssOutcome.VERIFIED,
            self.generation,
            True,
            self.cap,
            backend_generation=5,
        )
        with self.assertRaisesRegex(ValueError, "require flag readback"):
            RtssApplyResult(
                RtssOutcome.VERIFIED,
                self.request,
                readback=missing_flags,
                captured_state=self.captured,
            )

    def test_S1_FINAL_001_transaction_models_match_case_only_identity_variants(self):
        request_generation = RtssGeneration(
            1,
            2,
            3,
            CanonicalProfileIdentity.application("Game.exe"),
        )
        capture_generation = RtssGeneration(
            1,
            2,
            3,
            CanonicalProfileIdentity.application("game.EXE"),
        )
        readback_generation = RtssGeneration(
            1,
            2,
            3,
            CanonicalProfileIdentity.application("GAME.exe"),
        )
        request = RtssApplyRequest(
            request_generation,
            self.cap,
            RtssDenominatorStrategy.PROFILE_FILE,
            limiter_flag_mask=4,
            limiter_flag_values=0,
            reason="case-insensitive identity proof",
        )
        captured = CapturedProfileState(
            capture_generation,
            5,
            True,
            RationalCap(60, 1),
            limiter_flags=4,
            owned_flag_mask=4,
        )
        equivalent_capture = CapturedProfileState(
            request_generation,
            5,
            True,
            RationalCap(60, 1),
            limiter_flags=4,
            owned_flag_mask=4,
        )
        readback = RtssReadback(
            RtssOutcome.VERIFIED,
            readback_generation,
            True,
            self.cap,
            limiter_flags=0,
            backend_generation=5,
        )

        self.assertEqual(captured, equivalent_capture)
        result = RtssApplyResult(
            RtssOutcome.VERIFIED,
            request,
            readback=readback,
            captured_state=captured,
        )
        self.assertTrue(result.succeeded)

    def test_S1_FINAL_002_flag_mutation_requires_complete_captured_ownership(self):
        uncaptured_flags = CapturedProfileState(
            self.generation,
            5,
            True,
            RationalCap(60, 1),
        )
        with self.assertRaisesRegex(ValueError, "captured flag ownership"):
            RtssApplyResult(
                RtssOutcome.VERIFIED,
                self.request,
                readback=self.readback,
                captured_state=uncaptured_flags,
            )

        two_bit_request = RtssApplyRequest(
            self.generation,
            self.cap,
            RtssDenominatorStrategy.PROFILE_FILE,
            limiter_flag_mask=6,
            limiter_flag_values=0,
            reason="two owned limiter bits",
        )
        partially_captured = CapturedProfileState(
            self.generation,
            5,
            True,
            RationalCap(60, 1),
            limiter_flags=4,
            owned_flag_mask=4,
        )
        with self.assertRaisesRegex(ValueError, "captured flag ownership"):
            RtssApplyResult(
                RtssOutcome.VERIFIED,
                two_bit_request,
                readback=self.readback,
                captured_state=partially_captured,
            )

    def test_S1_FINAL_002_full_flag_ownership_ignores_unowned_readback_bits(self):
        readback_with_external_bits = RtssReadback(
            RtssOutcome.VERIFIED,
            self.generation,
            True,
            self.cap,
            limiter_flags=8,
            backend_generation=5,
        )

        result = RtssApplyResult(
            RtssOutcome.VERIFIED,
            self.request,
            readback=readback_with_external_bits,
            captured_state=self.captured,
        )
        self.assertTrue(result.succeeded)

    def test_S1_FINAL_002_failed_rollback_identifies_each_unrestored_owned_bit(self):
        request = RtssApplyRequest(
            self.generation,
            self.cap,
            RtssDenominatorStrategy.PROFILE_FILE,
            limiter_flag_mask=6,
            limiter_flag_values=0,
            reason="restore two owned limiter bits",
        )
        captured = CapturedProfileState(
            self.generation,
            5,
            True,
            RationalCap(60, 1),
            limiter_flags=6,
            owned_flag_mask=6,
        )
        partial_readback = RtssReadback(
            RtssOutcome.VERIFIED,
            self.generation,
            True,
            captured.cap,
            limiter_flags=4,
            backend_generation=5,
        )
        with self.assertRaisesRegex(ValueError, "every unrestored"):
            RtssRestoreResult(
                RtssOutcome.DEGRADED,
                self.generation,
                readback=partial_readback,
                captured_state=captured,
                failure_step=RtssFailureStep.ROLLBACK,
                error="one owned flag bit was not restored",
            )

        partial_rollback = RtssRestoreResult(
            RtssOutcome.DEGRADED,
            self.generation,
            readback=partial_readback,
            captured_state=captured,
            failure_step=RtssFailureStep.ROLLBACK,
            error="one owned flag bit was not restored",
            unrestored_flag_mask=2,
        )
        result = RtssApplyResult(
            RtssOutcome.DEGRADED,
            request,
            captured_state=captured,
            rollback=partial_rollback,
            failure_step=RtssFailureStep.SAVE,
            error="save failed and owned flag rollback was incomplete",
        )
        self.assertEqual(result.rollback.unrestored_flag_mask, 2)

    def test_S1_FINAL_002_all_unresolved_rollback_outcomes_account_for_flags(self):
        cases = (
            (RtssOutcome.CONFLICT, RtssFailureStep.CONFLICT),
            (
                RtssOutcome.UNSUPPORTED_CAPABILITY,
                RtssFailureStep.CAPABILITY,
            ),
            (RtssOutcome.FAILED, RtssFailureStep.CAPTURE),
            (RtssOutcome.DEGRADED, RtssFailureStep.ROLLBACK),
        )
        for outcome, step in cases:
            with self.subTest(outcome=outcome):
                with self.assertRaisesRegex(ValueError, "every unrestored"):
                    RtssRestoreResult(
                        outcome,
                        self.generation,
                        captured_state=self.captured,
                        failure_step=step,
                        error="rollback did not produce usable readback",
                    )

                rollback = RtssRestoreResult(
                    outcome,
                    self.generation,
                    captured_state=self.captured,
                    failure_step=step,
                    error="rollback did not produce usable readback",
                    unrestored_flag_mask=4,
                )
                result = RtssApplyResult(
                    RtssOutcome.DEGRADED,
                    self.request,
                    captured_state=self.captured,
                    rollback=rollback,
                    failure_step=RtssFailureStep.SAVE,
                    error="apply failed and rollback remains unresolved",
                )
                self.assertEqual(result.rollback.unrestored_flag_mask, 4)

    def test_S1_FINAL_002_apply_to_rollback_outcome_matrix_is_exhaustive(self):
        expected = {
            RtssOutcome.VERIFIED: frozenset(),
            RtssOutcome.REJECTED_VALIDATION: frozenset(),
            RtssOutcome.STALE_GENERATION: frozenset(),
            RtssOutcome.UNSUPPORTED_CAPABILITY: frozenset(),
            RtssOutcome.POLICY_REQUIRED: frozenset(),
            RtssOutcome.CONFLICT: frozenset(),
            RtssOutcome.FAILED: frozenset(),
            RtssOutcome.FAILED_ROLLED_BACK: frozenset(
                {RtssOutcome.VERIFIED}
            ),
            RtssOutcome.DEGRADED: frozenset(
                {
                    RtssOutcome.UNSUPPORTED_CAPABILITY,
                    RtssOutcome.CONFLICT,
                    RtssOutcome.FAILED,
                    RtssOutcome.DEGRADED,
                }
            ),
        }

        self.assertEqual(set(expected), set(RtssOutcome))
        self.assertEqual(
            rtss_contracts._APPLY_ROLLBACK_OUTCOMES,
            expected,
        )

    def test_S1_FINAL_002_requested_subset_and_external_bits_stay_outside_reporting(self):
        request = RtssApplyRequest(
            self.generation,
            self.cap,
            RtssDenominatorStrategy.PROFILE_FILE,
            limiter_flag_mask=2,
            limiter_flag_values=0,
            reason="mutate only one captured flag",
        )
        captured = CapturedProfileState(
            self.generation,
            5,
            True,
            RationalCap(60, 1),
            limiter_flags=6,
            owned_flag_mask=6,
        )
        partial_readback_with_external_bit = RtssReadback(
            RtssOutcome.VERIFIED,
            self.generation,
            True,
            captured.cap,
            limiter_flags=12,
            backend_generation=5,
        )
        rollback = RtssRestoreResult(
            RtssOutcome.DEGRADED,
            self.generation,
            readback=partial_readback_with_external_bit,
            captured_state=captured,
            failure_step=RtssFailureStep.READBACK,
            error="requested bit remains unrestored",
            unrestored_flag_mask=2,
        )

        result = RtssApplyResult(
            RtssOutcome.DEGRADED,
            request,
            captured_state=captured,
            rollback=rollback,
            failure_step=RtssFailureStep.SAVE,
            error="save failed and requested flag was not restored",
        )

        self.assertEqual(result.rollback.unrestored_flag_mask, 2)

    def test_S1_FINAL_002_cap_only_degraded_apply_needs_no_flag_uncertainty(self):
        request = RtssApplyRequest(
            self.generation,
            self.cap,
            RtssDenominatorStrategy.PROFILE_FILE,
            reason="cap only",
        )
        captured = CapturedProfileState(
            self.generation,
            5,
            True,
            RationalCap(60, 1),
        )
        rollback = RtssRestoreResult(
            RtssOutcome.DEGRADED,
            self.generation,
            captured_state=captured,
            failure_step=RtssFailureStep.READBACK,
            error="cap restoration could not be verified",
        )

        result = RtssApplyResult(
            RtssOutcome.DEGRADED,
            request,
            captured_state=captured,
            rollback=rollback,
            failure_step=RtssFailureStep.SAVE,
            error="save failed and cap rollback remains unresolved",
        )

        self.assertEqual(result.rollback.unrestored_flag_mask, 0)

    def test_S1_FINAL_002_missing_backend_epoch_cannot_prove_flag_restoration(self):
        readback_without_backend_epoch = RtssReadback(
            RtssOutcome.VERIFIED,
            self.generation,
            True,
            self.captured.cap,
            limiter_flags=4,
            profile_revision="revision-1",
            profile_revision_availability=RtssFieldAvailability.AVAILABLE,
            profile_document_availability=RtssFieldAvailability.AVAILABLE,
            profile_document=self.captured.profile_document,
        )

        with self.assertRaisesRegex(ValueError, "every unrestored"):
            RtssRestoreResult(
                RtssOutcome.DEGRADED,
                self.generation,
                readback=readback_without_backend_epoch,
                captured_state=self.captured,
                failure_step=RtssFailureStep.READBACK,
                error="backend epoch was not verified",
            )

        rollback = RtssRestoreResult(
            RtssOutcome.DEGRADED,
            self.generation,
            readback=readback_without_backend_epoch,
            captured_state=self.captured,
            failure_step=RtssFailureStep.READBACK,
            error="backend epoch was not verified",
            unrestored_flag_mask=4,
        )
        self.assertEqual(rollback.unrestored_flag_mask, 4)

    def test_S1_FINAL_002_cap_only_apply_needs_no_flag_capture(self):
        request = RtssApplyRequest(
            self.generation,
            self.cap,
            RtssDenominatorStrategy.PROFILE_FILE,
            reason="cap only",
        )
        captured = CapturedProfileState(
            self.generation,
            5,
            True,
            RationalCap(60, 1),
        )
        readback = RtssReadback(
            RtssOutcome.VERIFIED,
            self.generation,
            True,
            self.cap,
            backend_generation=5,
        )

        self.assertTrue(
            RtssApplyResult(
                RtssOutcome.VERIFIED,
                request,
                readback=readback,
                captured_state=captured,
            ).succeeded
        )

    def test_S1_FINAL_003_failed_cannot_retain_unresolved_mismatched_readback(self):
        mismatched_readback = RtssReadback(
            RtssOutcome.VERIFIED,
            self.generation,
            True,
            RationalCap(60, 1),
            limiter_flags=4,
            backend_generation=5,
        )
        with self.assertRaisesRegex(ValueError, "captured state"):
            RtssApplyResult(
                RtssOutcome.FAILED,
                self.request,
                readback=mismatched_readback,
                failure_step=RtssFailureStep.READBACK,
                error="exact readback mismatch",
            )

    def test_S1_FINAL_003_precapture_failed_graphs_are_state_free(self):
        for step in (
            RtssFailureStep.VALIDATE,
            RtssFailureStep.GENERATION,
            RtssFailureStep.CAPABILITY,
            RtssFailureStep.CAPTURE,
        ):
            with self.subTest(step=step):
                result = RtssApplyResult(
                    RtssOutcome.FAILED,
                    self.request,
                    failure_step=step,
                    error=f"{step.value} failed before mutation",
                )
                self.assertFalse(result.succeeded)
                self.assertIsNone(result.captured_state)

    def test_S1_FINAL_003_postmutation_failed_requires_exact_no_change_proof(self):
        no_change_readback = self.restored_readback()
        result = RtssApplyResult(
            RtssOutcome.FAILED,
            self.request,
            readback=no_change_readback,
            captured_state=self.captured,
            failure_step=RtssFailureStep.SAVE,
            error="save failed but exact probe proved no change",
        )
        self.assertFalse(result.succeeded)

        for step in (RtssFailureStep.APPLY, RtssFailureStep.SAVE):
            with self.subTest(step=step):
                with self.assertRaisesRegex(ValueError, "no-change readback"):
                    RtssApplyResult(
                        RtssOutcome.FAILED,
                        self.request,
                        failure_step=step,
                        error="mutation disposition unknown",
                    )

        mismatched = self.restored_readback(profile_revision="changed")
        with self.assertRaisesRegex(ValueError, "revision evidence"):
            RtssApplyResult(
                RtssOutcome.FAILED,
                self.request,
                readback=mismatched,
                captured_state=self.captured,
                failure_step=RtssFailureStep.READBACK,
                error="secondary readback did not prove no change",
            )

    def test_S1_FINAL_003_unknown_failure_phases_cannot_use_ordinary_failed(self):
        for step in (
            RtssFailureStep.ROLLBACK,
            RtssFailureStep.RESTORE,
            RtssFailureStep.DELETE,
            RtssFailureStep.CONFLICT,
        ):
            with self.subTest(step=step):
                with self.assertRaisesRegex(ValueError, "mutation disposition"):
                    RtssApplyResult(
                        RtssOutcome.FAILED,
                        self.request,
                        failure_step=step,
                        error="unsupported failure graph",
                    )

    def test_S1_FINAL_003_degraded_graph_records_failed_rollback(self):
        failed_rollback = RtssRestoreResult(
            RtssOutcome.DEGRADED,
            self.generation,
            captured_state=self.captured,
            failure_step=RtssFailureStep.ROLLBACK,
            error="owned state restoration remains uncertain",
            unrestored_flag_mask=4,
        )
        result = RtssApplyResult(
            RtssOutcome.DEGRADED,
            self.request,
            captured_state=self.captured,
            rollback=failed_rollback,
            failure_step=RtssFailureStep.SAVE,
            error="save failed and rollback was not verified",
        )
        self.assertFalse(result.succeeded)
        self.assertFalse(result.rollback.succeeded)

    def test_S1_FINAL_003_ordinary_failed_restore_cannot_hide_changed_state(self):
        changed_readbacks = {
            "cap": RtssReadback(
                RtssOutcome.VERIFIED,
                self.generation,
                True,
                RationalCap(59, 1),
                limiter_flags=4,
                profile_revision="revision-1",
                backend_generation=5,
                profile_revision_availability=RtssFieldAvailability.AVAILABLE,
                profile_document_availability=RtssFieldAvailability.AVAILABLE,
                profile_document=self.captured.profile_document,
            ),
            "existence": RtssReadback(
                RtssOutcome.VERIFIED,
                self.generation,
                False,
                None,
                backend_generation=5,
            ),
            "flags": self.restored_readback(limiter_flags=0),
            "document": self.restored_readback(
                profile_document=b"Limit=59\nLimitDenominator=1\n"
            ),
            "revision": self.restored_readback(profile_revision="revision-2"),
        }
        for field, readback in changed_readbacks.items():
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, "must not contain readback"):
                    RtssRestoreResult(
                        RtssOutcome.FAILED,
                        self.generation,
                        readback=readback,
                        captured_state=self.captured,
                        failure_step=RtssFailureStep.CAPTURE,
                        error="restore stopped before mutation",
                        unrestored_flag_mask=(
                            4 if field in {"flags", "existence"} else 0
                        ),
                    )

    def test_S1_FINAL_003_restore_failure_phases_are_non_recursive_and_explicit(self):
        invalid_graphs = (
            {
                "outcome": RtssOutcome.FAILED,
                "failure_step": RtssFailureStep.RESTORE,
                "error": "mutation may have occurred without capture",
            },
            {
                "outcome": RtssOutcome.FAILED,
                "captured_state": self.captured,
                "failure_step": RtssFailureStep.RESTORE,
                "error": "mutation may have occurred without readback",
                "unrestored_flag_mask": 4,
            },
            {
                "outcome": RtssOutcome.FAILED_ROLLED_BACK,
                "failure_step": RtssFailureStep.ROLLBACK,
                "error": "recursive restore disposition",
            },
            {
                "outcome": RtssOutcome.FAILED_ROLLED_BACK,
                "captured_state": self.captured,
                "failure_step": RtssFailureStep.ROLLBACK,
                "error": "recursive restore disposition",
                "unrestored_flag_mask": 4,
            },
        )
        for graph in invalid_graphs:
            with self.subTest(graph=graph):
                with self.assertRaises(ValueError):
                    RtssRestoreResult(
                        generation=self.generation,
                        **graph,
                    )

        pre_mutation_failure = RtssRestoreResult(
            RtssOutcome.FAILED,
            self.generation,
            captured_state=self.captured,
            failure_step=RtssFailureStep.CAPTURE,
            error="restore preparation failed before mutation",
            unrestored_flag_mask=4,
        )
        self.assertFalse(pre_mutation_failure.succeeded)

    def test_S1_FINAL_003_degraded_restore_exposes_all_changed_owned_state(self):
        changed = RtssReadback(
            RtssOutcome.VERIFIED,
            self.generation,
            True,
            RationalCap(59, 1),
            limiter_flags=0,
            profile_revision="revision-2",
            backend_generation=5,
            profile_revision_availability=RtssFieldAvailability.AVAILABLE,
            profile_document_availability=RtssFieldAvailability.AVAILABLE,
            profile_document=b"Limit=59\nLimitDenominator=1\n",
        )

        degraded = RtssRestoreResult(
            RtssOutcome.DEGRADED,
            self.generation,
            readback=changed,
            captured_state=self.captured,
            failure_step=RtssFailureStep.READBACK,
            error="restored state differs from every captured mutable field",
            unrestored_flag_mask=4,
        )

        self.assertIs(degraded.readback, changed)
        self.assertIs(degraded.captured_state, self.captured)
        self.assertEqual(degraded.unrestored_flag_mask, 4)

    def test_S1_FINAL_003_exact_restore_must_use_verified(self):
        for outcome, step in (
            (RtssOutcome.CONFLICT, RtssFailureStep.CONFLICT),
            (
                RtssOutcome.UNSUPPORTED_CAPABILITY,
                RtssFailureStep.CAPABILITY,
            ),
            (RtssOutcome.DEGRADED, RtssFailureStep.READBACK),
        ):
            with self.subTest(outcome=outcome):
                with self.assertRaisesRegex(ValueError, "must use the verified"):
                    RtssRestoreResult(
                        outcome,
                        self.generation,
                        readback=self.restored_readback(),
                        captured_state=self.captured,
                        failure_step=step,
                        error="incorrect non-success disposition",
                    )

    def test_S1_FINAL_003_restore_outcome_and_step_matrix_is_exhaustive(self):
        valid_steps_by_outcome = {
            RtssOutcome.VERIFIED: {RtssFailureStep.NONE},
            RtssOutcome.REJECTED_VALIDATION: set(),
            RtssOutcome.STALE_GENERATION: set(),
            RtssOutcome.UNSUPPORTED_CAPABILITY: {
                RtssFailureStep.CAPABILITY
            },
            RtssOutcome.POLICY_REQUIRED: set(),
            RtssOutcome.CONFLICT: {RtssFailureStep.CONFLICT},
            RtssOutcome.FAILED: {
                RtssFailureStep.VALIDATE,
                RtssFailureStep.GENERATION,
                RtssFailureStep.CAPABILITY,
                RtssFailureStep.CAPTURE,
            },
            RtssOutcome.FAILED_ROLLED_BACK: set(),
            RtssOutcome.DEGRADED: {
                RtssFailureStep.APPLY,
                RtssFailureStep.SAVE,
                RtssFailureStep.UPDATE,
                RtssFailureStep.READBACK,
                RtssFailureStep.ROLLBACK,
                RtssFailureStep.RESTORE,
                RtssFailureStep.DELETE,
            },
        }
        self.assertEqual(set(valid_steps_by_outcome), set(RtssOutcome))

        for outcome in RtssOutcome:
            for step in RtssFailureStep:
                with self.subTest(outcome=outcome, step=step):
                    kwargs = {
                        "captured_state": self.captured,
                        "failure_step": step,
                    }
                    if outcome is RtssOutcome.VERIFIED:
                        kwargs["readback"] = self.restored_readback()
                    else:
                        kwargs["error"] = "classified non-success restore"
                        kwargs["unrestored_flag_mask"] = 4
                    try:
                        RtssRestoreResult(
                            outcome,
                            self.generation,
                            **kwargs,
                        )
                    except ValueError:
                        accepted = False
                    else:
                        accepted = True
                    self.assertEqual(
                        accepted,
                        step in valid_steps_by_outcome[outcome],
                    )

    def test_S1_REV_001_verified_apply_rejects_mismatched_capture_identity(self):
        foreign_generation = RtssGeneration(
            1,
            2,
            3,
            CanonicalProfileIdentity.application("other.exe"),
        )
        foreign_capture = CapturedProfileState(
            foreign_generation,
            5,
            True,
            RationalCap(60, 1),
        )

        with self.assertRaisesRegex(ValueError, "captured generation"):
            RtssApplyResult(
                RtssOutcome.VERIFIED,
                self.request,
                readback=self.readback,
                captured_state=foreign_capture,
            )

    def test_S1_REV_001_verified_apply_rejects_mismatched_generations(self):
        stale_generation = RtssGeneration(1, 99, 3, self.identity)
        stale_readback = RtssReadback(
            RtssOutcome.VERIFIED,
            stale_generation,
            True,
            self.cap,
            limiter_flags=0,
            backend_generation=5,
        )
        with self.assertRaisesRegex(ValueError, "readback generation"):
            RtssApplyResult(
                RtssOutcome.VERIFIED,
                self.request,
                readback=stale_readback,
                captured_state=self.captured,
            )

        stale_capture = CapturedProfileState(
            stale_generation,
            5,
            True,
            RationalCap(60, 1),
        )
        with self.assertRaisesRegex(ValueError, "captured generation"):
            RtssApplyResult(
                RtssOutcome.VERIFIED,
                self.request,
                readback=self.readback,
                captured_state=stale_capture,
            )

        wrong_backend_readback = RtssReadback(
            RtssOutcome.VERIFIED,
            self.generation,
            True,
            self.cap,
            limiter_flags=0,
            backend_generation=6,
        )
        with self.assertRaisesRegex(ValueError, "backend generation"):
            RtssApplyResult(
                RtssOutcome.VERIFIED,
                self.request,
                readback=wrong_backend_readback,
                captured_state=self.captured,
            )

    def test_S1_REV_001_verified_apply_rejects_rollback_and_failure_details(self):
        for outcome, step in (
            (RtssOutcome.FAILED, RtssFailureStep.CAPTURE),
            (RtssOutcome.DEGRADED, RtssFailureStep.ROLLBACK),
        ):
            with self.subTest(outcome=outcome):
                failed_rollback = RtssRestoreResult(
                    outcome,
                    self.generation,
                    captured_state=self.captured,
                    failure_step=step,
                    error="rollback readback failed",
                    unrestored_flag_mask=4,
                )
                with self.assertRaises(ValueError):
                    RtssApplyResult(
                        RtssOutcome.VERIFIED,
                        self.request,
                        readback=self.readback,
                        captured_state=self.captured,
                        rollback=failed_rollback,
                    )

        restored_readback = self.restored_readback()
        verified_rollback = RtssRestoreResult(
            RtssOutcome.VERIFIED,
            self.generation,
            readback=restored_readback,
            captured_state=self.captured,
        )
        with self.assertRaises(ValueError):
            RtssApplyResult(
                RtssOutcome.VERIFIED,
                self.request,
                readback=self.readback,
                captured_state=self.captured,
                rollback=verified_rollback,
            )
        with self.assertRaisesRegex(ValueError, "failure step"):
            RtssApplyResult(
                RtssOutcome.VERIFIED,
                self.request,
                readback=self.readback,
                captured_state=self.captured,
                failure_step=RtssFailureStep.READBACK,
            )
        with self.assertRaisesRegex(ValueError, "must not have an error"):
            RtssApplyResult(
                RtssOutcome.VERIFIED,
                self.request,
                readback=self.readback,
                captured_state=self.captured,
                error="unexpected error",
            )

    def test_S1_REV_001_failed_rolled_back_requires_verified_matching_restore(self):
        with self.assertRaisesRegex(ValueError, "requires a rollback"):
            RtssApplyResult(
                RtssOutcome.FAILED_ROLLED_BACK,
                self.request,
                captured_state=self.captured,
                failure_step=RtssFailureStep.SAVE,
                error="save failed",
            )

        failed_rollback = RtssRestoreResult(
            RtssOutcome.DEGRADED,
            self.generation,
            captured_state=self.captured,
            failure_step=RtssFailureStep.ROLLBACK,
            error="rollback failed",
            unrestored_flag_mask=4,
        )
        with self.assertRaisesRegex(ValueError, "valid for the apply outcome"):
            RtssApplyResult(
                RtssOutcome.FAILED_ROLLED_BACK,
                self.request,
                captured_state=self.captured,
                rollback=failed_rollback,
                failure_step=RtssFailureStep.SAVE,
                error="save failed",
            )

        restored_readback = self.restored_readback()
        verified_rollback = RtssRestoreResult(
            RtssOutcome.VERIFIED,
            self.generation,
            readback=restored_readback,
            captured_state=self.captured,
        )
        result = RtssApplyResult(
            RtssOutcome.FAILED_ROLLED_BACK,
            self.request,
            readback=self.readback,
            captured_state=self.captured,
            rollback=verified_rollback,
            failure_step=RtssFailureStep.SAVE,
            error="save failed after mutation",
        )
        self.assertFalse(result.succeeded)
        self.assertTrue(result.rollback.succeeded)

    def test_S1_REV_001_failure_requires_details_and_precapture_is_state_free(self):
        with self.assertRaisesRegex(ValueError, "requires a failure step"):
            RtssApplyResult(RtssOutcome.FAILED, self.request)

        with self.assertRaisesRegex(ValueError, "pre-capture"):
            RtssApplyResult(
                RtssOutcome.STALE_GENERATION,
                self.request,
                captured_state=self.captured,
                failure_step=RtssFailureStep.GENERATION,
                error="stale generation",
            )

        rejected = RtssApplyResult(
            RtssOutcome.REJECTED_VALIDATION,
            self.request,
            failure_step=RtssFailureStep.VALIDATE,
            error="request rejected before capture",
        )
        self.assertIsNone(rejected.captured_state)
        self.assertIsNone(rejected.readback)
        self.assertIsNone(rejected.rollback)
        with self.assertRaisesRegex(ValueError, "outcome-inconsistent"):
            RtssApplyResult(
                RtssOutcome.STALE_GENERATION,
                self.request,
                failure_step=RtssFailureStep.VALIDATE,
                error="wrong rejection step",
            )

    def test_S1_REV_002_captured_state_rejects_impossible_presence_combinations(self):
        for kwargs in (
            {"cap": RationalCap(60, 1)},
            {"cap": None, "profile_revision": "revision"},
            {"cap": None, "profile_document": b"Limit=60\n"},
        ):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    CapturedProfileState(
                        self.generation,
                        5,
                        False,
                        **kwargs,
                    )

        with self.assertRaisesRegex(ValueError, "requires an exact cap"):
            CapturedProfileState(self.generation, 5, True, None)
        with self.assertRaisesRegex(ValueError, "require exact limiter flags"):
            CapturedProfileState(
                self.generation,
                5,
                True,
                RationalCap(60, 1),
                owned_flag_mask=4,
            )
        global_generation = RtssGeneration(
            1,
            2,
            3,
            CanonicalProfileIdentity.global_profile(),
        )
        with self.assertRaisesRegex(ValueError, "Global profile must exist"):
            CapturedProfileState(global_generation, 5, False, None)

    def test_S1_REV_002_readback_distinguishes_absence_from_failure(self):
        absent = RtssReadback(
            RtssOutcome.VERIFIED,
            self.generation,
            False,
            None,
            backend_generation=5,
        )
        self.assertTrue(absent.verified)

        with self.assertRaisesRegex(ValueError, "absent.*cap"):
            RtssReadback(
                RtssOutcome.VERIFIED,
                self.generation,
                False,
                self.cap,
            )
        with self.assertRaisesRegex(ValueError, "available profile revision"):
            RtssReadback(
                RtssOutcome.VERIFIED,
                self.generation,
                False,
                None,
                profile_revision="revision",
                profile_revision_availability=RtssFieldAvailability.AVAILABLE,
            )
        with self.assertRaisesRegex(ValueError, "requires an exact cap"):
            RtssReadback(
                RtssOutcome.VERIFIED,
                self.generation,
                True,
                None,
            )
        with self.assertRaisesRegex(ValueError, "requires a failure step"):
            RtssReadback(
                RtssOutcome.FAILED,
                self.generation,
                False,
                None,
            )

        failed = RtssReadback(
            RtssOutcome.FAILED,
            self.generation,
            False,
            None,
            failure_step=RtssFailureStep.READBACK,
            error="profile state unavailable",
        )
        self.assertFalse(failed.verified)

    def test_S1_FINAL_004_document_restore_requires_matching_bytes_or_hash(self):
        matching_bytes = self.restored_readback()
        self.assertTrue(
            RtssRestoreResult(
                RtssOutcome.VERIFIED,
                self.generation,
                readback=matching_bytes,
                captured_state=self.captured,
            ).succeeded
        )

        matching_hash = RtssReadback(
            RtssOutcome.VERIFIED,
            self.generation,
            True,
            self.captured.cap,
            limiter_flags=4,
            profile_revision="revision-1",
            backend_generation=5,
            profile_revision_availability=RtssFieldAvailability.AVAILABLE,
            profile_document_availability=RtssFieldAvailability.AVAILABLE,
            profile_document_sha256=sha256(self.captured.profile_document).digest(),
        )
        self.assertTrue(
            RtssRestoreResult(
                RtssOutcome.VERIFIED,
                self.generation,
                readback=matching_hash,
                captured_state=self.captured,
            ).succeeded
        )

        missing_document = RtssReadback(
            RtssOutcome.VERIFIED,
            self.generation,
            True,
            self.captured.cap,
            limiter_flags=4,
            profile_revision="revision-1",
            backend_generation=5,
            profile_revision_availability=RtssFieldAvailability.AVAILABLE,
        )
        with self.assertRaisesRegex(ValueError, "document or hash evidence"):
            RtssRestoreResult(
                RtssOutcome.VERIFIED,
                self.generation,
                readback=missing_document,
                captured_state=self.captured,
            )

        with self.assertRaisesRegex(ValueError, "document evidence must match"):
            RtssRestoreResult(
                RtssOutcome.VERIFIED,
                self.generation,
                readback=self.restored_readback(
                    profile_document=b"Limit=61\nLimitDenominator=1\n"
                ),
                captured_state=self.captured,
            )

    def test_S1_FINAL_004_revision_restore_requires_matching_evidence(self):
        missing_revision = RtssReadback(
            RtssOutcome.VERIFIED,
            self.generation,
            True,
            self.captured.cap,
            limiter_flags=4,
            backend_generation=5,
            profile_document_availability=RtssFieldAvailability.AVAILABLE,
            profile_document=self.captured.profile_document,
        )
        with self.assertRaisesRegex(ValueError, "revision evidence"):
            RtssRestoreResult(
                RtssOutcome.VERIFIED,
                self.generation,
                readback=missing_revision,
                captured_state=self.captured,
            )

        with self.assertRaisesRegex(ValueError, "revision evidence"):
            RtssRestoreResult(
                RtssOutcome.VERIFIED,
                self.generation,
                readback=self.restored_readback(profile_revision="revision-2"),
                captured_state=self.captured,
            )

    def test_S1_FINAL_004_cap_only_restore_does_not_require_document_evidence(self):
        captured = CapturedProfileState(
            self.generation,
            5,
            True,
            RationalCap(60, 1),
        )
        readback = RtssReadback(
            RtssOutcome.VERIFIED,
            self.generation,
            True,
            RationalCap(60, 1),
            backend_generation=5,
        )

        self.assertTrue(
            RtssRestoreResult(
                RtssOutcome.VERIFIED,
                self.generation,
                readback=readback,
                captured_state=captured,
            ).succeeded
        )

    def test_S1_FINAL_004_unavailable_document_evidence_is_explicit(self):
        unsupported = RtssReadback(
            RtssOutcome.UNSUPPORTED_CAPABILITY,
            self.generation,
            False,
            None,
            backend_generation=5,
            failure_step=RtssFailureStep.CAPABILITY,
            error="document readback is unsupported",
            profile_document_availability=RtssFieldAvailability.UNSUPPORTED,
        )
        unsupported_restore = RtssRestoreResult(
            RtssOutcome.UNSUPPORTED_CAPABILITY,
            self.generation,
            readback=unsupported,
            captured_state=self.captured,
            failure_step=RtssFailureStep.CAPABILITY,
            error="document-backed verification is unsupported",
            unrestored_flag_mask=4,
        )
        self.assertFalse(unsupported_restore.succeeded)

        failed = RtssReadback(
            RtssOutcome.FAILED,
            self.generation,
            False,
            None,
            backend_generation=5,
            failure_step=RtssFailureStep.READBACK,
            error="document read failed",
            profile_document_availability=RtssFieldAvailability.READ_FAILED,
        )
        degraded = RtssRestoreResult(
            RtssOutcome.DEGRADED,
            self.generation,
            readback=failed,
            captured_state=self.captured,
            failure_step=RtssFailureStep.RESTORE,
            error="document restoration cannot be verified",
            unrestored_flag_mask=4,
        )
        self.assertFalse(degraded.succeeded)

        for readback in (unsupported, failed):
            with self.subTest(availability=readback.profile_document_availability):
                with self.assertRaisesRegex(ValueError, "verified readback"):
                    RtssRestoreResult(
                        RtssOutcome.VERIFIED,
                        self.generation,
                        readback=readback,
                        captured_state=self.captured,
                    )

    def test_S1_REV_002_restore_enforces_conflicts_and_created_profile_deletion(self):
        with self.assertRaisesRegex(ValueError, "failure step"):
            RtssRestoreResult(
                RtssOutcome.VERIFIED,
                self.generation,
                readback=self.readback,
                captured_state=self.captured,
                failure_step=RtssFailureStep.CONFLICT,
                error="external edit unresolved",
            )

        missing_capture = CapturedProfileState(
            self.generation,
            5,
            False,
            None,
        )
        absent_readback = RtssReadback(
            RtssOutcome.VERIFIED,
            self.generation,
            False,
            None,
            backend_generation=5,
            profile_revision_availability=RtssFieldAvailability.VERIFIED_ABSENT,
            profile_document_availability=RtssFieldAvailability.VERIFIED_ABSENT,
        )
        deleted = RtssRestoreResult(
            RtssOutcome.VERIFIED,
            self.generation,
            readback=absent_readback,
            captured_state=missing_capture,
        )
        self.assertTrue(deleted.succeeded)

        with self.assertRaisesRegex(ValueError, "remove"):
            RtssRestoreResult(
                RtssOutcome.VERIFIED,
                self.generation,
                readback=self.readback,
                captured_state=missing_capture,
            )

        no_creation_request = RtssApplyRequest(
            self.generation,
            self.cap,
            RtssDenominatorStrategy.PROFILE_FILE,
            reason="profile must already exist",
        )
        with self.assertRaisesRegex(ValueError, "without permission"):
            RtssApplyResult(
                RtssOutcome.VERIFIED,
                no_creation_request,
                readback=self.readback,
                captured_state=missing_capture,
            )

    def test_S1_REV_002_requests_reject_unresolved_or_ambiguous_mutation_intent(self):
        global_generation = RtssGeneration(
            1,
            2,
            3,
            CanonicalProfileIdentity.global_profile(),
        )
        with self.assertRaisesRegex(ValueError, "Global profile creation"):
            RtssApplyRequest(
                global_generation,
                self.cap,
                RtssDenominatorStrategy.PROFILE_FILE,
                allow_profile_creation=True,
                reason="invalid Global creation",
            )
        for reason in ("", " \t "):
            with self.subTest(reason=repr(reason)):
                with self.assertRaisesRegex(ValueError, "empty or whitespace"):
                    RtssApplyRequest(
                        self.generation,
                        self.cap,
                        RtssDenominatorStrategy.PROFILE_FILE,
                        reason=reason,
                    )
        with self.assertRaisesRegex(ValueError, "resolved"):
            RtssApplyRequest(
                self.generation,
                self.cap,
                RtssDenominatorStrategy.UNRESOLVED,
                reason="unresolved mutation",
            )
        with self.assertRaisesRegex(ValueError, "non-empty owned mask"):
            RtssApplyRequest(
                self.generation,
                self.cap,
                RtssDenominatorStrategy.PROFILE_FILE,
                limiter_flag_values=4,
                reason="invalid flag mutation",
            )

    def test_RTSS_007_and_RTSS_009_owned_flag_values_stay_within_mask(self):
        with self.assertRaisesRegex(ValueError, "contained"):
            RtssApplyRequest(
                self.generation,
                self.cap,
                RtssDenominatorStrategy.PROFILE_FILE,
                limiter_flag_mask=4,
                limiter_flag_values=8,
                reason="invalid owned flag mutation",
            )

    def test_generation_rejects_untyped_identity_and_negative_dimensions(self):
        with self.assertRaises(TypeError):
            RtssGeneration(1, 2, 3, "game.exe")
        with self.assertRaisesRegex(ValueError, "must not be negative"):
            RtssGeneration(1, -1, 3, self.identity)


if __name__ == "__main__":
    unittest.main()
