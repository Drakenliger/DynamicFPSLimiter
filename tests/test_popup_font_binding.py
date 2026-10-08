"""Tests for launch popup font binding to registered default_font."""
import contextlib
import pytest
from core import launch_popup as lp
from core.ui_scale import ScaledDPG, resolve_scale

CONTEXT_NAMES = {
    "window", "child_window", "plot", "plot_axis", "table", "table_row",
    "group", "tab", "tab_bar", "drawlist", "draw_layer", "theme",
    "theme_component", "font_registry", "texture_registry",
    "handler_registry", "tooltip", "collapsing_header"
}


def _setup_fake_dpg(fake_dpg):
    """Ensure FakeDPG returns nullcontexts for DPG container macros."""
    for ctx in CONTEXT_NAMES:
        setattr(fake_dpg, ctx, lambda *a, **k: contextlib.nullcontext(123))


@pytest.mark.parametrize("dpi", [96, 144])
def test_loading_popup_binds_default_font_at_96_and_144_dpi(fake_dpg, tmp_path, monkeypatch, dpi):
    _setup_fake_dpg(fake_dpg)
    monkeypatch.setenv("WINDIR", "/windows")
    monkeypatch.setattr(
        lp.TrayManager, "get_centered_viewport_position", staticmethod(lambda w, h: (0, 0))
    )
    lp._loading_popup_active = False

    font_counter = 0

    def _add_font(*args, **kwargs):
        nonlocal font_counter
        font_counter += 1
        return 1000 + font_counter

    fake_dpg.add_font = _add_font

    scale = resolve_scale("Auto", dpi)
    dpg_adapter = ScaledDPG(fake_dpg, scale)

    base_dir = str(tmp_path / "core")
    lp.show_loading_popup("Loading...", Base_dir=base_dir, dpg=dpg_adapter)

    # FakeDPG call records contain four fields: (name, args, kwargs, thread_name)
    bind_calls = [
        (args, kwargs) for name, args, kwargs, _ in fake_dpg.calls if name == "bind_item_font"
    ]

    # The default_font handle returned by the first add_font call is 1001.
    expected_default_font_handle = 1001

    assert any(
        args == ("loading_text", expected_default_font_handle) for args, _ in bind_calls
    ), f"loading_text was not bound to default_font handle {expected_default_font_handle}. Recorded calls: {bind_calls}"


def test_loading_popup_handles_font_failure_nonfatally(fake_dpg, tmp_path, monkeypatch):
    _setup_fake_dpg(fake_dpg)
    monkeypatch.setenv("WINDIR", "/windows")
    monkeypatch.setattr(
        lp.TrayManager, "get_centered_viewport_position", staticmethod(lambda w, h: (0, 0))
    )
    lp._loading_popup_active = False

    def _failing_add_font(*args, **kwargs):
        raise OSError("Font file not found")

    fake_dpg.add_font = _failing_add_font

    base_dir = str(tmp_path / "core")
    # Should complete without raising exception
    lp.show_loading_popup("Loading...", Base_dir=base_dir, dpg=fake_dpg)
    assert lp._loading_popup_active is True
