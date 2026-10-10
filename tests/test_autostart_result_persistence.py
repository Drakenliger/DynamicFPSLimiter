"""Real app callers must persist disabled autostart after failed task creation.

Execute app.py's source AST without importing its GUI/native startup. Only the
Windows identity and subprocess boundaries are replaced; ConfigManager reads
and writes real temporary INIs, with the existing fake DPG/LHM fixtures.
"""
import ast
import configparser
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

import core.autostart as autostart


APP_SOURCE = Path(__file__).resolve().parents[1] / "src/core/app.py"
APP_PATH = r"C:\DynamicFPSLimiter\DFL.exe"
TASK_NAME = "DFL_PersistenceTest"
USER_ID = r"DOMAIN\InteractiveUser"
MISSING_HRESULT = 0x80070002


class NativeRun:
    """Simulate schtasks at the native boundary, never launching a process."""

    def __init__(self, *, fail_create=False, task_exists=False):
        self.fail_create = fail_create
        self.task_exists = task_exists
        self.commands = []
        self.create_files = []

    def __call__(self, args, **kwargs):
        assert isinstance(args, list) and args[0] == "schtasks"
        assert kwargs["creationflags"] == autostart.CREATE_NO_WINDOW
        assert not kwargs.get("shell", False)
        assert args[args.index("/TN") + 1] == TASK_NAME
        self.commands.append(args[1])
        if args[1] == "/Create":
            assert kwargs["check"] is True
            xml_path = Path(args[args.index("/XML") + 1])
            self.create_files.append(xml_path)
            assert autostart.task_xml_matches(xml_path.read_bytes(), APP_PATH, USER_ID)
            if self.fail_create:
                # check=True raises rather than returning a nonzero result.
                raise subprocess.CalledProcessError(1, args, stderr="Access denied")
            return subprocess.CompletedProcess(args, 0)
        if args[1] == "/Query":
            if "/HRESULT" in args:
                return subprocess.CompletedProcess(
                    args, 0 if self.task_exists else MISSING_HRESULT,
                    stdout="", stderr="",
                )
            assert "/XML" in args and kwargs["check"] is True
            return subprocess.CompletedProcess(
                args, 0,
                stdout=autostart.build_task_xml(APP_PATH, USER_ID).decode("utf-16"),
                stderr="",
            )
        assert args[1] == "/Delete" and kwargs["check"] is True
        return subprocess.CompletedProcess(args, 0)


@pytest.fixture
def harness(tmp_path, fake_dpg, fake_lhm, stub_logger, monkeypatch):
    # Import after native fixtures are installed; all initialization paths are
    # temporary and sensor discovery uses FakeComputer, never real hardware.
    from core.config_manager import ConfigManager

    monkeypatch.setattr(autostart, "current_user_id", lambda: USER_ID)
    monkeypatch.setattr(autostart, "current_user_sid", lambda user: "S-1-5-21-1001")

    def prepare(*, enabled, fail_create=False, task_exists=False):
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        settings_path = config_dir / "settings.ini"
        settings_path.write_text(
            f"[Preferences]\nlaunchonstartup={enabled}\n", encoding="utf-8",
        )
        cm = ConfigManager(
            stub_logger, fake_dpg, None, None, SimpleNamespace(themes={}),
            str(tmp_path / "core"),
        )
        assert Path(cm.settings_path) == settings_path
        assert_preference(cm, enabled)
        native = NativeRun(fail_create=fail_create, task_exists=task_exists)
        monkeypatch.setattr(autostart.subprocess, "run", native)
        manager = autostart.AutoStartManager(
            app_path=APP_PATH, task_name=TASK_NAME, logger=stub_logger,
        )
        namespace = {
            "cm": cm, "dpg": fake_dpg, "autostart": manager,
            "_acceptance_runtime": None, "logger": stub_logger,
        }
        return cm, native, namespace

    return prepare


def assert_preference(cm, expected):
    # Read the saved file independently, even if the memory value is wrong.
    saved = configparser.ConfigParser(interpolation=None)
    assert saved.read(cm.settings_path, encoding="utf-8") == [cm.settings_path]
    assert (cm.launchonstartup, saved.get("Preferences", "launchonstartup")) == (
        expected, str(expected),
    )


def execute_caller(caller, namespace, enabled=True):
    tree = ast.parse(APP_SOURCE.read_text(encoding="utf-8"))
    if caller == "checkbox":
        nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                 and node.name == "autostart_checkbox_callback"]
    else:
        assert caller == "startup"
        nodes = [node for node in tree.body if isinstance(node, ast.If)
                 and any(isinstance(child, ast.Call)
                         and isinstance(child.func, ast.Attribute)
                         and child.func.attr == "update_if_needed"
                         for child in ast.walk(node))]
    assert len(nodes) == 1
    # Compile the original function / entire startup conditional, including
    # its guard, rather than transcribing app logic or invoking a future helper.
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(APP_SOURCE), "exec"),
         namespace)
    if caller == "checkbox":
        namespace["dpg"].set_value("autostart_checkbox", enabled)
        namespace["autostart_checkbox_callback"]("autostart_checkbox", enabled, None)


@pytest.mark.parametrize("caller", ["checkbox", "startup"])
@pytest.mark.parametrize("fail_create", [False, True], ids=["success", "failure"])
def test_creation_result_persists_through_real_app_caller(harness, caller, fail_create):
    # Startup repairs an already-enabled preference with a confirmed missing
    # task; checkbox enables a previously-disabled preference.
    cm, native, namespace = harness(enabled=caller == "startup", fail_create=fail_create)
    execute_caller(caller, namespace)
    assert native.commands == (["/Create"] if caller == "checkbox"
                               else ["/Query", "/Create"])
    assert len(native.create_files) == 1
    assert not native.create_files[0].exists()
    if fail_create:
        assert any("Autostart create failed:" in message
                   for message in namespace["logger"].messages)
    assert_preference(cm, not fail_create)


def test_startup_matching_task_noop_keeps_enabled_preference(harness):
    # update_if_needed returns None for a retained matching task, not False.
    cm, native, namespace = harness(enabled=True, task_exists=True)
    execute_caller("startup", namespace)
    assert native.commands == ["/Query", "/Query"]
    assert native.create_files == []
    assert_preference(cm, True)


def test_checkbox_disabling_persists_and_deletes_existing_task(harness):
    cm, native, namespace = harness(enabled=True, task_exists=True)
    execute_caller("checkbox", namespace, enabled=False)
    assert native.commands == ["/Query", "/Delete"]
    assert native.create_files == []
    assert_preference(cm, False)
