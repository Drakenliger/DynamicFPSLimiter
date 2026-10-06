"""Tests for LibreHM sensor identity, duplicate naming per sensor type, first-None stability, and stale sample invalidation.

Uses AST parsing to execute actual production function and method bodies in isolated namespaces without importing or polluting clr/lhm_loader modules.
"""
import ast
from collections import defaultdict, deque
from pathlib import Path
import statistics
import threading
from types import SimpleNamespace
from unittest.mock import MagicMock

from core.cap_policy import evaluate_legacy_cap_change

SRC_DIR = Path(__file__).resolve().parents[1] / "src" / "core"


class MockSensor:
    def __init__(self, name, sensor_type, value=None, identifier=None):
        self.Name = name
        self.SensorType = sensor_type
        self.Value = value
        self.Identifier = identifier


class MockHardware:
    def __init__(self, name, hw_type, sensors=None):
        self.Name = name
        self.HardwareType = hw_type
        self.Sensors = sensors or []

    def Update(self):
        pass


class MockComputer:
    def __init__(self, hardware=None):
        self.Hardware = hardware or []
        self.IsGpuEnabled = False
        self.IsCpuEnabled = False

    def Open(self):
        pass

    def Close(self):
        pass


class FakeEnumItem:
    def __init__(self, name):
        self._name = name

    def ToString(self):
        return self._name

    def __str__(self):
        return self._name

    def __repr__(self):
        return self._name


def _load_lhm_ast(fake_types=None):
    tree = ast.parse((SRC_DIR / "librehardwaremonitor.py").read_text())
    # Strip top-level import core.lhm_loader from AST to avoid loading clr
    tree.body = [n for n in tree.body if not (isinstance(n, ast.ImportFrom) and n.module == "core.lhm_loader")]

    class LHMLoadError(RuntimeError):
        pass

    scope = {
        "get_types": lambda base_dir=None: fake_types() if fake_types else None,
        "ensure_loaded": lambda base_dir=None, logger=None: fake_types() if fake_types else None,
        "LHMLoadError": LHMLoadError,
        "deque": deque,
        "defaultdict": defaultdict,
        "time": SimpleNamespace(sleep=lambda x: None),
        "threading": threading,
        "np": None,
        "os": SimpleNamespace(),
        "sys": SimpleNamespace(),
        "Path": Path,
    }
    exec(compile(tree, "<librehardwaremonitor>", "exec"), scope)
    return scope


def _load_fps_evaluator():
    tree = ast.parse((SRC_DIR / "fps_utils.py").read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "FPSUtils")
    method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "evaluate_cap_change")
    scope = {"statistics": statistics, "evaluate_legacy_cap_change": evaluate_legacy_cap_change}
    exec(compile(ast.Module(body=[method], type_ignores=[]), "<FPSUtils>", "exec"), scope)
    return scope["evaluate_cap_change"]


def test_duplicate_names_across_types():
    """Duplicate names across different sensor types should NOT share count sequence."""
    lhm_scope = _load_lhm_ast()
    get_selected_sensor_details = lhm_scope["get_selected_sensor_details"]
    get_selected_sensor_values = lhm_scope["get_selected_sensor_values"]

    s_load = MockSensor("Core #1", FakeEnumItem("Load"), 50.0, "/cpu/0/load/1")
    s_temp = MockSensor("Core #1", FakeEnumItem("Temperature"), 60.0, "/cpu/0/temp/1")

    hw = MockHardware("CPU", FakeEnumItem("Cpu"), [s_load, s_temp])
    sensor_map = {s_load.SensorType: None, s_temp.SensorType: None}

    details = get_selected_sensor_details(hw, sensor_map)
    names = [d["name"] for d in details]

    # Both are first of their respective sensor types, so neither gets " (1)" suffix
    assert names == ["Core #1", "Core #1"]

    values = get_selected_sensor_values(hw, sensor_map)
    assert values[s_load.SensorType]["Core #1"] == 50.0
    assert values[s_temp.SensorType]["Core #1"] == 60.0


def test_first_none_then_recover_stability():
    """When the first duplicate sensor has Value=None, subsequent duplicate names and identifiers remain stable."""
    lhm_scope = _load_lhm_ast()
    get_selected_sensor_details = lhm_scope["get_selected_sensor_details"]
    get_selected_sensor_values = lhm_scope["get_selected_sensor_values"]

    st = FakeEnumItem("Control")
    s1 = MockSensor("Fan", st, None, "/gpu/0/fan/0")
    s2 = MockSensor("Fan", st, 80.0, "/gpu/0/fan/1")

    hw = MockHardware("GPU", FakeEnumItem("GpuNvidia"), [s1, s2])
    sensor_map = {st: None}

    # First polling tick: s1 Value is None
    details1 = get_selected_sensor_details(hw, sensor_map)
    assert details1[0]["name"] == "Fan"
    assert details1[0]["identifier"] == "/gpu/0/fan/0"
    assert details1[1]["name"] == "Fan (1)"
    assert details1[1]["identifier"] == "/gpu/0/fan/1"

    values1 = get_selected_sensor_values(hw, sensor_map)
    assert "Fan" not in values1[st]
    assert values1[st]["Fan (1)"] == 80.0

    # Second polling tick: s1 recovers
    s1.Value = 40.0
    values2 = get_selected_sensor_values(hw, sensor_map)
    assert values2[st]["Fan"] == 40.0
    assert values2[st]["Fan (1)"] == 80.0


def test_two_cpus_identical_sensor_names_distinct_histories():
    """Two CPUs with identical sensor names maintain distinct histories/percentiles via identifier."""
    st_temp = FakeEnumItem("Temperature")
    s_type = SimpleNamespace(Load=FakeEnumItem("Load"), Temperature=st_temp, Power=FakeEnumItem("Power"))
    hw_type = SimpleNamespace(Cpu=FakeEnumItem("Cpu"), GpuAmd=FakeEnumItem("GpuAmd"), GpuNvidia=FakeEnumItem("GpuNvidia"))

    s1 = MockSensor("Core Max", st_temp, 10.0, "/amdcpu/0/temp/0")
    s2 = MockSensor("Core Max", st_temp, 90.0, "/amdcpu/1/temp/0")
    cpu1 = MockHardware("CPU 1", hw_type.Cpu, [s1])
    cpu2 = MockHardware("CPU 2", hw_type.Cpu, [s2])

    comp = MockComputer([cpu1, cpu2])
    fake_types = (lambda: comp, s_type, hw_type)

    lhm_scope = _load_lhm_ast(lambda: fake_types)
    LHMSensor = lhm_scope["LHMSensor"]

    sensor = LHMSensor.__new__(LHMSensor)
    sensor.Computer = lambda: comp
    sensor.SensorType = s_type
    sensor.HardwareType = hw_type
    sensor.computer = comp
    sensor.percentile = 70
    sensor.interval = 0.01
    sensor.CPU_SENSORS = {s_type.Temperature: None}
    sensor.GPU_SENSORS = {}
    sensor.cpu_history = defaultdict(lambda: deque(maxlen=20))
    sensor.cpu_history_long = defaultdict(lambda: deque(maxlen=600))
    sensor.cpu_percentiles = defaultdict(float)
    sensor.gpu_history = defaultdict(lambda: deque(maxlen=20))
    sensor.gpu_history_long = defaultdict(lambda: deque(maxlen=600))
    sensor.gpu_percentiles = defaultdict(float)
    sensor._lock = threading.Lock()
    sensor._should_stop = SimpleNamespace(is_set=lambda: False)

    run_ticks = [0]
    def poll_running():
        run_ticks[0] += 1
        return run_ticks[0] <= 1

    sensor._running = poll_running
    sensor.dpg = MagicMock()
    sensor.gui_queue = None

    LHMSensor._poll_loop(sensor)

    assert sensor.cpu_percentiles["/amdcpu/0/temp/0"] == 10.0
    assert sensor.cpu_percentiles["/amdcpu/1/temp/0"] == 90.0


def test_gpu_removal_reindex_distinct_histories():
    """GPU removal/reindexing maintains distinct histories without corrupting percentiles."""
    st_load = FakeEnumItem("Load")
    s_type = SimpleNamespace(Load=st_load, Temperature=FakeEnumItem("Temperature"), Power=FakeEnumItem("Power"))
    hw_type = SimpleNamespace(Cpu=FakeEnumItem("Cpu"), GpuAmd=FakeEnumItem("GpuAmd"), GpuNvidia=FakeEnumItem("GpuNvidia"))

    g1_s = MockSensor("GPU Core", st_load, 90.0, "/gpu/0/load/0")
    g2_s = MockSensor("GPU Core", st_load, 30.0, "/gpu/1/load/0")
    gpu1 = MockHardware("GPU 1", hw_type.GpuNvidia, [g1_s])
    gpu2 = MockHardware("GPU 2", hw_type.GpuNvidia, [g2_s])

    comp = MockComputer([gpu1, gpu2])
    fake_types = (lambda: comp, s_type, hw_type)

    lhm_scope = _load_lhm_ast(lambda: fake_types)
    LHMSensor = lhm_scope["LHMSensor"]

    sensor = LHMSensor.__new__(LHMSensor)
    sensor.Computer = lambda: comp
    sensor.SensorType = s_type
    sensor.HardwareType = hw_type
    sensor.computer = comp
    sensor.percentile = 70
    sensor.interval = 0.01
    sensor.CPU_SENSORS = {}
    sensor.GPU_SENSORS = {st_load: None}
    sensor.cpu_history = defaultdict(lambda: deque(maxlen=20))
    sensor.cpu_history_long = defaultdict(lambda: deque(maxlen=600))
    sensor.cpu_percentiles = defaultdict(float)
    sensor.gpu_history = defaultdict(lambda: deque(maxlen=20))
    sensor.gpu_history_long = defaultdict(lambda: deque(maxlen=600))
    sensor.gpu_percentiles = defaultdict(float)
    sensor._lock = threading.Lock()
    sensor._should_stop = SimpleNamespace(is_set=lambda: False)

    run_ticks = [0]
    def poll_running():
        run_ticks[0] += 1
        if run_ticks[0] == 2: # GPU 1 removed on tick 2 within same poll loop
            comp.Hardware = [gpu2]
        return run_ticks[0] <= 2

    sensor._running = poll_running
    sensor.dpg = MagicMock()
    sensor.gui_queue = None

    LHMSensor._poll_loop(sensor)

    # GPU 1 identifier is unrefreshed -> None
    assert sensor.gpu_percentiles["/gpu/0/load/0"] is None
    # GPU 2 identifier remains 30.0 and is not corrupted by GPU 1's history
    assert sensor.gpu_percentiles["/gpu/1/load/0"] == 30.0


def test_get_all_sensor_infos_executes_actual_discovery():
    """get_all_sensor_infos populates discovery metadata including identifier and parameter_id."""
    st_temp = FakeEnumItem("Temperature")
    s_type = SimpleNamespace(Load=FakeEnumItem("Load"), Temperature=st_temp, Power=FakeEnumItem("Power"))
    hw_type = SimpleNamespace(Cpu=FakeEnumItem("Cpu"), GpuAmd=FakeEnumItem("GpuAmd"), GpuNvidia=FakeEnumItem("GpuNvidia"))

    s1 = MockSensor("Core Max", st_temp, 55.0, "/amdcpu/0/temp/0")
    hw = MockHardware("AMD CPU", hw_type.Cpu, [s1])
    comp = MockComputer([hw])

    fake_types = (lambda: comp, s_type, hw_type)
    lhm_scope = _load_lhm_ast(lambda: fake_types)
    get_all_sensor_infos = lhm_scope["get_all_sensor_infos"]

    infos = get_all_sensor_infos(None)
    assert len(infos) == 1
    assert infos[0]["identifier"] == "/amdcpu/0/temp/0"
    assert infos[0]["parameter_id"] == "cpu1_temperature_01"
    assert infos[0]["sensor_name_indexed"] == "Core Max"


def test_missing_identifier_does_not_fall_through_to_sibling():
    """Evaluator with a selected missing identifier returns None and does NOT fall through to sibling sensor."""
    evaluate_cap_change = _load_fps_evaluator()

    dpg = MagicMock()
    dpg.does_item_exist.return_value = True
    dpg.get_value.side_effect = lambda tag: {
        "input_monitoring_method": "LibreHM",
        "input_cpu1_load_01_enable": True,
        "input_cpu1_load_01_upper": 80.0,
        "input_cpu1_load_01_lower": 60.0,
    }.get(tag)

    sensor_info = {
        "parameter_id": "cpu1_load_01",
        "sensor_type": "Load",
        "sensor_name": "Core #1",
        "sensor_name_indexed": "Core #1",
        "hw_name": "CPU",
        "hw_type": "Cpu",
        "identifier": "/cpu/0/load/1",
    }

    cm = SimpleNamespace(sensor_infos=[sensor_info])

    # Sibling sensor (/cpu/0/load/2) has value 90.0 under same display name key ("Load", "Core #1"),
    # but selected identifier /cpu/0/load/1 is missing (None / not present)
    lhm_sensor = SimpleNamespace(
        _lock=None,
        cpu_percentiles={("Load", "Core #1"): 90.0}, # display key holds sibling value
        cpu_history_long={("Load", "Core #1"): [90.0]},
        gpu_percentiles={},
        gpu_history_long={},
        HardwareType=SimpleNamespace(Cpu="Cpu"),
    )

    fps_utils = SimpleNamespace(cm=cm, lhm_sensor=lhm_sensor, logger=MagicMock(), dpg=dpg, HardwareType=SimpleNamespace(Cpu="Cpu"))

    dec = evaluate_cap_change(fps_utils, [], [], "LibreHM")

    # Selected identifier is missing, so decrease check cannot trigger
    assert dec == (False, False)
