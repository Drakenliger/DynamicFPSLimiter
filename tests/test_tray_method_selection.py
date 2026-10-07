"""Portable integration of tray actions, GUI queue and actual method policy.

Compose production methods without importing pystray or Windows/.NET modules;
only the native menu item boundary is represented by a local stand-in.
"""
import ast
from pathlib import Path
import threading
from types import SimpleNamespace

import pytest

from core.gui_queue import GuiQueue

CORE = Path(__file__).resolve().parents[1] / "src" / "core"


def _production_methods(filename, class_name, names, namespace):
    path = CORE / filename
    tree = ast.parse(path.read_text(encoding="utf-8"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef)
               and node.name == class_name)
    methods = [node for node in cls.body if isinstance(node, ast.FunctionDef)
               and node.name in names]
    assert {node.name for node in methods} == set(names)
    exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), "exec"), namespace)
    return type(class_name, (), {name: namespace[name] for name in names})


def _radio_options():
    tree = ast.parse((CORE / "app.py").read_text(encoding="utf-8"))
    radios = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
              and isinstance(node.func, ast.Attribute)
              and node.func.attr == "add_radio_button"
              and any(kw.arg == "tag" and isinstance(kw.value, ast.Constant)
                      and kw.value.value == "input_capmethod" for kw in node.keywords)]
    assert len(radios) == 1
    return ast.literal_eval(next(kw.value for kw in radios[0].keywords if kw.arg == "items"))


@pytest.mark.parametrize("label, canonical, enabled", [
    ("Ratio", "ratio", {"input_capratio", "label_capratio", "label_maxcap",
                         "label_mincap", "input_maxcap", "input_mincap"}),
    ("Step", "step", {"input_capstep", "label_capstep", "label_maxcap",
                       "label_mincap", "input_maxcap", "input_mincap"}),
    ("Custom", "custom", {"input_customfpslimits"}),
])
def test_tray_method_selection_agrees_with_radio_and_policy(fake_dpg, label, canonical, enabled):
    class MenuItem:
        def __init__(self, text, action):
            self.text = text
            self.action = action

    Tray = _production_methods("tray_functions.py", "TrayManager", [
        "_method_menu_items", "_run_on_main", "_select_method_from_tray",
    ], {"MenuItem": MenuItem})
    Config = _production_methods("config_manager.py", "ConfigManager", [
        "current_method_callback",
    ], {})
    cm = Config()
    cm.dpg = fake_dpg
    cm.current_method = "unchanged"
    cm.themes = {"enabled_text_theme": "enabled", "disabled_text_theme": "disabled"}
    cm.tray = None
    logs = []
    cm.logger = SimpleNamespace(add_log=logs.append)
    callbacks = []
    actual_callback = cm.current_method_callback

    def record_callback(sender, app_data, user_data):
        callbacks.append((sender, app_data, user_data, threading.current_thread()))
        actual_callback(sender, app_data, user_data)

    cm.current_method_callback = record_callback
    errors = []
    queue = GuiQueue(on_error=lambda fn, exc: errors.append(exc))
    tray = Tray()
    tray.dpg, tray.cm, tray.gui_queue = fake_dpg, cm, queue
    # Icon/menu refresh is outside the selection contract and native boundary.
    tray._update_menu = lambda: None
    tray.update_hover_text = lambda: None
    items = list(tray._method_menu_items())
    options = _radio_options()
    assert [item.text for item in items] == options
    item = next(item for item in items if item.text == label)
    worker = threading.Thread(target=item.action, args=(None, None))
    worker.start()
    worker.join(timeout=5)
    assert not worker.is_alive()
    assert fake_dpg.calls == []
    assert callbacks == []
    assert logs == []
    assert cm.current_method == "unchanged"
    assert len(queue) == 1

    assert queue.drain() == 1
    assert errors == []
    assert len(queue) == 0
    assert len(callbacks) == 1
    assert callbacks[0] == (None, canonical, None, threading.main_thread())
    value = fake_dpg.values["input_capmethod"]
    assert value == label
    assert value in options
    assert value.lower() == cm.current_method == canonical
    writes = [call for call in fake_dpg.calls if call[0] == "set_value"]
    assert len(writes) == 1
    assert writes[0][1] == ("input_capmethod", label)
    themes = {call[1][0]: call[1][1] for call in fake_dpg.calls
              if call[0] == "bind_item_theme"}
    assert {tag for tag, theme in themes.items() if theme == "enabled"} == enabled
    assert all(theme == ("enabled" if tag in enabled else "disabled")
               for tag, theme in themes.items())
    assert logs == [f"Method selection changed: {canonical}"]
    assert all(call[3] == threading.main_thread().name for call in fake_dpg.calls)
