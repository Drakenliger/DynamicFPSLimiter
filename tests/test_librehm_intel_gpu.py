"""Regression tests for Intel GPU recognition and sensor tracking in LibreHardwareMonitor.

Verifies discovery (get_all_sensor_infos), GPU name retrieval (get_gpu_name, get_gpu_names),
and polling/readings with fake Intel GPU hardware, preserving AMD/NVIDIA behavior.
"""

from collections import defaultdict, deque
import threading
from types import SimpleNamespace
from unittest.mock import MagicMock

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


def test_intel_gpu_discovery(monkeypatch):
    """get_all_sensor_infos correctly identifies Intel GPU hardware and assigns parameter_id / hw_id."""
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


def test_multi_gpu_discovery_intel_amd_nvidia(monkeypatch):
    """get_all_sensor_infos correctly sequences indices across Intel, AMD, and NVIDIA GPUs."""
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
    assert infos[0]["hw_name"] == "Intel Iris Plus Graphics"
    assert infos[0]["hw_id"] == "gpu1"
    assert infos[0]["parameter_id"] == "gpu1_load_01"

    assert infos[1]["hw_name"] == "AMD Radeon RX 6800"
    assert infos[1]["hw_id"] == "gpu2"
    assert infos[1]["parameter_id"] == "gpu2_load_01"

    assert infos[2]["hw_name"] == "NVIDIA GeForce RTX 4090"
    assert infos[2]["hw_id"] == "gpu3"
    assert infos[2]["parameter_id"] == "gpu3_load_01"


def test_get_gpu_name_and_get_gpu_names_intel(monkeypatch, stub_logger, fake_dpg):
    """get_gpu_name and get_gpu_names recognize Intel GPUs along with AMD/NVIDIA."""
    intel_gpu = _FakeHardware("Intel Iris Plus Graphics", _FakeHardwareType.GpuIntel)
    nvidia_gpu = _FakeHardware("NVIDIA GeForce RTX 3080", _FakeHardwareType.GpuNvidia)

    comp = _FakeComputer([intel_gpu, nvidia_gpu])
    monkeypatch.setattr(lhm_mod, "ensure_loaded", lambda base_dir=None, logger=None: (lambda: comp, _FakeSensorType, _FakeHardwareType))

    sensor = lhm_mod.LHMSensor(lambda: True, stub_logger, fake_dpg, {}, interval=0.01, base_dir=None)

    assert sensor.get_gpu_name() == "Intel Iris Plus Graphics"
    assert sensor.get_gpu_names() == ["Intel Iris Plus Graphics", "NVIDIA GeForce RTX 3080"]


def test_poll_pass_intel_gpu(monkeypatch, stub_logger, fake_dpg):
    """_poll_pass records histories and updates percentiles/readings for Intel GPUs."""
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
