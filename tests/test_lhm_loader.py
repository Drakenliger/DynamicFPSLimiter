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


def _setup_mock_clr_and_hardware(monkeypatch, active_is_core=False, active_major=4, active_version="4.0.30319.42000", fail_core_assembly_load=False):
    add_ref_paths = []

    class MockCLR:
        _active_runtime_info = {
            "is_core": active_is_core,
            "major": active_major,
            "version": active_version,
        }

        @staticmethod
        def AddReference(path):
            norm_path = os.path.normpath(str(path))
            # Simulate failure if loading a CoreCLR assembly when active runtime is netfx / incompatible
            if fail_core_assembly_load and ("net8" in norm_path or "net9" in norm_path or "net10" in norm_path):
                raise RuntimeError("Assembly built for CoreCLR cannot be loaded in .NET Framework")
            add_ref_paths.append(norm_path)

    fake_hw_mod = ModuleType("LibreHardwareMonitor.Hardware")
    fake_hw_mod.Computer = type("Computer", (), {})
    fake_hw_mod.SensorType = type("SensorType", (), {})
    fake_hw_mod.HardwareType = type("HardwareType", (), {})

    fake_lhm_mod = ModuleType("LibreHardwareMonitor")
    fake_lhm_mod.Hardware = fake_hw_mod

    fake_system_mod = ModuleType("System")
    ver_obj = type("Version", (), {"Major": active_major, "Minor": 0, "Build": 0})
    fake_system_mod.Environment = type("Environment", (), {"Version": ver_obj})

    monkeypatch.setattr(lhm_loader, "clr", MockCLR)
    monkeypatch.setitem(sys.modules, "clr", MockCLR)
    monkeypatch.setitem(sys.modules, "System", fake_system_mod)

    # Note: If fail_core_assembly_load is True and a Core assembly is attempted, import should also fail if AddReference was bypassed
    if not fail_core_assembly_load:
        monkeypatch.setitem(sys.modules, "LibreHardwareMonitor", fake_lhm_mod)
        monkeypatch.setitem(sys.modules, "LibreHardwareMonitor.Hardware", fake_hw_mod)
    else:
        # simulate missing module if attempted
        monkeypatch.setitem(sys.modules, "LibreHardwareMonitor", fake_lhm_mod)
        monkeypatch.setitem(sys.modules, "LibreHardwareMonitor.Hardware", fake_hw_mod)

    return add_ref_paths


def test_installed_core8_with_active_framework_selects_net472(monkeypatch):
    """
    Coexistence regression: .NET 8 Core runtime is installed on machine,
    but pythonnet initialized .NET Framework (active_is_core=False, major=4).
    Must select package/net472 and successfully load types.
    """
    add_ref_paths = _setup_mock_clr_and_hardware(
        monkeypatch,
        active_is_core=False,
        active_major=4,
        fail_core_assembly_load=True,
    )

    monkeypatch.setattr(lhm_loader, "_detect_dotnet_core", lambda: "8.0.31")
    monkeypatch.setattr(lhm_loader, "_detect_dotnet_framework", lambda: "4.8")

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src", "core"))
    comp, sensor, hw = lhm_loader.ensure_loaded(base_dir=project_root)

    assert comp is not None
    assert len(add_ref_paths) == 1
    expected_path = os.path.normpath(
        os.path.join(project_root, "assets", "LHM_0.9.6_lib", "net472", "LibreHardwareMonitorLib.dll")
    )
    assert add_ref_paths[0] == expected_path
    assert lhm_loader._LOADED is True


@pytest.mark.parametrize(
    "active_major, expected_variant",
    [
        (8, "net8.0"),
        (9, "net9.0"),
        (10, "net10.0"),
    ],
)
def test_active_coreclr_with_matching_installed_runtime(monkeypatch, active_major, expected_variant):
    """
    When active pythonnet runtime is CoreCLR (is_core=True) and matches installed version,
    must select the corresponding net8/net9/net10 variant.
    """
    add_ref_paths = _setup_mock_clr_and_hardware(
        monkeypatch,
        active_is_core=True,
        active_major=active_major,
        active_version=f"{active_major}.0.0",
        fail_core_assembly_load=False,
    )

    monkeypatch.setattr(lhm_loader, "_detect_dotnet_core", lambda: f"{active_major}.0.0")
    monkeypatch.setattr(lhm_loader, "_detect_dotnet_framework", lambda: None)

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src", "core"))
    comp, sensor, hw = lhm_loader.ensure_loaded(base_dir=project_root)

    assert comp is not None
    assert len(add_ref_paths) == 1
    expected_path = os.path.normpath(
        os.path.join(project_root, "assets", "LHM_0.9.6_lib", expected_variant, "LibreHardwareMonitorLib.dll")
    )
    assert add_ref_paths[0] == expected_path
    assert lhm_loader._LOADED is True


def test_framework_only_system_selects_net472(monkeypatch):
    """
    On a system with only .NET Framework installed and active, selects package/net472.
    """
    add_ref_paths = _setup_mock_clr_and_hardware(
        monkeypatch,
        active_is_core=False,
        active_major=4,
    )

    monkeypatch.setattr(lhm_loader, "_detect_dotnet_core", lambda: None)
    monkeypatch.setattr(lhm_loader, "_detect_dotnet_framework", lambda: "4.7.2")

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src", "core"))
    comp, sensor, hw = lhm_loader.ensure_loaded(base_dir=project_root)

    assert len(add_ref_paths) == 1
    assert add_ref_paths[0].endswith(os.path.join("net472", "LibreHardwareMonitorLib.dll"))


def test_absent_selected_dll_fallback_to_net472(monkeypatch, tmp_path):
    """
    When active CoreCLR is detected (e.g. net6.0) but selected DLL is absent in net6.0,
    it falls back to package/net472 DLL.
    """
    add_ref_paths = _setup_mock_clr_and_hardware(
        monkeypatch,
        active_is_core=True,
        active_major=6,
        active_version="6.0.0",
    )

    pkg_dir = tmp_path / "assets" / "LHM_0.9.6_lib"
    net6_dir = pkg_dir / "net6.0"
    net472_dir = pkg_dir / "net472"
    net6_dir.mkdir(parents=True)
    net472_dir.mkdir(parents=True)

    net472_dll = net472_dir / "LibreHardwareMonitorLib.dll"
    net472_dll.write_text("fake dll content")

    monkeypatch.setattr(lhm_loader, "_detect_dotnet_core", lambda: "6.0.0")

    lhm_loader.ensure_loaded(base_dir=str(tmp_path))

    expected_fallback = os.path.normpath(str(net472_dll))
    assert len(add_ref_paths) == 1
    assert add_ref_paths[0] == expected_fallback


def test_mismatch_error_not_cached_as_loaded(monkeypatch):
    """
    If clr.AddReference or assembly import fails, LHMLoadError is raised
    and _LOADED remains False.
    """
    _setup_mock_clr_and_hardware(
        monkeypatch,
        active_is_core=False,
        active_major=4,
    )

    def boom(path):
        raise RuntimeError("Assembly load failed")

    monkeypatch.setattr(lhm_loader.clr, "AddReference", boom)

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src", "core"))

    with pytest.raises(lhm_loader.LHMLoadError):
        lhm_loader.ensure_loaded(base_dir=project_root)

    assert lhm_loader._LOADED is False
