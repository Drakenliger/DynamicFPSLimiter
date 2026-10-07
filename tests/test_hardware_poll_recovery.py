"""Finite production poll-loop tests; only native boundaries and clocks are fake."""
import ast
import threading
from collections import defaultdict, deque
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from test_librehm_sensor_identity import (
    SRC_DIR, _load_lhm_ast, _load_fps_evaluator, MockSensor, MockHardware, MockComputer,
)


@pytest.mark.parametrize('enabled', ['cpu', 'gpu'])
def test_lhm_failed_partial_pass_is_missing_then_recovers(caplog, enabled):
    scope = _load_lhm_ast()
    cls = scope['LHMSensor']
    m = cls.__new__(cls)
    m.HardwareType = SimpleNamespace(Cpu='cpu', GpuNvidia='gpu', GpuAmd='amd')
    cpu = MockSensor('Core', 'Load', 10, '/cpu')
    gpu = MockSensor('Core', 'Load', 20, '/gpu')
    ch = MockHardware('CPU', 'cpu', [cpu])
    gh = MockHardware('GPU', 'gpu', [gpu])
    m.computer = MockComputer([ch, gh])
    m.CPU_SENSORS = m.GPU_SENSORS = {'Load': None}
    for name in ('cpu_history', 'gpu_history', 'cpu_history_long', 'gpu_history_long'):
        setattr(m, name, defaultdict(lambda: deque(maxlen=20)))
    m._lock = threading.Lock()
    class LockedPercentiles(defaultdict):
        def __setitem__(self, key, value):
            assert m._lock.locked()
            super().__setitem__(key, value)
        def clear(self):
            assert m._lock.locked()
            super().clear()
    m.cpu_percentiles = LockedPercentiles(float)
    m.gpu_percentiles = LockedPercentiles(float)
    m._should_stop = threading.Event()
    m._running = lambda: True
    m.interval = .1
    m.percentile = 70
    m.logger = MagicMock()
    m.dpg = MagicMock()
    m.gui_queue = None
    tick = 0
    def update():
        assert m._lock.locked()
        if tick == 1:
            raise RuntimeError('driver reset')
    gh.Update = update
    evaluate = _load_fps_evaluator()
    dpg = MagicMock()
    dpg.does_item_exist.return_value = True
    dpg.get_value.side_effect = lambda tag: {'input_s_enable': True,
        'input_s_upper': 90, 'input_s_lower': 70}.get(tag)
    utils = SimpleNamespace(lhm_sensor=m, HardwareType=m.HardwareType,
        cm=SimpleNamespace(sensor_infos=[dict(parameter_id='s', identifier='/' + enabled,
            hw_type=enabled, sensor_type='Load', sensor_name='Core')]),
        dpg=dpg, logger=MagicMock())
    def sleep(interval):
        nonlocal tick
        assert interval == .1
        if tick == 0:
            assert m.cpu_percentiles['/cpu'] == 10
            cpu.Value = 99  # CPU is partially updated before GPU throws.
        elif tick == 1:
            assert all(v is None for v in m.cpu_percentiles.values())
            assert all(v is None for v in m.gpu_percentiles.values())
            assert not m.cpu_history and not m.gpu_history_long
            assert evaluate(utils, [], [], 'LibreHM') == (False, False)
            cpu.Value, gpu.Value = 30, 40
        else:
            assert m.cpu_percentiles['/cpu'] == 30
            assert m.gpu_percentiles['/gpu'] == 40
            assert list(m.cpu_history['/cpu']) == [30]
            assert list(m.gpu_history_long['/gpu']) == [40]
            m._should_stop.set()
        tick += 1
    scope['time'] = SimpleNamespace(sleep=sleep)
    m._poll_loop()
    assert tick == 3
    assert not m.cpu_percentiles and not m.gpu_percentiles
    assert any(r.name == 'root' and r.exc_info and 'driver reset' in r.exc_text
               for r in caplog.records)


def load_gpu():
    tree = ast.parse((SRC_DIR / 'gpu_monitor.py').read_text())
    # Remove only Windows DLL binding; no imported module cache alterations.
    tree.body = [n for n in tree.body if not (isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == 'pdh' for t in n.targets))]
    scope = {}
    exec(compile(tree, '<gpu_monitor>', 'exec'), scope)
    return scope


@pytest.mark.parametrize('failure', ['map', 'handles', 'status', 'cstatus', 'collect', 'setup'])
@pytest.mark.parametrize('reinit_raises', [False, True])
def test_pdh_one_retry_skips_old_handles_and_recovers(failure, reinit_raises, caplog):
    scope = load_gpu()
    cls = scope['GPUUsageMonitor']
    m = cls.__new__(cls)
    m._lock = threading.Lock()
    m._pdh_lock = threading.RLock()
    m.looping = True
    m._running = lambda: True
    m.interval = .1
    m.max_samples = 20
    m.percentile = 70
    m.luid = 'chosen'
    m.query_handle = 1
    m.instances = []
    class LockedSamples(list):
        def clear(self):
            assert m._lock.locked()
            super().clear()
        def append(self, value):
            assert m._lock.locked()
            super().append(value)
    m.samples = LockedSamples([5])
    m.gpu_percentile = 5
    m.logger = MagicMock()
    old = {'chosen': [0, 1, 2, 3], 'other': [4]}
    if failure == 'map': old = {}
    if failure == 'handles': old = {'chosen': []}
    m.counter_handles = old
    def setup(*args):
        if failure == 'setup': raise RuntimeError('setup failed')
        return 1, old
    m._setup_gpu_query_from_instances = setup
    reads, retries, observed, reinitializations = [], [], [], []
    actual_reinitialize = m.reinitialize
    def counted_reinitialize(engine_type):
        reinitializations.append(tick)
        assert m.gpu_percentile is None and m.samples == []
        return actual_reinitialize(engine_type)
    m.reinitialize = counted_reinitialize
    tick = 0
    def collect(q):
        assert m._pdh_lock._is_owned()
        return 7 if failure == 'collect' and tick <= (2 if reinit_raises else 1) else 0
    def read(h, fmt, unused, ptr):
        assert m._pdh_lock._is_owned()
        reads.append(h)
        val = ptr._obj
        val.doubleValue = {10: 30, 11: 40, 12: 99}.get(h, 12)
        if h == 1 and failure in ('status', 'cstatus'):
            val.CStatus = 8 if failure == 'cstatus' else 0
            return 9 if failure == 'status' else 0
        return 0
    # Exercise actual reinitialize/initialize bodies with fake native setup edges.
    m._init_gpu_state = lambda: 2
    m._setup_gpu_instances = lambda: ['new']
    def recovery_setup(*args):
        retries.append(tick)
        if reinit_raises and len(retries) == 1:
            raise RuntimeError('reset not ready')
        return 2, {'chosen': [10, 11], 'other': [12]}
    def sleep(interval):
        nonlocal tick
        if interval == .1 and m._pdh_lock._is_owned():
            return  # actual reinitialize warm-up collect delay
        observed.append((m.gpu_percentile, list(m.samples)))
        tick += 1
        if tick == 1:
            m._setup_gpu_query_from_instances = recovery_setup
        if tick == (4 if reinit_raises else 3): m.looping = False
    scope['pdh'] = SimpleNamespace(PdhCollectQueryData=collect,
        PdhGetFormattedCounterValue=read, PdhCloseQuery=lambda q: 0)
    scope['time'] = SimpleNamespace(sleep=sleep)
    m.gpu_run()
    assert observed[1] == (None, [])
    assert observed[-1] == (70, [70])
    assert 2 not in reads and 3 not in reads and 4 not in reads
    assert 12 not in reads  # selected LUID retained
    # initialize + reinitialize setup once per successful attempt, first failure once.
    assert len(reinitializations) == (2 if reinit_raises else 1)
    assert len(set(reinitializations)) == len(reinitializations)
    assert len(retries) == (2 if reinit_raises else 1)
    assert m.gpu_percentile is None and m.samples == []
    assert any(r.exc_info and r.name == 'root' for r in caplog.records)


@pytest.mark.parametrize('target,expected', [('chosen', [40, 50]), ('All', [90, 100])])
def test_pdh_healthy_aggregation_and_percentile(target, expected):
    scope = load_gpu()
    m = scope['GPUUsageMonitor'].__new__(scope['GPUUsageMonitor'])
    m._lock, m._pdh_lock = threading.Lock(), threading.RLock()
    m.samples, m.gpu_percentile = [], None
    m.max_samples, m.percentile, m.interval = 20, 70, .1
    m.luid, m.looping = target, True
    m._running = lambda: True
    m.query_handle, m.instances = 1, []
    m._setup_gpu_query_from_instances = lambda *a: (1, {'chosen': [1, 2], 'other': [3]})
    m.reinitialize = MagicMock(side_effect=AssertionError('healthy tick must not reset'))
    tick = 0
    def read(h, fmt, unused, ptr):
        assert m._pdh_lock._is_owned()
        ptr._obj.doubleValue = {1: 10, 2: 20 + tick * 10, 3: 80 + tick * 10}[h]
        return 0
    def sleep(interval):
        nonlocal tick
        if tick == 2:
            assert m.samples == expected
            assert m.gpu_percentile == round(expected[0] * .3 + expected[1] * .7)
            m.looping = False
        tick += 1
    scope['time'] = SimpleNamespace(sleep=sleep)
    scope['pdh'] = SimpleNamespace(PdhCollectQueryData=lambda q: 0,
                                   PdhGetFormattedCounterValue=read)
    m.gpu_run()
    m.reinitialize.assert_not_called()
    assert m.samples == [] and m.gpu_percentile is None
