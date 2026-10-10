"""Source autostart must launch Python with the absolute source entry point."""

import ast
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest

import core.autostart as autostart


NS = {"t": "http://schemas.microsoft.com/windows/2004/02/mit/task"}
USER = r"DOMAIN\SourceUser"
SID = "S-1-5-21-100-200-300-1001"
APP_SOURCE = Path(__file__).resolve().parents[1] / "src/core/app.py"


def _app_manager(base_dir, logger):
    # Execute the production assignment, never a copied target calculation.
    tree = ast.parse(APP_SOURCE.read_text(encoding="utf-8"))
    assignments = [
        node for node in tree.body if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "autostart"
                for target in node.targets)
    ]
    assert len(assignments) == 1
    namespace = {
        "AutoStartManager": autostart.AutoStartManager,
        "os": os, "sys": sys, "Base_dir": str(base_dir), "logger": logger,
    }
    module = ast.Module(body=assignments, type_ignores=[])
    exec(compile(module, str(APP_SOURCE), "exec"), namespace)
    return namespace["autostart"]


def _legacy_task(command):
    # The old task is otherwise fully compliant, isolating target migration.
    root = ET.fromstring(f"""<Task xmlns="{NS['t']}" version="1.2">
      <Triggers><LogonTrigger><Enabled>true</Enabled><UserId>{USER}</UserId>
      </LogonTrigger></Triggers>
      <Principals><Principal id="Author"><UserId>{USER}</UserId>
      <LogonType>InteractiveToken</LogonType><RunLevel>HighestAvailable</RunLevel>
      </Principal></Principals>
      <Settings><DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
      <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
      <ExecutionTimeLimit>PT0S</ExecutionTimeLimit></Settings>
      <Actions Context="Author"><Exec><Command /></Exec></Actions></Task>""")
    root.find("t:Actions/t:Exec/t:Command", NS).text = str(command)
    return ET.tostring(root, encoding="unicode")


class _Scheduler:
    """Inspect the actual closed XML tempfile at the schtasks boundary."""

    def __init__(self):
        self.xml = None
        self.created = []
        self.files = []
        self.calls = []

    def __call__(self, args, **kwargs):
        assert isinstance(args, list) and args[0] == "schtasks"
        assert not kwargs.get("shell", False)
        self.calls.append(args[:])
        if args[1] == "/Create":
            filename = Path(args[args.index("/XML") + 1])
            root = ET.parse(filename).getroot()
            self.files.append(filename)
            self.created.append(root)
            self.xml = ET.tostring(root, encoding="unicode")
            return subprocess.CompletedProcess(args, 0)
        assert args[1] == "/Query"
        if "/HRESULT" in args:
            code = 0x80070002 if self.xml is None else 0
            return subprocess.CompletedProcess(args, code, stdout="", stderr="")
        assert "/XML" in args and self.xml is not None
        return subprocess.CompletedProcess(args, 0, stdout=self.xml, stderr="")


@pytest.fixture
def scheduler(monkeypatch):
    boundary = _Scheduler()
    monkeypatch.setattr(autostart.subprocess, "run", boundary)
    monkeypatch.setattr(autostart, "current_user_id", lambda: USER)
    monkeypatch.setattr(autostart, "current_user_sid", lambda user: SID)
    return boundary


def _source_fixture(tmp_path, monkeypatch, stub_logger, pythonw, debug):
    src = tmp_path / "Sourcé checkout & spaces" / "src"
    core = src / "core"
    core.mkdir(parents=True)
    launcher = src / "__main__.py"
    launcher.write_text("# source launcher\n", encoding="utf-8")
    interpreter = tmp_path / "Pythön & spaces" / "python.exe"
    interpreter.parent.mkdir()
    interpreter.touch()
    windowless = interpreter.with_name("pythonw.exe")
    if pythonw:
        windowless.touch()
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    monkeypatch.setattr(sys, "executable", str(interpreter))
    flags = ["--debug"] if debug else []
    monkeypatch.setattr(sys, "argv", [str(launcher), *flags])
    expected_interpreter = windowless if pythonw and not debug else interpreter
    return (_app_manager(core, stub_logger), expected_interpreter,
            launcher, flags, src / "DynamicFPSLimiter.exe")


def _assert_source_task(root, interpreter, launcher, flags):
    command = root.findtext("t:Actions/t:Exec/t:Command", namespaces=NS)
    # First target assertion: unchanged source points to a nonexistent EXE.
    assert Path(command or "").is_file(), f"Autostart Command is missing: {command!r}"
    assert command == str(interpreter)
    arguments = root.findtext("t:Actions/t:Exec/t:Arguments", namespaces=NS)
    assert launcher.is_absolute() and launcher.is_file()
    assert arguments == subprocess.list2cmdline([os.path.normcase(str(launcher)), *flags])


def _assert_unchanged(manager, scheduler):
    creations = len(scheduler.created)
    start = len(scheduler.calls)
    xml = scheduler.xml
    manager.update_if_needed(True)
    assert len(scheduler.created) == creations
    assert scheduler.xml == xml
    assert [call[1] for call in scheduler.calls[start:]] == ["/Query", "/Query"]


@pytest.mark.parametrize("pythonw,debug", [
    pytest.param(True, False, id="windowless"),
    pytest.param(False, False, id="console-fallback"),
    pytest.param(True, True, id="debug-console"),
])
@pytest.mark.parametrize("initial", ["direct-create", "missing-task", "legacy-task"])
def test_source_task_create_and_repair(
        tmp_path, monkeypatch, stub_logger, scheduler, pythonw, debug, initial):
    manager, interpreter, launcher, flags, old_exe = _source_fixture(
        tmp_path, monkeypatch, stub_logger, pythonw, debug)
    if initial == "legacy-task":
        scheduler.xml = _legacy_task(old_exe)
    if initial == "direct-create":
        manager.create()
    else:
        manager.update_if_needed(True)
    _assert_source_task(ET.fromstring(scheduler.xml), interpreter, launcher, flags)
    assert len(scheduler.created) == 1
    assert [call[1] for call in scheduler.calls] == {
        "direct-create": ["/Create"],
        "missing-task": ["/Query", "/Create"],
        "legacy-task": ["/Query", "/Query", "/Create"],
    }[initial]
    assert all(not path.exists() for path in scheduler.files)
    _assert_unchanged(manager, scheduler)


def test_app_source_alias_keeps_lexical_path_from_arbitrary_cwd(
        tmp_path, monkeypatch, stub_logger, scheduler):
    _, interpreter, launcher, flags, _ = _source_fixture(
        tmp_path, monkeypatch, stub_logger, pythonw=True, debug=False)
    alias = tmp_path / "Logical source alias"
    try:
        alias.symlink_to(launcher.parent, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"Directory symlinks unavailable: {error}")
    lexical_launcher = alias / "__main__.py"
    assert lexical_launcher.resolve() != lexical_launcher
    unrelated = tmp_path / "Unrelated working directory"
    unrelated.mkdir()
    monkeypatch.chdir(unrelated)
    manager = _app_manager(alias / "core", stub_logger)
    manager.create()
    _assert_source_task(scheduler.created[-1], interpreter, lexical_launcher, flags)
    _assert_unchanged(_app_manager(alias / "core", stub_logger), scheduler)


@pytest.mark.parametrize("broken", ["missing-arguments", "wrong-script"])
def test_source_task_repairs_broken_arguments(
        tmp_path, monkeypatch, stub_logger, scheduler, broken):
    manager, interpreter, launcher, flags, _ = _source_fixture(
        tmp_path, monkeypatch, stub_logger, pythonw=True, debug=False)
    manager.create()
    _assert_source_task(scheduler.created[-1], interpreter, launcher, flags)
    _assert_unchanged(manager, scheduler)
    root = ET.fromstring(scheduler.xml)
    action = root.find("t:Actions/t:Exec", NS)
    arguments = action.find("t:Arguments", NS)
    if broken == "missing-arguments":
        action.remove(arguments)
    else:
        arguments.text = subprocess.list2cmdline([str(launcher.with_name("missing.py"))])
    scheduler.xml = ET.tostring(root, encoding="unicode")
    start = len(scheduler.calls)
    manager.update_if_needed(True)
    assert len(scheduler.created) == 2
    assert [call[1] for call in scheduler.calls[start:]] == ["/Query", "/Query", "/Create"]
    _assert_source_task(scheduler.created[-1], interpreter, launcher, flags)
    assert all(not path.exists() for path in scheduler.files)
    _assert_unchanged(manager, scheduler)


@pytest.mark.parametrize("initial", ["direct-create", "missing-task"])
@pytest.mark.parametrize("exe_name", ["DynamicFPSLimiter.exe", "Límiter & renamed.exe"])
def test_frozen_task_keeps_packaged_executable_without_arguments(
        tmp_path, monkeypatch, stub_logger, scheduler, initial, exe_name):
    package = tmp_path / "Packaged app with spaces"
    bundle = package / "_internal"
    bundle.mkdir(parents=True)
    executable = package / exe_name
    executable.touch()
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(bundle), raising=False)
    monkeypatch.setattr(sys, "executable", str(executable))
    monkeypatch.setattr(sys, "argv", [str(executable), "--debug"])
    manager = _app_manager(bundle, stub_logger)
    if initial == "direct-create":
        manager.create()
    else:
        manager.update_if_needed(True)
    root = scheduler.created[-1]
    command = root.findtext("t:Actions/t:Exec/t:Command", namespaces=NS)
    assert Path(command or "").is_file()
    assert command == str(executable)
    assert not root.findtext("t:Actions/t:Exec/t:Arguments", namespaces=NS)
    assert len(scheduler.created) == 1
    assert all(not path.exists() for path in scheduler.files)
    _assert_unchanged(manager, scheduler)
    moved_bundle = tmp_path / "Unrelated extraction directory"
    monkeypatch.setattr(sys, "_MEIPASS", str(moved_bundle), raising=False)
    _assert_unchanged(_app_manager(moved_bundle, stub_logger), scheduler)


@pytest.mark.parametrize("broken", [None, "missing-arguments", "wrong-script",
                                    "wrong-debug", "wrong-debug-case", "extra-flag",
                                    "wrong-command"])
def test_source_sid_alias_still_checks_command_and_arguments(
        tmp_path, monkeypatch, stub_logger, scheduler, broken):
    manager, interpreter, launcher, flags, old_exe = _source_fixture(
        tmp_path, monkeypatch, stub_logger, pythonw=True, debug=broken == "wrong-debug-case")
    manager.create()
    root = ET.fromstring(scheduler.xml)
    root.find("t:Triggers/t:LogonTrigger/t:UserId", NS).text = USER.lower()
    root.find("t:Principals/t:Principal/t:UserId", NS).text = SID
    action = root.find("t:Actions/t:Exec", NS)
    arguments = action.find("t:Arguments", NS)
    if broken == "missing-arguments":
        action.remove(arguments)
    elif broken == "wrong-script":
        arguments.text = subprocess.list2cmdline([str(launcher.with_name("wrong.py"))])
    elif broken == "wrong-debug":
        arguments.text = subprocess.list2cmdline([str(launcher), "--debug"])
    elif broken in ("wrong-debug-case", "extra-flag"):
        arguments.text = subprocess.list2cmdline([
            os.path.normcase(str(launcher)),
            "--DEBUG" if broken == "wrong-debug-case" else "--other"])
    elif broken == "wrong-command":
        action.find("t:Command", NS).text = str(old_exe)
    scheduler.xml = ET.tostring(root, encoding="unicode")
    manager.update_if_needed(True)
    assert len(scheduler.created) == (2 if broken else 1)
    _assert_source_task(ET.fromstring(scheduler.xml), interpreter, launcher, flags)
    _assert_unchanged(manager, scheduler)
    assert all(not path.exists() for path in scheduler.files)


def test_standalone_positional_constructor_and_default_xml_helpers(
        tmp_path, monkeypatch, stub_logger, scheduler):
    executable = tmp_path / "Explicit standalone.exe"
    executable.touch()
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", "different-runtime.exe")
    manager = autostart.AutoStartManager(str(executable), "Standalone", stub_logger)
    assert manager.task_name == "Standalone" and manager.logger is stub_logger
    manager.create()
    root = scheduler.created[-1]
    assert root.findtext("t:Actions/t:Exec/t:Command", namespaces=NS) == str(executable)
    assert not root.findtext("t:Actions/t:Exec/t:Arguments", namespaces=NS)
    xml = autostart.build_task_xml(str(executable), SID)
    assert autostart.task_xml_matches(xml, str(executable), USER, (SID,))
    assert not autostart.task_xml_matches(xml, str(executable), USER, (SID,), "wrong.py")


def _windows_runtime(monkeypatch):
    import ntpath
    from types import SimpleNamespace
    monkeypatch.setattr(autostart, "os", SimpleNamespace(
        path=ntpath, environ=os.environ, unlink=os.unlink))
    monkeypatch.setenv("ProgramFiles", r"C:\Program Files")
    monkeypatch.setenv("ProgramFiles(x86)", r"C:\Program Files (x86)")
    monkeypatch.setenv("ProgramW6432", r"C:\Program Files")
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    monkeypatch.setattr(sys, "executable", r"C:\Program Files\Python312\python.exe")
    monkeypatch.setattr(sys, "argv", ["source.py"])


@pytest.mark.parametrize("source,python,warns", [
    (r"C:\Users\Public\DFL\src\__main__.py", r"C:\Program Files\Python312\python.exe", True),
    (r"C:\Program Files\DFL\src\__main__.py", r"C:\Users\Public\Python\python.exe", False),
])
def test_source_install_warning_checks_source_not_python(
        monkeypatch, stub_logger, scheduler, source, python, warns):
    _windows_runtime(monkeypatch)
    monkeypatch.setattr(sys, "executable", python)
    manager = autostart.AutoStartManager(source_path=source, logger=stub_logger)
    manager.create()
    assert len(scheduler.created) == 1
    warnings = [msg for msg in stub_logger.messages if "outside Program Files" in msg]
    assert len(warnings) == int(warns)
    if warns:
        assert f"Autostart source path '{source}'" in warnings[0]


@pytest.mark.parametrize("frozen", [False, True])
def test_explicit_and_frozen_warning_keep_executable_contract(
        monkeypatch, stub_logger, scheduler, frozen):
    _windows_runtime(monkeypatch)
    executable = r"C:\Users\Public\DFL\DynamicFPSLimiter.exe"
    monkeypatch.setattr(sys, "frozen", frozen)
    monkeypatch.setattr(sys, "executable", executable)
    manager = autostart.AutoStartManager(
        app_path=None if frozen else executable,
        source_path=r"C:\Program Files\DFL\src\__main__.py", logger=stub_logger)
    assert manager.is_in_program_files(path=r"C:\Program Files\DFL\app.exe")
    assert not manager.is_in_program_files(path=executable)
    manager.create()
    assert stub_logger.messages == [
        f"Warning: Autostart executable path '{executable}' is outside Program Files. "
        "It is recommended to install under Program Files before enabling autostart."]
    assert len(scheduler.created) == 1


def test_windows_source_path_case_does_not_replace_task(
        monkeypatch, stub_logger, scheduler):
    _windows_runtime(monkeypatch)
    upper = autostart.AutoStartManager(
        source_path=r"C:\Users\Public\DFL\src\__main__.py", logger=stub_logger)
    lower = autostart.AutoStartManager(
        source_path=r"c:\users\public\dfl\src\__main__.py", logger=stub_logger)
    upper.create()
    _assert_unchanged(lower, scheduler)
