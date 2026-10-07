"""Start/Stop write admission race tests under concurrent session invalidations."""
import ast
from decimal import Decimal
import sys
import threading

import pytest

from test_app_session import load_app, worker, finish, restart, APP


def load_app_custom(*, lockless=False):
    tree = ast.parse(APP.read_text())
    names = {'_write_cap', 'start_stop_callback', 'monitoring_loop', 'plotting_loop', 'exit_gui', '_load_profile_on_gui'}
    selected = ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names], type_ignores=[])
    if lockless:
        class RemoveSessionLock(ast.NodeTransformer):
            def visit_With(self, node):
                self.generic_visit(node)
                if any(ast.unparse(item.context_expr) == 'session_lock' for item in node.items):
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
    from types import SimpleNamespace as NS
    cm = NS(current_profile='Global', autopilot=False, input_field_keys=[], input_button_tags=[],
            apply_current_input_values=noop, parse_decimal_set_to_string=str,
            load_profile_callback=noop,
            delaybeforedecrease=1, delaybeforeincrease=1, minvalidgpu=0, minvalidfps=0,
            gpucutofffordecrease=90, gpucutoffforincrease=70,
            cpucutofffordecrease=90, cpucutoffforincrease=70,
            idle_fps_delay=10, idle_mode=False, idle_fps_cap=20,
            gpupollinginterval=100, cpupollinginterval=100, globallimitonexit=False)
    from core.cap_policy import (build_cap_model, next_cap_on_decrease, exit_restore_cap,
                                 cap_readings_valid, confirm_librehm_decision, fresh_cap_evidence)
    from core.cap_change_log import make_row
    from core.session_policy import session_is_current
    ns = dict(make_row=make_row, cap_change_log=NS(record=noop, close=noop), exit_restore_cap=exit_restore_cap,
              fresh_cap_evidence=fresh_cap_evidence, cap_readings_valid=cap_readings_valid,
              confirm_librehm_decision=confirm_librehm_decision, build_cap_model=build_cap_model,
              profile_revision=0, session_is_current=session_is_current, next_cap_on_decrease=next_cap_on_decrease,
              Decimal=Decimal, running=False, session_number=0, session_lock=threading.Lock(),
              cm=cm, threading=NS(Thread=ThreadStub),
              dpg=NS(get_value=lambda _: "Legacy", set_value=noop, configure_item=noop, bind_item_theme=noop,
                     does_item_exist=lambda _: False, is_dearpygui_running=lambda: False),
              themes_manager=NS(themes={'stop_button_theme': 1, 'start_button_theme': 2}),
              tray=NS(set_running_state=noop), logger=NS(add_log=noop),
              lhm_sensor=NS(start=noop, stop=noop), reset_stats=noop,
              gpu_monitor=NS(reinitialize=noop, gpu_percentile=90, cleanup=noop),
              cpu_monitor=NS(cpu_percentile=50, stop=noop),
              fps_utils=NS(current_stepped_limits=lambda: [Decimal(30), Decimal(60), Decimal(90)],
                           evaluate_cap_change=lambda *a: (True, False), reset_summary_statistics=noop,
                           update_summary_statistics=noop, summary_fps=[], summary_cap=[]),
              rtss_manager=NS(get_fps_for_active_window=lambda: (Decimal(95), 'game')),
              rtss=NS(set_fractional_framerate=lambda *a, **kw: writes.append((threading.current_thread().name, a, ns['session_number'])),
                      set_fractional_fps_direct=lambda *a, **kw: writes.append((threading.current_thread().name, a, ns['session_number']))),
              monitor_idle=lambda _: False, _gui_submit=lambda *a: submitted.append(a),
              _update_legend_labels=noop, update_plot_FPS=noop, update_plot_usage=noop,
              time=NS(time=lambda: 1, sleep=noop), elapsed_time=0, max_points=100,
              fps_values=[], gpu_values=[], cpu_values=[], CurrentFPSOffset=0, fps_mean=0, idle_state=False)
    for name in ('time_series', 'fps_time_series', 'gpu_usage_series', 'cpu_usage_series', 'fps_series', 'cap_series'):
        ns[name] = []
    exec(compile(selected, str(APP), 'exec'), ns)
    return ns, writes, submitted, spawned


@pytest.mark.parametrize('invalidation', ['restart', 'exit'])
@pytest.mark.parametrize('lockless', [True, False], ids=['lockless-demonstrates-stale-write', 'lock-prevents-stale-write'])
def test_start_stop_write_admission_race(invalidation, lockless):
    """Pause inside start_stop_callback before direct write; removing lock reproduces stale write admission."""
    ns, writes, _, _ = load_app_custom(lockless=lockless)

    tree = ast.parse(APP.read_text())
    start_stop = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'start_stop_callback')
    write_nodes = [n for n in ast.walk(start_stop)
                   if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
                   and isinstance(n.value.func, ast.Name) and n.value.func.id == '_write_cap']
    write_nodes.sort(key=lambda n: n.lineno)
    target_line = write_nodes[0].lineno

    paused, release = threading.Event(), threading.Event()
    invalidation_attempted, invalidated = threading.Event(), threading.Event()

    class ObservedLock:
        def __init__(self):
            self.lock = threading.Lock()
        def __enter__(self):
            if threading.current_thread().name == 'invalidator':
                invalidation_attempted.set()
            self.lock.acquire()
        def __exit__(self, *args):
            self.lock.release()

    ns['session_lock'] = ObservedLock()

    def trace(frame, event, arg):
        if frame.f_code.co_name == 'start_stop_callback' and event == 'line' and frame.f_lineno == target_line and not paused.is_set():
            paused.set()
            assert release.wait(5)
        return trace

    def run_start_stop():
        sys.settrace(trace)
        try:
            ns['start_stop_callback'](None, None, ns['cm'])
        finally:
            sys.settrace(None)

    def do_invalidation():
        if invalidation == 'restart':
            restart(ns)
        elif invalidation == 'exit':
            ns['exit_gui']()
        invalidated.set()

    thread, errors = worker(run_start_stop)
    invalidator_errors = []

    def checked_invalidation():
        try:
            do_invalidation()
        except BaseException as exc:
            invalidator_errors.append(exc)
        finally:
            invalidated.set()

    invalidator = threading.Thread(target=checked_invalidation, name='invalidator')
    try:
        assert paused.wait(5)
        invalidator.start()
        if lockless:
            assert invalidated.wait(5)
        else:
            assert invalidation_attempted.wait(5)
            assert not invalidated.is_set()
    finally:
        release.set()

    finish(invalidator, invalidator_errors)
    finish(thread, errors)

    old_session_writes = [w for w in writes if w[0] == 'old-session']
    if not lockless:
        assert len(old_session_writes) >= 1
        assert all(w[2] == 1 for w in old_session_writes)
    else:
        stale_writes = [w for w in old_session_writes if w[2] != 1]
        assert len(stale_writes) > 0


@pytest.mark.parametrize('invalidation', ['restart', 'exit'])
def test_start_stop_forced_handoff_between_write_sections(invalidation):
    """Handoff after direct write before refresh section: refresh write is correctly suppressed by session guard."""
    ns, writes, _, _ = load_app_custom(lockless=False)

    tree = ast.parse(APP.read_text())
    start_stop = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'start_stop_callback')
    with_blocks = [n for n in ast.walk(start_stop) if isinstance(n, ast.With)]
    with_blocks.sort(key=lambda n: n.lineno)
    second_with_line = with_blocks[2].lineno

    paused, release = threading.Event(), threading.Event()
    invalidated = threading.Event()

    def trace(frame, event, arg):
        if frame.f_code.co_name == 'start_stop_callback' and event == 'line' and frame.f_lineno == second_with_line and not paused.is_set():
            paused.set()
            assert release.wait(5)
        return trace

    def run_start_stop():
        sys.settrace(trace)
        try:
            ns['start_stop_callback'](None, None, ns['cm'])
        finally:
            sys.settrace(None)

    def do_invalidation():
        if invalidation == 'restart':
            restart(ns)
        elif invalidation == 'exit':
            ns['exit_gui']()
        invalidated.set()

    thread, errors = worker(run_start_stop)
    invalidator_errors = []

    def checked_invalidation():
        try:
            do_invalidation()
        except BaseException as exc:
            invalidator_errors.append(exc)
        finally:
            invalidated.set()

    invalidator = threading.Thread(target=checked_invalidation, name='invalidator')
    try:
        assert paused.wait(5)
        invalidator.start()
        assert invalidated.wait(5)
    finally:
        release.set()

    finish(invalidator, invalidator_errors)
    finish(thread, errors)

    old_session_writes = [w for w in writes if w[0] == 'old-session']
    assert len(old_session_writes) == 1
    assert old_session_writes[0][2] == 1
    assert old_session_writes[0][1] == ('Global', Decimal(90))
