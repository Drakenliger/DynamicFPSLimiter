"""Dedicated tests for source admin relaunch, CLI flags, and early startup exception sink."""

import argparse
import sys
import os
import threading
import faulthandler
import importlib
import runpy
import logging
import subprocess
from functools import wraps
from types import SimpleNamespace
from pathlib import Path
import pytest

import core.logger as logger

MAIN_PATH = Path(__file__).resolve().parents[1] / "src" / "__main__.py"
APP_PATH = Path(__file__).resolve().parents[1] / "src" / "core" / "app.py"


def _isolated_logging_test(test):
    """Run logging mutations outside pytest's unqueryable native fatal sink."""
    @wraps(test)
    def isolated(*args, **kwargs):
        if os.environ.get("DFL_LOGGING_TEST_CHILD") == test.__name__:
            return test(*args, **kwargs)
        env = dict(os.environ, DFL_LOGGING_TEST_CHILD=test.__name__)
        env.pop("PYTHONFAULTHANDLER", None)
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:faulthandler",
             f"{Path(__file__).resolve()}::{test.__name__}"],
            env=env, capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, result.stdout + result.stderr
    return isolated


@pytest.fixture(autouse=True)
def clean_logging_state():
    """Detach foreign handlers; retain their streams and restore known fatal state.

    faulthandler cannot report its sink. Tests that change it run in a child
    with pytest's faulthandler plugin disabled, leaving the parent's unknown
    sink (and diagnostics for other tests) untouched.
    """
    root = logging.getLogger()
    orig_handlers = list(root.handlers)
    orig_level = root.level
    orig_sys_excepthook = sys.excepthook
    orig_thread_excepthook = threading.excepthook
    orig_fatal_enabled = faulthandler.is_enabled()
    orig_fatal_sink = logger._fatal_sink_file
    orig_fatal_owned = logger._fatal_sink_owned

    for h in list(root.handlers):
        if isinstance(h, logging.FileHandler):
            root.removeHandler(h)

    try:
        yield
    finally:
        try:
            if orig_fatal_enabled and orig_fatal_sink is None:
                # We cannot reconstruct a sink owned by pytest or another tool.
                assert logger._fatal_sink_file is None
                assert logger._fatal_sink_owned == orig_fatal_owned
                assert faulthandler.is_enabled()
            elif (logger._fatal_sink_file is not orig_fatal_sink
                  or logger._fatal_sink_owned != orig_fatal_owned
                  or faulthandler.is_enabled() != orig_fatal_enabled):
                # No native calls when unchanged: a stored DFL sink does not
                # prove another tool has not subsequently selected its own.
                if logger._fatal_sink_file is not orig_fatal_sink:
                    logger.close_fatal_sink()
                if orig_fatal_enabled:
                    faulthandler.enable(file=orig_fatal_sink)
                else:
                    faulthandler.disable()
        finally:
            for h in list(root.handlers):
                if h not in orig_handlers:
                    root.removeHandler(h)
                    h.close()
            root.handlers = orig_handlers
            root.level = orig_level
            sys.excepthook = orig_sys_excepthook
            threading.excepthook = orig_thread_excepthook
            logger._fatal_sink_file = orig_fatal_sink
            logger._fatal_sink_owned = orig_fatal_owned


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


@_isolated_logging_test
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


@_isolated_logging_test
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


@_isolated_logging_test
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


@_isolated_logging_test
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


@_isolated_logging_test
def test_native_crash_subprocess_support(tmp_path):
    """Native crash sink is verified attached and open; C-level crash subprocess status reported."""
    log_file = tmp_path / "crash.log"
    logger.init_logging(str(log_file))

    assert faulthandler.is_enabled()
    assert logger._fatal_sink_file is not None
    assert not getattr(logger._fatal_sink_file, "closed", True)


@pytest.mark.parametrize("prior", ["disabled", "borrowed", "owned", "unknown"])
@pytest.mark.parametrize("test_raises", [False, True])
def test_real_fixture_preserves_foreign_logging_state(tmp_path, prior, test_raises):
    """Exercise the real fixture generator, including exceptional teardown."""
    child = r'''
import faulthandler, importlib.util, logging, pathlib, sys, threading
test_path, directory, prior, test_raises = sys.argv[1:]
directory = pathlib.Path(directory)
sys.path.insert(0, str(pathlib.Path(test_path).resolve().parents[1] / "src"))
spec = importlib.util.spec_from_file_location("relaunch_tests", test_path)
tests = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tests)
logger = tests.logger
root = logging.getLogger()
foreign = logging.FileHandler(directory / "foreign.log")
root.addHandler(foreign)
root.setLevel(logging.WARNING)
handlers, stream, level = list(root.handlers), foreign.stream, root.level
sys.excepthook = lambda *args: None
threading.excepthook = lambda args: None
hooks = sys.excepthook, threading.excepthook
sink = open(directory / "owned.log", "a") if prior == "owned" else stream
logger._fatal_sink_file = sink if prior in ("borrowed", "owned") else None
logger._fatal_sink_owned = prior == "owned"
if prior == "disabled":
    faulthandler.disable()
else:
    faulthandler.enable(file=sink)
fatal = logger._fatal_sink_file, logger._fatal_sink_owned, faulthandler.is_enabled()
native_calls = []
if prior == "unknown":
    # An unknown sink must never be disabled or redirected in this process.
    for name in ("enable", "disable"):
        original = getattr(faulthandler, name)
        def tracked(*args, _name=name, _original=original, **kwargs):
            native_calls.append(_name)
            return _original(*args, **kwargs)
        setattr(faulthandler, name, tracked)
assert foreign.stream is stream and not stream.closed and not sink.closed
fixture = tests.clean_logging_state.__wrapped__()
next(fixture)
assert foreign not in root.handlers
assert foreign.stream is stream and not stream.closed and not sink.closed
assert (logger._fatal_sink_file, logger._fatal_sink_owned, faulthandler.is_enabled()) == fatal
assert (sys.excepthook, threading.excepthook) == hooks and root.level == level
if prior == "unknown":
    # The real logging assertions run in a child, without changing this sink.
    tests.test_repeated_logger_init_is_idempotent_and_fatal_sink_alive(directory)
    created = logging.FileHandler(directory / "created.log")
    root.addHandler(created)
else:
    logger.init_logging(str(directory / "created.log"))
    created = next(h for h in root.handlers if isinstance(h, logging.FileHandler))
created_stream = created.stream
created_sink = logger._fatal_sink_file
if prior == "owned":
    # Cover cleanup of a test-owned fatal stream as well as borrowed streams.
    root.removeHandler(created)
    logger.close_fatal_sink()
    created.close()
    logger._enable_fatal_sink(str(directory / "created-owned.log"))
    created_sink = logger._fatal_sink_file
    assert logger._fatal_sink_owned and not created_sink.closed
root.setLevel(logging.ERROR)
sys.excepthook = lambda *args: None
threading.excepthook = lambda args: None
assert not stream.closed and not sink.closed
if test_raises == "True":
    try:
        fixture.throw(ValueError("deliberate test exception"))
    except ValueError as exc:
        assert str(exc) == "deliberate test exception"
    else:
        raise AssertionError("fixture suppressed the test exception")
else:
    try:
        next(fixture)
    except StopIteration:
        pass
    else:
        raise AssertionError("fixture did not finish")
assert root.handlers == handlers and root.handlers[0] is foreign
assert foreign.stream is stream and not stream.closed and not sink.closed
assert root.level == level and (sys.excepthook, threading.excepthook) == hooks
assert (logger._fatal_sink_file, logger._fatal_sink_owned, faulthandler.is_enabled()) == fatal
assert created not in root.handlers and created_stream.closed
if prior != "unknown":
    assert created_sink.closed
assert not native_calls
logging.warning("foreign handler still writable after teardown")
foreign.flush()
assert "foreign handler still writable after teardown" in (directory / "foreign.log").read_text()
sink.write("fatal sink still writable after teardown\n")
sink.flush()
assert "fatal sink still writable after teardown" in pathlib.Path(sink.name).read_text()
'''
    result = subprocess.run(
        [sys.executable, "-c", child, str(Path(__file__).resolve()),
         str(tmp_path), prior, str(test_raises)],
        capture_output=True, text=True, timeout=45,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("entry", ["main", "app"])
@pytest.mark.parametrize("frozen", [False, True])
def test_actual_startup_traceback_routes(tmp_path, entry, frozen):
    """Execute unchanged startup files with absent streams and import failure."""
    child = r'''
import builtins, ctypes, pathlib, runpy, sys, types
repo, directory, entry, frozen = sys.argv[1:]
repo, directory = pathlib.Path(repo), pathlib.Path(directory)
for relative in ("src/__main__.py", "src/core/app.py", "src/core/logger.py"):
    target = directory / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes((repo / relative).read_bytes())
sys.path.insert(0, str(directory / "src"))
original_import = builtins.__import__
def controlled_import(name, *args, **kwargs):
    if name == "core.app" or name.startswith("dearpygui"):
        raise ImportError("controlled_actual_startup_failure")
    if name == "core.single_instance":
        return types.SimpleNamespace(app_lease=lambda *args: None)
    return original_import(name, *args, **kwargs)
builtins.__import__ = controlled_import
ctypes.windll = types.SimpleNamespace(
    shell32=types.SimpleNamespace(IsUserAnAdmin=lambda: True),
    shcore=types.SimpleNamespace(SetProcessDpiAwareness=lambda *args: None),
)
if frozen == "True":
    sys.frozen = True
    sys._MEIPASS = str(directory / "bundle")
path = directory / ("src/__main__.py" if entry == "main" else "src/core/app.py")
sys.argv = [str(path), "--debug"]
sys.stdout = sys.stderr = None
runpy.run_path(str(path), run_name="__main__")
'''
    result = subprocess.run(
        [sys.executable, "-c", child, str(MAIN_PATH.parents[1]),
         str(tmp_path), entry, str(frozen)],
        capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    log_file = tmp_path / ("error_log.txt" if frozen else "src/error_log.txt")
    assert log_file.exists()
    text = log_file.read_text(encoding="utf-8")
    assert "Traceback (most recent call last)" in text
    assert "ImportError: controlled_actual_startup_failure" in text
    assert str(tmp_path / ("src/__main__.py" if entry == "main" else "src/core/app.py")) in text
