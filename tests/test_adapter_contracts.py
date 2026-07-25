"""Contract tests for the initial deterministic TEST-002 seams."""

from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError
from decimal import Decimal

from src.core.controller_contracts import (
    FpsProcessSample,
    RationalCap as ControllerRationalCap,
    RtssApplyResult as ControllerRtssApplyResult,
    RtssGeneration as ControllerRtssGeneration,
    RtssReadback as ControllerRtssReadback,
    SensorReading,
    SensorSnapshot,
)
from src.core.rtss_contracts import (
    CapturedProfileState,
    RationalCap,
    RtssApplyRequest,
    RtssApplyResult,
    RtssDenominatorStrategy,
    RtssFailureStep,
    RtssGeneration,
    RtssOutcome,
    RtssReadback,
    RtssRestoreResult,
)
from tests.fakes import (
    FakeClock,
    FakeGenerationFactory,
    FakeRtssAdapter,
    ScriptedFpsProcessSource,
    ScriptedSensorSource,
)


class FakeClockContractTests(unittest.TestCase):
    def test_TEST_002_fake_clock_advances_without_sleeping(self):
        clock = FakeClock(Decimal("10.25"))
        self.assertEqual(clock.monotonic(), Decimal("10.25"))
        self.assertEqual(clock.advance(Decimal("0.75")), Decimal("11.00"))
        self.assertEqual(clock.monotonic(), Decimal("11.00"))

    def test_TEST_002_fake_clock_rejects_negative_advancement(self):
        clock = FakeClock()
        with self.assertRaises(ValueError):
            clock.advance(-1)
        self.assertEqual(clock.monotonic(), Decimal(0))


class ScriptedSourceContractTests(unittest.TestCase):
    def test_TEST_002_fps_process_sequence_is_deterministic(self):
        first = FpsProcessSample(Decimal("1"), Decimal("59.94"), "a.exe", 3)
        second = FpsProcessSample(Decimal("2"), None, None, 4, valid=False)
        source = ScriptedFpsProcessSource([first, second])

        self.assertIs(source.read_sample(), first)
        self.assertIs(source.read_sample(), second)
        with self.assertRaisesRegex(RuntimeError, "FPS/process samples exhausted"):
            source.read_sample()

    def test_TEST_002_sensor_sequence_is_deterministic_and_immutable(self):
        reading = SensorReading(
            "gpu/0",
            "gpu/0/load/0",
            "GPU Core",
            "Load",
            Decimal("82.5"),
            Decimal("5"),
        )
        mutable_input = [reading]
        snapshot = SensorSnapshot(Decimal("5"), 7, mutable_input)
        mutable_input.clear()
        source = ScriptedSensorSource([snapshot])

        self.assertEqual(source.read_snapshot().readings, (reading,))
        with self.assertRaises(FrozenInstanceError):
            snapshot.source_generation = 8
        with self.assertRaisesRegex(RuntimeError, "sensor snapshots exhausted"):
            source.read_snapshot()


class FakeRtssContractTests(unittest.TestCase):
    def test_TEST_002_queues_results_and_records_requests_in_order(self):
        cap_60 = RationalCap(60, 1)
        cap_90 = RationalCap(90, 1)
        generation = FakeGenerationFactory().create("game.exe")
        request_60 = RtssApplyRequest(
            generation,
            cap_60,
            RtssDenominatorStrategy.PROFILE_FILE,
            reason="test request 60",
        )
        request_90 = RtssApplyRequest(
            generation,
            cap_90,
            RtssDenominatorStrategy.PROFILE_FILE,
            reason="test request 90",
        )
        success_readback = RtssReadback(
            RtssOutcome.VERIFIED,
            generation,
            True,
            cap_60,
            limiter_flags=4,
            backend_generation=7,
        )
        captured = CapturedProfileState(
            generation,
            7,
            True,
            cap_90,
        )
        success = RtssApplyResult(
            RtssOutcome.VERIFIED,
            request_60,
            success_readback,
            captured,
        )
        failure = RtssApplyResult(
            RtssOutcome.FAILED,
            request_90,
            failure_step=RtssFailureStep.CAPTURE,
            error="capture failed before mutation",
        )
        adapter = FakeRtssAdapter(
            apply_results=[success, failure],
            readback_results=[success_readback],
        )

        self.assertIs(adapter.apply(request_60), success)
        self.assertIs(adapter.read(generation), success_readback)
        self.assertIs(adapter.apply(request_90), failure)
        self.assertEqual(
            adapter.requests,
            [
                ("apply", request_60),
                ("read", generation),
                ("apply", request_90),
            ],
        )
        with self.assertRaisesRegex(RuntimeError, "RTSS apply results exhausted"):
            adapter.apply(request_60)

    def test_TEST_002_represents_missing_readback_and_mismatch(self):
        requested = RationalCap(11750, 100)
        mismatched = RationalCap(117, 1)
        generation = FakeGenerationFactory().create("game.exe")
        request = RtssApplyRequest(
            generation,
            requested,
            RtssDenominatorStrategy.PROFILE_FILE,
            reason="test fractional request",
        )
        captured = CapturedProfileState(
            generation,
            7,
            True,
            mismatched,
        )
        failed_rollback = RtssRestoreResult(
            RtssOutcome.DEGRADED,
            generation,
            captured_state=captured,
            failure_step=RtssFailureStep.ROLLBACK,
            error="rollback readback missing",
        )
        missing = RtssApplyResult(
            RtssOutcome.DEGRADED,
            request,
            captured_state=captured,
            rollback=failed_rollback,
            failure_step=RtssFailureStep.READBACK,
            error="readback missing and rollback unverified",
        )
        mismatch_readback = RtssReadback(
            RtssOutcome.VERIFIED,
            generation,
            True,
            mismatched,
            backend_generation=7,
        )
        mismatch = RtssApplyResult(
            RtssOutcome.FAILED,
            request,
            mismatch_readback,
            captured,
            failure_step=RtssFailureStep.READBACK,
            error="request mismatch with exact no-change proof",
        )

        self.assertIsNone(missing.readback)
        self.assertFalse(missing.succeeded)
        self.assertNotEqual(mismatch.request.cap, mismatch.readback.cap)
        self.assertFalse(mismatch.succeeded)

    def test_TEST_002_controller_contracts_reexport_canonical_rtss_models(self):
        self.assertIs(ControllerRationalCap, RationalCap)
        self.assertIs(ControllerRtssApplyResult, RtssApplyResult)
        self.assertIs(ControllerRtssGeneration, RtssGeneration)
        self.assertIs(ControllerRtssReadback, RtssReadback)


class GenerationContractTests(unittest.TestCase):
    def test_TEST_002_generation_dimensions_vary_independently(self):
        factory = FakeGenerationFactory(
            application_generation=9,
            session_generation=10,
            profile_generation=20,
            source_generation=30,
        )
        original = factory.create("game-a.exe")

        factory.advance_session()
        session_changed = factory.create("game-a.exe")
        factory.advance_profile()
        profile_changed = factory.create("game-b.exe")
        factory.advance_source()
        source_changed = factory.create("game-b.exe")

        self.assertEqual(session_changed.session_generation, 11)
        self.assertEqual(session_changed.profile_generation, 20)
        self.assertEqual(session_changed.source_generation, 30)
        self.assertEqual(profile_changed.session_generation, 11)
        self.assertEqual(profile_changed.profile_generation, 21)
        self.assertEqual(profile_changed.source_generation, 30)
        self.assertEqual(profile_changed.profile_identity.name, "game-b.exe")
        self.assertEqual(source_changed.profile_generation, 21)
        self.assertEqual(source_changed.source_generation, 31)

        self.assertEqual(original.session_generation, 10)
        self.assertEqual(original.profile_generation, 20)
        self.assertEqual(original.source_generation, 30)
        self.assertEqual(original.profile_identity.name, "game-a.exe")
        with self.assertRaises(FrozenInstanceError):
            original.session_generation = 99
