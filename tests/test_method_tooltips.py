"""Tests for Monitoring Method and Capping Method tooltips."""

import contextlib
from types import SimpleNamespace as NS
import pytest

from core.tooltips import (
    get_tooltips,
    add_tooltip,
    apply_all_tooltips,
    update_all_tooltip_visibility,
)
from core.ui_scale import ScaledDPG


class DummyConfigManager:
    def __init__(self):
        self.input_field_keys = [
            "maxcap", "mincap", "capstep", "capratio",
            "gpucutofffordecrease", "gpucutoffforincrease",
            "cpucutofffordecrease", "cpucutoffforincrease",
            "capmethod", "customfpslimits",
            "delaybeforedecrease", "delaybeforeincrease",
            "monitoring_method"
        ]


def _setup_fake_dpg_tooltip(fake_dpg):
    def tooltip(parent=None, tag=None, **kwargs):
        fake_dpg._record("tooltip", (), {"parent": parent, "tag": tag, **kwargs})
        if tag:
            fake_dpg.items.add(tag)
        return contextlib.nullcontext()
    fake_dpg.tooltip = tooltip


def test_method_tooltips_content():
    tooltips = get_tooltips()
    assert "monitoring_method" in tooltips
    assert "capmethod" in tooltips

    assert tooltips["monitoring_method"] == (
        "Selects how hardware load is monitored. LibreHM evaluates upper and lower "
        "thresholds on enabled hardware sensors. Legacy monitors GPU 3D utilization and busiest CPU core load."
    )

    assert tooltips["capmethod"] == (
        "Selects how FPS limit steps are generated. Ratio and Step generate limits between Max "
        "and Min FPS (Ratio via percentage decreases, Step via fixed-FPS decrements). "
        "Custom uses a supplied list of limit values, falling back to Step if unavailable."
    )


def test_apply_and_visibility_tooltips_and_preserves_callbacks(fake_dpg, stub_logger):
    _setup_fake_dpg_tooltip(fake_dpg)
    cm = DummyConfigManager()

    mon_callback_sentinel = object()
    cap_callback_sentinel = object()

    fake_dpg.items.add("input_monitoring_method")
    fake_dpg.items.add("input_capmethod")
    fake_dpg.values["input_monitoring_method"] = "LibreHM"
    fake_dpg.values["input_capmethod"] = "Ratio"

    # Simulate registered callbacks on controls
    fake_dpg.configure_item("input_monitoring_method", callback=mon_callback_sentinel)
    fake_dpg.configure_item("input_capmethod", callback=cap_callback_sentinel)
    assert fake_dpg.calls[-2][2]["callback"] is mon_callback_sentinel
    assert fake_dpg.calls[-1][2]["callback"] is cap_callback_sentinel
    fake_dpg.calls.clear()

    tooltips = get_tooltips()
    for operation, show in (
        (apply_all_tooltips, True),
        (apply_all_tooltips, True),
        (update_all_tooltip_visibility, True),
        (update_all_tooltip_visibility, False),
        (update_all_tooltip_visibility, True),
    ):
        operation(fake_dpg, show, tooltips, cm, stub_logger) if operation is update_all_tooltip_visibility else operation(fake_dpg, tooltips, show, cm, stub_logger)

        # Every helper must preserve the registered sentinels and selections.
        assert fake_dpg.get_value("input_monitoring_method") == "LibreHM"
        assert fake_dpg.get_value("input_capmethod") == "Ratio"
        for call in fake_dpg.calls:
            if call[1] and call[1][0] in ("input_monitoring_method", "input_capmethod"):
                assert call[0] not in ("set_value", "set_item_callback")
                if call[0] == "configure_item":
                    assert not {"callback", "value", "default_value"}.intersection(call[2])

        if operation is update_all_tooltip_visibility:
            for tag in ("input_monitoring_method_tooltip", "input_capmethod_tooltip"):
                configs = [c for c in fake_dpg.calls if c[0] == "configure_item" and c[1][0] == tag]
                assert configs[-1][2]["show"] is show

    assert fake_dpg.does_item_exist("input_monitoring_method_tooltip")
    assert fake_dpg.does_item_exist("input_capmethod_tooltip")

    # Assert parent parameter passed to tooltip
    tooltip_calls = [c for c in fake_dpg.calls if c[0] == "tooltip"]
    parent_tags = {c[2].get("parent") for c in tooltip_calls}
    assert "input_monitoring_method" in parent_tags
    assert "input_capmethod" in parent_tags

    # Verify created text content in add_text calls
    add_text_calls = [c for c in fake_dpg.calls if c[0] == "add_text"]
    text_contents = [c[1][0] for c in add_text_calls]
    assert tooltips["monitoring_method"] in text_contents
    assert tooltips["capmethod"] in text_contents

def test_no_duplicate_tooltip_tags(fake_dpg, stub_logger):
    _setup_fake_dpg_tooltip(fake_dpg)
    cm = DummyConfigManager()
    fake_dpg.items.add("input_monitoring_method")
    fake_dpg.items.add("input_capmethod")

    tooltips = get_tooltips()
    apply_all_tooltips(fake_dpg, tooltips, True, cm, stub_logger)
    count_before = len([c for c in fake_dpg.calls if c[0] == "tooltip"])

    # Call again - idempotence should prevent duplicate creation
    apply_all_tooltips(fake_dpg, tooltips, True, cm, stub_logger)
    count_after = len([c for c in fake_dpg.calls if c[0] == "tooltip"])

    assert count_before == count_after


def test_missing_widgets_safely_skipped(fake_dpg, stub_logger):
    _setup_fake_dpg_tooltip(fake_dpg)
    cm = DummyConfigManager()
    # fake_dpg has no items added
    tooltips = get_tooltips()
    apply_all_tooltips(fake_dpg, tooltips, True, cm, stub_logger)

    assert not fake_dpg.does_item_exist("input_monitoring_method_tooltip")
    assert not fake_dpg.does_item_exist("input_capmethod_tooltip")


def test_scaled_dpg_wrap_scaling(fake_dpg, stub_logger):
    _setup_fake_dpg_tooltip(fake_dpg)
    cm = DummyConfigManager()

    # 1. Test at 96 DPI (scale = 1.0 -> wrap = 200)
    scaled_100 = ScaledDPG(fake_dpg, 1.0)
    scaled_100.items.add("input_monitoring_method")
    tooltips = get_tooltips()

    add_tooltip(scaled_100, "monitoring_method", tooltips, True, cm, stub_logger)
    add_text_100 = [c for c in fake_dpg.calls if c[0] == "add_text"][-1]
    assert add_text_100[2]["wrap"] == 200

    # 2. Test at 144 DPI (scale = 1.5 -> wrap = 300)
    fake_dpg.items.clear()
    fake_dpg.calls.clear()
    scaled_150 = ScaledDPG(fake_dpg, 1.5)
    scaled_150.items.add("input_capmethod")

    add_tooltip(scaled_150, "capmethod", tooltips, True, cm, stub_logger)
    add_text_150 = [c for c in fake_dpg.calls if c[0] == "add_text"][-1]
    assert add_text_150[2]["wrap"] == 300
