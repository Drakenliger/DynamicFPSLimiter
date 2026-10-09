"""Execute real startup binding/order without opening logging or native sinks."""

import ast
import builtins
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

import core.logger as logger


APP_PATH = Path(__file__).resolve().parents[1] / "src" / "core" / "app.py"


@pytest.mark.parametrize("frozen", [False, True])
@pytest.mark.parametrize("acceptance", [False, True])
def test_actual_startup_logger_binding(tmp_path, monkeypatch, frozen, acceptance):
    # Read at execution time so the runner can substitute baseline text in memory
    # via Path.read_text. Compile the entire original prefix, not just the helper;
    # no logger binding is seeded in the app namespace or supplied by an import fake.
    source = APP_PATH.read_text(encoding="utf-8")
    first_use = next(
        node for node in ast.parse(source).body
        if isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Attribute)
        and isinstance(node.value.func.value, ast.Name)
        and node.value.func.value.id == "logger"
        and node.value.func.attr == "set_dpg"
    )
    prefix = "".join(source.splitlines(keepends=True)[:first_use.end_lineno])
    events = []
    monkeypatch.setattr(logger, "init_logging", lambda path: events.append(("init", path)))
    monkeypatch.setattr(logger, "set_dpg", lambda dpg: events.append(("set_dpg", dpg)))
    monkeypatch.setattr(sys, "path", list(sys.path))
    monkeypatch.setattr(sys, "frozen", frozen, raising=False)
    bundle = tmp_path / "frozen bundle"
    if frozen:
        monkeypatch.setattr(sys, "_MEIPASS", str(bundle), raising=False)
    else:
        monkeypatch.delattr(sys, "_MEIPASS", raising=False)

    dpg = ModuleType("dearpygui.dearpygui")
    package = ModuleType("dearpygui")
    package.__path__ = []
    package.dearpygui = dpg
    monkeypatch.setitem(sys.modules, "dearpygui", package)
    monkeypatch.setitem(sys.modules, "dearpygui.dearpygui", dpg)

    lease = object()
    handle = object()

    def app_lease(value):
        events.append(("lease", value))
        return lease

    def unblock(paths):
        events.append(("unblock", paths))
        return True

    stubs = {
        "core.single_instance": SimpleNamespace(app_lease=app_lease),
        "core.ui_scale": SimpleNamespace(**dict.fromkeys(
            ("ScaledDPG", "UI_SCALE_CHOICES", "enable_native_dpi",
             "primary_monitor_dpi", "read_preference", "resolve_scale", "pixels")
        )),
        "core.pre_launch": SimpleNamespace(
            _unblock_alternate_data_streams=unblock, mark_first_launch_done=None,
        ),
    }
    original_import = builtins.__import__

    def controlled_import(name, *args, **kwargs):
        if name in stubs or name == "dearpygui.dearpygui":
            events.append(("import", name))
        if name in stubs:
            return stubs[name]
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", controlled_import)
    namespace = {"__file__": str(APP_PATH), "_single_instance_handle": handle}
    expected = []
    if acceptance:
        sink = str(tmp_path / "acceptance logs" / "error_log.txt")
        namespace["_acceptance_runtime"] = SimpleNamespace(
            configure_logging=lambda: events.append(("configure_logging", sink)),
            error_log_file=sink,
        )
        expected.append(("configure_logging", sink))
    else:
        base = bundle if frozen else APP_PATH.parent
        sink = str(base.parent / "error_log.txt")
    expected.extend([
        ("init", sink),
        ("import", "core.single_instance"),
        ("lease", handle),
        ("import", "dearpygui.dearpygui"),
        ("import", "core.ui_scale"),
        ("import", "core.pre_launch"),
    ])
    if not acceptance:
        expected.append(("unblock", [str(base.parent)]))
    expected.append(("set_dpg", dpg))

    assert "logger" not in namespace
    exec(compile(prefix, str(APP_PATH), "exec"), namespace)

    assert namespace["logger"] is logger
    assert namespace["_instance_lease"] is lease
    assert namespace["DLLs_unblocked"] is (not acceptance)
    assert events == expected
    assert list(tmp_path.iterdir()) == []
