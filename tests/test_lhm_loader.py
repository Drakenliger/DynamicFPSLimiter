import os
import sys
from types import ModuleType
import pytest

import core.lhm_loader as lhm_loader


@pytest.fixture(autouse=True)
def _reset_lhm_loader_state(monkeypatch):
    monkeypatch.setattr(lhm_loader, "_LOADED", False)
    monkeypatch.setattr(lhm_loader, "_Computer", None)
    monkeypatch.setattr(lhm_loader, "_SensorType", None)
    monkeypatch.setattr(lhm_loader, "_HardwareType", None)


def _setup_mock_clr_and_hardware_modules(monkeypatch):
    add_ref_paths = []

    class MockCLR:
        @staticmethod
        def AddReference(path):
            add_ref_paths.append(os.path.normpath(str(path)))

    fake_hw_mod = ModuleType("LibreHardwareMonitor.Hardware")
    fake_hw_mod.Computer = object()
    fake_hw_mod.SensorType = object()
    fake_hw_mod.HardwareType = object()

    fake_lhm_mod = ModuleType("LibreHardwareMonitor")
    fake_lhm_mod.Hardware = fake_hw_mod

    monkeypatch.setattr(lhm_loader, "clr", MockCLR)
    monkeypatch.setitem(sys.modules, "LibreHardwareMonitor", fake_lhm_mod)
    monkeypatch.setitem(sys.modules, "LibreHardwareMonitor.Hardware", fake_hw_mod)

    return add_ref_paths


@pytest.mark.parametrize(
    "core_ver, expected_variant",
    [
        ("8.0.0", "net8.0"),
        ("9.0.0", "net9.0"),
        ("10.0.0", "net10.0"),
    ],
)
def test_ensure_loaded_resolves_existing_dotnet_variants(monkeypatch, core_ver, expected_variant):
    add_ref_paths = _setup_mock_clr_and_hardware_modules(monkeypatch)

    monkeypatch.setattr(lhm_loader, "_detect_dotnet_core", lambda: core_ver)
    monkeypatch.setattr(lhm_loader, "_detect_dotnet_framework", lambda: None)

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src", "core"))
    lhm_loader.ensure_loaded(base_dir=project_root)

    expected_path = os.path.normpath(
        os.path.join(project_root, "assets", "LHM_0.9.6_lib", expected_variant, "LibreHardwareMonitorLib.dll")
    )

    assert len(add_ref_paths) == 1
    assert add_ref_paths[0] == expected_path


def test_ensure_loaded_fallback_to_net472_when_selected_dll_absent(monkeypatch, tmp_path):
    add_ref_paths = _setup_mock_clr_and_hardware_modules(monkeypatch)

    # Setup dummy directory structure in tmp_path with LHM_0.9.6_lib
    # where net6.0 folder exists (or is selected) but LibreHardwareMonitorLib.dll is missing in net6.0
    pkg_dir = tmp_path / "assets" / "LHM_0.9.6_lib"
    net6_dir = pkg_dir / "net6.0"
    net472_dir = pkg_dir / "net472"
    net6_dir.mkdir(parents=True)
    net472_dir.mkdir(parents=True)

    net472_dll = net472_dir / "LibreHardwareMonitorLib.dll"
    net472_dll.write_text("fake dll content")

    monkeypatch.setattr(lhm_loader, "_detect_dotnet_core", lambda: "6.0.0")
    monkeypatch.setattr(lhm_loader, "_detect_dotnet_framework", lambda: None)

    lhm_loader.ensure_loaded(base_dir=str(tmp_path))

    expected_fallback_path = os.path.normpath(str(net472_dll))

    assert len(add_ref_paths) == 1
    assert add_ref_paths[0] == expected_fallback_path


def test_ensure_loaded_fallback_when_no_variant_chosen(monkeypatch, tmp_path):
    add_ref_paths = _setup_mock_clr_and_hardware_modules(monkeypatch)

    pkg_dir = tmp_path / "assets" / "LHM_0.9.6_lib"
    net472_dir = pkg_dir / "net472"
    net472_dir.mkdir(parents=True)
    net472_dll = net472_dir / "LibreHardwareMonitorLib.dll"
    net472_dll.write_text("fake dll content")

    monkeypatch.setattr(lhm_loader, "_detect_dotnet_core", lambda: None)
    monkeypatch.setattr(lhm_loader, "_detect_dotnet_framework", lambda: None)
    monkeypatch.setattr(lhm_loader, "_choose_asset_variant", lambda base_dir: None)

    lhm_loader.ensure_loaded(base_dir=str(tmp_path))

    expected_fallback_path = os.path.normpath(str(net472_dll))

    assert len(add_ref_paths) == 1
    assert add_ref_paths[0] == expected_fallback_path
