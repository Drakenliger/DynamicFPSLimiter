"""Focused regression tests for FPSUtils.copy_from_plot callback.

Ensures fractional custom caps (e.g., 30.01, 45.5, 59.99) are preserved without
whole-FPS rounding or float conversions, sorting and deduplication are maintained,
integer ladders remain numerically unchanged, and values persist correctly across
INI profile save/reload.
"""
from decimal import Decimal
from types import SimpleNamespace
import pytest


def _make_fps_utils_and_cm(fake_dpg, stub_logger, fake_lhm, tmp_path):
    from core.config_manager import ConfigManager
    from core.fps_utils import FPSUtils

    cm = ConfigManager(
        stub_logger,
        fake_dpg,
        SimpleNamespace(set_profile_property=lambda *a, **k: True),
        None,
        SimpleNamespace(themes={}),
        base_dir=str(tmp_path / "core"),
    )
    lhm_sensor = SimpleNamespace(cpu_history_long={}, gpu_history_long={})
    fu = FPSUtils(cm, lhm_sensor, stub_logger, fake_dpg, 610, base_dir=None)

    fake_dpg.set_value("input_maxcap", 114)
    fake_dpg.set_value("input_mincap", 40)
    fake_dpg.set_value("input_capstep", 5)
    fake_dpg.set_value("input_capratio", 10)

    return fu, cm


def test_copy_from_plot_fractional_custom_caps(fake_dpg, stub_logger, fake_lhm, tmp_path):
    fu, cm = _make_fps_utils_and_cm(fake_dpg, stub_logger, fake_lhm, tmp_path)

    fake_dpg.set_value("input_capmethod", "custom")
    fake_dpg.set_value("input_customfpslimits", "30.01, 45.5, 59.99")

    fu.copy_from_plot()

    copied_str = fake_dpg.get_value("input_customfpslimits")
    parsed = cm.parse_and_normalize_string_to_decimal_set(copied_str)
    expected = [Decimal("30.01"), Decimal("45.5"), Decimal("59.99")]

    assert parsed == expected
    assert copied_str == "30.01, 45.50, 59.99"


def test_copy_from_plot_unsorted_duplicate_fractional_input(fake_dpg, stub_logger, fake_lhm, tmp_path):
    fu, cm = _make_fps_utils_and_cm(fake_dpg, stub_logger, fake_lhm, tmp_path)

    fake_dpg.set_value("input_capmethod", "custom")
    fake_dpg.set_value("input_customfpslimits", "59.99, 30.01, 45.5, 30.01")

    fu.copy_from_plot()

    copied_str = fake_dpg.get_value("input_customfpslimits")
    parsed = cm.parse_and_normalize_string_to_decimal_set(copied_str)
    expected = [Decimal("30.01"), Decimal("45.5"), Decimal("59.99")]

    assert parsed == expected
    assert copied_str == "30.01, 45.50, 59.99"


def test_copy_from_plot_integer_ladders(fake_dpg, stub_logger, fake_lhm, tmp_path):
    fu, cm = _make_fps_utils_and_cm(fake_dpg, stub_logger, fake_lhm, tmp_path)

    # Step method
    fake_dpg.set_value("input_maxcap", 100)
    fake_dpg.set_value("input_mincap", 40)
    fake_dpg.set_value("input_capstep", 10)
    fake_dpg.set_value("input_capratio", 10)
    fake_dpg.set_value("input_capmethod", "step")

    fu.copy_from_plot()

    copied_step_str = fake_dpg.get_value("input_customfpslimits")
    parsed_step = cm.parse_and_normalize_string_to_decimal_set(copied_step_str)
    expected_step = [Decimal("40"), Decimal("50"), Decimal("60"), Decimal("70"), Decimal("80"), Decimal("90"), Decimal("100")]
    assert parsed_step == expected_step
    assert copied_step_str == "40, 50, 60, 70, 80, 90, 100"

    # Ratio method
    fake_dpg.set_value("input_capmethod", "ratio")

    fu.copy_from_plot()

    copied_ratio_str = fake_dpg.get_value("input_customfpslimits")
    parsed_ratio = cm.parse_and_normalize_string_to_decimal_set(copied_ratio_str)
    expected_ratio = [
        Decimal("40"), Decimal("43"), Decimal("48"), Decimal("53"), Decimal("59"),
        Decimal("66"), Decimal("73"), Decimal("81"), Decimal("90"), Decimal("100")
    ]
    assert parsed_ratio == expected_ratio
    assert copied_ratio_str == "40, 43, 48, 53, 59, 66, 73, 81, 90, 100"


def test_copy_from_plot_persists_to_ini_and_reloads(fake_dpg, stub_logger, fake_lhm, tmp_path):
    fu, cm = _make_fps_utils_and_cm(fake_dpg, stub_logger, fake_lhm, tmp_path)

    fake_dpg.set_value("input_capmethod", "custom")
    fake_dpg.set_value("input_customfpslimits", "30.01, 45.5, 59.99")

    # Set profile dropdown and save profile
    fake_dpg.set_value("profile_dropdown", "Global")
    fu.copy_from_plot()

    for key in cm.input_field_keys:
        tag = f"input_{key}"
        if fake_dpg.get_value(tag) is None and key in cm.Default_settings_original:
            fake_dpg.set_value(tag, cm.Default_settings_original[key])

    cm.save_to_profile()

    # Create a fresh ConfigManager to reload INI from the same directory
    from core.config_manager import ConfigManager

    reloaded_cm = ConfigManager(
        stub_logger,
        fake_dpg,
        SimpleNamespace(set_profile_property=lambda *a, **k: True),
        None,
        SimpleNamespace(themes={}),
        base_dir=str(tmp_path / "core"),
    )

    saved_str = reloaded_cm.profiles_config["Global"]["customfpslimits"]
    reloaded_parsed = reloaded_cm.parse_and_normalize_string_to_decimal_set(saved_str)

    expected = [Decimal("30.01"), Decimal("45.5"), Decimal("59.99")]
    assert reloaded_parsed == expected
