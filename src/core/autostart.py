import os
import sys
import subprocess
import logging
import ntpath
import pathlib
import ctypes
import csv
import re
from functools import wraps
from ctypes import wintypes
import tempfile
import xml.etree.ElementTree as ET

TASK_NAME = "DynamicFPSLimiter"

TASK_NAMESPACE = "http://schemas.microsoft.com/windows/2004/02/mit/task"
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)


class IdentityLookupError(ValueError):
    """Native identity output cannot safely identify the current user."""


def report_operational_failure(method):
    """Report expected native failures without interrupting app callers."""
    @wraps(method)
    def call(self, *args, **kwargs):
        try:
            return method(self, *args, **kwargs)
        except (OSError, subprocess.CalledProcessError, IdentityLookupError) as error:
            message = f"Autostart {method.__name__} failed: {error}"
            if isinstance(error, subprocess.CalledProcessError) and error.stderr:
                message += f": {error.stderr.strip()}"
            logging.error(message)
            if self.logger is not None:
                self.logger.add_log(f"Error: {message}")
            return False
    return call


def current_user_id():
    """Return the process user's qualified Windows account name."""
    get_name = ctypes.WinDLL("secur32", use_last_error=True).GetUserNameExW
    get_name.argtypes = [ctypes.c_int, wintypes.LPWSTR, ctypes.POINTER(wintypes.ULONG)]
    get_name.restype = ctypes.c_ubyte  # BOOLEAN, not Win32 BOOL
    size = wintypes.ULONG(32768)
    buffer = ctypes.create_unicode_buffer(size.value)
    if not get_name(2, buffer, ctypes.byref(size)):  # NameSamCompatible
        raise ctypes.WinError(ctypes.get_last_error())
    return buffer.value


def current_user_sid(user_id):
    """Read and validate the current process user's SID and account name."""
    result = subprocess.run(
        ["whoami", "/user", "/fo", "csv", "/nh"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        creationflags=CREATE_NO_WINDOW, check=True,
    )
    try:
        rows = list(csv.reader(result.stdout.splitlines(), strict=True))
    except csv.Error as error:
        raise IdentityLookupError("Unexpected whoami user output") from error
    if len(rows) != 1 or len(rows[0]) != 2:
        raise IdentityLookupError("Unexpected whoami user output")
    account, sid = rows[0]
    if account.casefold() != user_id.casefold():
        raise IdentityLookupError("whoami account does not match the current user")
    if not re.fullmatch(r"S-1-[0-9]+(?:-[0-9]+){1,15}", sid):
        raise IdentityLookupError("Invalid current user SID")
    numbers = [int(part) for part in sid.split("-")[2:]]
    if numbers[0] >= 2**48 or any(part >= 2**32 for part in numbers[1:]):
        raise IdentityLookupError("Invalid current user SID")
    return sid


def build_task_xml(app_path, user_id, arguments=""):
    """Build an interactive logon task without battery or runtime limits."""
    def element(parent, name, text=None, **attributes):
        node = ET.SubElement(parent, f"{{{TASK_NAMESPACE}}}{name}", attributes)
        node.text = text
        return node
    task = ET.Element(f"{{{TASK_NAMESPACE}}}Task", version="1.2")
    trigger = element(element(task, "Triggers"), "LogonTrigger")
    element(trigger, "Enabled", "true")
    element(trigger, "UserId", user_id)
    principal = element(element(task, "Principals"), "Principal", id="Author")
    element(principal, "UserId", user_id)
    element(principal, "LogonType", "InteractiveToken")
    element(principal, "RunLevel", "HighestAvailable")
    settings = element(task, "Settings")
    element(settings, "DisallowStartIfOnBatteries", "false")
    element(settings, "StopIfGoingOnBatteries", "false")
    element(settings, "ExecutionTimeLimit", "PT0S")
    action = element(element(task, "Actions", Context="Author"), "Exec")
    element(action, "Command", app_path)
    if arguments:
        element(action, "Arguments", arguments)
    return ET.tostring(task, encoding="utf-16", xml_declaration=True)


def task_xml_matches(xml, app_path, user_id, known_aliases=(), arguments=""):
    """Require the command, arguments and all autostart policy fields to match."""
    try:
        task = ET.fromstring(xml)
    except (ET.ParseError, TypeError, ValueError):
        return False
    ns = {"t": TASK_NAMESPACE}
    if task.tag != f"{{{TASK_NAMESPACE}}}Task":
        return False
    triggers = task.findall("t:Triggers/*", ns)
    principals = task.findall("t:Principals/*", ns)
    actions = task.findall("t:Actions/*", ns)
    if len(triggers) != 1 or len(principals) != 1 or len(actions) != 1:
        return False
    trigger, principal, action = triggers[0], principals[0], actions[0]
    def value(node, name):
        return node.findtext(f"t:{name}", namespaces=ns)
    identities = {identity.casefold() for identity in (user_id, *known_aliases)}
    def same_user(identity):
        return bool(identity) and identity.casefold() in identities
    return (
        trigger.tag == f"{{{TASK_NAMESPACE}}}LogonTrigger"
        and same_user(value(trigger, "UserId"))
        and value(trigger, "Enabled") == "true"
        and same_user(value(principal, "UserId"))
        and value(principal, "LogonType") == "InteractiveToken"
        and value(principal, "RunLevel") == "HighestAvailable"
        and task.find("t:Actions", ns).get("Context") == principal.get("id")
        and action.tag == f"{{{TASK_NAMESPACE}}}Exec"
        and (value(action, "Command") or "").lower() == app_path.lower()
        and (value(action, "Arguments") or "") == arguments
        and task.findtext("t:Settings/t:DisallowStartIfOnBatteries", namespaces=ns) == "false"
        and task.findtext("t:Settings/t:StopIfGoingOnBatteries", namespaces=ns) == "false"
        and task.findtext("t:Settings/t:ExecutionTimeLimit", namespaces=ns) == "PT0S"
    )


class AutoStartManager:
    def __init__(self, app_path=None, task_name=TASK_NAME, logger=None, *, source_path=None):
        self.arguments = ""
        self.source_path = None
        if source_path is not None and not app_path:
            self.app_path, self.arguments = self.get_runtime_target(source_path)
            if not getattr(sys, "frozen", False):
                self.source_path = os.path.abspath(source_path)
        else:
            self.app_path = app_path or self.get_current_app_path()
        self.task_name = task_name
        self.logger = logger

    @staticmethod
    def get_runtime_target(source_path):
        """Use the running package, or launch the source entry through Python."""
        if getattr(sys, "frozen", False):
            return sys.executable, ""
        executable = sys.executable
        flags = ["--debug"] if "--debug" in sys.argv[1:] else []
        if not flags:
            pythonw = os.path.join(os.path.dirname(executable), "pythonw.exe")
            if os.path.isfile(pythonw):
                executable = pythonw
        source = os.path.normcase(os.path.abspath(source_path))
        return executable, subprocess.list2cmdline([source, *flags])

    @staticmethod
    def get_current_app_path():
        return os.path.abspath(sys.argv[0])

    def is_in_program_files(self, path=None):
        target = path or self.app_path
        if not target:
            return False

        if not ntpath.isabs(target):
            return False

        drive, _ = ntpath.splitdrive(target)
        if not drive or drive.startswith("\\\\") or drive.startswith("//"):
            return False

        norm_target = ntpath.normpath(target)
        pure_target = pathlib.PureWindowsPath(norm_target.lower())

        roots = []
        for var in ("ProgramFiles", "ProgramFiles(x86)", "ProgramW6432"):
            val = os.environ.get(var)
            if val and ntpath.isabs(val):
                r_drive, _ = ntpath.splitdrive(val)
                if r_drive and not r_drive.startswith("\\\\") and not r_drive.startswith("//"):
                    norm_root = ntpath.normpath(val)
                    roots.append(pathlib.PureWindowsPath(norm_root.lower()))

        if not roots:
            return False

        for root in roots:
            try:
                pure_target.relative_to(root)
                return True
            except ValueError:
                continue

        return False

    @report_operational_failure
    def task_exists(self):
        return self._task_exists()

    def _task_exists(self):
        result = subprocess.run(["schtasks", "/Query", "/TN", self.task_name, "/HRESULT"],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                creationflags=CREATE_NO_WINDOW)
        returncode = result.returncode & 0xFFFFFFFF
        if returncode == 0:
            return True
        # Normalize signed Windows HRESULTs; diagnostics may be localized.
        # Only a confirmed missing task permits creation.
        if returncode == 0x80070002:
            return False
        raise subprocess.CalledProcessError(
            result.returncode, result.args if hasattr(result, "args") else
            ["schtasks", "/Query", "/TN", self.task_name, "/HRESULT"],
            output=result.stdout, stderr=result.stderr,
        )

    @report_operational_failure
    def create(self):
        install_path = self.source_path or self.app_path
        if not self.is_in_program_files(path=install_path):
            path_kind = "source" if self.source_path else "executable"
            msg = (
                f"Autostart {path_kind} path '{install_path}' is outside Program Files. "
                "It is recommended to install under Program Files before enabling autostart."
            )
            try:
                logging.warning(msg)
            except Exception:
                pass
            try:
                if self.logger and hasattr(self.logger, "add_log"):
                    self.logger.add_log(f"Warning: {msg}")
            except Exception:
                pass

        xml = build_task_xml(self.app_path, current_user_id(), self.arguments)
        filename = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as stream:
                filename = stream.name
                stream.write(xml)
            return subprocess.run(
                ["schtasks", "/Create", "/TN", self.task_name, "/XML", filename, "/F"],
                creationflags=CREATE_NO_WINDOW, check=True,
            )
        finally:
            if filename is not None:
                os.unlink(filename)

    @report_operational_failure
    def delete(self):
        if self._task_exists():
            return subprocess.run(
                ["schtasks", "/Delete", "/TN", self.task_name, "/F"],
                creationflags=CREATE_NO_WINDOW, check=True,
            )

    @report_operational_failure
    def update_if_needed(self, startup_checkbox):
        if startup_checkbox:
            if self._task_exists():
                result = subprocess.run(
                    ["schtasks", "/Query", "/TN", self.task_name, "/XML"],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                    creationflags=CREATE_NO_WINDOW, check=True,
                )
                user_id = current_user_id()
                if not task_xml_matches(result.stdout, self.app_path, user_id,
                                        arguments=self.arguments):
                    sid = current_user_sid(user_id)
                    if not task_xml_matches(result.stdout, self.app_path, user_id, (sid,),
                                            arguments=self.arguments):
                        return self.create()
            else:
                return self.create()
        else:
            if self._task_exists():
                return self.delete()
