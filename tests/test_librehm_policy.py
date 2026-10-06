"""Portable tests of actual monitoring and sensor evaluation function bodies."""
import ast
from decimal import Decimal
from pathlib import Path
import statistics
from types import SimpleNamespace as NS

import pytest

from core.cap_policy import cap_readings_valid, confirm_librehm_decision, evaluate_legacy_cap_change
from test_app_session import load_app, worker, finish, restart


def real_evaluator(ns, enabled=True, value=95):
    tree = ast.parse((Path(__file__).resolve().parents[1] / 'src/core/fps_utils.py').read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'FPSUtils')
    method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'evaluate_cap_change')
    scope = {'statistics': statistics, 'evaluate_legacy_cap_change': evaluate_legacy_cap_change}
    exec(compile(ast.Module(body=[method], type_ignores=[]), '<FPSUtils>', 'exec'), scope)
    values = {'input_monitoring_method': 'LibreHM', 'input_load_enable': enabled,
              'input_load_upper': 90, 'input_load_lower': 70}
    ns['dpg'].get_value = values.get
    ns['dpg'].does_item_exist = lambda tag: tag in values
    ns['cm'].sensor_infos = [dict(parameter_id='load', sensor_type='Load', sensor_name='GPU',
                                    sensor_name_indexed='1 GPU', hw_type='Gpu', hw_name='card')]
    sensor = NS(gpu_percentiles={('Load', '1 GPU'): value},
                gpu_history_long={('Load', '1 GPU'): [95, 95]},
                cpu_percentiles={}, cpu_history_long={})
    obj = NS(cm=ns['cm'], dpg=ns['dpg'], lhm_sensor=sensor,
             HardwareType=NS(Cpu='Cpu'), logger=ns['logger'])
    ns['fps_utils'].evaluate_cap_change = lambda *args: scope['evaluate_cap_change'](obj, *args)
    return sensor, values


def run_passes(ns, writes, decisions, *, samples=None, on_tick=None):
    ticks, write_ticks = [], []
    original_write = ns['rtss'].set_fractional_framerate
    ns['rtss'].set_fractional_framerate = lambda *args: (write_ticks.append(len(ticks) + 1), original_write(*args))
    if decisions is not None:
        ns['fps_utils'].evaluate_cap_change = lambda *_: decisions[len(ticks)]
    if samples is not None:
        ns['rtss_manager'].get_fps_for_active_window = lambda: samples[len(ticks)]
    count = len(decisions) if decisions is not None else len(samples)
    def sleep(seconds):
        assert seconds == 1
        ticks.append(None)
        if on_tick:
            on_tick(len(ticks))
        if len(ticks) == count:
            ns['running'] = False
    ns['time'].sleep = sleep
    ns['monitoring_loop'](ns['session_number'])
    return write_ticks


@pytest.mark.parametrize('gpu', [None, 0, 5])
@pytest.mark.parametrize('method', ['LibreHM', 'Legacy'])
def test_real_sensor_decision_pdh_gate(gpu, method):
    ns, writes, _, _ = load_app()
    _, values = real_evaluator(ns)
    values['input_monitoring_method'] = method
    ns['cm'].minvalidgpu = 10
    ns['gpu_monitor'].gpu_percentile = gpu
    assert run_passes(ns, writes, None, samples=[(Decimal(95), 'game')]) == ([1] if method == 'LibreHM' else [])


@pytest.mark.parametrize('fps,process', [(None, 'game'), (0, 'game'), (-1, 'game'), (10, 'game'), (95, 'DynamicFPSLimiter.exe')])
def test_actual_fps_and_process_gate_even_with_valid_old_mean(fps, process):
    ns, writes, _, _ = load_app()
    real_evaluator(ns)
    ns['cm'].minvalidfps = 10
    ns['fps_values'][:] = [Decimal(95)] * 3
    ns['fps_mean'] = Decimal(95)
    assert run_passes(ns, writes, None, samples=[(fps, process)]) == []


@pytest.mark.parametrize('enabled,value', [(False, 95), (True, None)])
def test_real_no_enabled_or_no_data_does_not_write(enabled, value):
    ns, writes, _, _ = load_app()
    real_evaluator(ns, enabled, value)
    assert run_passes(ns, writes, None, samples=[(Decimal(95), 'game')] * 4) == []


@pytest.mark.parametrize('direction,delay,offset', [((True, False), 3, 0), ((False, True), 4, -60)])
def test_delay_exact_ticks(direction, delay, offset):
    ns, writes, _, _ = load_app()
    real_evaluator(ns)
    ns['CurrentFPSOffset'] = offset
    ns['cm'].delaybeforedecrease = 3
    ns['cm'].delaybeforeincrease = 4
    assert run_passes(ns, writes, [direction] * delay) == [delay]


def test_spike_neutral_and_opposite_break_independent_delays():
    ns, writes, _, _ = load_app()
    real_evaluator(ns)
    ns['cm'].delaybeforedecrease = 3
    ns['cm'].delaybeforeincrease = 2
    drop, rise, neutral = (True, False), (False, True), (False, False)
    assert run_passes(ns, writes, [drop, neutral, drop, rise, drop, drop, drop, rise, rise]) == [7, 9]


@pytest.mark.parametrize('bad_sample', [(0, 'game'), (95, 'DynamicFPSLimiter.exe')])
def test_ineligible_pass_breaks_confirmation(bad_sample):
    ns, writes, _, _ = load_app()
    real_evaluator(ns)
    ns['cm'].delaybeforedecrease = 2
    samples = [(95, 'game'), bad_sample, (95, 'game'), (95, 'game')]
    assert run_passes(ns, writes, [(True, False)] * 4, samples=samples) == [4]


def test_profile_revision_resets_confirmation():
    ns, writes, _, _ = load_app()
    real_evaluator(ns)
    ns['cm'].delaybeforedecrease = 3
    def revise(tick):
        if tick == 2:
            with ns['session_lock']:
                ns['profile_revision'] += 1
    assert run_passes(ns, writes, [(True, False)] * 5, on_tick=revise) == [5]


def test_new_start_has_fresh_confirmation():
    ns, writes, _, _ = load_app()
    real_evaluator(ns)
    ns['cm'].delaybeforedecrease = 3
    assert run_passes(ns, writes, [(True, False)] * 2) == []
    ns['running'] = True
    restart(ns)
    assert run_passes(ns, writes, [(True, False)] * 3) == [3]


@pytest.mark.parametrize('invalidate', ['session', 'profile'])
def test_paused_librehm_decision_cannot_seed_new_history(invalidate):
    import threading
    ns, writes, _, _ = load_app()
    real_evaluator(ns)
    ns['cm'].delaybeforedecrease = 2
    paused, release = threading.Event(), threading.Event()
    calls = []
    def decide(*_):
        calls.append(None)
        if len(calls) == 1:
            paused.set()
            assert release.wait(5)
        return True, False
    ns['fps_utils'].evaluate_cap_change = decide
    ticks = []
    def sleep(_):
        ticks.append(None)
        if len(ticks) == 2:
            ns['running'] = False
    ns['time'].sleep = sleep
    thread, errors = worker(lambda: ns['monitoring_loop'](1))
    try:
        assert paused.wait(5)
        if invalidate == 'session':
            restart(ns)
        else:
            with ns['session_lock']:
                ns['profile_revision'] += 1
    finally:
        release.set()
    finish(thread, errors)
    old_writes = [w for w in writes if w[0] == 'old-session']
    assert len(old_writes) == (0 if invalidate == 'session' else 1)
    if invalidate == 'profile':
        assert len(calls) == 3


def test_pure_confirmation_and_legacy_validity():
    assert cap_readings_valid('Legacy', 90, 0, 95, 10, 10)
    history = (0, 0)
    for decision, expected in [((True, False), (False, False)), ((False, True), (False, False)),
                               ((False, True), (False, True)), ((False, False), (False, False))]:
        history, result = confirm_librehm_decision(history, *decision, 3, 2)
        assert result == expected
    assert history == (0, 0)


@pytest.mark.parametrize('direction,offset', [('drop', 0), ('raise', -60)])
def test_real_legacy_thresholds_and_delays(direction, offset):
    ns, writes, _, _ = load_app()
    _, values = real_evaluator(ns)
    values['input_monitoring_method'] = 'Legacy'
    ns['cm'].delaybeforedecrease = 3
    ns['cm'].delaybeforeincrease = 2
    ns['CurrentFPSOffset'] = offset
    ns['gpu_monitor'].gpu_percentile = 95 if direction == 'drop' else 50
    ns['cpu_monitor'].cpu_percentile = 50
    delay = 3 if direction == 'drop' else 2
    assert run_passes(ns, writes, None, samples=[(Decimal(95), 'game')] * delay) == [delay]


def test_real_librehm_any_drop_all_raise_and_missing_sensor_semantics():
    ns, _, _, _ = load_app()
    sensor, values = real_evaluator(ns, value=50)
    ns['cm'].sensor_infos.append(dict(ns['cm'].sensor_infos[0], parameter_id='second',
                                     sensor_name='Other', sensor_name_indexed='1 Other'))
    values.update(input_second_enable=True, input_second_upper=90, input_second_lower=70)
    sensor.gpu_history_long[('Load', '1 Other')] = [50, 50]
    sensor.gpu_percentiles[('Load', '1 Other')] = 95
    evaluate = ns['fps_utils'].evaluate_cap_change
    assert evaluate([], [], 'LibreHM') == (True, False)
    sensor.gpu_percentiles[('Load', '1 Other')] = 80
    assert evaluate([], [], 'LibreHM') == (False, False)
    sensor.gpu_percentiles[('Load', '1 Other')] = 50
    assert evaluate([], [], 'LibreHM') == (False, True)
    # Existing behavior ignores a missing reading when other selected sensors have data.
    sensor.gpu_percentiles[('Load', '1 Other')] = None
    assert evaluate([], [], 'LibreHM') == (False, True)
    ns['cm'].sensor_infos = []
    assert evaluate([], [], 'LibreHM') == (False, False)


def test_librehm_confirmed_raise_preserves_existing_cooldown():
    ns, writes, _, _ = load_app()
    real_evaluator(ns)
    ns['cm'].delaybeforeincrease = 3
    ns['CurrentFPSOffset'] = -60
    assert run_passes(ns, writes, [(False, True)] * 6) == [3, 6]


@pytest.mark.parametrize('direction', ['drop', 'raise'])
@pytest.mark.parametrize('channel', ['gpu', 'cpu'])
@pytest.mark.parametrize('position', [0, 1])
@pytest.mark.parametrize('opposing', [50, 95])
def test_real_legacy_none_window_makes_no_decision(direction, channel, position, opposing):
    ns, _, _, _ = load_app()
    _, values = real_evaluator(ns)
    values['input_monitoring_method'] = 'Legacy'
    ns['cm'].delaybeforedecrease = ns['cm'].delaybeforeincrease = 2
    incomplete = [95 if direction == 'drop' else 0] * 2
    incomplete[position] = None
    other = [opposing] * 2
    gpu, cpu = (incomplete, other) if channel == 'gpu' else (other, incomplete)
    assert ns['fps_utils'].evaluate_cap_change(gpu, cpu, 'Legacy') == (False, False)


def test_profile_switch_during_real_evaluator_pins_backend_and_continues():
    import sys
    import threading
    ns, writes, _, _ = load_app()
    _, values = real_evaluator(ns)
    ns['cm'].delaybeforedecrease = 2
    ns['gpu_monitor'].gpu_percentile = None
    paused, release = threading.Event(), threading.Event()
    calls, reads, ticks = [], [], []
    original_get = ns['dpg'].get_value
    def get_value(tag):
        if tag == 'input_monitoring_method':
            reads.append(original_get(tag))
        return original_get(tag)
    ns['dpg'].get_value = get_value
    def load_profile(_, name, __):
        ns['cm'].current_profile = name
        values['input_monitoring_method'] = 'Legacy'
        ns['gpu_monitor'].gpu_percentile = 95
    ns['cm'].load_profile_callback = load_profile
    def trace(frame, event, arg):
        if frame.f_code.co_name == 'evaluate_cap_change' and event == 'call':
            calls.append((frame.f_locals.get('monitoring_method'), list(frame.f_locals['gpu_values'])))
            if len(calls) == 2:
                paused.set()
                assert release.wait(5)
        return trace
    def sleep(_):
        ticks.append(None)
        if len(ticks) == 3:
            ns['running'] = False
    ns['time'].sleep = sleep
    def run():
        sys.settrace(trace)
        try:
            ns['monitoring_loop'](1)
        finally:
            sys.settrace(None)
    thread, errors = worker(run)
    try:
        assert paused.wait(5)
        assert calls[1][1] == [None, None]
        ns['_load_profile_on_gui']('LegacyGame')
        assert ns['gpu_values'] == ns['cpu_values'] == ns['fps_values'] == []
        assert ns['CurrentFPSOffset'] == ns['fps_mean'] == 0
        assert not writes
    finally:
        release.set()
    finish(thread, errors)
    assert calls == [('LibreHM', [None]), ('LibreHM', [None, None]),
                     ('Legacy', [95]), ('Legacy', [95, 95])]
    assert reads == ['LibreHM', 'LibreHM', 'Legacy', 'Legacy']
    assert ns['gpu_values'] == [95, 95]
    assert ns['cpu_values'] == [50, 50]
    assert ns['fps_values'] == [Decimal(95), Decimal(95)]
    assert ns['fps_mean'] == Decimal(95)
    assert [w[1] for w in writes] == [('LegacyGame', Decimal(60))]
