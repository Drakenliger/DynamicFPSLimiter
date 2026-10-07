"""L14: AutoStartManager calls subprocess.run with argument lists, never shell=True.

Regression guard: every subprocess.run call must pass a list (program + args)
and never pass ``shell=True``. ``update_if_needed`` must still consume the
captured stdout and returncodes as before.
"""
import os
import ast
from types import SimpleNamespace
from unittest.mock import Mock
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

import core.autostart as autostart

SID_LOOKUP = autostart.current_user_sid

FIXED_APP_PATH = "C:\\DynamicFPSLimiter\\DFL.exe"
FIXED_TASK_NAME = "DFL_TestTask"

QUERY_ARGS = ["schtasks", "/Query", "/TN", FIXED_TASK_NAME, "/HRESULT"]
MISSING_HRESULT = 0x80070002
XML_ARGS = ["schtasks", "/Query", "/TN", FIXED_TASK_NAME, "/XML"]
DELETE_ARGS = ["schtasks", "/Delete", "/TN", FIXED_TASK_NAME, "/F"]
USER_ID = "DOMAIN\\InteractiveUser"
USER_SID = "S-1-5-21-100-200-300-1001"
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
    monkeypatch.setattr(autostart, "current_user_sid", lambda user_id: USER_SID)
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
    recorder.returncode = MISSING_HRESULT
    recorder.stderr = "ERROR: The system cannot find the file specified."
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


@pytest.mark.parametrize("trigger,principal", [
    (USER_ID.lower(), USER_ID.upper()),
    (USER_SID, USER_SID),
    (USER_ID.lower(), USER_SID),
    (USER_SID, USER_ID.upper()),
])
def test_equivalent_account_xml_remains_untouched(autostart_manager, trigger, principal):
    mgr, recorder = autostart_manager
    root = ET.fromstring(autostart.build_task_xml(FIXED_APP_PATH, USER_ID))
    ns = {"t": autostart.TASK_NAMESPACE}
    root.find("t:Triggers/t:LogonTrigger/t:UserId", ns).text = trigger
    root.find("t:Principals/t:Principal/t:UserId", ns).text = principal
    recorder.stdout = ET.tostring(root, encoding="unicode")
    mgr.update_if_needed(True)
    _assert_call_sequences(recorder, [QUERY_ARGS, XML_ARGS])


@pytest.mark.parametrize("field", ["Triggers/LogonTrigger", "Principals/Principal"])
@pytest.mark.parametrize("wrong_user", ["S-1-5-21-100-200-300-1002", "DOMAIN\\OtherUser"])
def test_wrong_identity_replaces_task(autostart_manager, field, wrong_user):
    mgr, recorder = autostart_manager
    root = ET.fromstring(autostart.build_task_xml(FIXED_APP_PATH, USER_SID))
    root.find("/".join(f"{{{autostart.TASK_NAMESPACE}}}{part}" for part in
                       (field + "/UserId").split("/"))).text = wrong_user
    recorder.stdout = ET.tostring(root, encoding="unicode")
    mgr.update_if_needed(True)
    _assert_call_sequences(recorder, [QUERY_ARGS, XML_ARGS, CREATE_ARGS])


def test_pure_matcher_does_not_accept_unknown_sid():
    xml = autostart.build_task_xml(FIXED_APP_PATH, USER_SID)
    assert not autostart.task_xml_matches(xml, FIXED_APP_PATH, USER_ID)
    assert autostart.task_xml_matches(xml, FIXED_APP_PATH, USER_ID, (USER_SID,))


@pytest.mark.parametrize("output", [
    f'"{USER_ID.lower()}","{USER_SID}"\r\n',
    f'"{USER_ID.upper()}","{USER_SID}"\n',
])
def test_current_user_sid_checked_csv_boundary(monkeypatch, output):
    recorder = _RunRecorder(stdout=output)
    monkeypatch.setattr(autostart.subprocess, "run", recorder)
    assert autostart.current_user_sid(USER_ID) == USER_SID
    _assert_call_sequences(recorder, [["whoami", "/user", "/fo", "csv", "/nh"]])
    assert recorder.calls[0][1]["check"] is True
    assert recorder.calls[0][1]["text"] is True


@pytest.mark.parametrize("output", [
    "", '"DOMAIN\\OtherUser","S-1-5-21-1001"',
    f'"{USER_ID}","not-a-sid"', f'"{USER_ID}","S-1-5-4294967296"',
    f'"{USER_ID}","S-1-281474976710656-1"',
    f'"{USER_ID}","{USER_SID}","extra"',
    f'"{USER_ID}","{USER_SID}"\n"other","S-1-5-1"',
])
def test_current_user_sid_rejects_unvalidated_output(monkeypatch, output):
    monkeypatch.setattr(autostart.subprocess, "run", _RunRecorder(stdout=output))
    with pytest.raises(ValueError):
        autostart.current_user_sid(USER_ID)


@pytest.mark.parametrize("error", [subprocess.CalledProcessError(1, "whoami"), OSError("launch failed")])
def test_sid_native_failure_does_not_replace_task(autostart_manager, monkeypatch, error, caplog):
    mgr, recorder = autostart_manager
    recorder.stdout = autostart.build_task_xml(FIXED_APP_PATH, USER_SID).decode("utf-16")
    monkeypatch.setattr(autostart, "current_user_sid", SID_LOOKUP)
    def run(args, **kwargs):
        if args[0] == "whoami":
            assert kwargs["check"] is True
            assert kwargs["creationflags"] == 0x08000000
            raise error
        return recorder(args, **kwargs)
    monkeypatch.setattr(autostart.subprocess, "run", run)
    mgr.logger = Mock()
    assert mgr.update_if_needed(True) is False
    assert "failed" in caplog.text
    mgr.logger.add_log.assert_called_once()
    _assert_call_sequences(recorder, [QUERY_ARGS, XML_ARGS])


@pytest.mark.parametrize("returncode", [MISSING_HRESULT, MISSING_HRESULT - 2**32])
@pytest.mark.parametrize("diagnostic", ["", "Das System kann die angegebene Datei nicht finden."])
def test_update_if_needed_creates_when_task_missing(
        autostart_manager, monkeypatch, returncode, diagnostic):
    mgr, recorder = autostart_manager
    def run(args, **kwargs):
        result = recorder(args, **kwargs)
        if args == QUERY_ARGS:
            return _FakeResult(returncode, "", diagnostic)
        return result
    monkeypatch.setattr(autostart.subprocess, "run", run)
    assert mgr.update_if_needed(True).returncode == 0
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
def test_creation_failure_is_reported_and_temp_removed(autostart_manager, monkeypatch, failure, caplog):
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
    mgr.logger = Mock()
    assert mgr.create() is False
    assert "failed" in caplog.text
    messages = [call.args[0] for call in mgr.logger.add_log.call_args_list]
    assert len(messages) == 2
    assert messages[0].startswith("Warning:") and "outside Program Files" in messages[0]
    assert messages[1].startswith("Error: Autostart create failed:")
    assert files and all(not Path(filename).exists() for filename in files)


def test_failed_update_query_does_not_overwrite_task(autostart_manager, monkeypatch, caplog):
    mgr, recorder = autostart_manager
    def run(args, **kwargs):
        if "/XML" in args:
            assert kwargs["check"] is True
            raise subprocess.CalledProcessError(1, args, stderr="access denied")
        return recorder(args, **kwargs)
    monkeypatch.setattr(autostart.subprocess, "run", run)
    mgr.logger = Mock()
    assert mgr.update_if_needed(True) is False
    assert "failed" in caplog.text
    mgr.logger.add_log.assert_called_once()
    _assert_call_sequences(recorder, [QUERY_ARGS])


@pytest.mark.parametrize("operation,enabled", [("create", True), ("delete", False),
    ("query", True), ("identity", True), ("sid", True)])
@pytest.mark.parametrize("caller", ["startup", "checkbox"])
@pytest.mark.parametrize("query_returncode", [None, 1, 0x80070005, 0x80070005 - 2**32])
def test_actual_callers_report_failure_and_continue(
        autostart_manager, monkeypatch, caplog, operation, enabled, caller, query_returncode):
    if caller == "checkbox" and operation == "sid":
        pytest.skip("Checkbox creation does not resolve SID aliases")
    mgr, recorder = autostart_manager
    mgr.logger = Mock()
    recorder.stdout = autostart.build_task_xml(FIXED_APP_PATH, USER_SID).decode("utf-16")
    if caller == "checkbox" and operation == "query":
        enabled = False
    def run(args, **kwargs):
        if operation == "query" and args == QUERY_ARGS and query_returncode is not None:
            recorder(args, **kwargs)
            return _FakeResult(query_returncode, "", "ERROR: The system cannot find the file specified.")
        if ((operation == "create" and "/Create" in args)
                or (operation == "delete" and "/Delete" in args)
                or (operation == "query" and "/Query" in args)):
            raise subprocess.CalledProcessError(1, args, stderr="native denied")
        if operation == "create" and "/Query" in args:
            return _FakeResult(MISSING_HRESULT, "", "ERROR: The system cannot find the file specified.")
        return recorder(args, **kwargs)
    monkeypatch.setattr(autostart.subprocess, "run", run)
    if operation in ("identity", "sid"):
        def fail(*args):
            raise OSError("identity unavailable")
        monkeypatch.setattr(autostart, "current_user_id" if operation == "identity"
                            else "current_user_sid", fail)
    tree = ast.parse((Path(__file__).resolve().parents[1] / "src/core/app.py").read_text())
    results = []
    class ObservedManager:
        def __getattr__(self, name):
            def invoke(*args):
                result = getattr(mgr, name)(*args)
                results.append(result)
                return result
            return invoke
    namespace = {"autostart": ObservedManager(), "_acceptance_runtime": None,
        "cm": SimpleNamespace(launchonstartup=enabled, update_preference_setting=Mock()),
        "dpg": SimpleNamespace(get_value=lambda tag: enabled)}
    if caller == "startup":
        node = next(n for n in tree.body if isinstance(n, ast.If)
                    and any(isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
                            and c.func.attr == "update_if_needed" for c in ast.walk(n)))
    else:
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                    and n.name == "autostart_checkbox_callback")
    exec(compile(ast.Module(body=[node], type_ignores=[]), "app.py", "exec"), namespace)
    if caller == "checkbox":
        namespace[node.name](None, enabled, None)
    assert results == [False]
    assert "failed" in caplog.text
    messages = [call.args[0] for call in mgr.logger.add_log.call_args_list]
    if operation == "create" or (caller == "checkbox" and operation == "identity"):
        assert len(messages) == 2
        assert messages[0].startswith("Warning:") and "outside Program Files" in messages[0]
        assert messages[1].startswith("Error: Autostart create failed:")
    else:
        assert len(messages) == 1
        assert messages[0].startswith("Error:")
    if operation in ("query", "identity", "sid"):
        assert not recorder.files


def test_programming_defect_propagates(autostart_manager, monkeypatch):
    mgr, _ = autostart_manager
    def broken():
        raise ValueError("programming defect")
    monkeypatch.setattr(autostart, "current_user_id", broken)
    with pytest.raises(ValueError, match="programming defect"):
        mgr.create()


@pytest.mark.parametrize("returncode", [1, 0x80070005, 0x80070005 - 2**32])
@pytest.mark.parametrize("diagnostic", ["access denied", "", "unrecognized diagnostic",
    "ERROR: The system cannot find the file specified."])
def test_failed_existence_query_never_creates(autostart_manager, caplog, returncode, diagnostic):
    mgr, recorder = autostart_manager
    mgr.logger = Mock()
    recorder.returncode = returncode
    recorder.stderr = diagnostic
    assert mgr.update_if_needed(True) is False
    _assert_call_sequences(recorder, [QUERY_ARGS])
    assert "failed" in caplog.text
    mgr.logger.add_log.assert_called_once()
