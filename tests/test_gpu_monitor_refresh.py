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


class _NativeFunction:
    """Callable allowing future ctypes argtypes/restype assignments."""

    def __init__(self, implementation):
        self.implementation = implementation

    def __call__(self, *args):
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
        self.next_handle = 100
        for name in (
            "PdhEnumObjectItemsW", "PdhEnumObjectsW", "PdhOpenQueryW",
            "PdhCloseQuery", "PdhAddEnglishCounterW", "PdhCollectQueryData",
        ):
            setattr(self, name, _NativeFunction(getattr(self, name)))

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
        if self._value(refresh):
            self.cached_instances = list(self.live_instances)
        return self._multi_sz(["GPU Engine"], objects, size)

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


def test_reinitialize_discovers_new_gpu_engine_instances(monkeypatch, stub_logger):
    old_instance = "pid_4100_luid_0x00000000_0x00001234_phys_0_eng_0_engtype_3D"
    new_instances = [
        "pid_8200_luid_0x00000000_0x00005678_phys_0_eng_0_engtype_3D",
        "pid_8200_luid_0x00000000_0x00005678_phys_0_eng_1_engtype_3D",
        "pid_8200_luid_0x00000000_0x00005678_phys_0_eng_2_engtype_Compute",
    ]
    native = _CachedPDH([old_instance])
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
