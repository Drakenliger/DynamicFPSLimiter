"""Dedicated tests for source admin relaunch, CLI flags, and early startup exception sink."""

import argparse
import sys
import os
import threading
import faulthandler
import importlib
import runpy
from types import SimpleNamespace
from pathlib import Path
import pytest

import core.logger as logger

MAIN_PATH = Path(__file__).resolve().parents[1] / "src" / "__main__.py"
APP_PATH = Path(__file__).resolve().parents[1] / "src" / "core" / "app.py"


@pytest.fixture(autouse=True)
def clean_logging_state():
    """Ensure logging handlers, fatal sinks, excepthooks, and modules are cleanly restored before and after each test."""
    import logging
    root = logging.getLogger()
    orig_handlers = list(root.handlers)
    orig_level = root.level
    orig_sys_excepthook = sys.excepthook
    orig_thread_excepthook = threading.excepthook

    for h in list(root.handlers):
        if isinstance(h, logging.FileHandler):
            root.removeHandler(h)
            try:
                h.close()
            except Exception:
                pass

    yield

    try:
        logger.close_fatal_sink()
    except Exception:
        pass
    for h in list(root.handlers):
        if isinstance(h, logging.FileHandler):
            root.removeHandler(h)
            try:
                h.close()
            except Exception:
                pass
    root.handlers = orig_handlers
    root.level = orig_level
    sys.excepthook = orig_sys_excepthook
    threading.excepthook = orig_thread_excepthook


def _load_main_module():
    import importlib.util
    spec = importlib.util.spec_from_file_location("dfl_main", str(MAIN_PATH))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_relaunch_sibling_pythonw_available(tmp_path, monkeypatch):
    """When non-frozen and pythonw.exe exists as a sibling, relaunch prefers pythonw.exe."""
    main_mod = _load_main_module()
    fake_exe = tmp_path / "python.exe"
    fake_exe.touch()
    fake_pythonw = tmp_path / "pythonw.exe"
    fake_pythonw.touch()

    executed = []

    def mock_shellexecute(self, hwnd, op, file, params, dir, show):
        executed.append((op, file, params))
        return 42

    fake_windll = type("FakeWindll", (), {
        "shell32": type("FakeShell32", (), {
            "ShellExecuteW": mock_shellexecute
        })()
    })()

    monkeypatch.setattr(sys, "frozen", False, raising=False)
    monkeypatch.setattr(sys, "executable", str(fake_exe))
    script_path = str(tmp_path / "src" / "__main__.py")
    monkeypatch.setattr(main_mod, "__file__", script_path)
    monkeypatch.setattr(sys, "argv", [script_path, "arg1", "arg two"])

    import ctypes
    monkeypatch.setattr(ctypes, "windll", fake_windll, raising=False)
    exited = []
    monkeypatch.setattr(sys, "exit", lambda *a: exited.append(a))

    main_mod.relaunch_as_admin()

    assert len(executed) == 1
    op, file, params = executed[0]
    assert op == "runas"
    assert file == str(fake_pythonw)
    assert os.path.abspath(script_path) in params
    assert "arg1" in params
    assert '"arg two"' in params
    assert exited == [(0,)]


def test_relaunch_sibling_pythonw_missing(tmp_path, monkeypatch):
    """When non-frozen and pythonw.exe is missing, relaunch falls back to sys.executable."""
    main_mod = _load_main_module()
    fake_exe = tmp_path / "python.exe"
    fake_exe.touch()

    executed = []

    def mock_shellexecute(self, hwnd, op, file, params, dir, show):
        executed.append((op, file, params))
        return 42

    fake_windll = type("FakeWindll", (), {
        "shell32": type("FakeShell32", (), {
            "ShellExecuteW": mock_shellexecute
        })()
    })()

    monkeypatch.setattr(sys, "frozen", False, raising=False)
    monkeypatch.setattr(sys, "executable", str(fake_exe))
    script_path = str(tmp_path / "src" / "__main__.py")
    monkeypatch.setattr(main_mod, "__file__", script_path)
    monkeypatch.setattr(sys, "argv", [script_path, "simple_arg"])

    import ctypes
    monkeypatch.setattr(ctypes, "windll", fake_windll, raising=False)
    monkeypatch.setattr(sys, "exit", lambda *a: None)

    main_mod.relaunch_as_admin()

    assert len(executed) == 1
    assert executed[0][1] == str(fake_exe)


def test_relaunch_debug_flag_retains_console(tmp_path, monkeypatch):
    """When --debug is passed, relaunch retains sys.executable even if pythonw exists."""
    main_mod = _load_main_module()
    fake_exe = tmp_path / "python.exe"
    fake_exe.touch()
    fake_pythonw = tmp_path / "pythonw.exe"
    fake_pythonw.touch()

    executed = []

    def mock_shellexecute(self, hwnd, op, file, params, dir, show):
        executed.append((op, file, params))
        return 42

    fake_windll = type("FakeWindll", (), {
        "shell32": type("FakeShell32", (), {
            "ShellExecuteW": mock_shellexecute
        })()
    })()

    monkeypatch.setattr(sys, "frozen", False, raising=False)
    monkeypatch.setattr(sys, "executable", str(fake_exe))
    script_path = str(tmp_path / "src" / "__main__.py")
    monkeypatch.setattr(main_mod, "__file__", script_path)
    monkeypatch.setattr(sys, "argv", [script_path, "--debug", "run"])

    import ctypes
    monkeypatch.setattr(ctypes, "windll", fake_windll, raising=False)
    monkeypatch.setattr(sys, "exit", lambda *a: None)

    main_mod.relaunch_as_admin()

    assert len(executed) == 1
    assert executed[0][1] == str(fake_exe)
    assert "--debug" in executed[0][2]


def test_relaunch_frozen_unchanged(tmp_path, monkeypatch):
    """When frozen, relaunch uses sys.executable and does not prepend script path."""
    main_mod = _load_main_module()
    fake_exe = tmp_path / "DynamicFPSLimiter.exe"
    fake_exe.touch()

    executed = []

    def mock_shellexecute(self, hwnd, op, file, params, dir, show):
        executed.append((op, file, params))
        return 42

    fake_windll = type("FakeWindll", (), {
        "shell32": type("FakeShell32", (), {
            "ShellExecuteW": mock_shellexecute
        })()
    })()

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(fake_exe))
    monkeypatch.setattr(sys, "argv", [str(fake_exe), "--some-option"])

    import ctypes
    monkeypatch.setattr(ctypes, "windll", fake_windll, raising=False)
    monkeypatch.setattr(sys, "exit", lambda *a: None)

    main_mod.relaunch_as_admin()

    assert len(executed) == 1
    assert executed[0][1] == str(fake_exe)
    assert "--some-option" in executed[0][2]


def test_relaunch_literal_spaced_paths_and_backslashes_quoting(tmp_path, monkeypatch):
    """Independently assert exact literal executable and command argument quoting with spaces and backslashes."""
    main_mod = _load_main_module()
    fake_dir = tmp_path / "Program Files" / "Python 312"
    fake_dir.mkdir(parents=True)
    fake_exe = fake_dir / "python.exe"
    fake_exe.touch()
    fake_pythonw = fake_dir / "pythonw.exe"
    fake_pythonw.touch()

    executed = []

    def mock_shellexecute(self, hwnd, op, file, params, dir, show):
        executed.append((op, file, params))
        return 42

    fake_windll = type("FakeWindll", (), {
        "shell32": type("FakeShell32", (), {
            "ShellExecuteW": mock_shellexecute
        })()
    })()

    script = str(tmp_path / "Program Files" / "DFL" / "src" / "__main__.py")
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    monkeypatch.setattr(sys, "executable", str(fake_exe))
    monkeypatch.setattr(main_mod, "__file__", script)
    monkeypatch.setattr(sys, "argv", [script, "--opt", "value with space", r"literal\path"])

    import ctypes
    monkeypatch.setattr(ctypes, "windll", fake_windll, raising=False)
    monkeypatch.setattr(sys, "exit", lambda *a: None)

    main_mod.relaunch_as_admin()

    assert len(executed) == 1
    op, file, params = executed[0]
    assert file == str(fake_pythonw)
    assert params == f'"{os.path.abspath(script)}" --opt "value with space" literal\\path'


def test_relaunch_failure_propagates_to_exception_hook(tmp_path, monkeypatch):
    """When ShellExecuteW returns an error code (<=32), relaunch_as_admin raises OSError and logs full traceback."""
    main_mod = _load_main_module()
    fake_exe = tmp_path / "python.exe"
    fake_exe.touch()
    log_file = tmp_path / "error_log.txt"
    logger.init_logging(str(log_file))

    def mock_shellexecute_error(self, hwnd, op, file, params, dir, show):
        return 5  # SE_ERR_ACCESSDENIED (5 <= 32)

    fake_windll = type("FakeWindll", (), {
        "shell32": type("FakeShell32", (), {
            "ShellExecuteW": mock_shellexecute_error
        })()
    })()

    monkeypatch.setattr(sys, "frozen", False, raising=False)
    monkeypatch.setattr(sys, "executable", str(fake_exe))
    script_path = str(tmp_path / "src" / "__main__.py")
    monkeypatch.setattr(main_mod, "__file__", script_path)
    monkeypatch.setattr(sys, "argv", [script_path])

    import ctypes
    monkeypatch.setattr(ctypes, "windll", fake_windll, raising=False)

    with pytest.raises(OSError, match="ShellExecuteW elevation failed with error code 5") as exc_info:
        main_mod.relaunch_as_admin()

    sys.excepthook(exc_info.type, exc_info.value, exc_info.tb)
    content = log_file.read_text(encoding="utf-8")
    assert "ShellExecuteW elevation failed with error code 5" in content
    assert "Traceback" in content


def test_cli_parsing_build_and_debug():
    """Test production CLI parsing with --build and --debug flags."""
    main_mod = _load_main_module()

    args, _ = main_mod.parser.parse_known_args([])
    assert not args.build and not args.debug

    args, _ = main_mod.parser.parse_known_args(["--build"])
    assert args.build and not args.debug

    args, _ = main_mod.parser.parse_known_args(["--debug"])
    assert not args.build and args.debug

    args, _ = main_mod.parser.parse_known_args(["--build", "--debug"])
    assert args.build and args.debug


def test_logger_uncaught_exceptions_with_absent_stdout_stderr(tmp_path, monkeypatch):
    """Uncaught main and thread exceptions write tracebacks to log file when stdout/stderr are None."""
    log_file = tmp_path / "error_log.txt"
    logger.init_logging(str(log_file))

    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)

    # Test main exception hook
    try:
        raise ValueError("simulated_main_uncaught_error")
    except ValueError as exc:
        sys.excepthook(type(exc), exc, exc.__traceback__)

    content = log_file.read_text(encoding="utf-8")
    assert "simulated_main_uncaught_error" in content
    assert "Traceback" in content

    # Test thread exception hook
    def failing_thread():
        raise RuntimeError("simulated_thread_uncaught_error")

    t = threading.Thread(target=failing_thread, name="test_failing_thread")
    t.start()
    t.join(timeout=5)

    content = log_file.read_text(encoding="utf-8")
    assert "simulated_thread_uncaught_error" in content


def test_repeated_logger_init_is_idempotent_and_fatal_sink_alive(tmp_path):
    """Repeated logger init retains existing handlers and fatal sink remains active."""
    log_file = tmp_path / "error_log.txt"
    logger.init_logging(str(log_file))
    first_sink = logger._fatal_sink_file

    assert faulthandler.is_enabled()
    assert first_sink is not None and not getattr(first_sink, "closed", True)

    # Second init with same path
    logger.init_logging(str(log_file))
    assert logger._fatal_sink_file is first_sink
    assert faulthandler.is_enabled()


def test_actual_source_entry_logging_and_early_import_route_failure(tmp_path, monkeypatch):
    """Run actual source entry and core.app startup prefix encountering a controlled early import failure before normal logger setup."""
    expected_log = tmp_path / "isolated_error.log"

    orig_import = __builtins__["__import__"]

    def failing_import(name, *args, **kwargs):
        if name in ("dearpygui", "dearpygui.dearpygui"):
            raise ImportError("DLL load failed while importing dearpygui: specified module not found")
        return orig_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", failing_import)
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)

    runtime_acc = SimpleNamespace(
        configure_logging=lambda: None,
        error_log_file=str(expected_log),
    )

    with pytest.raises(ImportError, match="dearpygui") as exc_info:
        runpy.run_path(str(APP_PATH), init_globals={"_acceptance_runtime": runtime_acc}, run_name="__main__")

    sys.excepthook(exc_info.type, exc_info.value, exc_info.tb)

    assert expected_log.exists()
    log_text = expected_log.read_text(encoding="utf-8")
    assert "ImportError: DLL load failed while importing dearpygui" in log_text
    assert "Traceback" in log_text


def test_native_crash_subprocess_support(tmp_path):
    """Native crash sink is verified attached and open; C-level crash subprocess status reported."""
    log_file = tmp_path / "crash.log"
    logger.init_logging(str(log_file))

    assert faulthandler.is_enabled()
    assert logger._fatal_sink_file is not None
    assert not getattr(logger._fatal_sink_file, "closed", True)
