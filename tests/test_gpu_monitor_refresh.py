"""Regression for newly created GPU engines hidden by PDH's item cache.

Microsoft documents that PdhEnumObjectItemsW reuses cached items until
PdhEnumObjects is called with bRefresh=TRUE:
https://learn.microsoft.com/en-us/windows/win32/api/pdh/nf-pdh-pdhenumobjectitemsw

Only native calls and sleep are faked; monitor initialization, enumeration,
counter setup, query closure and reinitialization execute their real code.
"""

import ctypes
import threading
from types import SimpleNamespace

import pytest


OLD_INSTANCE = "pid_4100_luid_0x00000000_0x00001234_phys_0_eng_0_engtype_3D"


class _NativeFunction:
    """Callable allowing future ctypes argtypes/restype assignments."""

    def __init__(self, implementation, events):
        self.implementation = implementation
        self.events = events

    def __call__(self, *args):
        self.events.append(self.implementation.__name__)
        return self.implementation(*args)


class _CachedPDH:
    MORE_DATA = 0x800007D2

    def __init__(self, instances):
        self.live_instances = list(instances)
        self.cached_instances = None
        self.queries = {}
        self.closed_queries = []
        self.adds = []
        self.collects = []
        self.events = []
        self.refresh_status = self.MORE_DATA
        self.refresh_calls = []
        self.next_handle = 100
        for name in (
            "PdhEnumObjectItemsW", "PdhEnumObjectsW", "PdhOpenQueryW",
            "PdhCloseQuery", "PdhAddEnglishCounterW", "PdhCollectQueryData",
        ):
            setattr(self, name, _NativeFunction(getattr(self, name), self.events))

    @staticmethod
    def _value(value):
        return value.value if hasattr(value, "value") else value

    def _new_handle(self, output):
        self.next_handle += 1
        output._obj.value = self.next_handle
        return self.next_handle

    def _multi_sz(self, names, buffer, size):
        text = "\0".join(names) + "\0\0"
        capacity = size._obj.value
        size._obj.value = len(text)
        if buffer is None or capacity < len(text):
            return self.MORE_DATA
        for index, char in enumerate(text):
            buffer[index] = char
        return 0

    def PdhEnumObjectItemsW(self, source, machine, object_name, counters,
                           counter_size, instances, instance_size, detail, flags):
        assert self._value(object_name) == "GPU Engine"
        # The first listing snapshots live names; even a new query cannot
        # change that snapshot. Only a native object refresh updates it.
        if self.cached_instances is None:
            self.cached_instances = list(self.live_instances)
        counter_status = self._multi_sz(
            ["Utilization Percentage"], counters, counter_size
        )
        instance_status = self._multi_sz(
            self.cached_instances, instances, instance_size
        )
        return counter_status or instance_status

    def PdhEnumObjectsW(self, source, machine, objects, size, detail, refresh):
        self.refresh_calls.append((
            source, machine, objects, size._obj.value,
            self._value(detail), self._value(refresh),
        ))
        if (self.refresh_status & 0xFFFFFFFF) not in (0, self.MORE_DATA):
            return self.refresh_status
        if self._value(refresh):
            self.cached_instances = list(self.live_instances)
        self._multi_sz(["GPU Engine"], objects, size)
        return self.refresh_status

    def PdhOpenQueryW(self, source, user_data, output):
        query = self._new_handle(output)
        self.queries[query] = {}
        return 0

    def PdhCloseQuery(self, query):
        query = self._value(query)
        # Removing the query also invalidates all its native counter handles.
        del self.queries[query]
        self.closed_queries.append(query)
        return 0

    def PdhAddEnglishCounterW(self, query, path, user_data, output):
        query, path = self._value(query), self._value(path)
        counter = self._new_handle(output)
        self.queries[query][counter] = path
        self.adds.append((query, path))
        return 0

    def PdhCollectQueryData(self, query):
        query = self._value(query)
        assert query in self.queries, "collect used a closed query"
        self.collects.append(query)
        return 0


@pytest.fixture
def native_monitor(monkeypatch, stub_logger):
    native = _CachedPDH([OLD_INSTANCE])
    # Install before import, including on Windows, so the dedicated Linux
    # command needs no collection-time windll stub from another test module.
    monkeypatch.setattr(ctypes, "windll", SimpleNamespace(pdh=native), raising=False)
    from core import gpu_monitor

    monkeypatch.setattr(gpu_monitor, "pdh", native)
    monkeypatch.setattr(gpu_monitor.time, "sleep", lambda _: None)
    monitor = gpu_monitor.GPUUsageMonitor.__new__(gpu_monitor.GPUUsageMonitor)
    monitor.logger = stub_logger
    monitor.query_handle = None
    monitor.counter_handles = {}
    monitor.instances = []
    monitor._pdh_lock = threading.RLock()
    return monitor, native


@pytest.mark.parametrize("status", [0, 0x800007D2, -2147481646],
                         ids=["success", "unsigned-more-data", "signed-more-data"])
def test_first_enumeration_refreshes_before_items(native_monitor, status):
    monitor, native = native_monitor
    native.refresh_status = status
    # Start with an already populated, stale PDH cache even on first initialize.
    native.cached_instances = [OLD_INSTANCE.replace("pid_4100", "pid_1000")]

    monitor.initialize()

    assert native.events == [
        "PdhOpenQueryW", "PdhEnumObjectsW", "PdhEnumObjectItemsW",
        "PdhEnumObjectItemsW", "PdhAddEnglishCounterW",
    ]
    assert native.refresh_calls == [(None, None, None, 0, 400, 1)]
    assert monitor.instances == [OLD_INSTANCE]
    assert len(native.adds) == 1
    assert native.collects == []
    # Check the declared boundary contract; the fake cannot prove marshalling.
    refresh = native.PdhEnumObjectsW
    assert refresh.argtypes == [
        ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_wchar),
        ctypes.POINTER(ctypes.c_uint32), ctypes.c_uint32, ctypes.c_int32,
    ]
    assert refresh.restype is ctypes.c_int32
    assert ctypes.sizeof(refresh.restype) == 4
    assert ctypes.sizeof(refresh.argtypes[3]._type_) == 4
    assert ctypes.sizeof(refresh.argtypes[4]) == 4
    assert ctypes.sizeof(refresh.argtypes[5]) == 4


def test_reinitialize_discovers_new_gpu_engine_instances(native_monitor):
    monitor, native = native_monitor
    old_instance = OLD_INSTANCE
    new_instances = [
        "pid_8200_luid_0x00000000_0x00005678_phys_0_eng_0_engtype_3D",
        "pid_8200_luid_0x00000000_0x00005678_phys_0_eng_1_engtype_3D",
        "pid_8200_luid_0x00000000_0x00005678_phys_0_eng_2_engtype_Compute",
    ]

    monitor.initialize()
    old_query = monitor.query_handle.value
    old_path = f"\\GPU Engine({old_instance})\\Utilization Percentage"
    old_counters = set(native.queries[old_query])
    assert monitor.instances == [old_instance]
    assert native.adds == [(old_query, old_path)]
    assert set(monitor.counter_handles) == {"0x00001234"}

    native.live_instances = list(new_instances)
    # Changing the live population alone must not silently update the cache.
    assert native.cached_instances == [old_instance]
    monitor.reinitialize()
    new_query = monitor.query_handle.value

    assert new_query != old_query
    assert native.closed_queries == [old_query]
    assert set(native.queries) == {new_query}
    assert native.collects == [new_query, new_query]
    assert monitor.instances == new_instances, "reinitialize reused cached GPU instances"

    new_paths = [
        f"\\GPU Engine({instance})\\Utilization Percentage"
        for instance in new_instances[:2]
    ]
    assert list(native.queries[new_query].values()) == new_paths
    # Exact history detects repeated counter adds, including to retired queries.
    assert native.adds == [(old_query, old_path)] + [
        (new_query, path) for path in new_paths
    ]
    assert set(monitor.counter_handles) == {"0x00005678"}
    new_counters = {handle.value for handle in monitor.counter_handles["0x00005678"]}
    assert new_counters == set(native.queries[new_query])
    assert old_counters.isdisjoint(new_counters)
    assert len(native.refresh_calls) == 2


@pytest.mark.parametrize("initialized", [False, True], ids=["first-init", "reinit"])
def test_refresh_error_closes_query_without_using_stale_items(native_monitor, initialized):
    monitor, native = native_monitor
    if initialized:
        monitor.initialize()
    previous_queries = list(native.queries)
    previous_adds = list(native.adds)
    native.events.clear()
    native.refresh_status = ctypes.c_int32(0xC0000BBD).value  # PDH_INVALID_ARGUMENT
    native.live_instances = [OLD_INSTANCE.replace("pid_4100", "pid_8200")]

    with pytest.raises(RuntimeError, match="Failed to refresh PDH object cache"):
        monitor.reinitialize() if initialized else monitor.initialize()

    assert native.events == (["PdhCloseQuery"] if initialized else []) + [
        "PdhOpenQueryW", "PdhEnumObjectsW", "PdhCloseQuery",
    ]
    assert native.closed_queries == previous_queries + [native.next_handle]
    assert native.queries == {}
    assert monitor.query_handle is None
    assert monitor.counter_handles == {}
    assert monitor.instances == []
    assert monitor.engine_type is None
    assert native.adds == previous_adds
    assert native.collects == []


def test_refresh_is_reentrant_and_serializes_native_work(native_monitor):
    monitor, native = native_monitor
    # Exercise the real path while its caller already owns the PDH lock.
    with monitor._pdh_lock:
        monitor.reinitialize()

    refresh_entered = threading.Event()
    release_refresh = threading.Event()
    contender_waiting = threading.Event()
    real_refresh = native.PdhEnumObjectsW.implementation
    real_lock = monitor._pdh_lock

    class ObservedLock:
        def __enter__(self):
            if threading.current_thread().name == "contender":
                contender_waiting.set()
            real_lock.acquire()
            return self

        def __exit__(self, *exc):
            real_lock.release()

    def gated_refresh(*args):
        refresh_entered.set()
        assert release_refresh.wait(5), "refresh gate timed out"
        return real_refresh(*args)

    monitor._pdh_lock = ObservedLock()
    native.PdhEnumObjectsW.implementation = gated_refresh
    errors = []

    def worker():
        try:
            monitor.initialize()
        except Exception as exc:
            errors.append(exc)

    refresher = threading.Thread(target=worker, name="refresher", daemon=True)
    contender = threading.Thread(target=worker, name="contender", daemon=True)
    native.events.clear()
    native.collects.clear()
    refresher.start()
    try:
        assert refresh_entered.wait(5), "refresh never reached native boundary"
        before_contender = list(native.events)
        contender.start()
        assert contender_waiting.wait(5), "contender never attempted PDH lock"
        assert native.events == before_contender, "native work overlapped refresh"
        assert native.collects == []
    finally:
        release_refresh.set()
        refresher.join(5)
        if contender.ident is not None:
            contender.join(5)

    assert not refresher.is_alive() and not contender.is_alive()
    assert errors == []
    assert len(native.refresh_calls) == 3
    assert len(native.queries) == 1
    assert native.collects == []
