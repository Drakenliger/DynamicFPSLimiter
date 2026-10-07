"""A1 recovery exercised through the actual AST-loaded production loop."""
import logging
from decimal import Decimal
import threading

import pytest

from test_app_session import load_app, worker, finish, restart
from test_librehm_policy import real_evaluator


@pytest.mark.parametrize('site', ['setup', 'sample', 'evaluation', 'write', 'dpg'])
@pytest.mark.parametrize('direction', ['decrease', 'increase'])
def test_one_failure_logs_paces_and_requires_fresh_confirmation(caplog, site, direction):
    ns, writes, _, _ = load_app()
    sensor, values = real_evaluator(ns, value=95 if direction == 'decrease' else 50)
    sensor.gpu_history_long = {('Load', '1 GPU'): [50, 50] if direction == 'increase' else [95, 95]}
    ns['cm'].delaybeforedecrease = ns['cm'].delaybeforeincrease = 2
    if direction == 'increase':
        ns['CurrentFPSOffset'] = -30
    owner, attr = {
        'setup': (ns['gpu_monitor'], 'reinitialize'),
        'sample': (ns['rtss_manager'], 'get_fps_for_active_window'),
        'evaluation': (ns['fps_utils'], 'evaluate_cap_change'),
        'write': (ns['rtss'], 'set_fractional_framerate'),
        'dpg': (ns['dpg'], 'get_value'),
    }[site]
    original = getattr(owner, attr)
    calls = []
    def fail_once(*args, **kwargs):
        calls.append(args)
        if len(calls) == 1:
            raise ValueError('one-time ' + site)
        return original(*args, **kwargs)
    setattr(owner, attr, fail_once)
    ticks, write_ticks = [], []
    original_record = ns['cap_change_log'].record
    ns['cap_change_log'].record = lambda row: (write_ticks.append(len(ticks) + 1), original_record(row))
    initial_offset = ns['CurrentFPSOffset']
    def sleep(seconds):
        assert seconds == 1
        ticks.append(seconds)
        if len(ticks) == (2 if site == 'write' else 1):
            assert not writes
            assert ns['CurrentFPSOffset'] == initial_offset
            assert ns['fps_values'] == ns['gpu_values'] == ns['cpu_values'] == []
        if len(ticks) == 4:
            ns['running'] = False
    ns['time'].sleep = sleep
    with caplog.at_level(logging.ERROR):
        ns['monitoring_loop'](1)
    assert len(ticks) == 4
    assert write_ticks[0] == (4 if site == 'write' else 3)
    assert len(writes) == 1
    assert ns['CurrentFPSOffset'] == (-30 if direction == 'decrease' else 0)
    records = [r for r in caplog.records if 'Monitoring pass failed' in r.message]
    assert len(records) == 1 and records[0].exc_info[0] is ValueError
    assert 'one-time ' + site in caplog.text and 'Traceback' in caplog.text


@pytest.mark.parametrize('change', ['replacement', 'profile'])
def test_failed_paused_old_pass_cannot_clear_current_state(change, caplog):
    ns, writes, _, _ = load_app()
    paused, release = threading.Event(), threading.Event()
    def sample():
        paused.set()
        assert release.wait(5)
        raise RuntimeError('retired sample')
    ns['rtss_manager'].get_fps_for_active_window = sample
    ticks = []
    def sleep(seconds):
        ticks.append(seconds)
        ns['running'] = False
    ns['time'].sleep = sleep
    thread, errors = worker(lambda: ns['monitoring_loop'](1))
    try:
        assert paused.wait(5)
        if change == 'replacement':
            restart(ns)
        else:
            with ns['session_lock']:
                ns['profile_revision'] += 1
                ns['cm'].current_profile = 'replacement.exe'
        with ns['session_lock']:
            ns['gpu_values'] = [12, 13]
            ns['cpu_values'] = [22]
            ns['fps_values'] = [Decimal(44)]
            ns['fps_mean'] = Decimal(44)
            ns['CurrentFPSOffset'] = -7
        before_writes = list(writes)
    finally:
        release.set()
    finish(thread, errors)
    assert writes == before_writes
    assert (ns['gpu_values'], ns['cpu_values'], ns['fps_values'], ns['fps_mean'], ns['CurrentFPSOffset']) == ([12, 13], [22], [Decimal(44)], Decimal(44), -7)
    assert ticks == ([] if change == 'replacement' else [1])


@pytest.mark.parametrize('exception', [SystemExit, KeyboardInterrupt])
def test_signals_are_not_contained(exception):
    ns, _, _, _ = load_app()
    def fail():
        raise exception()
    ns['gpu_monitor'].reinitialize = fail
    with pytest.raises(exception):
        ns['monitoring_loop'](1)


@pytest.mark.parametrize('restore', [False, True])
def test_idle_write_exception_does_not_advance_state(restore, caplog):
    ns, writes, _, _ = load_app()
    ns['cm'].idle_mode = True
    ns['CurrentFPSOffset'] = -30
    ns['monitor_idle'] = lambda _: not restore
    ns['fps_utils'].evaluate_cap_change = lambda *args: (False, False)
    calls, ticks = [], []
    original = ns['rtss'].set_fractional_framerate
    def write(*args):
        calls.append(args)
        if len(calls) == (2 if restore else 1):
            raise RuntimeError('idle write failure')
        return original(*args)
    ns['rtss'].set_fractional_framerate = write
    if restore:
        ns['monitor_idle'] = lambda _: len(ticks) == 0
    def sleep(seconds):
        assert seconds == 1
        ticks.append(seconds)
        if len(ticks) == (2 if restore else 1):
            assert ns['idle_state'] is restore
            assert ns['CurrentFPSOffset'] == -30
        if len(ticks) == 3:
            ns['running'] = False
    ns['time'].sleep = sleep
    ns['monitoring_loop'](1)
    assert len(writes) == (2 if restore else 1)
    assert ns['idle_state'] is (not restore)
    assert calls[-1] == ('Global', Decimal(60) if restore else 20)
    assert 'idle write failure' in caplog.text


@pytest.mark.parametrize('direction', ['decrease', 'increase'])
def test_failed_legacy_sample_requires_entire_new_delay(direction):
    ns, writes, _, _ = load_app()
    _, values = real_evaluator(ns)
    values['input_monitoring_method'] = 'Legacy'
    ns['cm'].delaybeforedecrease = ns['cm'].delaybeforeincrease = 3
    ns['gpu_monitor'].gpu_percentile = 95 if direction == 'decrease' else 50
    if direction == 'increase':
        ns['CurrentFPSOffset'] = -30
    ticks, write_ticks = [], []
    def sample():
        if len(ticks) == 2:
            raise RuntimeError('partial legacy history failure')
        return Decimal(95), 'game'
    ns['rtss_manager'].get_fps_for_active_window = sample
    original = ns['rtss'].set_fractional_framerate
    ns['rtss'].set_fractional_framerate = lambda *args: (write_ticks.append(len(ticks) + 1), original(*args))
    def sleep(seconds):
        assert seconds == 1
        ticks.append(seconds)
        if len(ticks) == 3:
            assert ns['gpu_values'] == ns['cpu_values'] == ns['fps_values'] == []
        if len(ticks) == 6:
            ns['running'] = False
    ns['time'].sleep = sleep
    ns['monitoring_loop'](1)
    assert write_ticks == [6] and len(writes) == 1
