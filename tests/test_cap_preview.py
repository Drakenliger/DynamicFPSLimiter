"""Tests for the read-only FPS cap ladder preview in the Framerate Limits box."""
import ast
import contextlib
import threading
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

from core.ui_scale import ScaledDPG
from core.fps_utils import FPSUtils
from core.gui_queue import GuiQueue
from test_app_session import load_app, worker, finish

ROOT = Path(__file__).resolve().parents[1]


def functions(path, names, namespace):
    tree = ast.parse((ROOT / path).read_text())
    nodes = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name in names]
    exec(compile(ast.Module(body=nodes, type_ignores=[]), path, 'exec'), namespace)
    return namespace


class RecordingDPG:
    contexts = {'window', 'child_window', 'plot', 'plot_axis', 'table', 'table_row',
                'group', 'tab', 'tab_bar', 'drawlist', 'draw_layer', 'theme',
                'theme_component', 'font_registry', 'texture_registry',
                'handler_registry', 'tooltip', 'collapsing_header'}

    def __init__(self):
        self.calls = []
        self.items = set()
        self.stack = []
        self.ancestry = []
        self.parents = {}
        self.live_draws = {}
        self.call_threads = []
        self.next_id = 0
        self.width = 610
        self.values = {
            "input_maxcap": 60,
            "input_mincap": 30,
            "input_capstep": 10,
            "input_capratio": 10,
            "input_capmethod": "Step",
            "input_customfpslimits": "30, 40, 50, 60"
        }

    def __getattr__(self, name):
        if name.startswith('mv'):
            return name
        def call(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            self.call_threads.append(threading.get_ident())
            self.ancestry.append((name, args, kwargs, tuple(self.stack)))
            if name == 'does_item_exist':
                return args[0] in self.items
            if name == 'delete_item':
                removed = {args[0]}
                while True:
                    children = {item for item, parent in self.parents.items() if parent in removed}
                    if children <= removed:
                        break
                    removed.update(children)
                self.items.difference_update(removed)
                for item in removed:
                    self.parents.pop(item, None)
                    self.live_draws.pop(item, None)
                return
            if name == 'get_viewport_width':
                return self.width
            if name == 'get_value':
                return self.values.get(args[0])
            if name == 'set_value':
                self.values[args[0]] = args[1]
                return
            if name in self.contexts or name.startswith(('add_', 'draw_')):
                self.next_id += 1
                item = kwargs.get('tag', self.next_id)
                self.items.add(item)
                self.parents[item] = kwargs.get('parent', self.stack[-1][1] if self.stack else None)
                if name.startswith('draw_') and name not in self.contexts:
                    self.live_draws[item] = (name, args, kwargs)
            if name in self.contexts:
                identity = (name, item, kwargs)
                @contextlib.contextmanager
                def context():
                    self.stack.append(identity)
                    try:
                        yield item
                    finally:
                        assert self.stack.pop() is identity
                return context()
            return 123
        return call

    def tagged(self, name, tag):
        return next(k for n, a, k in self.calls if n == name and k.get('tag') == tag)


class Config(NS):
    def __getattr__(self, name):
        return lambda *a, **kw: None


def test_ui_construction_parent_stack_and_no_old_drawlist():
    raw = RecordingDPG()
    dpg = ScaledDPG(raw, 1.0)
    tree = ast.parse((ROOT / 'src/core/app.py').read_text())

    main_window = next(n for n in tree.body if isinstance(n, ast.With)
                       and isinstance(n.items[0].context_expr, ast.Call)
                       and any(k.arg == 'tag' and isinstance(k.value, ast.Constant)
                               and k.value.value == 'Primary Window' for k in n.items[0].context_expr.keywords))

    noop = lambda *a, **kw: None
    cm = Config(settings=defaultdict(lambda: 40, customfpslimits='30, 60'),
                sensor_infos=[])
    ns = dict(dpg=dpg, cm=cm,
              themes_manager=NS(themes=defaultdict(lambda: 123)), bold_font=123, app_title='Test',
              display_version=lambda: '1.0', textures=defaultdict(lambda: 'raw'),
              tray=NS(minimize_to_tray=noop, drag_viewport=noop, on_mouse_release=noop, on_mouse_click=noop),
              exit_gui=noop, start_stop_callback=noop, toggle_luid_selection=noop,
              build_profile_section=noop, build_plot_window=noop,
              fps_utils=NS(reset_custom_limits=noop, copy_from_plot=noop), Viewport_width=610)

    exec(compile(ast.Module(body=[main_window], type_ignores=[]), 'app.py', 'exec'), ns)

    text_call = next(c for c in raw.calls if c[0] == 'add_text' and c[2].get('tag') == 'label_caps_preview')
    assert (text_call[1][0] if text_call[1] else text_call[2]['default_value']) == "Caps DFL will use"
    drawlist_cfg = raw.tagged('drawlist', 'fps_cap_drawlist')
    assert drawlist_cfg['width'] == 210
    assert drawlist_cfg['height'] == 35
    heading = next(c for c in raw.ancestry if c[0] == 'add_text' and c[1] == ('Framerate Limits',))
    limits_child = next(parent for parent in reversed(heading[3]) if parent[0] == 'child_window')
    for tag in ('label_caps_preview', 'fps_cap_drawlist'):
        record = next(c for c in raw.ancestry if c[2].get('tag') == tag)
        assert next(parent for parent in reversed(record[3]) if parent[0] == 'child_window') is limits_child
        assert raw.parents[tag] == limits_child[1]
    assert raw.stack == []

    drawlist_calls = [c for c in raw.calls if c[0] == 'drawlist']
    fps_cap_drawlists = [c for c in drawlist_calls if c[2].get('tag') == 'fps_cap_drawlist']
    assert len(fps_cap_drawlists) == 1


def preview(scale=1):
    """Use real FPSUtils drawing/ladder methods without initializing .NET hardware."""
    raw = RecordingDPG()
    fps = FPSUtils.__new__(FPSUtils)
    fps.dpg = ScaledDPG(raw, scale)
    fps.last_fps_limits = []
    fps.logger = None
    fps.cm = NS(parse_and_normalize_string_to_decimal_set=lambda text: sorted({Decimal(v) for v in text.split(',')}))
    fps.reset_summary_statistics()
    with fps.dpg.drawlist(width=210, height=35, tag='fps_cap_drawlist'):
        pass
    return raw, fps


def assert_preview(raw, fps, caps_and_x, active):
    """Check surviving primitives, so missing deletion cannot hide behind call-log clearing."""
    scale = fps.dpg.scale
    assert fps.last_fps_limits == [cap for cap, x in caps_and_x]
    assert fps._last_ladder_geometry == (210, scale, active)
    assert raw.parents['Foreground'] == 'fps_cap_drawlist'
    lines = [c for c in raw.live_draws.values() if c[0] == 'draw_line']
    texts = [c for c in raw.live_draws.values() if c[0] == 'draw_text']
    assert len(lines) == len(texts) == len(caps_and_x)
    assert [c[1][1] for c in texts] == [str(cap) for cap, x in caps_and_x]
    for (cap, x), line, text in zip(caps_and_x, lines, texts):
        highlighted = active is not None and cap == active
        color = (255, 215, 0) if highlighted else (200, 200, 200)
        y1, y2 = (5, 25) if highlighted else (9, 21)
        assert line[1] == ((round(x * scale), round(y1 * scale)),
                           (round(x * scale), round(y2 * scale)))
        assert line[2]['color'] == text[2]['color'] == color
        assert line[2]['thickness'] == (3 if highlighted else 1) * scale
        assert line[2]['parent'] == text[2]['parent'] == 'Foreground'
        assert 0 <= text[1][0][0] <= round(210 * scale)
        assert text[1][0][1] == round(23 * scale)
        assert text[2]['size'] == 14 * scale


@pytest.mark.parametrize('dpi', [96, 144])
def test_ladder_visualization_transitions_and_dpi_scaling(dpi):
    raw, fps = preview(dpi / 96)
    fps.update_fps_cap_visualization(active_applied_cap=40)
    assert_preview(raw, fps, [(30, 5), (40, 71), (50, 138), (60, 205)], 40)

    for method, text, cap in [('Step', '', 60), ('Custom', '59.94', Decimal('59.94'))]:
        raw.calls.clear()  # Keep the previous layer and its primitives intact.
        raw.values.update(input_mincap=60, input_capmethod=method, input_customfpslimits=text)
        fps.update_fps_cap_visualization(active_applied_cap=cap)
        assert ('delete_item', ('Foreground',), {}) in raw.calls
        assert_preview(raw, fps, [(cap, 105)], cap)

    # Changing only the observer removes gold; unchanged geometry is cached.
    fps.update_fps_cap_visualization(active_applied_cap=None)
    assert_preview(raw, fps, [(Decimal('59.94'), 105)], None)
    raw.calls.clear()
    fps.update_fps_cap_visualization()
    assert not any(c[0] in ('delete_item', 'draw_layer', 'draw_line', 'draw_text') for c in raw.calls)
    raw.width = 1000
    fps.update_fps_cap_visualization()
    assert not any(c[0] == 'draw_line' for c in raw.calls)

    # Empty producer is a helper seam: ordinary Custom inputs fall back to Step.
    actual_limits = fps.current_stepped_limits
    fps.current_stepped_limits = lambda: []
    raw.calls.clear()
    fps.update_fps_cap_visualization()
    assert ('delete_item', ('Foreground',), {}) in raw.calls
    assert 'Foreground' not in raw.items
    assert not raw.live_draws
    assert fps.last_fps_limits == []
    assert fps._last_ladder_geometry is None
    fps.current_stepped_limits = actual_limits
    raw.values.update(input_capmethod='Step', input_mincap=30)
    fps.update_fps_cap_visualization()
    assert_preview(raw, fps, [(30, 5), (40, 71), (50, 138), (60, 205)], None)


class NativeWrites:
    """Native boundary only: accepted caps are independent of the app observer."""
    def __init__(self, ns):
        self.ns = ns
        self.caps = {'Global': Decimal(60), 'gameA': Decimal(30)}
        self.events = []
        self.outcome = lambda profile, cap: True

    def write(self, profile, cap):
        assert self.ns['session_lock'].locked(), 'native write must be admitted'
        result = self.outcome(profile, cap)
        self.events.append((self.ns['session_number'], profile, cap, result))
        if isinstance(result, Exception):
            raise result
        if result:
            self.caps[profile] = cap
        return result


def preview_app():
    """Reuse the session harness; execute unmodified app bodies and the real queue."""
    ns, _, _, spawned = load_app()
    raw, fps = preview()
    raw.values.update(input_capstep=15, input_monitoring_method='Legacy')
    fps.evaluate_cap_change = lambda *a: (True, False)  # Deterministic decision input.
    cm = ns['cm']
    cm.build_sensor_enable_map = lambda dpg: {}
    logs, rows, queue_errors = [], [], []
    queue = GuiQueue(on_error=lambda fn, exc: queue_errors.append((fn, exc)))
    ns.update(dpg=fps.dpg, fps_utils=fps, active_applied_cap=None, running=False,
              session_number=0, gui_running=True, _gui_submit=queue.submit,
              logger=NS(add_log=logs.append), get_active_warnings=lambda *a: [],
              cap_change_log=NS(record=rows.append))
    functions('src/core/app.py', {'_update_idle_ui', 'reset_stats'}, ns)
    native = NativeWrites(ns)
    ns['rtss'] = NS(get_framerate_limit=lambda profile, **kw: native.caps[profile],
                    set_fractional_framerate=native.write, set_fractional_fps_direct=native.write)
    ns['start_stop_callback'](None, None, cm)
    assert ns['running'] and ns['session_number'] == 1
    assert ns['active_applied_cap'] == native.caps['Global'] == 60
    assert [event[1:] for event in native.events] == [('Global', Decimal(60), True)] * 2
    assert [s['args'] for s in spawned] == [(1,), (1,)]
    return ns, raw, fps, native, queue, queue_errors, rows, logs


class MonitoringComplete(Exception):
    """End the harness at the real inter-pass sleep without altering tested state."""


def monitor_passes(ns, after_pass):
    original_sleep = ns['time'].sleep
    ns['time'].sleep = after_pass
    try:
        with pytest.raises(MonitoringComplete):
            ns['monitoring_loop'](ns['session_number'])
    finally:
        ns['time'].sleep = original_sleep


def one_pass(ns):
    def sleep(delay):
        assert delay == 1
        raise MonitoringComplete
    monitor_passes(ns, sleep)


LADDER = [(30, 5), (45, 105), (60, 205)]


def observe(ns, raw, fps, native, queue, queue_errors, expected, ladder=LADDER, *, enqueue=True):
    if enqueue:
        queue.submit(ns['_update_idle_ui'])
    pending = len(queue)
    before = len(raw.call_threads)
    assert queue.drain() == pending
    assert not queue_errors
    assert set(raw.call_threads[before:]) == {threading.get_ident()}
    assert ns['active_applied_cap'] == expected
    if ns['running']:
        assert expected == native.caps[ns['cm'].current_profile]
    else:
        assert expected is None
    assert_preview(raw, fps, ladder, expected)


@pytest.mark.parametrize('failure', [False, RuntimeError('native write failed')], ids=['native-False', 'native-exception'])
def test_admitted_write_success_and_failure_and_stopped_restart(failure):
    ns, raw, fps, native, queue, errors, rows, logs = preview_app()
    one_pass(ns)  # Actual monitoring decrease admission: 60 -> 45.
    assert ns['CurrentFPSOffset'] == -15
    observe(ns, raw, fps, native, queue, errors, Decimal(45))
    rows_before = list(rows)
    native.outcome = lambda profile, cap: failure
    one_pass(ns)  # Admitted attempt at 30 fails without replacing successful 45.
    assert native.events[-1] == (1, 'Global', Decimal(30), failure)
    assert ns['CurrentFPSOffset'] == -15
    assert rows == rows_before
    observe(ns, raw, fps, native, queue, errors, Decimal(45))

    # A background submission does no DPG work. Drain after actual Stop/restart
    # reads current globals, even when submission saw the previous gold cap.
    native.outcome = lambda profile, cap: True
    for expected in (None, Decimal(60)):
        before = list(raw.calls)
        observer_before = ns['active_applied_cap']
        writes_before = list(native.events)
        def enqueue_transition():
            queue.submit(ns['start_stop_callback'], None, None, ns['cm'])
            queue.submit(ns['_update_idle_ui'])
        thread, thread_errors = worker(enqueue_transition)
        finish(thread, thread_errors)
        assert raw.calls == before
        assert ns['active_applied_cap'] == observer_before and native.events == writes_before
        assert len(queue) == 2
        observe(ns, raw, fps, native, queue, errors, expected, enqueue=False)
    assert ns['running'] and ns['session_number'] == 3
    assert [event[0] for event in native.events[-4:]] == [2, 2, 3, 3]
    assert not any('Error in GUI update loop' in message for message in logs)


def test_retired_monitor_and_queued_refresh_cannot_restore_old_gold():
    ns, raw, fps, native, queue, errors, rows, logs = preview_app()
    one_pass(ns)
    observe(ns, raw, fps, native, queue, errors, Decimal(45))
    paused, release = threading.Event(), threading.Event()

    def decide(*args):
        queue.submit(ns['_update_idle_ui'])  # Submitted while the old cap is 45.
        paused.set()
        assert release.wait(5)
        return True, False

    fps.evaluate_cap_change = decide
    thread, thread_errors = worker(lambda: ns['monitoring_loop'](1))
    try:
        assert paused.wait(5)
        ns['start_stop_callback'](None, None, ns['cm'])
        ns['start_stop_callback'](None, None, ns['cm'])
        writes_after_restart = list(native.events)
        observe(ns, raw, fps, native, queue, errors, Decimal(60), enqueue=False)
    finally:
        release.set()
        finish(thread, thread_errors)
    assert native.events == writes_after_restart
    assert ns['session_number'] == 3 and ns['CurrentFPSOffset'] == 0
    assert ns['active_applied_cap'] == native.caps['Global'] == 60
    assert_preview(raw, fps, LADDER, Decimal(60))


def test_profile_handoff_and_idle_transitions():
    ns, raw, fps, native, queue, errors, rows, logs = preview_app()
    one_pass(ns)
    observe(ns, raw, fps, native, queue, errors, Decimal(45))
    ns['cm'].idle_mode = True
    ns['cm'].idle_fps_cap = 15
    idle_inputs = iter([True, False])
    ns['monitor_idle'] = lambda delay: next(idle_inputs)
    snapshots = []
    events_before = len(native.events)

    def sleep(delay):
        expected = Decimal(15) if not snapshots else Decimal(45)
        observe(ns, raw, fps, native, queue, errors, expected)
        snapshots.append((ns['idle_state'], ns['active_applied_cap']))
        if len(snapshots) == 2:
            raise MonitoringComplete

    monitor_passes(ns, sleep)  # Keeps production's saved active cap across passes.
    assert snapshots == [(True, Decimal(15)), (False, Decimal(45))]
    assert [event[1:] for event in native.events[events_before:]] == [('Global', 15, True), ('Global', Decimal(45), True)]
    assert [row[5] for row in rows[-2:]] == ['idle', 'idle_restore']
    assert ns['CurrentFPSOffset'] == -15


@pytest.mark.parametrize('rollback_ok', [True, False])
def test_failed_incoming_profile_observer_matches_successful_writes(rollback_ok):
    ns, raw, fps, native, queue, errors, rows, logs = preview_app()
    one_pass(ns)
    observe(ns, raw, fps, native, queue, errors, Decimal(45))
    cm = ns['cm']
    cm.input_field_keys = ['mincap', 'maxcap']
    cm.mincap, cm.maxcap = 30, 60
    raw.values.update(game_name='Unsaved Game', new_profile_input='Unsaved Profile')
    loads = []

    def load(name, publish=True):
        loads.append((name, publish))
        raw.values.update(input_mincap=30, input_maxcap=90)
        cm.mincap, cm.maxcap = 30, 90
        return True

    cm.load_profile_raw = load
    native.outcome = lambda profile, cap: profile != 'gameA' and (cap != 45 or rollback_ok)
    before = len(native.events)
    assert ns['_load_profile_on_gui']('gameA', 1, 0) is False
    assert loads == [('gameA', False)]
    assert [event[1:] for event in native.events[before:]] == [
        ('Global', Decimal(60), True), ('gameA', Decimal(90), False), ('Global', Decimal(45), rollback_ok)]
    assert native.caps['gameA'] == 30
    assert cm.current_profile == raw.values['profile_dropdown'] == 'Global'
    assert ns['profile_revision'] == 0
    assert (cm.mincap, cm.maxcap) == (30, 60)
    assert (raw.values['input_mincap'], raw.values['input_maxcap']) == (30, 60)
    assert (raw.values['game_name'], raw.values['new_profile_input']) == ('Unsaved Game', 'Unsaved Profile')
    observe(ns, raw, fps, native, queue, errors, Decimal(45 if rollback_ok else 60))

    # Retain successful handoff coverage, with a distinct incoming ladder/cap.
    native.outcome = lambda profile, cap: True
    assert ns['_load_profile_on_gui']('gameA', 1, 0) is True
    assert cm.current_profile == raw.values['profile_dropdown'] == 'gameA'
    assert ns['profile_revision'] == 1 and ns['CurrentFPSOffset'] == 0
    observe(ns, raw, fps, native, queue, errors, Decimal(90),
            [(30, 5), (45, 55), (60, 105), (75, 155), (90, 205)])
