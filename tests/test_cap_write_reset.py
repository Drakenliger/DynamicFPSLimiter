"""Post-write evidence regressions executing the actual app function ASTs."""
from decimal import Decimal

import pytest

from core.cap_policy import fresh_cap_evidence
from test_app_session import load_app
from test_librehm_policy import real_evaluator, run_passes


def assert_empty(ns):
    assert ns['gpu_values'] == ns['cpu_values'] == ns['fps_values'] == []
    assert ns['fps_mean'] == 0


def seed(ns):
    for key in ('gpu_values', 'cpu_values', 'fps_values'):
        ns[key] = [95, 95, 95]
    ns['fps_mean'] = 95


def setup(method):
    ns, writes, _, _ = load_app()
    sensor, values = real_evaluator(ns)
    values['input_monitoring_method'] = method
    ns['fps_utils'].current_stepped_limits = lambda: list(map(Decimal, (30, 60, 90, 120, 150)))
    return ns, writes, sensor, values


def test_pure_reset_has_no_list_aliases_or_retained_state():
    first, second = fresh_cap_evidence(), fresh_cap_evidence()
    assert first == second == ([], [], [], 0, (0, 0))
    lists = first[:3] + second[:3]
    assert len({id(value) for value in lists}) == 6
    first[0].append(95)
    assert all(value == [] for value in lists[1:])


@pytest.mark.parametrize('method', ['Legacy', 'LibreHM'])
@pytest.mark.parametrize('delay', [2, 3])
def test_successive_decreases_need_entire_new_window(method, delay):
    ns, writes, _, _ = setup(method)
    ns['cm'].delaybeforedecrease = delay
    def check(tick):
        if tick % delay == 0:
            assert_empty(ns)
        else:
            assert len(ns['gpu_values']) == tick % delay
    assert run_passes(ns, writes, None, samples=[(200, 'game')] * (2 * delay), on_tick=check) == [delay, 2 * delay]
    assert [w[1][1] for w in writes] == [120, 90]


@pytest.mark.parametrize('method', ['Legacy', 'LibreHM'])
def test_next_decrease_uses_only_fresh_fps_mean(method):
    ns, writes, _, _ = setup(method)
    ns['cm'].delaybeforedecrease = 2
    samples = [(200, 'game')] * 2 + [(65, 'game')] * 2
    assert run_passes(ns, writes, None, samples=samples) == [2, 4]
    assert [w[1][1] for w in writes] == [120, 60]
    assert_empty(ns)


@pytest.mark.parametrize('method', ['Legacy', 'LibreHM'])
@pytest.mark.parametrize('offset,expected', [(-120, [60, 90]), (-100, [60, 90])])
def test_raise_and_off_ladder_fallback_reset_without_changing_cooldown(method, offset, expected):
    ns, writes, sensor, _ = setup(method)
    ns['CurrentFPSOffset'] = offset
    ns['cm'].delaybeforeincrease = 3
    ns['gpu_monitor'].gpu_percentile = 50
    sensor.gpu_percentiles[('Load', '1 GPU')] = 50
    def check(tick):
        if tick in (3, 6):
            assert_empty(ns)
    assert run_passes(ns, writes, None, samples=[(200, 'game')] * 6, on_tick=check) == [3, 6]
    assert [w[1][1] for w in writes] == expected


@pytest.mark.parametrize('method', ['Legacy', 'LibreHM'])
def test_idle_enter_restore_clear_evidence_and_preserve_active_cap(method):
    ns, writes, _, _ = setup(method)
    ns['CurrentFPSOffset'] = -30
    ns['cm'].delaybeforedecrease = 2
    ns['cm'].idle_mode = True
    ticks = []
    ns['monitor_idle'] = lambda _: len(ticks) == 1
    def check(tick):
        ticks.append(tick)
        if tick in (2, 3, 5):
            assert_empty(ns)
        if tick in (2, 3):
            assert ns['CurrentFPSOffset'] == -30
            assert ns['idle_state'] == (tick == 2)
    assert run_passes(ns, writes, None, samples=[(200, 'game')] * 5, on_tick=check) == [2, 3, 5]
    assert [w[1][1] for w in writes] == [20, 120, 90]


@pytest.mark.parametrize('method', ['Legacy', 'LibreHM'])
def test_overlapping_thresholds_allow_one_write_per_pass(method):
    ns, writes, _, values = setup(method)
    ns['cm'].gpucutofffordecrease = ns['cm'].cpucutofffordecrease = 40
    ns['cm'].gpucutoffforincrease = ns['cm'].cpucutoffforincrease = 100
    values.update(input_load_upper=40, input_load_lower=100)
    assert ns['fps_utils'].evaluate_cap_change([90], [50], method) == (True, True)
    assert run_passes(ns, writes, None, samples=[(200, 'game')] * 2) == [1, 2]
    assert [w[1][1] for w in writes] == [120, 90]


@pytest.mark.parametrize('starting', [True, False])
def test_start_stop_max_writes_reset_each_time_before_threads(starting):
    ns, writes, _, spawned = load_app()
    ns['running'] = not starting
    seed(ns)
    events = []
    def write(*args):
        events.append(('write', args))
        # Simulate evidence arriving between the two initial writes: each clears it.
        seed(ns)
    ns['rtss'].set_fractional_fps_direct = write
    ns['rtss'].set_fractional_framerate = write
    class Thread:
        def __init__(self, **kwargs):
            events.append(('thread', kwargs['target'].__name__))
            assert_empty(ns)
        def start(self):
            pass
    ns['threading'].Thread = Thread
    ns['start_stop_callback'](None, None, ns['cm'])
    assert_empty(ns)
    assert ns['running'] == starting
    assert ns['CurrentFPSOffset'] == 0
    assert not ns['idle_state']
    assert events[:2] == [('write', ('Global', Decimal(90)))] * 2
    assert [e[1] for e in events[2:]] == (['monitoring_loop', 'plotting_loop'] if starting else [])


def test_start_monitor_confirmation_begins_after_both_initial_writes():
    ns, writes, _, _ = setup('LibreHM')
    ns['running'] = False
    ns['cm'].delaybeforedecrease = 2
    events = []
    def write(*args):
        events.append(args)
    ns['rtss'].set_fractional_fps_direct = write
    ns['rtss'].set_fractional_framerate = write
    class Thread:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
        def start(self):
            if self.kwargs['target'] is ns['monitoring_loop']:
                assert events == [('Global', Decimal(150))] * 2
                assert_empty(ns)
                # Run the real monitor immediately when spawned.
                ns['rtss'].set_fractional_framerate = lambda *args: writes.append(('monitor', args, 2))
                assert run_passes(ns, writes, None, samples=[(200, 'game')] * 4) == [2, 4]
                ns['running'] = True
    ns['threading'].Thread = Thread
    ns['start_stop_callback'](None, None, ns['cm'])
    assert [w[1][1] for w in writes] == [120, 90]


def test_configured_global_exit_write_resets_shared_evidence():
    ns, writes, _, _ = load_app()
    seed(ns)
    ns['CurrentFPSOffset'] = -30
    ns['idle_state'] = True
    ns['cm'].globallimitonexit = True
    ns['cm'].globallimitonexit_fps = 72
    ns['exit_gui']()
    assert_empty(ns)
    assert [w[1] for w in writes] == [('Global', Decimal(72))]
    assert not ns['running']
    assert ns['CurrentFPSOffset'] == -30
    assert ns['idle_state']
