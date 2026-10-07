"""Regression tests for Intel GPU recognition and sensor tracking in LibreHardwareMonitor.

Verifies discovery (get_all_sensor_infos), GPU name retrieval (get_gpu_name, get_gpu_names),
and polling/readings with fake Intel GPU hardware, preserving AMD/NVIDIA behavior and old saved parameter IDs.
"""

from collections import defaultdict, deque
import threading
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from core import librehardwaremonitor as lhm_mod


class _FakeEnumItem:
    def __init__(self, name):
        self._name = name

    def ToString(self):
        return self._name

    def __str__(self):
        return self._name

    def __repr__(self):
        return self._name


class _FakeHardwareType:
    Cpu = _FakeEnumItem("Cpu")
    GpuAmd = _FakeEnumItem("GpuAmd")
    GpuNvidia = _FakeEnumItem("GpuNvidia")
    GpuIntel = _FakeEnumItem("GpuIntel")


class _FakeSensorType:
    Load = _FakeEnumItem("Load")
    Temperature = _FakeEnumItem("Temperature")
    Power = _FakeEnumItem("Power")


class _FakeSensor:
    def __init__(self, name, sensor_type, value=None, identifier=None):
        self.Name = name
        self.SensorType = sensor_type
        self.Value = value
        self.Identifier = identifier


class _FakeHardware:
    def __init__(self, name, hw_type, sensors=None):
        self.Name = name
        self.HardwareType = hw_type
        self.Sensors = sensors or []

    def Update(self):
        pass


class _FakeComputer:
    def __init__(self, hardware=None):
        self.Hardware = hardware or []
        self.IsGpuEnabled = False
        self.IsCpuEnabled = False
        self.close_calls = 0

    def Open(self):
        pass

    def Close(self):
        self.close_calls += 1


@pytest.mark.parametrize("layout", ["intel-first", "intel-middle"])
def test_saved_profile_roundtrip_after_intel_admission(
    layout, tmp_path, monkeypatch, fake_dpg, stub_logger
):
    """Real persistence keeps legacy ordinals and defaults across Intel admission."""
    from core.config_manager import ConfigManager

    cpu = _FakeHardware("CPU", _FakeHardwareType.Cpu, [
        _FakeSensor("CPU Total", _FakeSensorType.Load, 15, "/cpu/0/load/0")
    ])
    amd = _FakeHardware("AMD", _FakeHardwareType.GpuAmd, [
        _FakeSensor("GPU Core", _FakeSensorType.Load, 85, "/amdgpu/0/load/0")
    ])
    nvidia = _FakeHardware("NVIDIA", _FakeHardwareType.GpuNvidia, [
        _FakeSensor("GPU Core", _FakeSensorType.Load, 35, "/nvidiagpu/0/load/0")
    ])
    intel = _FakeHardware("Intel", _FakeHardwareType.GpuIntel, [
        _FakeSensor("GPU Core", _FakeSensorType.Load, 10, "/intelgpu/0/load/0")
    ])
    hardware = [cpu, amd, nvidia]
    monkeypatch.setattr(
        lhm_mod, "get_types",
        lambda base_dir=None: (
            lambda: _FakeComputer(hardware), _FakeSensorType, _FakeHardwareType
        ),
    )
    # Only the hardware boundary is fake; ConfigManager discovers sensors itself.
    assert ConfigManager.__init__.__globals__["get_all_sensor_infos"] is lhm_mod.get_all_sensor_infos

    def create_manager():
        manager = ConfigManager(
            stub_logger, fake_dpg,
            SimpleNamespace(set_profile_property=lambda *args, **kwargs: True),
            None,
            SimpleNamespace(themes={"enabled_text_theme": 1, "disabled_text_theme": 2}),
            str(tmp_path / "core"),
        )
        # Match the dynamic initialization sequence in app.py.
        manager.update_dynamic_input_field_keys()
        manager.update_dynamic_default_settings()
        manager.update_dynamic_key_type_map()
        return manager

    def assert_profile_values(manager, expected_ids, expected_values):
        actual_ids = {sensor["hw_name"]: sensor["parameter_id"] for sensor in manager.sensor_infos}
        assert actual_ids == expected_ids
        for hardware_name, values in expected_values.items():
            for suffix, expected in values.items():
                actual = fake_dpg.get_value(f"input_{expected_ids[hardware_name]}_{suffix}")
                assert actual == expected, (layout, hardware_name, suffix, actual, expected)
                assert type(actual) is type(expected), (layout, hardware_name, suffix)

    legacy_ids = {
        "CPU": "cpu1_load_01", "AMD": "gpu1_load_01", "NVIDIA": "gpu2_load_01"
    }
    expected_values = {
        "CPU": {"enable": True, "lower": 11, "upper": 77},
        "AMD": {"enable": True, "lower": 31, "upper": 71},
        "NVIDIA": {"enable": False, "lower": 43, "upper": 93},
    }
    original = create_manager()
    assert {sensor["hw_name"]: sensor["parameter_id"] for sensor in original.sensor_infos} == legacy_ids
    for key in original.input_field_keys:
        fake_dpg.set_value(f"input_{key}", original.Default_settings_original[key])
    for hardware_name, values in expected_values.items():
        for suffix, value in values.items():
            fake_dpg.set_value(f"input_{legacy_ids[hardware_name]}_{suffix}", value)
    original.save_profile("LegacyMixedGPU")

    hardware = (
        [intel, cpu, amd, nvidia] if layout == "intel-first"
        else [cpu, amd, intel, nvidia]
    )
    admitted_ids = {**legacy_ids, "Intel": "gpu3_load_01"}
    expected_values["Intel"] = {"enable": False, "lower": 0, "upper": 100}
    fake_dpg.values.clear()
    fake_dpg.items.clear()
    restarted = create_manager()
    assert restarted.load_profile_raw("LegacyMixedGPU") is True
    assert_profile_values(restarted, admitted_ids, expected_values)

    restarted.save_profile("ResavedMixedGPU")
    fake_dpg.values.clear()
    fake_dpg.items.clear()
    final = create_manager()
    assert final.load_profile_raw("ResavedMixedGPU") is True
    assert_profile_values(final, admitted_ids, expected_values)


def test_intel_gpu_discovery_standalone(monkeypatch):
    """Intel GPU on an Intel-only system starts at gpu1 for discovery."""
    intel_load = _FakeSensor("GPU Core", _FakeSensorType.Load, 45.0, "/intelgpu/0/load/0")
    intel_temp = _FakeSensor("GPU Core", _FakeSensorType.Temperature, 65.0, "/intelgpu/0/temperature/0")
    intel_power = _FakeSensor("GPU Package", _FakeSensorType.Power, 15.0, "/intelgpu/0/power/0")
    intel_gpu = _FakeHardware("Intel Iris Plus Graphics 640", _FakeHardwareType.GpuIntel, [intel_load, intel_temp, intel_power])

    comp = _FakeComputer([intel_gpu])

    monkeypatch.setattr(lhm_mod, "get_types", lambda base_dir=None: (lambda: comp, _FakeSensorType, _FakeHardwareType))

    infos = lhm_mod.get_all_sensor_infos(None)

    assert len(infos) == 3

    load_info = next(i for i in infos if i["sensor_type"] == _FakeSensorType.Load)
    assert load_info["hw_type"] == _FakeHardwareType.GpuIntel
    assert load_info["hw_name"] == "Intel Iris Plus Graphics 640"
    assert load_info["hw_id"] == "gpu1"
    assert load_info["parameter_id"] == "gpu1_load_01"
    assert load_info["sensor_name_indexed"] == "1 GPU Core"
    assert load_info["identifier"] == "/intelgpu/0/load/0"

    temp_info = next(i for i in infos if i["sensor_type"] == _FakeSensorType.Temperature)
    assert temp_info["parameter_id"] == "gpu1_temperature_01"

    power_info = next(i for i in infos if i["sensor_type"] == _FakeSensorType.Power)
    assert power_info["parameter_id"] == "gpu1_power_01"


def test_multi_gpu_discovery_preserves_amd_nvidia_ordinal_ids(monkeypatch):
    """Raw hardware Intel -> AMD -> NVIDIA gives AMD gpu1, NVIDIA gpu2, Intel gpu3, preserving old saved profiles."""
    intel_gpu = _FakeHardware(
        "Intel Iris Plus Graphics", _FakeHardwareType.GpuIntel,
        [_FakeSensor("GPU Core", _FakeSensorType.Load, 10.0, "/intelgpu/0/load/0")]
    )
    amd_gpu = _FakeHardware(
        "AMD Radeon RX 6800", _FakeHardwareType.GpuAmd,
        [_FakeSensor("GPU Core", _FakeSensorType.Load, 20.0, "/amdgpu/0/load/0")]
    )
    nvidia_gpu = _FakeHardware(
        "NVIDIA GeForce RTX 4090", _FakeHardwareType.GpuNvidia,
        [_FakeSensor("GPU Core", _FakeSensorType.Load, 30.0, "/nvidiagpu/0/load/0")]
    )

    comp = _FakeComputer([intel_gpu, amd_gpu, nvidia_gpu])
    monkeypatch.setattr(lhm_mod, "get_types", lambda base_dir=None: (lambda: comp, _FakeSensorType, _FakeHardwareType))

    infos = lhm_mod.get_all_sensor_infos(None)

    assert len(infos) == 3

    # AMD is relative first -> gpu1
    assert infos[0]["hw_name"] == "AMD Radeon RX 6800"
    assert infos[0]["hw_id"] == "gpu1"
    assert infos[0]["parameter_id"] == "gpu1_load_01"
    assert infos[0]["sensor_name_indexed"] == "1 GPU Core"

    # NVIDIA is relative second -> gpu2
    assert infos[1]["hw_name"] == "NVIDIA GeForce RTX 4090"
    assert infos[1]["hw_id"] == "gpu2"
    assert infos[1]["parameter_id"] == "gpu2_load_01"
    assert infos[1]["sensor_name_indexed"] == "2 GPU Core"

    # Intel appended -> gpu3
    assert infos[2]["hw_name"] == "Intel Iris Plus Graphics"
    assert infos[2]["hw_id"] == "gpu3"
    assert infos[2]["parameter_id"] == "gpu3_load_01"
    assert infos[2]["sensor_name_indexed"] == "3 GPU Core"


def test_old_saved_profile_targeting(monkeypatch):
    """Old saved profile settings for gpu1 target AMD, while Intel receives gpu3."""
    intel_gpu = _FakeHardware(
        "Intel Iris Plus Graphics", _FakeHardwareType.GpuIntel,
        [_FakeSensor("GPU Core", _FakeSensorType.Load, 10.0, "/intelgpu/0/load/0")]
    )
    amd_gpu = _FakeHardware(
        "AMD Radeon RX 6800", _FakeHardwareType.GpuAmd,
        [_FakeSensor("GPU Core", _FakeSensorType.Load, 85.0, "/amdgpu/0/load/0")]
    )

    comp = _FakeComputer([intel_gpu, amd_gpu])
    monkeypatch.setattr(lhm_mod, "get_types", lambda base_dir=None: (lambda: comp, _FakeSensorType, _FakeHardwareType))

    infos = lhm_mod.get_all_sensor_infos(None)

    # Simulated profile lookup by parameter_id
    gpu1_info = next(i for i in infos if i["parameter_id"] == "gpu1_load_01")
    gpu2_info = next(i for i in infos if i["parameter_id"] == "gpu2_load_01")

    assert gpu1_info["hw_name"] == "AMD Radeon RX 6800"
    assert gpu1_info["identifier"] == "/amdgpu/0/load/0"

    assert gpu2_info["hw_name"] == "Intel Iris Plus Graphics"
    assert gpu2_info["identifier"] == "/intelgpu/0/load/0"


def test_get_gpu_name_and_get_gpu_names_intel(monkeypatch, stub_logger, fake_dpg):
    """get_gpu_name and get_gpu_names order AMD/NVIDIA first and Intel appended."""
    intel_gpu = _FakeHardware("Intel Iris Plus Graphics", _FakeHardwareType.GpuIntel)
    nvidia_gpu = _FakeHardware("NVIDIA GeForce RTX 3080", _FakeHardwareType.GpuNvidia)

    comp = _FakeComputer([intel_gpu, nvidia_gpu])
    monkeypatch.setattr(lhm_mod, "ensure_loaded", lambda base_dir=None, logger=None: (lambda: comp, _FakeSensorType, _FakeHardwareType))

    sensor = lhm_mod.LHMSensor(lambda: True, stub_logger, fake_dpg, {}, interval=0.01, base_dir=None)

    assert sensor.get_gpu_name() == "NVIDIA GeForce RTX 3080"
    assert sensor.get_gpu_names() == ["NVIDIA GeForce RTX 3080", "Intel Iris Plus Graphics"]


def test_get_gpu_name_intel_only(monkeypatch, stub_logger, fake_dpg):
    """get_gpu_name and get_gpu_names work on Intel-only systems."""
    intel_gpu = _FakeHardware("Intel Iris Plus Graphics", _FakeHardwareType.GpuIntel)

    comp = _FakeComputer([intel_gpu])
    monkeypatch.setattr(lhm_mod, "ensure_loaded", lambda base_dir=None, logger=None: (lambda: comp, _FakeSensorType, _FakeHardwareType))

    sensor = lhm_mod.LHMSensor(lambda: True, stub_logger, fake_dpg, {}, interval=0.01, base_dir=None)

    assert sensor.get_gpu_name() == "Intel Iris Plus Graphics"
    assert sensor.get_gpu_names() == ["Intel Iris Plus Graphics"]


def test_poll_pass_intel_gpu_standalone(monkeypatch, stub_logger, fake_dpg):
    """_poll_pass records histories and updates percentiles/readings for standalone Intel GPU."""
    intel_load = _FakeSensor("GPU Core", _FakeSensorType.Load, 50.0, "/intelgpu/0/load/0")
    intel_temp = _FakeSensor("GPU Core", _FakeSensorType.Temperature, 60.0, "/intelgpu/0/temp/0")
    intel_gpu = _FakeHardware("Intel Iris Plus Graphics 650", _FakeHardwareType.GpuIntel, [intel_load, intel_temp])

    comp = _FakeComputer([intel_gpu])
    monkeypatch.setattr(lhm_mod, "ensure_loaded", lambda base_dir=None, logger=None: (lambda: comp, _FakeSensorType, _FakeHardwareType))

    sensor = lhm_mod.LHMSensor(lambda: True, stub_logger, fake_dpg, {}, interval=0.01, base_dir=None)

    with sensor._lock:
        readings = sensor._poll_pass()

    assert "Intel Iris Plus Graphics 650:" in readings
    assert "1 GPU Core" in readings
    assert "50.0" in readings
    assert "60.0" in readings

    assert sensor.gpu_percentiles["/intelgpu/0/load/0"] == 50.0
    assert sensor.gpu_percentiles["/intelgpu/0/temp/0"] == 60.0
    assert list(sensor.gpu_history["/intelgpu/0/load/0"]) == [50.0]
    assert sensor.gpu_hw_names == ["Intel Iris Plus Graphics 650"]


def test_poll_pass_mixed_gpus_indexing_agreement(monkeypatch, stub_logger, fake_dpg):
    """Active polling with Intel + AMD preserves AMD as index 1 and Intel as index 2."""
    intel_load = _FakeSensor("GPU Core", _FakeSensorType.Load, 30.0, "/intelgpu/0/load/0")
    amd_load = _FakeSensor("GPU Core", _FakeSensorType.Load, 75.0, "/amdgpu/0/load/0")

    intel_gpu = _FakeHardware("Intel Iris Plus Graphics", _FakeHardwareType.GpuIntel, [intel_load])
    amd_gpu = _FakeHardware("AMD Radeon RX 6700 XT", _FakeHardwareType.GpuAmd, [amd_load])

    comp = _FakeComputer([intel_gpu, amd_gpu])
    monkeypatch.setattr(lhm_mod, "ensure_loaded", lambda base_dir=None, logger=None: (lambda: comp, _FakeSensorType, _FakeHardwareType))

    sensor = lhm_mod.LHMSensor(lambda: True, stub_logger, fake_dpg, {}, interval=0.01, base_dir=None)

    with sensor._lock:
        readings = sensor._poll_pass()

    # Index 1 = AMD, Index 2 = Intel
    assert sensor.gpu_hw_names == ["AMD Radeon RX 6700 XT", "Intel Iris Plus Graphics"]

    assert sensor.gpu_percentiles[(_FakeSensorType.Load, "1 GPU Core")] == 75.0
    assert sensor.gpu_percentiles[(_FakeSensorType.Load, "2 GPU Core")] == 30.0

    assert sensor.gpu_percentiles["/amdgpu/0/load/0"] == 75.0
    assert sensor.gpu_percentiles["/intelgpu/0/load/0"] == 30.0

    blocks = readings.split("\n\n")
    assert blocks[0].startswith("AMD Radeon RX 6700 XT:")
    assert "1 GPU Core" in blocks[0]
    assert "75.0" in blocks[0]

    assert blocks[1].startswith("Intel Iris Plus Graphics:")
    assert "2 GPU Core" in blocks[1]
    assert "30.0" in blocks[1]
