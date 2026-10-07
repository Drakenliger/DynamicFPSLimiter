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

    # Instantiate FPSUtils bypassing get_types / LHMLoadError
    utils = FPSUtils.__new__(FPSUtils)
    utils.cm = cm
    utils.lhm_sensor = lhm_sensor
    utils.logger = logger
    utils.dpg = dpg
    utils.HardwareType = SimpleNamespace(Cpu="Cpu", Gpu="Gpu")
    utils.SensorType = SimpleNamespace(Load="Load")
    return utils


def test_evaluator_missing_enabled_sensor_blocks_increase():
    # Healthy sensor (temp_1): 50 <= lower=70
    # Missing sensor (temp_2): percentile is None
    sensor_infos = [
        {"parameter_id": "temp_1", "sensor_type": "Temperature", "sensor_name": "GPU Temp 1", "hw_type": "Gpu", "hw_name": "GPU"},
        {"parameter_id": "temp_2", "sensor_type": "Temperature", "sensor_name": "GPU Temp 2", "hw_type": "Gpu", "hw_name": "GPU"},
    ]
    dpg_values = {
        "input_temp_1_enable": True, "input_temp_1_upper": 90.0, "input_temp_1_lower": 70.0,
        "input_temp_2_enable": True, "input_temp_2_upper": 90.0, "input_temp_2_lower": 70.0,
    }
    gpu_percentiles = {("Temperature", "GPU Temp 1"): 50.0, ("Temperature", "GPU Temp 2"): None}
    gpu_history = {("Temperature", "GPU Temp 1"): [50.0, 50.0], ("Temperature", "GPU Temp 2"): [50.0, 50.0]}

    utils = make_fps_utils(sensor_infos, dpg_values, gpu_percentiles, gpu_history)
    decision = utils.evaluate_cap_change([], [], "LibreHM")
    assert decision == (False, False)


def test_evaluator_empty_history_blocks_increase():
    # Healthy sensor (temp_1): 50 <= lower=70
    # Sensor with empty history (temp_2): history is []
    sensor_infos = [
        {"parameter_id": "temp_1", "sensor_type": "Temperature", "sensor_name": "GPU Temp 1", "hw_type": "Gpu", "hw_name": "GPU"},
        {"parameter_id": "temp_2", "sensor_type": "Temperature", "sensor_name": "GPU Temp 2", "hw_type": "Gpu", "hw_name": "GPU"},
    ]
    dpg_values = {
        "input_temp_1_enable": True, "input_temp_1_upper": 90.0, "input_temp_1_lower": 70.0,
        "input_temp_2_enable": True, "input_temp_2_upper": 90.0, "input_temp_2_lower": 70.0,
    }
    gpu_percentiles = {("Temperature", "GPU Temp 1"): 50.0, ("Temperature", "GPU Temp 2"): 50.0}
    gpu_history = {("Temperature", "GPU Temp 1"): [50.0, 50.0], ("Temperature", "GPU Temp 2"): []}

    utils = make_fps_utils(sensor_infos, dpg_values, gpu_percentiles, gpu_history)
    decision = utils.evaluate_cap_change([], [], "LibreHM")
    assert decision == (False, False)


def test_evaluator_disabled_missing_sensor_does_not_block():
    # Enabled healthy sensor (temp_1): 50 <= lower=70
    # Disabled missing sensor (temp_2): enable=False, percentile=None
    sensor_infos = [
        {"parameter_id": "temp_1", "sensor_type": "Temperature", "sensor_name": "GPU Temp 1", "hw_type": "Gpu", "hw_name": "GPU"},
        {"parameter_id": "temp_2", "sensor_type": "Temperature", "sensor_name": "GPU Temp 2", "hw_type": "Gpu", "hw_name": "GPU"},
    ]
    dpg_values = {
        "input_temp_1_enable": True, "input_temp_1_upper": 90.0, "input_temp_1_lower": 70.0,
        "input_temp_2_enable": False, "input_temp_2_upper": 90.0, "input_temp_2_lower": 70.0,
    }
    gpu_percentiles = {("Temperature", "GPU Temp 1"): 50.0, ("Temperature", "GPU Temp 2"): None}
    gpu_history = {("Temperature", "GPU Temp 1"): [50.0, 50.0], ("Temperature", "GPU Temp 2"): []}

    utils = make_fps_utils(sensor_infos, dpg_values, gpu_percentiles, gpu_history)
    decision = utils.evaluate_cap_change([], [], "LibreHM")
    assert decision == (False, True)


def test_evaluator_valid_overload_can_still_decrease_with_missing_sensor():
    # Overloaded sensor (temp_1): 95 >= upper=90
    # Missing sensor (temp_2): percentile is None
    sensor_infos = [
        {"parameter_id": "temp_1", "sensor_type": "Temperature", "sensor_name": "GPU Temp 1", "hw_type": "Gpu", "hw_name": "GPU"},
        {"parameter_id": "temp_2", "sensor_type": "Temperature", "sensor_name": "GPU Temp 2", "hw_type": "Gpu", "hw_name": "GPU"},
    ]
    dpg_values = {
        "input_temp_1_enable": True, "input_temp_1_upper": 90.0, "input_temp_1_lower": 70.0,
        "input_temp_2_enable": True, "input_temp_2_upper": 90.0, "input_temp_2_lower": 70.0,
    }
    gpu_percentiles = {("Temperature", "GPU Temp 1"): 95.0, ("Temperature", "GPU Temp 2"): None}
    gpu_history = {("Temperature", "GPU Temp 1"): [95.0, 95.0], ("Temperature", "GPU Temp 2"): []}

    utils = make_fps_utils(sensor_infos, dpg_values, gpu_percentiles, gpu_history)
    decision = utils.evaluate_cap_change([], [], "LibreHM")
    assert decision == (True, False)


def test_evaluator_no_enabled_sensors_returns_no_decision():
    sensor_infos = [
        {"parameter_id": "temp_1", "sensor_type": "Temperature", "sensor_name": "GPU Temp 1", "hw_type": "Gpu", "hw_name": "GPU"},
    ]
    dpg_values = {
        "input_temp_1_enable": False, "input_temp_1_upper": 90.0, "input_temp_1_lower": 70.0,
    }
    gpu_percentiles = {("Temperature", "GPU Temp 1"): 50.0}
    gpu_history = {("Temperature", "GPU Temp 1"): [50.0, 50.0]}

    utils = make_fps_utils(sensor_infos, dpg_values, gpu_percentiles, gpu_history)
    decision = utils.evaluate_cap_change([], [], "LibreHM")
    assert decision == (False, False)


def test_evaluator_empty_sensor_infos_returns_no_decision():
    utils = make_fps_utils([], {})
    decision = utils.evaluate_cap_change([], [], "LibreHM")
    assert decision == (False, False)
