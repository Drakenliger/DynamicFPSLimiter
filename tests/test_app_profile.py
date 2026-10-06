"""Profile switches within an existing monitoring session, without app import."""
from decimal import Decimal
import threading

import pytest

from core.cap_policy import build_cap_model
from test_app_session import load_app, worker, finish

LADDERS = {
    'Global': [Decimal(60), Decimal(90), Decimal(120)],
    'gameA': [Decimal('20.5'), Decimal('30.5'), Decimal('40.5')],
    'gameB': [Decimal('5.25'), Decimal('10.25'), Decimal('15.25')],
}


def setup_profile(ns, initial):
    cm = ns['cm']
    cm.current_profile = initial
    cm.load_profile_callback = lambda _, name, __: setattr(cm, 'current_profile', name)
    cm.gpucutofffordecrease = 90
    cm.gpucutoffforincrease = 50
    ns['fps_utils'].current_stepped_limits = lambda: LADDERS[cm.current_profile]


@pytest.mark.parametrize('initial,target', [('Global', 'gameA'), ('gameA', 'Global'), ('gameA', 'gameB')])
def test_switch_rebuilds_ladder_bounds_and_resets_decisions(initial, target):
    ns, writes, submitted, _ = load_app()
    setup_profile(ns, initial)
    passes = 0
    def sleep(_):
        nonlocal passes
        passes += 1
        if passes == 1:
            ns['CurrentFPSOffset'] = -1000
            ns['fps_mean'] = 1
            ns['fps_values'][:] = [1, 2, 3]
            ns['gpu_values'][:] = [999]
            ns['cpu_values'][:] = [999]
            ns['idle_state'] = True
            ns['_load_profile_on_gui'](target)
            assert ns['CurrentFPSOffset'] == ns['fps_mean'] == 0
            assert not ns['idle_state']
            assert not any(ns[k] for k in ('fps_values', 'gpu_values', 'cpu_values'))
        else:
            ns['running'] = False
    ns['time'].sleep = sleep
    ns['monitoring_loop'](1)
    assert ns['session_number'] == 1
    assert [w[1] for w in writes] == [(initial, LADDERS[initial][-2]), (target, LADDERS[target][-2])]
    assert ns['fps_values'] == ns['gpu_values'] == ns['cpu_values'] == []
    assert ns['fps_mean'] == 0
    _, _, maximum, lower, upper = build_cap_model(LADDERS[target])
    plots = [args for args in submitted if args[0] is ns['update_plot_FPS']]
    assert plots[-1][1:] == ((Decimal(95)-lower)/(upper-lower)*100,
                            (LADDERS[target][-2]-lower)/(upper-lower)*100)
    assert ns['CurrentFPSOffset'] == LADDERS[target][-2] - maximum


@pytest.mark.parametrize('pause_at', ['sample', 'decision', 'cap'])
def test_paused_old_profile_pass_cannot_admit_state_or_cap(pause_at):
    ns, writes, _, _ = load_app()
    setup_profile(ns, 'Global')
    paused, release = threading.Event(), threading.Event()
    def pause():
        if not paused.is_set():
            paused.set()
            assert release.wait(5)
    if pause_at == 'sample':
        def sample():
            pause()
            return Decimal(95), 'game'
        ns['rtss_manager'].get_fps_for_active_window = sample
    elif pause_at == 'decision':
        def decision(*_):
            pause()
            return True, False
        ns['fps_utils'].evaluate_cap_change = decision
    else:
        original = ns['next_cap_on_decrease']
        def cap(*args):
            result = original(*args)
            pause()
            return result
        ns['next_cap_on_decrease'] = cap
    ns['time'].sleep = lambda _: ns.update(running=False)
    thread, errors = worker(lambda: ns['monitoring_loop'](1))
    try:
        assert paused.wait(5)
        ns['_load_profile_on_gui']('gameB')
        assert ns['fps_values'] == ns['gpu_values'] == ns['cpu_values'] == []
        assert ns['fps_mean'] == ns['CurrentFPSOffset'] == 0
    finally:
        release.set()
    finish(thread, errors)
    assert [w[1] for w in writes] == [('gameB', Decimal('10.25'))]
    assert ns['fps_values'] == ns['gpu_values'] == ns['cpu_values'] == []
    assert ns['fps_mean'] == 0


def test_profile_change_discards_idle_cached_active_cap():
    ns, writes, _, _ = load_app()
    setup_profile(ns, 'Global')
    ns['cm'].idle_mode = True
    ns['monitor_idle'] = lambda _: ns['cm'].current_profile == 'Global'
    passes = 0
    def sleep(_):
        nonlocal passes
        passes += 1
        if passes == 1:
            assert ns['idle_state']
            ns['_load_profile_on_gui']('gameB')
        else:
            ns['running'] = False
    ns['time'].sleep = sleep
    ns['monitoring_loop'](1)
    assert [w[1] for w in writes] == [('Global', 20), ('gameB', Decimal('10.25'))]
    assert not ns['idle_state']


def test_profile_change_resets_increase_cooldown():
    ns, writes, _, _ = load_app()
    setup_profile(ns, 'Global')
    ns['cm'].delaybeforeincrease = 20
    pass_number = 0
    def decide(*_):
        return (pass_number in (0, 2), pass_number in (1, 3))
    ns['fps_utils'].evaluate_cap_change = decide
    def sleep(_):
        nonlocal pass_number
        pass_number += 1
        if pass_number == 2:
            ns['_load_profile_on_gui']('gameB')
        elif pass_number == 4:
            ns['running'] = False
    ns['time'].sleep = sleep
    ns['monitoring_loop'](1)
    assert [w[1] for w in writes] == [('Global', Decimal(90)), ('Global', Decimal(120)),
                                    ('gameB', Decimal('10.25')), ('gameB', Decimal('15.25'))]


def test_profile_load_and_model_snapshot_are_coherent():
    ns, writes, _, _ = load_app()
    setup_profile(ns, 'Global')
    loading, release, attempted = (threading.Event() for _ in range(3))
    class ObservedLock:
        def __init__(self):
            self.lock = threading.Lock()
        def __enter__(self):
            if threading.current_thread().name == 'monitor':
                attempted.set()
            self.lock.acquire()
        def __exit__(self, *_):
            self.lock.release()
    ns['session_lock'] = ObservedLock()
    inputs = {'ladder': LADDERS['Global']}
    def load(_, name, __):
        ns['cm'].current_profile = name
        loading.set()
        assert release.wait(5)
        inputs['ladder'] = LADDERS[name]
    ns['cm'].load_profile_callback = load
    ns['fps_utils'].current_stepped_limits = lambda: inputs['ladder']
    ns['time'].sleep = lambda _: ns.update(running=False)
    loader, loader_errors = worker(lambda: ns['_load_profile_on_gui']('gameB'))
    monitor_errors = []
    def monitor():
        try:
            ns['monitoring_loop'](1)
        except BaseException as exc:
            monitor_errors.append(exc)
    thread = threading.Thread(target=monitor, name='monitor')
    try:
        assert loading.wait(5)
        thread.start()
        assert attempted.wait(5)
        assert not writes
    finally:
        release.set()
    finish(loader, loader_errors)
    finish(thread, monitor_errors)
    assert [w[1] for w in writes] == [('gameB', Decimal('10.25'))]


def test_profile_switch_waits_for_admitted_cap_write():
    ns, writes, _, _ = load_app()
    setup_profile(ns, 'Global')
    entered, release, attempted, switched = (threading.Event() for _ in range(4))
    class ObservedLock:
        def __init__(self):
            self.lock = threading.Lock()
        def __enter__(self):
            if threading.current_thread().name == 'switch':
                attempted.set()
            self.lock.acquire()
        def __exit__(self, *_):
            self.lock.release()
    ns['session_lock'] = ObservedLock()
    original_write = ns['rtss'].set_fractional_framerate
    def write(*args):
        if args[0] == 'Global':
            entered.set()
            assert release.wait(5)
        original_write(*args)
    ns['rtss'].set_fractional_framerate = write
    ns['time'].sleep = lambda _: switched.wait(5)
    switch_errors = []
    def switch():
        try:
            ns['_load_profile_on_gui']('gameB')
            assert ns['CurrentFPSOffset'] == ns['fps_mean'] == 0
            assert ns['fps_values'] == ns['gpu_values'] == ns['cpu_values'] == []
            ns['running'] = False
        except BaseException as exc:
            switch_errors.append(exc)
        finally:
            switched.set()
    thread, errors = worker(lambda: ns['monitoring_loop'](1))
    switcher = threading.Thread(target=switch, name='switch')
    try:
        assert entered.wait(5)
        switcher.start()
        assert attempted.wait(5)
        assert ns['cm'].current_profile == 'Global'
        assert not switched.is_set()
    finally:
        release.set()
    finish(switcher, switch_errors)
    finish(thread, errors)
    assert [w[1] for w in writes] == [('Global', Decimal(90))]
    assert ns['CurrentFPSOffset'] == 0
