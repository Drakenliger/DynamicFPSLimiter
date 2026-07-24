"""Characterization tests for CTRL-001 and validation tests for CTRL-005."""

from __future__ import annotations

import ast
import copy
import unittest
from decimal import Decimal
from pathlib import Path

from src.core.cap_selection import (
    select_legacy_decrease_cap,
    validate_cap_ladder,
)


def reviewed_inline_decrease_reference(
    cap_ladder,
    current_cap,
    measured_fps,
    decrease_requested,
):
    """Test-only transcription of the reviewed CTRL-001 path."""

    if not decrease_requested or not cap_ladder:
        return None
    if current_cap == min(cap_ladder):
        return None

    try:
        lower_values = [value for value in cap_ladder if value < measured_fps]
        if lower_values:
            if current_cap <= measured_fps:
                current_index = cap_ladder.index(current_cap)
                if current_index < 0:
                    return cap_ladder[current_index - 1]
            else:
                return max(lower_values)
    except ValueError:
        lower_values = [value for value in cap_ladder if value < current_cap]
        if lower_values:
            return max(lower_values)
    return None


def load_reviewed_decrease_application_seam():
    """Compile the actual legacy decrease try/except without importing DFL."""

    dfl_path = Path(__file__).resolve().parents[1] / "src" / "core" / "DFL_v5.py"
    source = dfl_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(dfl_path))
    monitoring_loop = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "monitoring_loop"
    )
    matching_boundaries = [
        node
        for node in ast.walk(monitoring_loop)
        if isinstance(node, ast.Try)
        and any(
            isinstance(call, ast.Call)
            and isinstance(call.func, ast.Name)
            and call.func.id == "select_legacy_decrease_cap"
            for call in ast.walk(node)
        )
    ]
    if len(matching_boundaries) != 1:
        raise AssertionError(
            "expected one ValueError boundary around legacy decrease application"
        )

    wrapper = ast.parse(
        "def exercise_decrease_application("
        "fps_limit_list, current_fps_cap, fps_mean, should_decrease, "
        "current_maxcap, CurrentFPSOffset, rtss, current_profile"
        "):\n"
        "    return CurrentFPSOffset\n"
    )
    wrapper.body[0].body = [
        copy.deepcopy(matching_boundaries[0]),
        ast.Return(value=ast.Name(id="CurrentFPSOffset", ctx=ast.Load())),
    ]
    ast.fix_missing_locations(wrapper)
    namespace = {
        "select_legacy_decrease_cap": select_legacy_decrease_cap,
    }
    exec(compile(wrapper, str(dfl_path), "exec"), namespace)
    return namespace["exercise_decrease_application"]


class ScriptedLegacyRtssWriter:
    """Record legacy RTSS attempts and raise on a scripted number of calls."""

    def __init__(self, value_error_count):
        self.value_error_count = value_error_count
        self.requests = []

    def set_fractional_framerate(self, profile_name, cap):
        self.requests.append((profile_name, cap))
        if len(self.requests) <= self.value_error_count:
            raise ValueError("scripted RTSS application failure")


class LegacyDecreaseSelectionTests(unittest.TestCase):
    """CTRL-001 differential characterization without correcting the defect."""

    def test_CTRL_001_no_decrease_request_selects_nothing(self):
        self.assertIsNone(
            select_legacy_decrease_cap([30, 60, 90], 90, 75, False)
        )

    def test_CTRL_001_present_caps_do_not_step_down_at_or_below_measured_fps(self):
        ladder = [30, 60, 90]
        for current_cap in ladder:
            with self.subTest(current_cap=current_cap):
                self.assertIsNone(
                    select_legacy_decrease_cap(
                        ladder, current_cap, Decimal("120"), True
                    ),
                    "reviewed defect: a present cap does not step down",
                )

    def test_CTRL_001_missing_current_cap_falls_back_below_current_cap(self):
        self.assertEqual(
            select_legacy_decrease_cap([30, 60, 90], 75, 120, True),
            60,
        )

    def test_CTRL_001_current_cap_above_measured_fps_jumps_below_measurement(self):
        self.assertEqual(
            select_legacy_decrease_cap([30, 60, 90, 120], 120, 89, True),
            60,
        )

    def test_CTRL_001_current_cap_equal_to_measured_fps_selects_nothing(self):
        self.assertIsNone(
            select_legacy_decrease_cap([30, 60, 90], 60, 60, True)
        )

    def test_CTRL_001_no_value_below_measured_fps_selects_nothing(self):
        self.assertIsNone(
            select_legacy_decrease_cap([30, 60, 90], 90, 30, True)
        )

    def test_CTRL_001_one_element_ladder_selects_nothing(self):
        self.assertIsNone(select_legacy_decrease_cap([60], 60, 120, True))

    def test_CTRL_001_preserves_exact_decimal_values(self):
        selected = select_legacy_decrease_cap(
            [Decimal("59.94"), Decimal("60.00"), Decimal("117.50")],
            Decimal("120.00"),
            Decimal("117.50"),
            True,
        )
        self.assertEqual(selected, Decimal("60.00"))
        self.assertIsInstance(selected, Decimal)
        self.assertEqual(selected.as_tuple(), Decimal("60.00").as_tuple())

    def test_CTRL_001_matches_reviewed_inline_algorithm_over_matrix(self):
        ladders = (
            [30, 60, 90],
            [Decimal("59.94"), Decimal("60.00"), Decimal("117.50")],
            [60],
            [90, 30, 60],
        )
        current_caps = (20, 30, 45, 60, 75, 90, 120, Decimal("59.94"))
        measured_values = (20, 30, 59, 60, 75, 90, 120, Decimal("117.50"))

        for ladder in ladders:
            for current_cap in current_caps:
                for measured_fps in measured_values:
                    for decrease_requested in (False, True):
                        with self.subTest(
                            ladder=ladder,
                            current_cap=current_cap,
                            measured_fps=measured_fps,
                            decrease_requested=decrease_requested,
                        ):
                            expected = reviewed_inline_decrease_reference(
                                ladder,
                                current_cap,
                                measured_fps,
                                decrease_requested,
                            )
                            actual = select_legacy_decrease_cap(
                                ladder,
                                current_cap,
                                measured_fps,
                                decrease_requested,
                            )
                            self.assertEqual(actual, expected)


class LegacyDecreaseApplicationTests(unittest.TestCase):
    """REV-001 characterization of the reviewed ValueError boundary."""

    def test_REV_001_first_rtss_value_error_uses_reviewed_fallback(self):
        exercise = load_reviewed_decrease_application_seam()
        rtss = ScriptedLegacyRtssWriter(value_error_count=1)

        offset = exercise(
            [30, 60, 90, 120],
            120,
            89,
            True,
            120,
            0,
            rtss,
            "game.exe",
        )

        self.assertEqual(rtss.requests, [("game.exe", 60), ("game.exe", 90)])
        self.assertEqual(offset, -30)

    def test_REV_001_fallback_rtss_value_error_remains_uncaught(self):
        exercise = load_reviewed_decrease_application_seam()
        rtss = ScriptedLegacyRtssWriter(value_error_count=2)

        with self.assertRaisesRegex(
            ValueError,
            "scripted RTSS application failure",
        ):
            exercise(
                [30, 60, 90, 120],
                120,
                89,
                True,
                120,
                0,
                rtss,
                "game.exe",
            )

        self.assertEqual(rtss.requests, [("game.exe", 60), ("game.exe", 90)])


class CapLadderValidationTests(unittest.TestCase):
    """CTRL-005 pure validation scaffolding; intentionally unwired."""

    def test_CTRL_005_accepts_valid_integer_and_decimal_ladders(self):
        self.assertEqual(
            validate_cap_ladder([30, 60, 90], lower_bound=30, upper_bound=90),
            (Decimal(30), Decimal(60), Decimal(90)),
        )
        self.assertEqual(
            validate_cap_ladder(
                [Decimal("59.94"), Decimal("60.00"), Decimal("117.50")],
                lower_bound=Decimal("1"),
                upper_bound=Decimal("240"),
            ),
            (Decimal("59.94"), Decimal("60.00"), Decimal("117.50")),
        )

    def test_CTRL_005_accepts_one_element_ladder(self):
        self.assertEqual(
            validate_cap_ladder([60], lower_bound=60, upper_bound=60),
            (Decimal(60),),
        )

    def test_CTRL_005_rejects_empty_ladder(self):
        with self.assertRaises(ValueError):
            validate_cap_ladder([], lower_bound=1, upper_bound=240)

    def test_CTRL_005_rejects_duplicates(self):
        with self.assertRaises(ValueError):
            validate_cap_ladder([30, 60, 60], lower_bound=1, upper_bound=240)

    def test_CTRL_005_rejects_unsorted_values(self):
        with self.assertRaises(ValueError):
            validate_cap_ladder([30, 90, 60], lower_bound=1, upper_bound=240)

    def test_CTRL_005_rejects_non_finite_values(self):
        for value in (Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_cap_ladder([value], lower_bound=1, upper_bound=240)

    def test_CTRL_005_rejects_strings_booleans_and_binary_floats(self):
        for value in ("60", True, False, 60.0):
            with self.subTest(value=value), self.assertRaises(TypeError):
                validate_cap_ladder([value], lower_bound=1, upper_bound=240)

    def test_CTRL_005_enforces_explicit_lower_and_upper_limits(self):
        for ladder in ([29, 60], [60, 91]):
            with self.subTest(ladder=ladder), self.assertRaises(ValueError):
                validate_cap_ladder(ladder, lower_bound=30, upper_bound=90)
        self.assertEqual(
            validate_cap_ladder([30, 90], lower_bound=30, upper_bound=90),
            (Decimal(30), Decimal(90)),
        )

    def test_CTRL_005_rejects_invalid_explicit_bounds(self):
        with self.assertRaises(ValueError):
            validate_cap_ladder([60], lower_bound=90, upper_bound=30)
        for bound in (
            Decimal("NaN"),
            Decimal("Infinity"),
            Decimal("-Infinity"),
        ):
            with self.subTest(bound=bound), self.assertRaises(ValueError):
                validate_cap_ladder([60], lower_bound=bound, upper_bound=90)
        for bound in ("1", True, 1.0):
            with self.subTest(bound=bound), self.assertRaises(TypeError):
                validate_cap_ladder([60], lower_bound=bound, upper_bound=90)
