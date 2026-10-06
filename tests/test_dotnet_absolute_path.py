import os
import sys
import subprocess
from unittest import mock
import pytest

SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

import core.lhm_loader as lhm_loader


def test_detect_dotnet_core_uses_absolute_program_files_path(tmp_path, monkeypatch):
    """
    Test that _detect_dotnet_core uses an absolute ProgramFiles dotnet executable
    and returns highest runtime version.
    """
    fake_pf = tmp_path / "Program Files"
    dotnet_dir = fake_pf / "dotnet"
    dotnet_dir.mkdir(parents=True)

    dotnet_bin = dotnet_dir / ("dotnet.exe" if sys.platform == "win32" else "dotnet")
    dotnet_bin.write_text("#!/bin/sh\necho 'Microsoft.NETCore.App 8.0.0 [/fake/path]'")
    dotnet_bin.chmod(0o755)

    monkeypatch.setenv("ProgramFiles", str(fake_pf))

    called_cmds = []

    def fake_check_output(cmd, **kwargs):
        called_cmds.append(cmd)
        return "Microsoft.NETCore.App 8.0.0 [/fake/path]\nMicrosoft.NETCore.App 6.0.1 [/fake/path]\n"

    monkeypatch.setattr(subprocess, "check_output", fake_check_output)

    res = lhm_loader._detect_dotnet_core()

    assert res == "8.0.0"
    assert len(called_cmds) == 1
    # Command must be an absolute path to Program Files executable, NOT bare 'dotnet'
    assert called_cmds[0][0] == str(dotnet_bin)
    assert called_cmds[0][0] != "dotnet"


def test_hostile_path_executable_never_called(tmp_path, monkeypatch):
    """
    Test that a hostile 'dotnet' executable in PATH is never invoked when ProgramFiles dotnet does not exist.
    """
    hostile_dir = tmp_path / "hostile_bin"
    hostile_dir.mkdir()
    hostile_bin = hostile_dir / ("dotnet.exe" if sys.platform == "win32" else "dotnet")
    hostile_bin.write_text("#!/bin/sh\necho 'MALICIOUS'")
    hostile_bin.chmod(0o755)

    fake_pf = tmp_path / "Program Files"
    fake_pf.mkdir()

    monkeypatch.setenv("PATH", str(hostile_dir) + os.pathsep + os.environ.get("PATH", ""))
    monkeypatch.setenv("ProgramFiles", str(fake_pf))

    called_cmds = []

    def fake_check_output(cmd, **kwargs):
        called_cmds.append(cmd)
        return "MALICIOUS"

    monkeypatch.setattr(subprocess, "check_output", fake_check_output)

    res = lhm_loader._detect_dotnet_core()

    # check_output should never have been called because dotnet executable does not exist in ProgramFiles
    assert len(called_cmds) == 0
    assert res is None


def test_missing_dotnet_executable_falls_back_to_shared_scan(tmp_path, monkeypatch):
    """
    Test that if the dotnet binary is absent, _detect_dotnet_core falls back safely
    to scanning the shared folder without executing subprocess.
    """
    fake_pf = tmp_path / "Program Files"
    shared_ver_dir = fake_pf / "dotnet" / "shared" / "Microsoft.NETCore.App" / "7.0.5"
    shared_ver_dir.mkdir(parents=True)

    monkeypatch.setenv("ProgramFiles", str(fake_pf))

    called_cmds = []

    def fake_check_output(cmd, **kwargs):
        called_cmds.append(cmd)
        return ""

    monkeypatch.setattr(subprocess, "check_output", fake_check_output)

    res = lhm_loader._detect_dotnet_core()

    assert len(called_cmds) == 0
    assert res == "7.0.5"


def test_missing_dotnet_binary_and_missing_shared_returns_none(tmp_path, monkeypatch):
    """
    Test that if neither dotnet binary nor shared folder exists, _detect_dotnet_core safely returns None.
    """
    fake_pf = tmp_path / "EmptyProgramFiles"
    fake_pf.mkdir()

    monkeypatch.setenv("ProgramFiles", str(fake_pf))

    called_cmds = []
    monkeypatch.setattr(subprocess, "check_output", lambda cmd, **kwargs: called_cmds.append(cmd))

    res = lhm_loader._detect_dotnet_core()

    assert len(called_cmds) == 0
    assert res is None


def test_subprocess_error_falls_back_to_shared_scan(tmp_path, monkeypatch):
    """
    Test that if subprocess raises an exception, _detect_dotnet_core falls back safely to shared directory scan.
    """
    fake_pf = tmp_path / "Program Files"
    dotnet_dir = fake_pf / "dotnet"
    shared_ver_dir = dotnet_dir / "shared" / "Microsoft.NETCore.App" / "6.0.0"
    shared_ver_dir.mkdir(parents=True)

    dotnet_bin = dotnet_dir / ("dotnet.exe" if sys.platform == "win32" else "dotnet")
    dotnet_bin.write_text("#!/bin/sh\nexit 1")
    dotnet_bin.chmod(0o755)

    monkeypatch.setenv("ProgramFiles", str(fake_pf))

    def fake_check_output(cmd, **kwargs):
        raise subprocess.CalledProcessError(1, cmd)

    monkeypatch.setattr(subprocess, "check_output", fake_check_output)

    res = lhm_loader._detect_dotnet_core()

    assert res == "6.0.0"
