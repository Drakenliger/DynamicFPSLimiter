"""Execute selected app functions without importing or launching core.app."""
import ast
from decimal import Decimal
from pathlib import Path
import sys
import threading
from types import SimpleNamespace as NS

import pytest

from core.cap_policy import (build_cap_model, next_cap_on_decrease, exit_restore_cap,
                             cap_readings_valid, confirm_librehm_decision, fresh_cap_evidence)
from core.session_policy import session_is_current

APP = Path(__file__).resolve().parents[1] / 'src/core/app.py'


def load_app(*, lockless=False):
    tree = ast.parse(APP.read_text())
    names = {'start_stop_callback', 'monitoring_loop', 'plotting_loop', 'exit_gui', '_load_profile_on_gui'}
    selected = ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names], type_ignores=[])
    if lockless:
        class RemoveSessionLock(ast.NodeTransformer):
            def visit_With(self, node):
                self.generic_visit(node)
                if ast.unparse(node.items[0].context_expr) == 'session_lock':
                    return node.body
                return node
        selected = RemoveSessionLock().visit(selected)
    noop = lambda *a, **kw: None
    writes, submitted, spawned = [], [], []
    class ThreadStub:
        def __init__(self, **kw):
            spawned.append(kw)
        def start(self):
            pass
    cm = NS(current_profile='Global', autopilot=False, input_field_keys=[], input_button_tags=[],
            apply_current_input_values=noop, parse_decimal_set_to_string=str,
            delaybeforedecrease=1, delaybeforeincrease=1, minvalidgpu=0, minvalidfps=0,
            gpucutofffordecrease=90, gpucutoffforincrease=70,
            cpucutofffordecrease=90, cpucutoffforincrease=70,
            idle_fps_delay=10, idle_mode=False, idle_fps_cap=20,
            gpupollinginterval=100, cpupollinginterval=100, globallimitonexit=False)
    ns = dict(exit_restore_cap=exit_restore_cap, fresh_cap_evidence=fresh_cap_evidence, cap_readings_valid=cap_readings_valid, confirm_librehm_decision=confirm_librehm_decision, build_cap_model=build_cap_model, profile_revision=0, session_is_current=session_is_current, next_cap_on_decrease=next_cap_on_decrease,
              Decimal=Decimal, running=True, session_number=1, session_lock=threading.Lock(),
              cm=cm, threading=NS(Thread=ThreadStub),
              dpg=NS(get_value=lambda _: "Legacy", set_value=noop, configure_item=noop, bind_item_theme=noop, does_item_exist=lambda _: False,
                     is_dearpygui_running=lambda: False),
              themes_manager=NS(themes={'stop_button_theme': 1, 'start_button_theme': 2}),
              tray=NS(set_running_state=noop), logger=NS(add_log=noop),
              lhm_sensor=NS(start=noop, stop=noop), reset_stats=noop,
              gpu_monitor=NS(reinitialize=noop, gpu_percentile=90, cleanup=noop),
              cpu_monitor=NS(cpu_percentile=50, stop=noop),
              fps_utils=NS(current_stepped_limits=lambda: [Decimal(30), Decimal(60), Decimal(90)],
                           evaluate_cap_change=lambda *a: (True, False), reset_summary_statistics=noop,
                           update_summary_statistics=noop, summary_fps=[], summary_cap=[]),
              rtss_manager=NS(get_fps_for_active_window=lambda: (Decimal(95), 'game')),
              rtss=NS(set_fractional_framerate=lambda *a: writes.append((threading.current_thread().name, a, ns['session_number'])),
                      set_fractional_fps_direct=lambda *a: writes.append((threading.current_thread().name, a, ns['session_number']))),
              monitor_idle=lambda _: False, _gui_submit=lambda *a: submitted.append(a),
              _update_legend_labels=noop, update_plot_FPS=noop, update_plot_usage=noop,
              time=NS(time=lambda: 1, sleep=noop), elapsed_time=0, max_points=100,
              fps_values=[], gpu_values=[], cpu_values=[], CurrentFPSOffset=0, fps_mean=0, idle_state=False)
    for name in ('time_series', 'fps_time_series', 'gpu_usage_series', 'cpu_usage_series', 'fps_series', 'cap_series'):
        ns[name] = []
    exec(compile(selected, str(APP), 'exec'), ns)
    return ns, writes, submitted, spawned


def worker(fn):
    errors = []
    def run():
        try:
            fn()
        except BaseException as exc:
            errors.append(exc)
    thread = threading.Thread(target=run, name='old-session')
    thread.start()
    return thread, errors


def finish(thread, errors):
    thread.join(timeout=5)
    assert not thread.is_alive()
    assert not errors


def restart(ns):
    ns['start_stop_callback'](None, None, ns['cm'])
    ns['start_stop_callback'](None, None, ns['cm'])
    assert ns['session_number'] == 3
    assert ns['running']


@pytest.mark.parametrize('loop', ['monitoring_loop', 'plotting_loop'])
def test_old_sleeping_loop_exits_after_stop_start(loop):
    ns, writes, submitted, spawned = load_app()
    sleeping, release = threading.Event(), threading.Event()
    def sleep(_):
        sleeping.set()
        assert release.wait(5)
    ns['time'].sleep = sleep
    thread, errors = worker(lambda: ns[loop](1))
    try:
        assert sleeping.wait(5)
        restart(ns)
        before = (len(writes), len(submitted))
    finally:
        release.set()
    finish(thread, errors)
    assert (len(writes), len(submitted)) == before
    assert [s['args'] for s in spawned] == [(3,), (3,)]


def test_old_monitor_paused_before_decision_cannot_write():
    ns, writes, _, _ = load_app()
    paused, release = threading.Event(), threading.Event()
    def decide(*_):
        paused.set()
        assert release.wait(5)
        return True, False
    ns['fps_utils'].evaluate_cap_change = decide
    thread, errors = worker(lambda: ns['monitoring_loop'](1))
    try:
        assert paused.wait(5)
        restart(ns)
    finally:
        release.set()
    finish(thread, errors)
    assert not [w for w in writes if w[0] == 'old-session']


@pytest.mark.parametrize('lockless', [True, False], ids=['lockless-demonstrates-stale-write', 'shared-lock-prevents-stale-write'])
def test_pause_after_admission_before_rtss_call(lockless):
    """Pause before RTSS entry; removing only locks reproduces stale admission."""
    ns, writes, _, _ = load_app(lockless=lockless)
    tree = ast.parse(APP.read_text())
    monitor = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'monitoring_loop')
    call_line = min(n.lineno for n in ast.walk(monitor) if isinstance(n, ast.Expr)
                    and isinstance(n.value, ast.Call) and ast.unparse(n.value) == 'rtss.set_fractional_framerate(current_profile, next_fps)')
    paused, release = threading.Event(), threading.Event()
    invalidation_attempted, restarted = threading.Event(), threading.Event()
    class ObservedLock:
        def __init__(self):
            self.lock = threading.Lock()
        def __enter__(self):
            if threading.current_thread().name == 'restart':
                invalidation_attempted.set()
            self.lock.acquire()
        def __exit__(self, *args):
            self.lock.release()
    ns['session_lock'] = ObservedLock()
    ns['time'].sleep = lambda _: restarted.wait(5)
    def trace(frame, event, arg):
        if frame.f_code.co_name == 'monitoring_loop' and event == 'line' and frame.f_lineno == call_line and not paused.is_set():
            paused.set()
            assert release.wait(5)
        return trace
    def run():
        sys.settrace(trace)
        try:
            ns['monitoring_loop'](1)
        finally:
            sys.settrace(None)
    def invalidate():
        restart(ns)
        restarted.set()
    thread, errors = worker(run)
    restart_errors = []
    def checked_invalidate():
        try:
            invalidate()
        except BaseException as exc:
            restart_errors.append(exc)
            restarted.set()
    invalidator = threading.Thread(target=checked_invalidate, name='restart')
    try:
        assert paused.wait(5)
        assert not writes  # The RTSS stub has not been entered.
        invalidator.start()
        if lockless:
            assert restarted.wait(5)
        else:
            assert invalidation_attempted.wait(5)
            assert ns['session_number'] == 1
            assert not restarted.is_set()
    finally:
        release.set()
    finish(invalidator, restart_errors)
    finish(thread, errors)
    old_writes = [w for w in writes if w[0] == 'old-session']
    assert old_writes == [('old-session', ('Global', Decimal(60)), 3 if lockless else 1)]


@pytest.mark.parametrize("exit_cap", [False, True])
def test_exit_invalidates_session(exit_cap):
    ns, writes, _, _ = load_app()
    ns["cm"].globallimitonexit = exit_cap
    ns["cm"].globallimitonexit_fps = 60
    ns['exit_gui']()
    assert ns['session_number'] == 2
    assert not ns['running']
    assert len(writes) == 2 + int(exit_cap)
    assert [w[1] for w in writes[:2]] == [("Global", Decimal(90))] * 2
    if exit_cap:
        assert writes[-1][1:] == (("Global", Decimal(60)), 2)


def test_old_cap_calculation_cannot_reset_new_session_offset():
    ns, writes, _, _ = load_app()
    paused, release = threading.Event(), threading.Event()
    def calculate(*args):
        result = next_cap_on_decrease(*args)
        assert result == Decimal(60)
        paused.set()
        assert release.wait(5)
        return result
    ns['next_cap_on_decrease'] = calculate
    thread, errors = worker(lambda: ns['monitoring_loop'](1))
    try:
        assert paused.wait(5)
        restart(ns)
        assert ns['CurrentFPSOffset'] == 0
    finally:
        release.set()
    finish(thread, errors)
    assert ns['CurrentFPSOffset'] == 0
    assert not [w for w in writes if w[0] == 'old-session']


@pytest.mark.parametrize('seed', [False, True], ids=['empty', 'seeded'])
def test_old_sample_cannot_contaminate_new_session_histories(seed):
    ns, writes, _, _ = load_app()
    paused, release = threading.Event(), threading.Event()
    def sample():
        paused.set()
        assert release.wait(5)
        return Decimal(95), 'game'
    ns['rtss_manager'].get_fps_for_active_window = sample
    thread, errors = worker(lambda: ns['monitoring_loop'](1))
    try:
        assert paused.wait(5)
        restart(ns)
        if seed:
            ns['fps_values'][:] = [Decimal(45)]
            ns['gpu_values'][:] = [25]
            ns['cpu_values'][:] = [15]
            ns['fps_mean'] = Decimal(45)
        before = tuple(list(ns[k]) for k in ('fps_values', 'gpu_values', 'cpu_values')) + (ns['fps_mean'],)
    finally:
        release.set()
    finish(thread, errors)
    after = tuple(list(ns[k]) for k in ('fps_values', 'gpu_values', 'cpu_values')) + (ns['fps_mean'],)
    assert after == before
    assert not [w for w in writes if w[0] == 'old-session']


def test_idle_write_and_state_are_atomic_with_restart():
    ns, writes, _, _ = load_app()
    ns['cm'].idle_mode = True
    ns['monitor_idle'] = lambda _: True
    paused, release, attempted, restarted = (threading.Event() for _ in range(4))
    states = []
    class ObservedLock:
        def __init__(self):
            self.lock = threading.Lock()
        def __enter__(self):
            if threading.current_thread().name == 'restart':
                attempted.set()
            self.lock.acquire()
        def __exit__(self, *args):
            if threading.current_thread().name == 'old-session' and writes and not paused.is_set():
                states.append(ns['idle_state'])
                paused.set()
                assert release.wait(5)
            self.lock.release()
    ns['session_lock'] = ObservedLock()
    ns['time'].sleep = lambda _: restarted.wait(5)
    thread, errors = worker(lambda: ns['monitoring_loop'](1))
    restart_errors = []
    def invalidate():
        try:
            restart(ns)
        except BaseException as exc:
            restart_errors.append(exc)
        finally:
            restarted.set()
    invalidator = threading.Thread(target=invalidate, name='restart')
    try:
        assert paused.wait(5)
        invalidator.start()
        assert attempted.wait(5)
        assert ns['session_number'] == 1
    finally:
        release.set()
    finish(invalidator, restart_errors)
    finish(thread, errors)
    assert states == [True]
    assert ns['idle_state'] is False
    assert [w for w in writes if w[0] == 'old-session'] == [('old-session', ('Global', 20), 1)]
