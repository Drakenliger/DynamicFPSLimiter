"""
Linux-portable tests for LibreHM decision helper and evaluate_cap_change missing enabled sensor behavior.
"""

from types import SimpleNamespace
import pytest
from core.fps_utils import FPSUtils, evaluate_librehm_decision


def test_pure_evaluate_librehm_decision():
    # 1. No enabled sensors -> (False, False)
    assert evaluate_librehm_decision(has_enabled_sensors=False, decrease_checks=[True], increase_checks=[True], has_missing_enabled_data=False) == (False, False)
    assert evaluate_librehm_decision(has_enabled_sensors=False, decrease_checks=[], increase_checks=[], has_missing_enabled_data=True) == (False, False)

    # 2. Enabled healthy sensor + missing sensor -> decrease=False, increase=False
    assert evaluate_librehm_decision(has_enabled_sensors=True, decrease_checks=[], increase_checks=[True], has_missing_enabled_data=True) == (False, False)

    # 3. Valid overload + missing sensor -> decrease=True, increase=False
    assert evaluate_librehm_decision(has_enabled_sensors=True, decrease_checks=[True], increase_checks=[], has_missing_enabled_data=True) == (True, False)

    # 4. Disabled missing sensor (so has_missing_enabled_data=False) + healthy enabled sensor -> decrease=False, increase=True
    assert evaluate_librehm_decision(has_enabled_sensors=True, decrease_checks=[], increase_checks=[True], has_missing_enabled_data=False) == (False, True)

    # 5. Increase checks empty + no missing data -> decrease=False, increase=False
    assert evaluate_librehm_decision(has_enabled_sensors=True, decrease_checks=[], increase_checks=[], has_missing_enabled_data=False) == (False, False)


class MockDPG:
    def __init__(self, values=None, items=None):
        self.values = values or {}
        self.items = set(items or self.values.keys())

    def does_item_exist(self, tag):
        return tag in self.items or tag in self.values

    def get_value(self, tag):
        return self.values.get(tag)

    def set_value(self, tag, val):
        self.values[tag] = val


class MockLogger:
    def __init__(self):
        self.logs = []

    def add_log(self, msg):
        self.logs.append(msg)


def make_fps_utils(sensor_infos, dpg_values, gpu_percentiles=None, gpu_history=None, cpu_percentiles=None, cpu_history=None):
    cm = SimpleNamespace(sensor_infos=sensor_infos)
    dpg = MockDPG(dpg_values)
    lhm_sensor = SimpleNamespace(
        _lock=None,
        gpu_percentiles=gpu_percentiles or {},
        gpu_history_long=gpu_history or {},
        cpu_percentiles=cpu_percentiles or {},
        cpu_history_long=cpu_history or {},
        gpu_hw_names=[],
    )
    logger = MockLogger()

    utils = FPSUtils.__new__(FPSUtils)
    utils.cm = cm
    utils.lhm_sensor = lhm_sensor
    utils.logger = logger
    utils.dpg = dpg
    utils.HardwareType = SimpleNamespace(Cpu="Cpu", Gpu="Gpu")
    utils.SensorType = SimpleNamespace(Load="Load", Temperature="Temperature")
    return utils


@pytest.mark.parametrize("hw_type", ["Cpu", "Gpu"])
@pytest.mark.parametrize("case,expected", [
    ("none_value", (False, False)),
    ("empty_history", (False, False)),
    ("disabled_missing", (False, True)),
    ("valid_overload", (True, False)),
    ("no_enabled", (False, False)),
])
def test_evaluator_canonical_identifier_cases(hw_type, case, expected):
    prefix = "cpu" if hw_type == "Cpu" else "gpu"
    id1 = f"/{prefix}/0/load/1"
    id2 = f"/{prefix}/0/load/2"

    sensor_infos = [
        {"parameter_id": "s1", "sensor_type": "Load", "sensor_name": "Core #1", "hw_type": hw_type, "hw_name": "HW1", "identifier": id1},
        {"parameter_id": "s2", "sensor_type": "Load", "sensor_name": "Core #2", "hw_type": hw_type, "hw_name": "HW1", "identifier": id2},
    ]

    if case == "none_value":
        dpg_values = {
            "input_s1_enable": True, "input_s1_upper": 90.0, "input_s1_lower": 70.0,
            "input_s2_enable": True, "input_s2_upper": 90.0, "input_s2_lower": 70.0,
        }
        percentiles = {id1: 50.0, id2: None}
        history = {id1: [50.0, 50.0], id2: [50.0, 50.0]}
    elif case == "empty_history":
        dpg_values = {
            "input_s1_enable": True, "input_s1_upper": 90.0, "input_s1_lower": 70.0,
            "input_s2_enable": True, "input_s2_upper": 90.0, "input_s2_lower": 70.0,
        }
        percentiles = {id1: 50.0, id2: 50.0}
        history = {id1: [50.0, 50.0], id2: []}
    elif case == "disabled_missing":
        dpg_values = {
            "input_s1_enable": True, "input_s1_upper": 90.0, "input_s1_lower": 70.0,
            "input_s2_enable": False, "input_s2_upper": 90.0, "input_s2_lower": 70.0,
        }
        percentiles = {id1: 50.0, id2: None}
        history = {id1: [50.0, 50.0], id2: []}
    elif case == "valid_overload":
        dpg_values = {
            "input_s1_enable": True, "input_s1_upper": 90.0, "input_s1_lower": 70.0,
            "input_s2_enable": True, "input_s2_upper": 90.0, "input_s2_lower": 70.0,
        }
        percentiles = {id1: 95.0, id2: None}
        history = {id1: [95.0, 95.0], id2: []}
    elif case == "no_enabled":
        dpg_values = {
            "input_s1_enable": False, "input_s1_upper": 90.0, "input_s1_lower": 70.0,
            "input_s2_enable": False, "input_s2_upper": 90.0, "input_s2_lower": 70.0,
        }
        percentiles = {id1: 50.0, id2: 50.0}
        history = {id1: [50.0, 50.0], id2: [50.0, 50.0]}

    p_dict = {"cpu_percentiles": percentiles, "cpu_history": history} if hw_type == "Cpu" else {"gpu_percentiles": percentiles, "gpu_history": history}
    utils = make_fps_utils(sensor_infos, dpg_values, **p_dict)
    assert utils.evaluate_cap_change([], [], "LibreHM") == expected


@pytest.mark.parametrize("hw_type", ["Cpu", "Gpu"])
def test_healthy_tuple_alias_must_not_override_missing_canonical_identity(hw_type):
    prefix = "cpu" if hw_type == "Cpu" else "gpu"
    canonical_id = f"/{prefix}/0/load/1"

    sensor_infos = [
        {"parameter_id": "s1", "sensor_type": "Load", "sensor_name": "Core #1", "hw_type": hw_type, "hw_name": "HW1", "identifier": canonical_id},
    ]
    dpg_values = {
        "input_s1_enable": True, "input_s1_upper": 90.0, "input_s1_lower": 70.0,
    }

    # Percentiles dict maps tuple alias key ("Load", "Core #1") to healthy 50.0,
    # but canonical_id is None / missing.
    percentiles = {("Load", "Core #1"): 50.0, canonical_id: None}
    history = {("Load", "Core #1"): [50.0, 50.0], canonical_id: []}

    p_dict = {"cpu_percentiles": percentiles, "cpu_history": history} if hw_type == "Cpu" else {"gpu_percentiles": percentiles, "gpu_history": history}
    utils = make_fps_utils(sensor_infos, dpg_values, **p_dict)

    # Must resolve via canonical identifier (None) and NOT fall back to healthy tuple alias
    assert utils.evaluate_cap_change([], [], "LibreHM") == (False, False)


def test_evaluator_empty_sensor_infos_returns_no_decision():
    utils = make_fps_utils([], {})
    assert utils.evaluate_cap_change([], [], "LibreHM") == (False, False)
