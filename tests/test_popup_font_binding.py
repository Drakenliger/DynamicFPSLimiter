"""Regression test for launch popup font binding.

Ensures show_loading_popup binds loading_text to default_font (which is created and
registered by ThemesManager) rather than nonexistent regular_font or incorrect bold_font.
"""
import contextlib
import os
import sys
import types
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"


@contextlib.contextmanager
def isolated_popup_imports(monkeypatch):
    """Isolate tray dependency and popup module imports, restoring sys.modules and core package attributes on exit."""
    import core

    names = ("tray_functions", "drag_helper", "launch_popup")
    absent = object()
    saved_modules = {name: sys.modules.get("core." + name, absent) for name in names}
    saved_attrs = {name: vars(core).get(name, absent) for name in names}

    pystray_stub = types.ModuleType("pystray")
    pystray_stub.Icon = pystray_stub.MenuItem = pystray_stub.Menu = lambda *a, **k: None
    monkeypatch.setitem(sys.modules, "pystray", pystray_stub)

    try:
        for name in names:
            sys.modules.pop("core." + name, None)
            vars(core).pop(name, None)

        from core import launch_popup as lp
        from core.themes import ThemesManager

        yield lp, ThemesManager
    finally:
        for name in names:
            if saved_modules[name] is absent:
                sys.modules.pop("core." + name, None)
            else:
                sys.modules["core." + name] = saved_modules[name]

            if saved_attrs[name] is absent:
                vars(core).pop(name, None)
            else:
                setattr(core, name, saved_attrs[name])


@pytest.fixture
def popup_dpg_env(fake_dpg):
    """Set up fake_dpg environment for launch_popup testing."""
    fake_dpg.window = lambda *a, **k: contextlib.nullcontext()
    fake_dpg.theme = lambda *a, **k: contextlib.nullcontext()
    fake_dpg.theme_component = lambda *a, **k: contextlib.nullcontext()
    return fake_dpg


def test_themes_manager_font_keys(popup_dpg_env, monkeypatch):
    """Verify that ThemesManager defines default_font and not regular_font."""
    with isolated_popup_imports(monkeypatch) as (_, ThemesManager):
        monkeypatch.setenv("WINDIR", os.environ.get("WINDIR", "/fake/windir"))
        tm = ThemesManager("/fake/base", dpg=popup_dpg_env)
        assert tm.font_path.endswith("segoeui.ttf")
        assert tm.get_font("default_font") is None
        assert tm.get_font("regular_font") is None


def test_loading_popup_binds_registered_default_font(popup_dpg_env, monkeypatch):
    """Prove that show_loading_popup binds 'loading_text' to the actual registered default font handle."""
    with isolated_popup_imports(monkeypatch) as (lp, ThemesManager):
        monkeypatch.setattr(
            lp.TrayManager, "get_centered_viewport_position", staticmethod(lambda w, h: (0, 0))
        )
        lp._loading_popup_active = False

        # Assign distinct handles for each registered font based on path and size
        # default_font: segoeui.ttf @ 18 -> 1001
        # bold_font: segoeuib.ttf @ 18 -> 1002
        # monospaced_font: consola.ttf @ 14 -> 1003
        # bold_font_large: segoeuib.ttf @ 24 -> 1004
        font_handles = {
            ("segoeui.ttf", 18): 1001,
            ("segoeuib.ttf", 18): 1002,
            ("consola.ttf", 14): 1003,
            ("segoeuib.ttf", 24): 1004,
        }

        def mock_add_font(path, size):
            popup_dpg_env._record("add_font", (path, size), {})
            filename = os.path.basename(path)
            return font_handles.get((filename, size), 9999)

        popup_dpg_env.add_font = mock_add_font
        popup_dpg_env.font_registry = lambda: contextlib.nullcontext()

        monkeypatch.setenv("WINDIR", os.environ.get("WINDIR", "/fake/windir"))

        # Show loading popup with real ThemesManager
        lp.show_loading_popup("Loading...", Base_dir="/fake/base", dpg=popup_dpg_env)

        # Check font bindings on fake_dpg
        calls = popup_dpg_env.calls
        bind_font_calls = [c for c in calls if c[0] == "bind_item_font"]

        assert len(bind_font_calls) == 1
        item_id, font_id = bind_font_calls[0][1]
        assert item_id == "loading_text"

        # Explicitly verify loading_text received the default font handle (1001)
        DEFAULT_FONT_HANDLE = 1001
        BOLD_FONT_HANDLE = 1002
        assert font_id == DEFAULT_FONT_HANDLE
        assert font_id != BOLD_FONT_HANDLE

        # Ensure bind_theme was also called
        bind_theme_calls = [c for c in calls if c[0] == "bind_theme"]
        assert len(bind_theme_calls) >= 1

        lp.hide_loading_popup(dpg=popup_dpg_env)


def test_loading_popup_handles_font_binding_exceptions(popup_dpg_env, monkeypatch):
    """Preserve failure behavior: if font/theme binding raises, popup creation succeeds."""
    with isolated_popup_imports(monkeypatch) as (lp, ThemesManager):
        monkeypatch.setattr(
            lp.TrayManager, "get_centered_viewport_position", staticmethod(lambda w, h: (0, 0))
        )
        lp._loading_popup_active = False

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

    with isolated_popup_imports(monkeypatch) as (lp, _):
        monkeypatch.setattr(
            lp.TrayManager, "get_centered_viewport_position", staticmethod(lambda w, h: (0, 0))
        )
        lp._loading_popup_active = False

        monkeypatch.setenv("WINDIR", os.environ.get("WINDIR", "/fake/windir"))

        scaled_dpg = ScaledDPG(popup_dpg_env, scale=1.5)
        lp.show_loading_popup("Scaling test", Base_dir="/fake/base", dpg=scaled_dpg)

        assert lp._loading_popup_active is True

        call_names = [c[0] for c in popup_dpg_env.calls]
        assert "setup_dearpygui" in call_names
        assert "show_viewport" in call_names

        lp.hide_loading_popup(dpg=scaled_dpg)
