"""Regression tests: GPU counter setup and single-ownership lifecycle.

Ensures GPUUsageMonitor creates exactly one owned set of PDH counters per query on startup,
avoiding duplicate PdhAddEnglishCounterW calls and orphaned counter handles. Tests
alternative engine types, close/restart lifecycle, error cleanup, and PDH lock serialization.
"""
import ctypes
import threading
import time
import types

from conftest import StubLogger
from core import gpu_monitor
from core.gpu_monitor import GPUUsageMonitor


def _fake_pdh(added_counters=None, closed_queries=None, collects=None):
    if added_counters is None:
        added_counters = []
    if closed_queries is None:
        closed_queries = []
    if collects is None:
        collects = []

    counter_handle_counter = [0x1000]

    def enum_object_items(p1, p2, obj, counter_buf, counter_size, inst_buf, inst_size, d1, d2):
        instances = "luid_0x00000000_0x00010000_phys_0_eng_0_engtype_3D\x00luid_0x00000000_0x00010000_phys_0_eng_1_engtype_Copy\x00\x00"
        ptr_inst = ctypes.cast(inst_size, ctypes.POINTER(ctypes.c_ulong))
        ptr_counter = ctypes.cast(counter_size, ctypes.POINTER(ctypes.c_ulong))
        if inst_buf is None:
            ptr_inst.contents.value = len(instances)
            ptr_counter.contents.value = 10
            return 0
        inst_buf[:len(instances)] = instances
        return 0

    def open_query(src, flags, handle_ref):
        ptr = ctypes.cast(handle_ref, ctypes.POINTER(ctypes.c_void_p))
        ptr.contents.value = 0x9999
        return 0

    def close_query(handle):
        closed_queries.append(handle)
        return 0

    def add_counter(query_handle, path, user_data, counter_ref):
        counter_handle_counter[0] += 1
        h = ctypes.c_void_p(counter_handle_counter[0])
        ptr = ctypes.cast(counter_ref, ctypes.POINTER(ctypes.c_void_p))
        ptr.contents.value = counter_handle_counter[0]
        added_counters.append((query_handle, path, h))
        return 0

    def collect_query_data(query_handle):
        collects.append(query_handle)
        return 0

    def get_formatted_value(handle, fmt, scale, val_ref):
        ptr = ctypes.cast(val_ref, ctypes.POINTER(gpu_monitor.PDH_FMT_COUNTERVALUE))
        ptr.contents.CStatus = 0
        ptr.contents.doubleValue = 25.0
        return 0

    return types.SimpleNamespace(
        PdhEnumObjectItemsW=enum_object_items,
        PdhOpenQueryW=open_query,
        PdhCloseQuery=close_query,
        PdhAddEnglishCounterW=add_counter,
        PdhCollectQueryData=collect_query_data,
        PdhGetFormattedCounterValue=get_formatted_value,
    )


def test_no_duplicate_counters_on_start(monkeypatch, stub_logger):
    added_counters = []
    fake_pdh_inst = _fake_pdh(added_counters=added_counters)
    monkeypatch.setattr(gpu_monitor, "pdh", fake_pdh_inst)

    running = True
    mon = GPUUsageMonitor(
        get_running=lambda: running,
        logger_instance=stub_logger,
        dpg_instance=None,
        themes_instance=None,
        interval=0.01,
    )

    try:
        # Give worker thread time to run gpu_run initial setup
        time.sleep(0.05)
        # Verify PdhAddEnglishCounterW was called exactly ONCE for engtype_3D instance during initialize,
        # and NOT called again when gpu_run started.
        paths = [path for _, path, _ in added_counters]
        assert len(paths) == 1
        assert "engtype_3D" in paths[0]
        assert "engtype_Copy" not in paths[0]

        # Verify active handles in mon.counter_handles match the single added handle
        all_handles = [h for handles in mon.counter_handles.values() for h in handles]
        assert len(all_handles) == 1
        assert all_handles[0].value == added_counters[0][2].value
    finally:
        mon.cleanup()


def test_alternative_engine_type(monkeypatch, stub_logger):
    added_counters = []
    fake_pdh_inst = _fake_pdh(added_counters=added_counters)
    monkeypatch.setattr(gpu_monitor, "pdh", fake_pdh_inst)

    mon = GPUUsageMonitor.__new__(GPUUsageMonitor)
    mon.interval = 0.01
    mon.max_samples = 20
    mon.samples = []
    mon.gpu_percentile = 0
    mon.percentile = 70
    mon.logger = stub_logger
    mon.dpg = None
    mon.themes_manager = None
    mon.query_handle = None
    mon.counter_handles = {}
    mon.instances = []
    mon._engine_type = None
    mon._pdh_lock = threading.RLock()

    # Initialize explicitly with engtype_Copy
    mon.initialize(engine_type="engtype_Copy")

    paths = [path for _, path, _ in added_counters]
    assert len(paths) == 1
    assert "engtype_Copy" in paths[0]
    assert mon._engine_type == "engtype_Copy"

    mon._close_query()
    assert mon.query_handle is None
    assert mon.counter_handles == {}
    assert mon._engine_type is None


def test_close_restart_lifecycle(monkeypatch, stub_logger):
    added_counters = []
    closed_queries = []
    fake_pdh_inst = _fake_pdh(added_counters=added_counters, closed_queries=closed_queries)
    monkeypatch.setattr(gpu_monitor, "pdh", fake_pdh_inst)

    mon = GPUUsageMonitor.__new__(GPUUsageMonitor)
    mon.interval = 0.01
    mon.max_samples = 20
    mon.samples = []
    mon.gpu_percentile = 0
    mon.percentile = 70
    mon.logger = stub_logger
    mon.dpg = None
    mon.themes_manager = None
    mon.query_handle = None
    mon.counter_handles = {}
    mon.instances = []
    mon._engine_type = None
    mon._pdh_lock = threading.RLock()

    mon.initialize()
    q1 = mon.query_handle
    assert len(added_counters) == 1
    assert closed_queries == []

    # Close query
    mon._close_query()
    assert closed_queries == [q1]
    assert mon.query_handle is None
    assert mon.counter_handles == {}
    assert mon._engine_type is None

    # Restart query
    mon.initialize()
    q2 = mon.query_handle
    assert len(added_counters) == 2
    assert mon.query_handle is not None
    assert len(mon.counter_handles) == 1


def test_error_cleanup_on_failed_collect(monkeypatch, stub_logger):
    added_counters = []
    closed_queries = []

    def failing_collect(handle):
        return 0x80000001  # PDH error

    fake_pdh_inst = _fake_pdh(added_counters=added_counters, closed_queries=closed_queries)
    fake_pdh_inst.PdhCollectQueryData = failing_collect
    monkeypatch.setattr(gpu_monitor, "pdh", fake_pdh_inst)

    mon = GPUUsageMonitor.__new__(GPUUsageMonitor)
    mon.interval = 0.01
    mon.max_samples = 20
    mon.samples = [10]
    mon.gpu_percentile = 10
    mon.percentile = 70
    mon.logger = stub_logger
    mon.dpg = None
    mon.themes_manager = None
    mon.query_handle = None
    mon.counter_handles = {}
    mon.instances = []
    mon._engine_type = None
    mon.looping = False
    mon._lock = threading.Lock()
    mon._pdh_lock = threading.RLock()

    # Pre-initialize query
    mon.initialize()
    q1 = mon.query_handle

    # Running gpu_run should catch failing initial collect and clean up query/handles
    mon.gpu_run()

    assert closed_queries == [q1]
    assert mon.query_handle is None
    assert mon.counter_handles == {}
    assert mon._engine_type is None
    assert mon.samples == []
    assert mon.gpu_percentile is None
