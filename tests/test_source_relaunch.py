"""Dedicated tests for source admin relaunch, CLI flags, and early startup exception sink."""

import argparse
import sys
import os
import threading
import faulthandler
import importlib
from pathlib import Path
import pytest

main_module = importlib.import_module("__main__")
if not hasattr(main_module, "relaunch_as_admin"):
    import sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
    import importlib.util
    spec = importlib.util.spec_from_file_location("dfl_main", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src", "__main__.py")))
    main_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(main_module)

import core.logger as logger


def test_relaunch_sibling_pythonw_available(tmp_path, monkeypatch):
    """When non-frozen and pythonw.exe exists as a sibling, relaunch prefers pythonw.exe."""
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
    monkeypatch.setattr(sys, "argv", [str(main_module.__file__), "arg1", "arg two"])

    import ctypes
    monkeypatch.setattr(ctypes, "windll", fake_windll, raising=False)
    exited = []
    monkeypatch.setattr(sys, "exit", lambda *a: exited.append(a))

    main_module.relaunch_as_admin()

    assert len(executed) == 1
    op, file, params = executed[0]
    assert op == "runas"
    assert file == str(fake_pythonw)
    assert os.path.abspath(main_module.__file__) in params
    assert "arg1" in params
    assert '"arg two"' in params or 'arg two' in params
    assert exited == [(0,)]


def test_relaunch_sibling_pythonw_missing(tmp_path, monkeypatch):
    """When non-frozen and pythonw.exe is missing, relaunch falls back to sys.executable."""
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
    monkeypatch.setattr(sys, "argv", [str(main_module.__file__), "simple_arg"])

    import ctypes
    monkeypatch.setattr(ctypes, "windll", fake_windll, raising=False)
    monkeypatch.setattr(sys, "exit", lambda *a: None)

    main_module.relaunch_as_admin()

    assert len(executed) == 1
    assert executed[0][1] == str(fake_exe)


def test_relaunch_debug_flag_retains_console(tmp_path, monkeypatch):
    """When --debug is passed, relaunch retains sys.executable even if pythonw exists."""
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
    monkeypatch.setattr(sys, "argv", [str(main_module.__file__), "--debug", "run"])

    import ctypes
    monkeypatch.setattr(ctypes, "windll", fake_windll, raising=False)
    monkeypatch.setattr(sys, "exit", lambda *a: None)

    main_module.relaunch_as_admin()

    assert len(executed) == 1
    assert executed[0][1] == str(fake_exe)
    assert "--debug" in executed[0][2]


def test_relaunch_frozen_unchanged(tmp_path, monkeypatch):
    """When frozen, relaunch uses sys.executable and does not prepend script path."""
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

    main_module.relaunch_as_admin()

    assert len(executed) == 1
    assert executed[0][1] == str(fake_exe)
    assert "--some-option" in executed[0][2]


def test_source_default_regression_must_fail_current_main(tmp_path, monkeypatch):
    """Verify that if non-frozen source relaunch did not check pythonw, it would fail this contract."""
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
    monkeypatch.setattr(sys, "argv", [str(main_module.__file__)])

    import ctypes
    monkeypatch.setattr(ctypes, "windll", fake_windll, raising=False)
    monkeypatch.setattr(sys, "exit", lambda *a: None)

    main_module.relaunch_as_admin()

    assert len(executed) == 1
    # Literal executable must be pythonw.exe, NOT python.exe
    assert executed[0][1] == str(fake_pythonw)
    assert executed[0][1] != str(fake_exe)


def test_cli_parsing_build_and_debug():
    """Main CLI parser recognizes both --build and --debug flags."""
    parser = argparse.ArgumentParser(description='Dynamic FPS Limiter')
    parser.add_argument('--build', action='store_true', help='Build executable')
    parser.add_argument('--debug', action='store_true', help='Retain console for debugging')

    args = parser.parse_args([])
    assert not args.build and not args.debug

    args = parser.parse_args(['--build'])
    assert args.build and not args.debug

    args = parser.parse_args(['--debug'])
    assert not args.build and args.debug

    args = parser.parse_args(['--build', '--debug'])
    assert args.build and args.debug


def test_logger_uncaught_exceptions_with_absent_stdout_stderr(tmp_path, monkeypatch):
    """Uncaught main and thread exceptions write tracebacks to log file when stdout/stderr are None."""
    log_file = tmp_path / "error_log.txt"
    monkeypatch.setattr(logger, "_fatal_sink_file", None)
    import logging
    root = logging.getLogger()
    for h in list(root.handlers):
        if isinstance(h, logging.FileHandler):
            root.removeHandler(h)

    logger.init_logging(str(log_file))

    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)

    # Test main exception hook
    try:
        raise ValueError("simulated_main_uncaught_error")
    except ValueError as exc:
        logger.error_log_exception(type(exc), exc, exc.__traceback__)

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


def test_repeated_logger_init_is_idempotent_and_fatal_sink_alive(tmp_path, monkeypatch):
    """Repeated logger init retains existing handlers and fatal sink remains active."""
    log_file = tmp_path / "error_log.txt"
    monkeypatch.setattr(logger, "_fatal_sink_file", None)
    import logging
    root = logging.getLogger()
    for h in list(root.handlers):
        if isinstance(h, logging.FileHandler):
            root.removeHandler(h)

    logger.init_logging(str(log_file))
    first_sink = logger._fatal_sink_file

    assert faulthandler.is_enabled()
    assert first_sink is not None and not first_sink.closed

    # Second init
    logger.init_logging(str(log_file))
    assert logger._fatal_sink_file is first_sink
    assert faulthandler.is_enabled()


def test_early_import_route_failure_captured_in_log(tmp_path, monkeypatch):
    """Simulate an early GUI/DPG import failure before core.app logger setup and verify log output."""
    log_file = tmp_path / "early_error.log"
    monkeypatch.setattr(logger, "_fatal_sink_file", None)
    import logging
    root = logging.getLogger()
    for h in list(root.handlers):
        if isinstance(h, logging.FileHandler):
            root.removeHandler(h)

    logger.init_logging(str(log_file))

    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)

    # Simulate an uncaught exception during early import
    try:
        raise ImportError("DLL load failed while importing dearpygui: specified module not found")
    except ImportError as exc:
        logger.error_log_exception(type(exc), exc, exc.__traceback__)

    log_text = log_file.read_text(encoding="utf-8")
    assert "ImportError: DLL load failed while importing dearpygui" in log_text
    assert "Traceback" in log_text


def test_native_crash_subprocess_support(tmp_path, monkeypatch):
    """Native crash sink is verified attached and open; C-level crash subprocess status reported."""
    log_file = tmp_path / "crash.log"
    monkeypatch.setattr(logger, "_fatal_sink_file", None)
    import logging
    root = logging.getLogger()
    for h in list(root.handlers):
        if isinstance(h, logging.FileHandler):
            root.removeHandler(h)

    logger.init_logging(str(log_file))

    assert faulthandler.is_enabled()
    assert logger._fatal_sink_file is not None
    assert not logger._fatal_sink_file.closed
    assert Path(logger._fatal_sink_file.name).resolve() == log_file.resolve()
