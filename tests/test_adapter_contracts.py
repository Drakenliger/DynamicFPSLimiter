"""Contract tests for the initial deterministic TEST-002 seams."""

from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError
from decimal import Decimal

from src.core.controller_contracts import (
    FpsProcessSample,
    RationalCap,
    RtssApplyResult,
    RtssReadbackResult,
    SensorReading,
    SensorSnapshot,
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
        success_readback = RtssReadbackResult(True, cap_60, limiter_flags=4)
        success = RtssApplyResult(True, cap_60, success_readback)
        failure = RtssApplyResult(False, cap_90, None, error="save failed")
        generation = FakeGenerationFactory().create("game.exe")
        adapter = FakeRtssAdapter(
            apply_results=[success, failure],
            readback_results=[success_readback],
        )

        self.assertIs(adapter.apply_cap(generation, cap_60), success)
        self.assertIs(adapter.read_cap(generation), success_readback)
        self.assertIs(adapter.apply_cap(generation, cap_90), failure)
        self.assertEqual(
            adapter.requests,
            [
                ("apply_cap", generation, cap_60),
                ("read_cap", generation, None),
                ("apply_cap", generation, cap_90),
            ],
        )
        with self.assertRaisesRegex(RuntimeError, "RTSS apply results exhausted"):
            adapter.apply_cap(generation, cap_60)

    def test_TEST_002_represents_missing_readback_and_mismatch(self):
        requested = RationalCap(11750, 100)
        mismatched = RationalCap(117, 1)
        missing = RtssApplyResult(True, requested, None)
        mismatch = RtssApplyResult(
            True,
            requested,
            RtssReadbackResult(True, mismatched),
        )

        self.assertIsNone(missing.readback)
        self.assertNotEqual(mismatch.requested_cap, mismatch.readback.cap)


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
        self.assertEqual(source_changed.profile_generation, 21)
        self.assertEqual(source_changed.source_generation, 31)

        self.assertEqual(original.session_generation, 10)
        self.assertEqual(original.profile_generation, 20)
        self.assertEqual(original.source_generation, 30)
        with self.assertRaises(FrozenInstanceError):
            original.session_generation = 99
