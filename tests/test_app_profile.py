"""Profile switches within an existing monitoring session, without app import."""
import ast
from decimal import Decimal
import sys
import threading

import pytest

from core.cap_policy import build_cap_model
from test_app_session import load_app, worker, finish, APP

LADDERS = {
    'Global': [Decimal(60), Decimal(90), Decimal(120)],
    'gameA': [Decimal('20.5'), Decimal('30.5'), Decimal('40.5')],
    'gameB': [Decimal('5.25'), Decimal('10.25'), Decimal('15.25')],
}


def setup_profile(ns, initial):
    cm = ns['cm']
    cm.current_profile = initial
    cm.load_profile_raw = lambda name, **kw: setattr(cm, 'current_profile', name)
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
    assert [w[1] for w in writes] == [(initial, LADDERS[initial][-2]), (initial, LADDERS[initial][-1]),
                                    (target, LADDERS[target][-1]), (target, LADDERS[target][-2])]
    assert ns['fps_values'] == ns['gpu_values'] == ns['cpu_values'] == []
    assert ns['fps_mean'] == 0
    _, _, maximum, lower, upper = build_cap_model(LADDERS[target])
    plots = [args for args in submitted if args[0] is ns['update_plot_FPS']]
    assert plots[-1][1:] == ((Decimal(95)-lower)/(upper-lower)*100,
                            (LADDERS[target][-2]-lower)/(upper-lower)*100)
    assert ns['CurrentFPSOffset'] == LADDERS[target][-2] - maximum


@pytest.mark.parametrize('scenario', ['decrease', 'increase', 'idle', 'idle-restore'])
@pytest.mark.parametrize('pause_at', ['sample', 'decision', 'cap'])
def test_paused_old_profile_pass_cannot_admit_state_or_cap(scenario, pause_at):
    ns, writes, _, _ = load_app()
    setup_profile(ns, 'Global')
    paused, release = threading.Event(), threading.Event()
    def pause():
        if not paused.is_set():
            paused.set()
            assert release.wait(5)

    if scenario == 'decrease':
        ns['fps_utils'].evaluate_cap_change = lambda *_: (True, False)
    elif scenario == 'increase':
        ns['CurrentFPSOffset'] = -30
        ns['fps_utils'].evaluate_cap_change = lambda *_: (False, True)
    elif scenario == 'idle':
        ns['cm'].idle_mode = True
        ns['monitor_idle'] = lambda _: True
    elif scenario == 'idle-restore':
        ns['cm'].idle_mode = True
        ns['idle_state'] = True
        ns['monitor_idle'] = lambda _: False

    get_fps_calls = [0]
    def sample():
        get_fps_calls[0] += 1
        if get_fps_calls[0] == 1:
            if pause_at == 'sample':
                pause()
            return Decimal(95), 'game'
        ns['running'] = False
        return Decimal(95), 'game'
    ns['rtss_manager'].get_fps_for_active_window = sample

    if pause_at == 'decision':
        if scenario in ('decrease', 'increase'):
            def decision(*_):
                pause()
                return (scenario == 'decrease', scenario == 'increase')
            ns['fps_utils'].evaluate_cap_change = decision
        else:
            def decision(_):
                pause()
                return scenario == 'idle'
            ns['monitor_idle'] = decision
    elif pause_at == 'cap':
        if scenario == 'decrease':
            original = ns['next_cap_on_decrease']
            def cap(*args):
                result = original(*args)
                pause()
                return result
            ns['next_cap_on_decrease'] = cap
        elif scenario == 'increase':
            lookup_line, _ = increase_locations(ast.parse(APP.read_text()), 'ladder')
        else:
            def decision(_):
                pause()
                return scenario == 'idle'
            ns['monitor_idle'] = decision

    def sleep(_):
        ns['running'] = False
    ns['time'].sleep = sleep

    def run():
        if scenario == 'increase' and pause_at == 'cap':
            run_at_lookup(ns, lookup_line, pause)
        else:
            ns['monitoring_loop'](1)
    thread, errors = worker(run)
    history_before = None
    try:
        assert paused.wait(5)
        assert ns['running'] is True
        ns['_load_profile_on_gui']('gameB')
        ns['fps_values'][:] = [Decimal(45)]
        ns['gpu_values'][:] = [25]
        ns['cpu_values'][:] = [15]
        ns['fps_mean'] = Decimal(45)
        if scenario == 'increase':
            ns['CurrentFPSOffset'] = -5
        elif scenario == 'idle-restore':
            ns['idle_state'] = True
        history_before = (list(ns['fps_values']), list(ns['gpu_values']), list(ns['cpu_values']), ns['fps_mean'])
        assert ns['running'] is True
    finally:
        release.set()
        finish(thread, errors)
    assert [w[1] for w in writes] == [('Global', LADDERS['Global'][-1]),
                                    ('gameB', LADDERS['gameB'][-1])]
    history_after = (list(ns['fps_values']), list(ns['gpu_values']), list(ns['cpu_values']), ns['fps_mean'])
    assert history_after == history_before
    if scenario == 'increase':
        assert ns['CurrentFPSOffset'] == -5


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
    assert [w[1] for w in writes] == [('Global', 20), ('Global', Decimal(120)),
                                    ('gameB', Decimal('15.25')), ('gameB', Decimal('10.25'))]
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
                                    ('Global', Decimal(120)), ('gameB', Decimal('15.25')),
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
    def load(name, **kw):
        ns['cm'].current_profile = name
        loading.set()
        assert release.wait(5)
        inputs['ladder'] = LADDERS[name]
    ns['cm'].load_profile_raw = load
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
        assert [w[1] for w in writes] == [('Global', Decimal(120))]
    finally:
        release.set()
    finish(loader, loader_errors)
    finish(thread, monitor_errors)
    assert [w[1] for w in writes] == [('Global', Decimal(120)),
                                    ('gameB', Decimal('15.25')), ('gameB', Decimal('10.25'))]


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
    def sleep(_):
        assert switched.wait(5)
    ns['time'].sleep = sleep
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
    assert [w[1] for w in writes] == [('Global', Decimal(90)), ('Global', Decimal(120)),
                                    ('gameB', Decimal('15.25'))]
    assert ns['CurrentFPSOffset'] == 0


def increase_locations(tree, arm):
    """Locate the actual lookup and its write admission by semantic context."""
    monitor = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                   and n.name == 'monitoring_loop')
    increase_try = next(n for n in ast.walk(monitor) if isinstance(n, ast.Try)
                        and any(isinstance(h.type, ast.Name) and h.type.id == 'ValueError'
                                for h in n.handlers))
    body = increase_try.orelse if arm == 'ladder' else increase_try.handlers[0].body
    nodes = [n for statement in body for n in ast.walk(statement)]
    lookup = next(n for n in nodes if isinstance(n, ast.Assign)
                  and any(isinstance(t, ast.Name) and t.id == 'next_fps' for t in n.targets)
                  and isinstance(n.value, ast.Subscript)
                  and isinstance(n.value.value, ast.Name)
                  and n.value.value.id == 'fps_limit_list')
    admission = next(n for n in nodes if isinstance(n, ast.With)
                     and any(isinstance(s, ast.Expr) and isinstance(s.value, ast.Call)
                             and isinstance(s.value.func, ast.Name) and s.value.func.id == '_write_cap'
                             for s in n.body))
    return lookup.lineno, admission


def run_at_lookup(ns, line, pause):
    def trace(frame, event, arg):
        if (frame.f_globals is ns and frame.f_code.co_name == 'monitoring_loop'
                and event == 'line' and frame.f_lineno == line):
            pause()
        return trace
    previous_trace = sys.gettrace()
    sys.settrace(trace)
    try:
        ns['monitoring_loop'](1)
    finally:
        sys.settrace(previous_trace)


@pytest.mark.parametrize('arm', ['ladder', 'non-ladder'])
@pytest.mark.parametrize('remove_guard', [False, True], ids=['protected', 'actual-guard-removed'])
def test_increase_lookup_profile_handoff(arm, remove_guard):
    """Each final increase guard prevents an actual suspended old-model write."""
    def transform(tree):
        _, admission = increase_locations(tree, arm)
        if remove_guard:
            guard = next(n for n in admission.body if isinstance(n, ast.If)
                         and ast.unparse(n.test) == 'captured_profile_revision != profile_revision')
            admission.body.remove(guard)
        return tree
    ns, writes, _, _ = load_app(transform=transform)
    setup_profile(ns, 'Global')
    ns['CurrentFPSOffset'] = -30 if arm == 'ladder' else -25
    ns['fps_utils'].evaluate_cap_change = lambda *_: (False, True)
    lookup_line, _ = increase_locations(ast.parse(APP.read_text()), arm)
    paused, release = threading.Event(), threading.Event()
    def pause():
        assert not paused.is_set()
        paused.set()
        assert release.wait(5)
    ns['time'].sleep = lambda _: ns.update(running=False)
    samples = 0
    def sample():
        nonlocal samples
        samples += 1
        if samples > 1:
            ns['running'] = False
        return Decimal(95), 'game'
    ns['rtss_manager'].get_fps_for_active_window = sample
    thread, errors = worker(lambda: run_at_lookup(ns, lookup_line, pause))
    try:
        assert paused.wait(5)
        assert not writes
        ns['_load_profile_on_gui']('gameB')
        ns['CurrentFPSOffset'] = -5
        ns['fps_values'][:] = [Decimal(45)]
        ns['gpu_values'][:] = [25]
        ns['cpu_values'][:] = [15]
        ns['fps_mean'] = Decimal(45)
        before = (list(ns['fps_values']), list(ns['gpu_values']),
                  list(ns['cpu_values']), ns['fps_mean'])
    finally:
        release.set()
        finish(thread, errors)
    after = (list(ns['fps_values']), list(ns['gpu_values']),
             list(ns['cpu_values']), ns['fps_mean'])
    if remove_guard:
        assert [w[1] for w in writes] == [('Global', Decimal(120)),
                                        ('gameB', Decimal('15.25')), ('Global', Decimal(120))]
        assert writes[-1] == ('old-session', ('Global', Decimal(120)), 1)
        assert ns['CurrentFPSOffset'] == 0
        assert after == ([], [], [], 0)
    else:
        assert [w[1] for w in writes] == [('Global', Decimal(120)), ('gameB', Decimal('15.25'))]
        assert not any(w[0] == 'old-session' for w in writes)
        assert ns['CurrentFPSOffset'] == -5
        assert after == before
