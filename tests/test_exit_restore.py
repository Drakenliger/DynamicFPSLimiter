"""PR5 regressions execute exit_gui through the shared app AST harness."""
from decimal import Decimal
import threading

import pytest

from core.cap_policy import exit_restore_cap
from test_app_session import load_app, worker, finish
from test_cap_write_reset import seed, assert_empty


@pytest.mark.parametrize('profile', ['game.exe', 'Global'])
@pytest.mark.parametrize('running', [True, False])
@pytest.mark.parametrize('exit_cap', [True, False])
@pytest.mark.parametrize('idle', [True, False], ids=['idle', 'dropped'])
def test_exit_write_order_and_cleanup(profile, running, exit_cap, idle):
    ns, _, _, _ = load_app()
    ns['running'] = running
    ns['cm'].current_profile = profile
    ns['cm'].globallimitonexit = exit_cap
    ns['cm'].globallimitonexit_fps = Decimal('72.25')
    ns['CurrentFPSOffset'] = Decimal('-30.5')
    ns['idle_state'] = idle
    ladder = [Decimal('90.125'), Decimal('30'), Decimal('60.5')]
    snapshots = []
    def limits():
        assert ns['session_lock'].locked()
        snapshots.append(True)
        return ladder
    ns['fps_utils'].current_stepped_limits = limits
    events, caps, resets = [], {}, []
    original_reset = ns['fresh_cap_evidence']
    def reset():
        resets.append(True)
        return original_reset()
    ns['fresh_cap_evidence'] = reset
    def write(path, name, cap):
        assert ns['session_lock'].locked()
        assert ns['session_number'] == 2 and not ns['running']
        assert isinstance(cap, Decimal)
        if events:
            assert_empty(ns)
        events.append((path, name, cap))
        caps[name] = cap
        seed(ns)
        # A later live profile/ladder change must not alter the exit snapshot.
        ns['cm'].current_profile = 'other.exe'
        ladder[:] = [Decimal(999)]
    ns['rtss'].set_fractional_fps_direct = lambda *a: write('direct', *a)
    ns['rtss'].set_fractional_framerate = lambda *a: write('refresh', *a)
    cleanup = []
    ns['gpu_monitor'].cleanup = lambda: cleanup.append('gpu')
    ns['cpu_monitor'].stop = lambda: cleanup.append('cpu')
    ns['lhm_sensor'].stop = lambda: cleanup.append('lhm')
    ns['dpg'].is_dearpygui_running = lambda: True
    ns['dpg'].destroy_context = lambda: cleanup.append('gui')
    seed(ns)
    ns['exit_gui']()
    expected = ([('direct', profile, Decimal('90.125')),
                 ('refresh', profile, Decimal('90.125'))] if running else [])
    if exit_cap:
        expected.append(('refresh', 'Global', Decimal('72.25')))
    assert events == expected
    assert len(resets) == len(expected)
    assert snapshots == ([True] if running else [])
    assert cleanup == ['gpu', 'cpu', 'lhm', 'gui']
    assert ns['session_number'] == 2 and not ns['running'] and not ns['gui_running']
    if expected:
        assert_empty(ns)
    if running:
        assert caps[profile] == (Decimal('72.25') if profile == 'Global' and exit_cap else Decimal('90.125'))


def test_stopped_helper_does_not_require_a_ladder():
    assert exit_restore_cap(False, 'game.exe', ()) is None


@pytest.mark.parametrize('exit_cap', [False, True])
def test_old_monitoring_decision_cannot_overwrite_exit_restore(exit_cap):
    ns, writes, _, _ = load_app()
    ns['cm'].current_profile = 'game.exe'
    ns['cm'].globallimitonexit = exit_cap
    ns['cm'].globallimitonexit_fps = Decimal('72.25')
    paused, release = threading.Event(), threading.Event()
    def decide(*_):
        paused.set()
        assert release.wait(5)
        return True, False
    ns['fps_utils'].evaluate_cap_change = decide
    thread, errors = worker(lambda: ns['monitoring_loop'](1))
    try:
        assert paused.wait(5)
        ns['exit_gui']()
        before = list(writes)
    finally:
        release.set()
    finish(thread, errors)
    assert writes == before
    assert [w[1] for w in writes] == [('game.exe', Decimal(90))] * 2 + (
        [('Global', Decimal('72.25'))] if exit_cap else [])
    assert all(w[2] == 2 for w in writes)


@pytest.mark.parametrize('exit_cap', [False, True])
@pytest.mark.parametrize('pause_after', [1, 2, 3],
                         ids=['snapshot-release', 'direct-release', 'refresh-release'])
def test_rejected_exit_admission_still_cleans_up(exit_cap, pause_after):
    ns, writes, _, _ = load_app()
    ns['cm'].current_profile = 'game.exe'
    ns['cm'].globallimitonexit = exit_cap
    ns['cm'].globallimitonexit_fps = Decimal('72.25')
    paused, release = threading.Event(), threading.Event()

    class ReleasePauseLock:
        def __init__(self):
            self.lock = threading.Lock()
            self.exit_acquires = 0

        def __enter__(self):
            self.lock.acquire()
            if threading.current_thread() is exit_thread:
                self.exit_acquires += 1

        def __exit__(self, *args):
            self.lock.release()
            # Pause only exit's chosen acquire, after releasing the real lock.
            # The callback must be free to acquire it and invalidate the session.
            if (threading.current_thread() is exit_thread
                    and self.exit_acquires == pause_after):
                paused.set()
                assert release.wait(5)

    ns['session_lock'] = ReleasePauseLock()
    cleanup = []
    ns['gpu_monitor'].cleanup = lambda: cleanup.append('gpu')
    ns['cpu_monitor'].stop = lambda: cleanup.append('cpu')
    ns['lhm_sensor'].stop = lambda: cleanup.append('lhm')
    ns['dpg'].is_dearpygui_running = lambda: True
    ns['dpg'].destroy_context = lambda: cleanup.append('gui')
    errors = []

    def exit_on_thread():
        try:
            ns['exit_gui']()
        except BaseException as exc:
            errors.append(exc)

    exit_thread = threading.Thread(target=exit_on_thread, name='exit')
    exit_thread.start()
    try:
        assert paused.wait(5)
        assert ns['session_number'] == 2 and not ns['running']
        # Execute the actual callback on the other thread while exit is unlocked.
        ns['start_stop_callback'](None, None, ns['cm'])
        assert ns['session_number'] == 3 and ns['running']
        before = list(writes)
    finally:
        release.set()
    finish(exit_thread, errors)
    assert writes == before
    exit_writes = [w for w in writes if w[0] == 'exit']
    assert exit_writes == [('exit', ('game.exe', Decimal(90)), 2)] * (pause_after - 1)
    assert cleanup == ['gpu', 'cpu', 'lhm', 'gui']
