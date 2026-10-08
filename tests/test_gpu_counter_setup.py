"""Regression tests for GPU PDH counter setup and ownership lifecycle.

Ensures that GPUUsageMonitor creates exactly one owned counter set per query on start,
does not add duplicate counters on worker startup or overwrite existing counter handles,
properly handles reinitialization and alternative engine types, and maintains cleanup/recovery.
"""

import ctypes
import sys
import threading
import time
import types
from unittest.mock import MagicMock

if not hasattr(ctypes, "windll"):
    ctypes.windll = types.SimpleNamespace(pdh=None)

import pytest

from core import gpu_monitor
from core.gpu_monitor import GPUUsageMonitor


class MockPDH:
    def __init__(self, instances=None):
        self.instances = instances or [
            "phys_0_eng_0_luid_0x00000000_0x00001234_engtype_3D",
            "phys_0_eng_1_luid_0x00000000_0x00001234_engtype_Compute",
            "phys_0_eng_2_luid_0x00000000_0x00005678_engtype_3D",
        ]
        self.next_query_id = 100
        self.next_counter_id = 1000
        self.queries = {}  # qh_val -> dict of {ch_val: counter_path}
        self.closed_queries = set()
        self.add_counter_calls = []  # [(qh_val, counter_path, ch_val)]
        self.close_query_calls = []  # [qh_val]
        self.collect_calls = []  # [qh_val]

    def _set_ref_val(self, ref, val):
        # ref can be a ctypes.byref (cparam) or a ctypes pointer/structure
        if hasattr(ref, "_obj"):
            ref._obj.value = val
        elif hasattr(ref, "contents"):
            ref.contents.value = val
        else:
            ref.value = val

    def PdhOpenQueryW(self, szDataSource, dwUserData, phQuery):
        qh = self.next_query_id
        self.next_query_id += 1
        self._set_ref_val(phQuery, qh)
        self.queries[qh] = {}
        return 0

    def PdhCloseQuery(self, hQuery):
        qh = hQuery.value if hasattr(hQuery, "value") else hQuery
        if qh in self.queries:
            self.closed_queries.add(qh)
            del self.queries[qh]
            self.close_query_calls.append(qh)
        return 0

    def PdhEnumObjectItemsW(
        self,
        szDataSource,
        szMachineName,
        szObjectName,
        mszCounterList,
        pcchCounterListLength,
        mszInstanceList,
        pcchInstanceListLength,
        dwDetailLevel,
        dwFlags,
    ):
        inst_str = "\x00".join(self.instances) + "\x00\x00"
        if mszInstanceList is None or not hasattr(mszInstanceList, "_type_"):
            if pcchCounterListLength:
                self._set_ref_val(pcchCounterListLength, 100)
            if pcchInstanceListLength:
                self._set_ref_val(pcchInstanceListLength, len(inst_str) + 10)
            return 0
        else:
            for i, char in enumerate(inst_str):
                mszInstanceList[i] = char
            return 0

    def PdhAddEnglishCounterW(self, hQuery, szFullCounterPath, dwUserData, phCounter):
        qh = hQuery.value if hasattr(hQuery, "value") else hQuery
        if qh not in self.queries:
            return 0x800007D0
        ch = self.next_counter_id
        self.next_counter_id += 1
        self._set_ref_val(phCounter, ch)
        self.queries[qh][ch] = szFullCounterPath
        self.add_counter_calls.append((qh, szFullCounterPath, ch))
        return 0

    def PdhCollectQueryData(self, hQuery):
        qh = hQuery.value if hasattr(hQuery, "value") else hQuery
        if qh not in self.queries:
            return 1
        self.collect_calls.append(qh)
        return 0

    def PdhGetFormattedCounterValue(self, hCounter, dwFormat, pValue, pValueOut):
        ch = hCounter.value if hasattr(hCounter, "value") else hCounter
        found = any(ch in counters for counters in self.queries.values())
        if not found:
            return 1
        val = pValueOut.contents
        val.CStatus = 0
        val.doubleValue = 25.0
        return 0


def _make_monitor(mock_pdh, stub_logger):
    m = GPUUsageMonitor.__new__(GPUUsageMonitor)
    m.interval = 0.01
    m.max_samples = 20
    m.samples = []
    m.gpu_percentile = 0
    m.percentile = 70
    m.logger = stub_logger
    m.dpg = None
    m.themes_manager = None
    m.gui_queue = None
    m.query_handle = None
    m.counter_handles = {}
    m.instances = []
    m.luid_selected = False
    m.luid = "All"
    m.looping = False
    m._lock = threading.Lock()
    m._pdh_lock = threading.RLock()
    m._detecting = False
    m._thread = None
    return m


def test_monitor_start_adds_counters_exactly_once(monkeypatch, stub_logger):
    """Verify initialize() followed by worker startup (gpu_run initial block)
    adds counters exactly once per matching instance and does not duplicate handles."""
    mock_pdh = MockPDH()
    monkeypatch.setattr(gpu_monitor, "pdh", mock_pdh)
    monkeypatch.setattr(gpu_monitor.time, "sleep", lambda *a, **k: None)

    m = _make_monitor(mock_pdh, stub_logger)
    m.initialize()

    qh = m.query_handle.value
    assert qh in mock_pdh.queries
    assert len(mock_pdh.add_counter_calls) == 2  # 2 engtype_3D instances
    assert len(mock_pdh.queries[qh]) == 2

    ticks = 0
    def fake_sleep(interval):
        nonlocal ticks
        ticks += 1
        m.looping = False

    monkeypatch.setattr(gpu_monitor.time, "sleep", fake_sleep)

    # Simulate worker run loop initial iteration
    m.looping = True
    m._running = lambda: False  # Exit loop after initial setup pass

    m.gpu_run(engine_type="engtype_3D")

    # Assert exactly 2 counters total were registered on the query handle
    assert len(mock_pdh.add_counter_calls) == 2
    assert len(mock_pdh.queries[qh]) == 2

    # Check that all registered counter handles in Python map match active native query handles
    registered_handles = set()
    for luid, h_list in m.counter_handles.items():
        for h in h_list:
            registered_handles.add(h.value)

    assert registered_handles == set(mock_pdh.queries[qh].keys())


def test_reinitialize_creates_fresh_query_and_closes_old(monkeypatch, stub_logger):
    """Verify reinitialize creates a fresh query and closes old handles/queries."""
    mock_pdh = MockPDH()
    monkeypatch.setattr(gpu_monitor, "pdh", mock_pdh)
    monkeypatch.setattr(gpu_monitor.time, "sleep", lambda *a, **k: None)

    m = _make_monitor(mock_pdh, stub_logger)
    m.initialize()

    old_qh = m.query_handle.value
    assert old_qh in mock_pdh.queries
    old_counter_handles = {h.value for h_list in m.counter_handles.values() for h in h_list}

    m.reinitialize(engine_type="engtype_3D")

    new_qh = m.query_handle.value
    assert new_qh != old_qh
    assert old_qh in mock_pdh.closed_queries
    assert old_qh not in mock_pdh.queries
    assert new_qh in mock_pdh.queries

    new_counter_handles = {h.value for h_list in m.counter_handles.values() for h in h_list}
    assert old_counter_handles.isdisjoint(new_counter_handles)
    assert len(mock_pdh.queries[new_qh]) == 2


def test_alternative_engine_type_reconfigures_counters(monkeypatch, stub_logger):
    """Verify passing a non-3D engine_type (e.g. engtype_Compute) configures counters for that engine type."""
    mock_pdh = MockPDH()
    monkeypatch.setattr(gpu_monitor, "pdh", mock_pdh)
    monkeypatch.setattr(gpu_monitor.time, "sleep", lambda *a, **k: None)

    m = _make_monitor(mock_pdh, stub_logger)
    m.initialize()  # Default engtype_3D: 2 instances

    ticks = 0
    def fake_sleep(interval):
        nonlocal ticks
        ticks += 1
        m.looping = False

    monkeypatch.setattr(gpu_monitor.time, "sleep", fake_sleep)

    m.looping = True
    m._running = lambda: False

    m.gpu_run(engine_type="engtype_Compute")

    # engtype_Compute has only 1 instance in MockPDH
    qh = m.query_handle.value
    compute_counter_paths = [path for _, path, _ in mock_pdh.add_counter_calls if "engtype_Compute" in path]
    assert len(compute_counter_paths) == 1
    assert len(mock_pdh.queries[qh]) == 1


def test_setup_failure_preserves_recovery_and_cleanup(monkeypatch, stub_logger):
    """Verify that setup failure invalidates readings and handles, allowing recovery."""
    mock_pdh = MockPDH()
    monkeypatch.setattr(gpu_monitor, "pdh", mock_pdh)

    ticks = 0
    def fake_sleep(interval):
        nonlocal ticks
        ticks += 1
        m.looping = False

    monkeypatch.setattr(gpu_monitor.time, "sleep", fake_sleep)

    m = _make_monitor(mock_pdh, stub_logger)
    m.initialize()

    # Force failure on PdhCollectQueryData
    mock_pdh.PdhCollectQueryData = lambda qh: 0x800007D0

    m.looping = True
    m._running = lambda: False

    m.gpu_run(engine_type="engtype_3D")

    assert m.counter_handles == {}
    assert m.samples == []
    assert m.gpu_percentile is None
