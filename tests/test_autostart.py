"""L14: AutoStartManager calls subprocess.run with argument lists, never shell=True.

Regression guard: every subprocess.run call must pass a list (program + args)
and never pass ``shell=True``. ``update_if_needed`` must still consume the
captured stdout and returncodes as before.
"""
import os
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

import core.autostart as autostart

FIXED_APP_PATH = "C:\\DynamicFPSLimiter\\DFL.exe"
FIXED_TASK_NAME = "DFL_TestTask"

QUERY_ARGS = ["schtasks", "/Query", "/TN", FIXED_TASK_NAME]
XML_ARGS = ["schtasks", "/Query", "/TN", FIXED_TASK_NAME, "/XML"]
DELETE_ARGS = ["schtasks", "/Delete", "/TN", FIXED_TASK_NAME, "/F"]
USER_ID = "DOMAIN\\InteractiveUser"
CREATE_ARGS = ["schtasks", "/Create", "/TN", FIXED_TASK_NAME, "/XML", "<temp>", "/F"]



class _FakeResult:
    def __init__(self, returncode, stdout, stderr):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class _RunRecorder:
    """Stand-in for subprocess.run: records (args, kwargs), returns a fake
    CompletedProcess carrying the configured returncode/stdout/stderr."""

    def __init__(self, returncode=0, stdout="", stderr=""):
        self.calls = []
        self.files = []
        self.xml = []
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

    def __call__(self, *args, **kwargs):
        if "/Create" in args[0]:
            filename = args[0][args[0].index("/XML") + 1]
            self.files.append(filename)
            self.xml.append(ET.parse(filename).getroot())
        self.calls.append((args, kwargs))
        return _FakeResult(self.returncode, self.stdout, self.stderr)


@pytest.fixture
def autostart_manager(fake_dpg, monkeypatch):
    mgr = autostart.AutoStartManager(
        app_path=FIXED_APP_PATH,
        task_name=FIXED_TASK_NAME,
    )
    monkeypatch.setattr(autostart, "current_user_id", lambda: USER_ID)
    recorder = _RunRecorder()
    monkeypatch.setattr(autostart.subprocess, "run", recorder)
    return mgr, recorder


def _assert_call_sequences(recorder, expected):
    actual = []
    for args, _ in recorder.calls:
        command = args[0][:]
        if "/Create" in command:
            command[command.index("/XML") + 1] = "<temp>"
        actual.append(command)
    assert actual == expected
    assert all(not os.path.exists(path) for path in recorder.files)
    for args, kwargs in recorder.calls:
        assert kwargs["creationflags"] == 0x08000000
        assert "shell" not in kwargs, f"shell=True leaked into call: {kwargs}"
        assert isinstance(args[0], list), f"expected argument list, got: {args[0]!r}"


def test_create_passes_argument_list_no_joined_string(autostart_manager):
    mgr, recorder = autostart_manager
    mgr.create()
    _assert_call_sequences(recorder, [CREATE_ARGS])


def test_task_exists_passes_argument_list_and_uses_returncode(autostart_manager):
    mgr, recorder = autostart_manager
    recorder.returncode = 0
    assert mgr.task_exists() is True
    recorder.returncode = 1
    assert mgr.task_exists() is False
    _assert_call_sequences(recorder, [QUERY_ARGS, QUERY_ARGS])


def test_delete_passes_argument_list(autostart_manager):
    mgr, recorder = autostart_manager
    recorder.returncode = 0
    mgr.delete()
    _assert_call_sequences(recorder, [QUERY_ARGS, DELETE_ARGS])


def test_update_if_needed_recreates_when_xml_path_mismatches(autostart_manager):
    mgr, recorder = autostart_manager
    recorder.returncode = 0
    recorder.stdout = "<xml><Command>C:\\Old\\Location\\DFL.exe</Command></xml>"
    mgr.update_if_needed(True)
    _assert_call_sequences(
        recorder,
        [QUERY_ARGS, XML_ARGS, CREATE_ARGS],
    )


def test_update_if_needed_keeps_task_when_xml_path_matches(autostart_manager):
    mgr, recorder = autostart_manager
    recorder.returncode = 0
    recorder.stdout = autostart.build_task_xml(FIXED_APP_PATH, USER_ID).decode("utf-16")
    mgr.update_if_needed(True)
    _assert_call_sequences(recorder, [QUERY_ARGS, XML_ARGS])


def test_update_if_needed_creates_when_task_missing(autostart_manager):
    mgr, recorder = autostart_manager
    recorder.returncode = 1  # task does not exist
    mgr.update_if_needed(True)
    _assert_call_sequences(recorder, [QUERY_ARGS, CREATE_ARGS])


def test_update_if_needed_removes_when_checkbox_off(autostart_manager):
    mgr, recorder = autostart_manager
    recorder.returncode = 0
    mgr.update_if_needed(False)
    _assert_call_sequences(recorder, [QUERY_ARGS, QUERY_ARGS, DELETE_ARGS])

@pytest.mark.parametrize("app_path,user_id", [
    (FIXED_APP_PATH, USER_ID),
    ('C:\\Apps & Tools\\é <test>\\DFL.exe', 'DÖMAIN\\A&B<user>'),
])
def test_captured_xml_policy_and_escaping(autostart_manager, monkeypatch, app_path, user_id):
    mgr, recorder = autostart_manager
    mgr.app_path = app_path
    monkeypatch.setattr(autostart, "current_user_id", lambda: user_id)
    mgr.create()
    root = recorder.xml[0]
    ns = {"t": autostart.TASK_NAMESPACE}
    assert root.tag == f"{{{autostart.TASK_NAMESPACE}}}Task"
    assert root.get("version") == "1.2"
    for path, expected in {
        "Triggers/LogonTrigger/UserId": user_id,
        "Triggers/LogonTrigger/Enabled": "true",
        "Principals/Principal/UserId": user_id,
        "Principals/Principal/LogonType": "InteractiveToken",
        "Principals/Principal/RunLevel": "HighestAvailable",
        "Settings/DisallowStartIfOnBatteries": "false",
        "Settings/StopIfGoingOnBatteries": "false",
        "Settings/ExecutionTimeLimit": "PT0S",
        "Actions/Exec/Command": app_path,
    }.items():
        assert root.findtext("/".join("t:" + part for part in path.split("/")), namespaces=ns) == expected
    assert root.find("t:Actions", ns).get("Context") == root.find("t:Principals/t:Principal", ns).get("id")
    _assert_call_sequences(recorder, [CREATE_ARGS])


@pytest.mark.parametrize("field,old_value", [
    ("DisallowStartIfOnBatteries", "true"),
    ("StopIfGoingOnBatteries", "true"),
    ("ExecutionTimeLimit", "PT72H"),
    ("ExecutionTimeLimit", None),
])
def test_migrates_same_executable_with_old_constraints(autostart_manager, field, old_value):
    mgr, recorder = autostart_manager
    root = ET.fromstring(autostart.build_task_xml(FIXED_APP_PATH, USER_ID))
    settings = root.find(f"{{{autostart.TASK_NAMESPACE}}}Settings")
    node = settings.find(f"{{{autostart.TASK_NAMESPACE}}}{field}")
    if old_value is None:
        settings.remove(node)
    else:
        node.text = old_value
    recorder.stdout = ET.tostring(root, encoding="unicode")
    mgr.update_if_needed(True)
    _assert_call_sequences(recorder, [QUERY_ARGS, XML_ARGS, CREATE_ARGS])


@pytest.mark.parametrize("failure", ["nonzero", "raised"])
def test_creation_failure_is_reported_and_temp_removed(autostart_manager, monkeypatch, failure):
    mgr, recorder = autostart_manager
    files = []
    def run(args, **kwargs):
        filename = args[args.index("/XML") + 1]
        files.append(filename)
        # Open the actual, closed file as schtasks would, including write access.
        with open(filename, "rb+") as stream:
            ET.parse(stream)
        assert kwargs["check"] is True
        assert kwargs["creationflags"] == 0x08000000
        if failure == "nonzero":
            raise subprocess.CalledProcessError(1, args)
        raise OSError("native launch failed")
    monkeypatch.setattr(autostart.subprocess, "run", run)
    with pytest.raises(subprocess.CalledProcessError if failure == "nonzero" else OSError):
        mgr.create()
    assert files and all(not Path(filename).exists() for filename in files)


def test_failed_update_query_does_not_overwrite_task(autostart_manager, monkeypatch):
    mgr, recorder = autostart_manager
    def run(args, **kwargs):
        if "/XML" in args:
            assert kwargs["check"] is True
            raise subprocess.CalledProcessError(1, args, stderr="access denied")
        return recorder(args, **kwargs)
    monkeypatch.setattr(autostart.subprocess, "run", run)
    with pytest.raises(subprocess.CalledProcessError):
        mgr.update_if_needed(True)
    _assert_call_sequences(recorder, [QUERY_ARGS])
