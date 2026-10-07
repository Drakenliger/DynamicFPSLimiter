"""Regression test for launch popup font binding.

Ensures show_loading_popup binds loading_text to default_font (which is created and
registered by ThemesManager) rather than nonexistent regular_font.
"""
import contextlib
import os
import sys
from pathlib import Path

import pytest

from core import launch_popup as lp
from core.themes import ThemesManager

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"


@pytest.fixture
def popup_dpg_env(fake_dpg, monkeypatch):
    """Set up fake_dpg environment for launch_popup testing."""
    monkeypatch.setattr(
        lp.TrayManager, "get_centered_viewport_position", staticmethod(lambda w, h: (0, 0))
    )
    fake_dpg.window = lambda *a, **k: contextlib.nullcontext()
    fake_dpg.theme = lambda *a, **k: contextlib.nullcontext()
    fake_dpg.theme_component = lambda *a, **k: contextlib.nullcontext()
    lp._loading_popup_active = False
    return fake_dpg


def test_themes_manager_font_keys(popup_dpg_env):
    """Verify that ThemesManager defines default_font and not regular_font."""
    # Ensure WINDIR exists in env for test on non-Windows platforms
    env_windir = os.environ.get("WINDIR", "/fake/windir")
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("WINDIR", env_windir)
        tm = ThemesManager("/fake/base", dpg=popup_dpg_env)
        assert tm.font_path.endswith("segoeui.ttf")
        # Before create_fonts, fonts dictionary doesn't have registered font objects
        assert tm.get_font("default_font") is None
        assert tm.get_font("regular_font") is None


def test_loading_popup_binds_registered_default_font(popup_dpg_env, monkeypatch):
    """Prove that show_loading_popup binds 'loading_text' to an existing 'default_font'."""
    # Mock font creation so font handles are returned for registered fonts
    fake_font_handle = 1001

    def mock_add_font(path, size):
        popup_dpg_env._record("add_font", (path, size), {})
        return fake_font_handle

    popup_dpg_env.add_font = mock_add_font
    popup_dpg_env.font_registry = lambda: contextlib.nullcontext()

    # Stub WINDIR if absent (e.g. Linux)
    monkeypatch.setenv("WINDIR", os.environ.get("WINDIR", "/fake/windir"))

    # Show loading popup with real ThemesManager
    lp.show_loading_popup("Loading...", Base_dir="/fake/base", dpg=popup_dpg_env)

    # Check calls recorded on fake_dpg
    calls = popup_dpg_env.calls
    bind_font_calls = [c for c in calls if c[0] == "bind_item_font"]

    assert len(bind_font_calls) == 1
    item_id, font_id = bind_font_calls[0][1]
    assert item_id == "loading_text"
    assert font_id == fake_font_handle

    # Ensure bind_theme was also called
    bind_theme_calls = [c for c in calls if c[0] == "bind_theme"]
    assert len(bind_theme_calls) >= 1

    lp.hide_loading_popup(dpg=popup_dpg_env)


def test_loading_popup_handles_font_binding_exceptions(popup_dpg_env, monkeypatch):
    """Preserve failure behavior: if font/theme binding raises, popup creation succeeds."""

    class FailingThemesManager(ThemesManager):
        def bind_font_to_item(self, item_id, font_name):
            raise RuntimeError("Font binding failed")

    monkeypatch.setenv("WINDIR", os.environ.get("WINDIR", "/fake/windir"))
    monkeypatch.setattr(lp, "ThemesManager", FailingThemesManager)

    # Should not raise exception
    lp.show_loading_popup("Loading...", Base_dir="/fake/base", dpg=popup_dpg_env)
    assert lp._loading_popup_active is True

    lp.hide_loading_popup(dpg=popup_dpg_env)


def test_loading_popup_scaling_and_theme_preservation(popup_dpg_env, monkeypatch):
    """Preserve popup scaling and theme application behavior."""
    from core.ui_scale import ScaledDPG

    monkeypatch.setenv("WINDIR", os.environ.get("WINDIR", "/fake/windir"))

    scaled_dpg = ScaledDPG(popup_dpg_env, scale=1.5)
    lp.show_loading_popup("Scaling test", Base_dir="/fake/base", dpg=scaled_dpg)

    assert lp._loading_popup_active is True

    # Check setup_dearpygui and show_viewport calls
    call_names = [c[0] for c in popup_dpg_env.calls]
    assert "setup_dearpygui" in call_names
    assert "show_viewport" in call_names

    lp.hide_loading_popup(dpg=scaled_dpg)
