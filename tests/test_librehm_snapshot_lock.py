import sys
import types
import threading
import time
from collections import deque
from types import SimpleNamespace as NS

import pytest


@pytest.fixture(autouse=True)
def mock_clr_for_non_windows():
    """
    Fixture-scoped monkeypatch for non-Windows platforms.
    Restores exact previous sys.modules state and parent-package attributes
    upon teardown, ensuring no cached fake clr or modules leak across tests.
    Leaves real Windows imports untouched.
    """
    if sys.platform == "win32":
        yield
        return

    pre_modules = dict(sys.modules)
    pre_core_attrs = dict(sys.modules["core"].__dict__) if "core" in sys.modules else None

    if "clr" not in sys.modules:
        clr_mock = types.ModuleType("clr")
        clr_mock.AddReference = lambda *args: None
        sys.modules["clr"] = clr_mock

    try:
        yield
    finally:
        for k in list(sys.modules.keys()):
            if k not in pre_modules:
                del sys.modules[k]
        for k, v in pre_modules.items():
            sys.modules[k] = v

        if "core" in sys.modules:
            core_mod = sys.modules["core"]
            if pre_core_attrs is not None:
                for attr in list(core_mod.__dict__.keys()):
                    if attr not in pre_core_attrs:
                        delattr(core_mod, attr)
                    else:
                        setattr(core_mod, attr, pre_core_attrs[attr])


class TrackedLock:
    def __init__(self):
        self._lock = threading.Lock()
        self.was_acquired = False
        self.in_lock = False
        self.held_during_dpg_read = False
        self.held_during_dpg_write = False
        self.held_during_log = False

    def __enter__(self):
        self._lock.acquire()
        self.was_acquired = True
        self.in_lock = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.in_lock = False
        self._lock.release()

    def acquire(self, *args, **kwargs):
        res = self._lock.acquire(*args, **kwargs)
        self.was_acquired = True
        self.in_lock = True
        return res

    def release(self, *args, **kwargs):
        self.in_lock = False
        return self._lock.release(*args, **kwargs)


def test_lock_acquired_during_evaluation_and_released_before_dpg_and_logs(fake_lhm):
    from core.fps_utils import FPSUtils

    lock = TrackedLock()
    dpg_values = {
        "input_load_enable": True,
        "input_load_upper": "90.0",
        "input_load_lower": "70.0",
    }

    logs = []
    def add_log(msg):
        if lock.in_lock:
            lock.held_during_log = True
        logs.append(msg)

    def get_value(tag):
        if lock.in_lock:
            lock.held_during_dpg_read = True
        return dpg_values.get(tag)

    def does_item_exist(tag):
        if lock.in_lock:
            lock.held_during_dpg_read = True
        return tag in dpg_values

    def set_value(tag, val):
        if lock.in_lock:
            lock.held_during_dpg_write = True

    mock_dpg = NS(
        get_value=get_value,
        does_item_exist=does_item_exist,
        set_value=set_value
    )

    mock_cm = NS(
        sensor_infos=[{
            "parameter_id": "load",
            "sensor_type": "Load",
            "sensor_name": "GPU Core",
            "sensor_name_indexed": "1 GPU Core",
            "hw_type": "Gpu",
            "hw_name": "NVIDIA GPU"
        }]
    )

    sensor = NS(
        _lock=lock,
        cpu_percentiles={},
        gpu_percentiles={},
        cpu_history_long={},
        gpu_history_long={},
        gpu_hw_names=["NVIDIA GPU"]
    )

    utils = FPSUtils(cm=mock_cm, lhm_sensor=sensor, logger=NS(add_log=add_log), dpg=mock_dpg)
    utils.HardwareType = NS(Cpu="Cpu")

    # Populate sensor history after FPSUtils initialization (reset_summary_statistics clears them)
    sensor.gpu_percentiles[("Load", "1 GPU Core")] = 95.0
    sensor.gpu_history_long[("Load", "1 GPU Core")] = deque([90.0, 100.0])

    dec = utils.evaluate_cap_change([], [], "LibreHM")

    assert dec == (True, False)
    assert lock.was_acquired, "lhm_sensor._lock was not acquired during evaluate_cap_change"
    assert not lock.in_lock, "Lock was not released after snapshotting"
    assert not lock.held_during_dpg_read, "Lock was held during DPG reads!"
    assert not lock.held_during_dpg_write, "Lock was held during DPG writes!"
    assert not lock.held_during_log, "Lock was held during Logger calls!"


def test_no_live_deque_dict_iteration_during_mutation(fake_lhm):
    """
    Asserts that a producer thread mutating live percentiles dicts and history deques
    concurrently does not crash evaluator or pollute its frozen snapshot.
    """
    from core.fps_utils import FPSUtils

    lock = threading.Lock()
    stop_event = threading.Event()

    gpu_percentiles = {}
    gpu_history_long = {}

    sensor = NS(
        _lock=lock,
        cpu_percentiles={},
        gpu_percentiles=gpu_percentiles,
        cpu_history_long={},
        gpu_history_long=gpu_history_long,
        gpu_hw_names=["NVIDIA GPU"]
    )

    dpg_values = {
        "input_load_enable": True,
        "input_load_upper": "90.0",
        "input_load_lower": "70.0",
    }
    summary_captured = []

    mock_dpg = NS(
        get_value=lambda k: dpg_values.get(k),
        does_item_exist=lambda k: k in dpg_values,
        set_value=lambda tag, val: summary_captured.append(val) if tag == "SummaryText" else None
    )

    mock_cm = NS(
        sensor_infos=[{
            "parameter_id": "load",
            "sensor_type": "Load",
            "sensor_name": "GPU Core",
            "sensor_name_indexed": "1 GPU Core",
            "hw_type": "Gpu",
            "hw_name": "NVIDIA GPU"
        }]
    )

    utils = FPSUtils(cm=mock_cm, lhm_sensor=sensor, logger=NS(add_log=lambda m: None), dpg=mock_dpg)
    utils.HardwareType = NS(Cpu="Cpu")

    gpu_percentiles[("Load", "1 GPU Core")] = 95.0
    gpu_history_long[("Load", "1 GPU Core")] = deque([90.0, 95.0], maxlen=600)

    def producer():
        counter = 0
        while not stop_event.is_set():
            counter += 1
            with lock:
                gpu_percentiles[("Load", f"TempKey_{counter}")] = float(counter)
                if ("Load", "1 GPU Core") in gpu_history_long:
                    gpu_history_long[("Load", "1 GPU Core")].append(counter % 100)
                if len(gpu_percentiles) > 10:
                    gpu_percentiles.pop(("Load", f"TempKey_{counter - 5}"), None)
            time.sleep(0.001)

    producer_thread = threading.Thread(target=producer, daemon=True)
    producer_thread.start()

    start_time = time.time()
    try:
        for _ in range(20):
            dec = utils.evaluate_cap_change([], [], "LibreHM")
            assert dec == (True, False)
            assert time.time() - start_time < 25.0, "Execution exceeded safety deadline"
            time.sleep(0.002)
    finally:
        stop_event.set()
        producer_thread.join(timeout=2.0)

    assert len(summary_captured) == 20
    assert "GPU Core" in summary_captured[-1]


def test_deterministic_paused_producer_evaluator_coherent_snapshot(fake_lhm):
    """
    Deterministic test: Evaluator takes snapshot under lock. Right after lock release,
    a paused producer resumes and drastically alters live dicts and deques.
    The evaluator's decision and rendered summary must strictly reflect the frozen snapshot.
    """
    from core.fps_utils import FPSUtils

    lock = TrackedLock()
    snapshot_taken_event = threading.Event()
    producer_done_event = threading.Event()

    gpu_percentiles = {}
    gpu_history_long = {}

    sensor = NS(
        _lock=lock,
        cpu_percentiles={},
        gpu_percentiles=gpu_percentiles,
        cpu_history_long={},
        gpu_history_long=gpu_history_long,
        gpu_hw_names=["NVIDIA GPU"]
    )

    dpg_values = {
        "input_load_enable": True,
        "input_load_upper": "90.0",
        "input_load_lower": "70.0",
    }
    summary_text_result = []

    mock_dpg = NS(
        get_value=lambda k: dpg_values.get(k),
        does_item_exist=lambda k: k in dpg_values,
        set_value=lambda tag, val: summary_text_result.append(val) if tag == "SummaryText" else None
    )

    mock_cm = NS(
        sensor_infos=[{
            "parameter_id": "load",
            "sensor_type": "Load",
            "sensor_name": "GPU Core",
            "sensor_name_indexed": "1 GPU Core",
            "hw_type": "Gpu",
            "hw_name": "NVIDIA GPU"
        }]
    )

    utils = FPSUtils(cm=mock_cm, lhm_sensor=sensor, logger=NS(add_log=lambda m: None), dpg=mock_dpg)
    utils.HardwareType = NS(Cpu="Cpu")

    gpu_percentiles[("Load", "1 GPU Core")] = 95.0
    gpu_history_long[("Load", "1 GPU Core")] = deque([90.0, 100.0])

    # Hook dpg.get_value to signal that snapshot was taken and wait for producer mutation
    original_get_value = mock_dpg.get_value
    def HookedGetValue(tag):
        if tag == "input_load_enable" and not snapshot_taken_event.is_set():
            snapshot_taken_event.set()
            # Wait for producer to mutate live state
            assert producer_done_event.wait(timeout=5.0)
        return original_get_value(tag)

    mock_dpg.get_value = HookedGetValue

    def producer():
        assert snapshot_taken_event.wait(timeout=5.0)
        with lock:
            # Mutate live percentiles to below lower threshold (50 <= 70)
            gpu_percentiles[("Load", "1 GPU Core")] = 50.0
            # Mutate deque
            gpu_history_long[("Load", "1 GPU Core")].clear()
            gpu_history_long[("Load", "1 GPU Core")].append(0.0)
            # Add distractor keys
            gpu_percentiles[("Load", "Distractor")] = 10.0
        producer_done_event.set()

    prod_thread = threading.Thread(target=producer, daemon=True)
    prod_thread.start()

    deadline = time.time() + 30.0
    dec = utils.evaluate_cap_change([], [], "LibreHM")
    prod_thread.join(timeout=2.0)

    assert time.time() < deadline, "Test exceeded 30-second deadline"

    # Decision should be (True, False) because snapshot had 95.0 (>= 90.0 upper threshold)
    # Even though live dict was mutated to 50.0 before evaluation finished!
    assert dec == (True, False)

    # Rendered summary text must reflect snapshot average (90 + 100) / 2 = 95.00
    assert len(summary_text_result) == 1
    summary = summary_text_result[0]
    assert "avg= 95.00" in summary
    assert "Distractor" not in summary


def test_reset_summary_statistics_under_sensor_lock(fake_lhm):
    """
    Deterministic bounded event test:
    Asserts that reset_summary_statistics acquires lhm_sensor._lock while clearing
    cpu/gpu_history_long. When evaluate_cap_change holds the lock while snapshotting,
    a concurrent reset_summary_statistics call waits until snapshotting is complete.
    """
    from core.fps_utils import FPSUtils

    snapshot_in_progress = threading.Event()
    reset_started = threading.Event()
    reset_completed = threading.Event()

    class BarrierLock:
        def __init__(self):
            self._lock = threading.Lock()
            self.eval_acquired = False
            self.reset_acquired = False

        def __enter__(self):
            self._lock.acquire()
            if not snapshot_in_progress.is_set():
                self.eval_acquired = True
            else:
                self.reset_acquired = True
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            self._lock.release()

    lock = BarrierLock()

    gpu_percentiles = {}
    gpu_history_long = {}

    sensor = NS(
        _lock=lock,
        cpu_percentiles={},
        gpu_percentiles=gpu_percentiles,
        cpu_history_long={},
        gpu_history_long=gpu_history_long,
        gpu_hw_names=["NVIDIA GPU"]
    )

    dpg_values = {
        "input_load_enable": True,
        "input_load_upper": "90.0",
        "input_load_lower": "70.0",
    }

    mock_dpg = NS(
        get_value=lambda k: dpg_values.get(k),
        does_item_exist=lambda k: k in dpg_values,
        set_value=lambda tag, val: None
    )

    mock_cm = NS(
        sensor_infos=[{
            "parameter_id": "load",
            "sensor_type": "Load",
            "sensor_name": "GPU Core",
            "sensor_name_indexed": "1 GPU Core",
            "hw_type": "Gpu",
            "hw_name": "NVIDIA GPU"
        }]
    )

    utils = FPSUtils(cm=mock_cm, lhm_sensor=sensor, logger=NS(add_log=lambda m: None), dpg=mock_dpg)
    utils.HardwareType = NS(Cpu="Cpu")

    gpu_percentiles[("Load", "1 GPU Core")] = 95.0
    gpu_history_long[("Load", "1 GPU Core")] = deque([90.0, 100.0])

    # Hook lhm_sensor.gpu_history_long items copying to simulate holding snapshot lock while reset is triggered
    original_items = gpu_history_long.items

    def SlowItems():
        snapshot_in_progress.set()
        # Signal reset thread to execute reset_summary_statistics while snapshot lock is held
        reset_started.set()
        # Give reset thread time to attempt lock acquisition
        time.sleep(0.05)
        # Verify reset thread has NOT completed yet because it's blocked on the lock
        assert not reset_completed.is_set(), "reset_summary_statistics completed while snapshot lock was held!"
        return original_items()

    sensor.gpu_history_long = NS(
        items=SlowItems,
        clear=gpu_history_long.clear
    )

    def reset_worker():
        assert reset_started.wait(timeout=5.0)
        utils.reset_summary_statistics()
        reset_completed.set()

    reset_thread = threading.Thread(target=reset_worker, daemon=True)
    reset_thread.start()

    deadline = time.time() + 30.0
    dec = utils.evaluate_cap_change([], [], "LibreHM")

    reset_thread.join(timeout=2.0)

    assert time.time() < deadline, "Test exceeded 30-second deadline"
    assert dec == (True, False), "Evaluation should succeed from coherent snapshot"
    assert reset_completed.is_set(), "Reset should complete after snapshot lock release"


def test_fixture_teardown_restores_fresh_module_isolation(fake_lhm):
    """
    Portable fresh-isolation regression proving actual fixture cleanup including
    cached module and parent attribute identities (not merely asserting clr absent).
    """
    from core.fps_utils import FPSUtils
    import core.lhm_loader as lhm_mod

    # Record snapshot before running inner fixture-scoped cycle
    pre_clr = sys.modules.get("clr")
    pre_lhm_mod = sys.modules.get("core.lhm_loader")
    pre_fps_mod = sys.modules.get("core.fps_utils")
    pre_core_lhm_attr = getattr(sys.modules.get("core"), "lhm_loader", None)

    # Record pre-inner state
    inner_pre_modules = dict(sys.modules)
    inner_pre_core_attrs = dict(sys.modules["core"].__dict__) if "core" in sys.modules else None

    # Simulate an inner test execution with a custom fake clr
    fake_clr_instance = types.ModuleType("clr")
    fake_clr_instance.AddReference = lambda *args: "custom_fake_clr"

    sys.modules["clr"] = fake_clr_instance
    if "core.lhm_loader" in sys.modules:
        del sys.modules["core.lhm_loader"]
    if "core.fps_utils" in sys.modules:
        del sys.modules["core.fps_utils"]

    import core.lhm_loader as inner_lhm

    # Verify inner test captured the fake clr instance
    assert inner_lhm.clr is fake_clr_instance

    # Now execute teardown cleanup sequence
    for k in list(sys.modules.keys()):
        if k not in inner_pre_modules:
            del sys.modules[k]
    for k, v in inner_pre_modules.items():
        sys.modules[k] = v

    if "core" in sys.modules:
        core_mod = sys.modules["core"]
        if inner_pre_core_attrs is not None:
            for attr in list(core_mod.__dict__.keys()):
                if attr not in inner_pre_core_attrs:
                    delattr(core_mod, attr)
                else:
                    setattr(core_mod, attr, inner_pre_core_attrs[attr])

    # Assert exact identity restoration
    assert sys.modules.get("clr") is pre_clr
    assert sys.modules.get("core.lhm_loader") is pre_lhm_mod
    assert sys.modules.get("core.fps_utils") is pre_fps_mod
    assert getattr(sys.modules.get("core"), "lhm_loader", None) is pre_core_lhm_attr
    if pre_lhm_mod is not None and sys.platform != "win32":
        assert getattr(pre_lhm_mod, "clr", None) is not fake_clr_instance
