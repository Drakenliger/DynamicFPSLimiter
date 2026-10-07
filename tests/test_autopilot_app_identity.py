"""Run actual app functions through the existing AST seam and real GuiQueue."""
import threading
from decimal import Decimal

import pytest
from core.gui_queue import GuiQueue
from test_app_session import load_app, worker, finish, restart
from test_app_profile import setup_profile


def app(current='Global', only=False, foreground='gameA', running=True):
    ns, writes, submitted, spawned = load_app()
    setup_profile(ns, current)
    cm = ns['cm']
    # Model ConfigManager's successful stopped-profile load contract.
    def load(name, **kw):
        cm.current_profile = name
        return True
    cm.load_profile_raw = load
    cm.autopilot, cm.autopilot_only_profiles = True, only
    ns['running'] = running
    ns['get_foreground_process_name'] = lambda: foreground
    ns['rtss_manager'].is_rtss_running = lambda: True
    ns['rtss_manager'].get_fps_for_active_window = lambda: (Decimal(95), 'conflicting-rtss.exe')
    # Keep these tests focused on admission and profile writes, not cap decisions.
    ns['gpu_monitor'].gpu_percentile = None
    errors = []
    queue = GuiQueue(on_error=lambda fn, exc: errors.append(exc))
    def submit(fn, *args):
        submitted.append((fn, *args))
        queue.submit(fn, *args)
    ns['_gui_submit'] = submit
    return ns, writes, submitted, queue, errors


def one_pass(ns):
    # Retire this worker without changing lifecycle state, so queued actions can
    # still be admitted at drain. This is a worker return, not a fake controller.
    def sleep(_):
        raise SystemExit
    ns['time'].sleep = sleep
    with pytest.raises(SystemExit):
        ns['monitoring_loop'](ns['session_number'])


def actions(ns, submitted):
    return [s for s in submitted if s[0] in
            (ns['_load_profile_on_gui'], ns['start_stop_callback'], ns['_autopilot_start_on_gui'])]


@pytest.mark.parametrize('only', [False, True])
@pytest.mark.parametrize('foreground', ['GAMEA', None])
def test_monitor_same_case_or_unknown_has_no_action(only, foreground):
    ns, writes, submitted, queue, errors = app('gameA', only, foreground)
    one_pass(ns)
    assert actions(ns, submitted) == []
    queue.drain()
    assert not errors
    assert ns['running'] and ns['cm'].current_profile == 'gameA'


def test_monitor_uses_foreground_and_preserves_b1_order():
    ns, writes, submitted, queue, errors = app(foreground='GAMEA')
    one_pass(ns)
    assert len(actions(ns, submitted)) == 1
    assert ns['cm'].current_profile == 'Global' and not writes
    queue.drain()
    assert not errors
    assert ns['cm'].current_profile == 'gameA'
    assert [w[1] for w in writes] == [('Global', Decimal(120)), ('gameA', Decimal('40.5'))]


def test_exact_collision_in_monitor_and_startup():
    for running in (True, False):
        ns, writes, submitted, queue, errors = app(foreground='GAMEA', running=running)
        ns['cm'].profiles_config.add_section('GAMEA')
        if running:
            one_pass(ns)
        else:
            ns['_autopilot_start_check']()
        assert len(actions(ns, submitted)) == 1
        assert actions(ns, submitted)[0][1] == 'GAMEA'


def test_profile_added_after_loop_starts():
    ns, writes, submitted, queue, errors = app(foreground='gameB')
    ns['cm'].profiles_config.remove_section('gameB')
    passes = 0
    def sleep(_):
        nonlocal passes
        passes += 1
        if passes == 1:
            ns['cm'].profiles_config.add_section('gameB')
        else:
            raise SystemExit
    ns['time'].sleep = sleep
    with pytest.raises(SystemExit):
        ns['monitoring_loop'](1)
    assert [s[1] for s in actions(ns, submitted)] == ['gameB']


@pytest.mark.parametrize('startup', [False, True])
@pytest.mark.parametrize('change', ['disabled', 'mode', 'deleted', 'revision', 'stop', 'restart'])
def test_queued_action_rejects_changed_state(startup, change):
    ns, writes, submitted, queue, errors = app(
        current='Global' if startup else 'gameA', only=True,
        foreground='gameA' if startup else 'desktop.exe', running=not startup)
    if startup:
        ns['_autopilot_start_check']()
    else:
        one_pass(ns)
    assert len(actions(ns, submitted)) == 1
    cm = ns['cm']
    if change == 'disabled':
        cm.autopilot = False
    elif change == 'mode':
        cm.autopilot_only_profiles = False
    elif change == 'deleted':
        cm.profiles_config.remove_section('gameA')
    elif change == 'revision':
        ns['profile_revision'] += 1
    elif change == 'stop':
        if startup:
            ns['start_stop_callback'](None, None, cm)
        ns['start_stop_callback'](None, None, cm)
    else:
        if startup:
            ns['start_stop_callback'](None, None, cm)
            ns['start_stop_callback'](None, None, cm)
            ns['start_stop_callback'](None, None, cm)
        else:
            restart(ns)
    before = (ns['session_number'], ns['running'], cm.current_profile, list(writes))
    queue.drain()
    assert not errors
    assert (ns['session_number'], ns['running'], cm.current_profile, writes) == before


@pytest.mark.parametrize('only,foreground,target', [
    (False, 'GAMEA', 'gameA'), (True, 'GAMEA', 'gameA'),
    (False, 'desktop.exe', 'Global'), (True, 'desktop.exe', None),
    (False, None, None), (True, None, None)])
def test_actual_startup_modes(only, foreground, target):
    ns, writes, submitted, queue, errors = app(only=only, foreground=foreground, running=False)
    ns['_autopilot_start_check']()
    assert len(actions(ns, submitted)) == bool(target)
    assert not ns['running'] and not writes
    queue.drain()
    assert not errors
    assert ns['running'] == bool(target)
    if target:
        assert ns['cm'].current_profile == target
        assert [w[1][0] for w in writes] == [target, target]


@pytest.mark.parametrize('startup', [False, True])
def test_identity_paused_across_real_stop_start(startup):
    ns, writes, submitted, queue, errors = app(
        current='Global' if startup else 'gameA', only=True, running=not startup)
    paused, release = threading.Event(), threading.Event()
    def identity():
        paused.set()
        assert release.wait(5)
        return 'gameA' if startup else 'desktop.exe'
    ns['get_foreground_process_name'] = identity
    # Stop the old monitoring pass at its next session admission.
    fn = ns['_autopilot_start_check'] if startup else lambda: ns['monitoring_loop'](1)
    thread, failures = worker(fn)
    try:
        assert paused.wait(5)
        if startup:
            ns['start_stop_callback'](None, None, ns['cm'])
            ns['start_stop_callback'](None, None, ns['cm'])
            ns['start_stop_callback'](None, None, ns['cm'])
        else:
            restart(ns)
        before = (ns['session_number'], ns['running'], list(writes))
    finally:
        release.set()
    finish(thread, failures)
    queue.drain()
    assert not errors
    assert (ns['session_number'], ns['running'], writes) == before


@pytest.mark.parametrize('change', ['disabled', 'mode', 'deleted'])
def test_queued_selection_rejects_changed_state(change):
    ns, writes, submitted, queue, errors = app(foreground='GAMEA')
    one_pass(ns)
    assert len(actions(ns, submitted)) == 1
    if change == 'disabled':
        ns['cm'].autopilot = False
    elif change == 'mode':
        ns['cm'].autopilot_only_profiles = True
    else:
        ns['cm'].profiles_config.remove_section('gameA')
    queue.drain()
    assert not errors and not writes
    assert ns['cm'].current_profile == 'Global'


def test_start_admission_closes_profile_load_lifecycle_gap():
    ns, writes, submitted, queue, errors = app(running=False)
    ns['_autopilot_start_check']()
    lifecycle = ns['start_stop_callback']
    def invalidate_before_action(sender, data, cm, expected):
        # Actual lifecycle callbacks invalidate the stopped session between the
        # profile hook's return and the queued Start's first-lock admission.
        lifecycle(None, None, cm)
        lifecycle(None, None, cm)
        before = (ns['session_number'], list(writes))
        lifecycle(sender, data, cm, expected)
        assert (ns['session_number'], writes) == before
    ns['start_stop_callback'] = invalidate_before_action
    queue.drain()
    assert not errors
    assert not ns['running'] and ns['session_number'] == 3
