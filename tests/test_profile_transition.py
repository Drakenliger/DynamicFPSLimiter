"""Real app handoff bodies, ConfigManager loader, FPS ladder and GuiQueue."""
import ast
from decimal import Decimal
from types import SimpleNamespace as NS
import threading

import pytest

from core.gui_queue import GuiQueue
from core.profile_policy import effective_max, profile_request_current, profile_transition_kind
from test_app_session import APP, load_app, restart, worker, finish


@pytest.mark.parametrize('target,current,running,expected', [
    ('gameA', 'Global', True, 'switch'), ('Global', 'gameA', True, 'switch'),
    ('gameB', 'gameA', True, 'switch'), ('gameA', 'gameA', True, 'same'),
    ('gameA', 'gameA', False, 'load'), ('absent', 'Global', False, 'invalid'),
    ('absent', 'Global', True, 'invalid')])
def test_admission(target, current, running, expected):
    assert profile_transition_kind(target, ('Global', 'gameA', 'gameB'), current, running) == expected


def test_decimal_custom_max_and_request_generation():
    assert effective_max([Decimal('144.125'), Decimal('30.25'), Decimal('59.99')]) == Decimal('144.125')
    assert profile_request_current(1, 2, 1, 2)
    assert not profile_request_current(1, 2, 3, 2)
    assert not profile_request_current(1, 2, 1, 3)
    with pytest.raises(ValueError):
        effective_max([])


@pytest.fixture
def app(tmp_path, fake_dpg, fake_lhm, stub_logger):
    from core.config_manager import ConfigManager
    from core.fps_utils import FPSUtils
    ns, _, _, _ = load_app()
    cm = ConfigManager(stub_logger, fake_dpg, ns['rtss'], None, NS(themes={}), str(tmp_path / 'src'))
    cm.load_preferences()
    cm.profiles_config.read_dict({
        'Global': {'capmethod': 'custom', 'maxcap': '120', 'customfpslimits': '60, 90, 120'},
        'gameA': {'capmethod': 'custom', 'maxcap': '40', 'customfpslimits': '20.5, 40.5, 144.125'},
        'gameB': {'capmethod': 'custom', 'maxcap': '15', 'customfpslimits': '5.25, 10.25, 15.25'}})
    fps = FPSUtils(cm, NS(), stub_logger, fake_dpg)
    cm.load_profile_raw('Global')
    cm.apply_current_input_values()
    queue = GuiQueue()
    ns.update(cm=cm, fps_utils=fps, dpg=fake_dpg, logger=stub_logger, _gui_submit=queue.submit)
    cm.profile_transition_hook = ns['_request_profile_transition']
    caps = {'Global': Decimal(90), 'gameA': Decimal('40.5'), 'gameB': Decimal('10.25')}
    events, rows = [], []
    def write(profile, cap):
        assert ns['session_lock'].locked()
        events.append(('write', profile, cap, cm.current_profile))
        caps[profile] = cap
        return True
    ns['rtss'].set_fractional_framerate = write
    ns['rtss'].get_framerate_limit = lambda profile, **kw: caps[profile]
    ns['cap_change_log'].record = rows.append
    ns['CurrentFPSOffset'] = -30
    ns['fps_values'] = [95]
    ns['gpu_values'] = [90]
    ns['cpu_values'] = [50]
    ns['fps_mean'] = 95
    raw = cm.load_profile_raw
    def load(name, **kw):
        events.append(('load', name))
        return raw(name, **kw)
    cm.load_profile_raw = load
    return ns, cm, fake_dpg, queue, caps, events, rows


def state(ns):
    return (ns['profile_revision'], ns['CurrentFPSOffset'], ns['fps_mean'],
            list(ns['fps_values']), list(ns['gpu_values']), list(ns['cpu_values']), ns['idle_state'])


@pytest.mark.parametrize('initial,target', [('Global', 'gameA'), ('gameA', 'Global'), ('gameA', 'gameB')])
def test_actual_running_handoff(app, initial, target):
    ns, cm, dpg, queue, caps, events, rows = app
    cm.load_profile_raw(initial)
    cm.apply_current_input_values()
    outgoing_max = effective_max(ns['fps_utils'].current_stepped_limits())
    events.clear()
    assert cm.load_profile_callback(None, target, None) is True
    incoming_max = effective_max(ns['fps_utils'].current_stepped_limits())
    assert events == [('write', initial, outgoing_max, initial), ('load', target),
                      ('write', target, incoming_max, initial)]
    assert caps[initial] == outgoing_max and caps[target] == incoming_max
    assert cm.current_profile == dpg.get_value('profile_dropdown') == target
    assert state(ns) == (1, 0, 0, [], [], [], False)
    assert [r[5] for r in rows] == ['profile_restore', 'profile_start']


@pytest.mark.parametrize('target', ['Global', 'missing', 'deleted'])
def test_same_or_invalid_is_inert(app, target):
    ns, cm, dpg, _, _, events, _ = app
    before = state(ns), dict(dpg.values), cm.current_profile
    assert cm.load_profile_callback(None, target, None) is (target == 'Global')
    assert (state(ns), dict(dpg.values), cm.current_profile) == before
    assert events == []


def test_stopped_selection_and_same_raw_reload(app):
    ns, cm, dpg, _, _, events, _ = app
    ns['running'] = False
    before = state(ns)
    assert cm.load_profile_callback(None, 'gameA', None) is True
    dpg.set_value('input_customfpslimits', '1,2')
    assert cm.load_profile_callback(None, 'gameA', None) is True
    assert dpg.get_value('input_customfpslimits') == '20.5, 40.5, 144.125'
    assert events == [('load', 'gameA'), ('load', 'gameA')]
    assert state(ns) == before


@pytest.mark.parametrize('failure', ['outgoing-false', 'outgoing-exception', 'load', 'apply', 'incoming-false', 'incoming-exception'])
def test_failed_handoff_does_not_publish_or_reset(app, failure):
    ns, cm, dpg, _, caps, events, rows = app
    before = state(ns), dict(dpg.values), cm.current_profile, cm.maxcap
    actual_write = ns['rtss'].set_fractional_framerate
    def write(profile, cap):
        if ((profile == 'Global' and cap == 120 and failure.startswith('outgoing'))
                or (profile == 'gameA' and failure.startswith('incoming'))):
            if failure.endswith('exception'):
                raise OSError('native failed')
            return False
        return actual_write(profile, cap)
    ns['rtss'].set_fractional_framerate = write
    if failure == 'load':
        cm.load_profile_raw = lambda *a, **kw: False
    if failure == 'apply':
        cm.apply_current_input_values = lambda: False
    assert cm.load_profile_callback(None, 'gameA', None) is False
    assert (state(ns), dict(dpg.values), cm.current_profile, cm.maxcap) == before
    assert caps['Global'] == 90
    assert not any(r[5] == 'profile_start' for r in rows)


@pytest.mark.parametrize('selected', [True, False])
def test_delete_zero_is_final_and_unselected_does_not_retarget(app, selected):
    ns, cm, dpg, _, caps, events, _ = app
    cm.load_profile_raw('gameA')
    cm.apply_current_input_values()
    events.clear()
    deleted = 'gameA' if selected else 'gameB'
    dpg.set_value('profile_dropdown', deleted)
    def zero(profile, key, cap, **kw):
        events.append(('zero', profile, key, cap))
        caps[profile] = cap
        return True
    cm.rtss.set_profile_property = zero
    cm.delete_selected_profile_callback()
    assert deleted not in cm.profiles_config
    assert caps[deleted] == 0 and events[-1] == ('zero', deleted, 'FramerateLimit', 0)
    if selected:
        assert events[:-1] == [('write', 'gameA', Decimal('144.125'), 'gameA'),
                              ('load', 'Global'), ('write', 'Global', Decimal(120), 'gameA')]
        assert cm.current_profile == 'Global' and ns['profile_revision'] == 1
    else:
        assert len(events) == 1 and cm.current_profile == 'gameA' and ns['profile_revision'] == 0


@pytest.mark.parametrize('route', ['initial', 'startup', 'tray', 'save', 'add', 'process-add'])
def test_selection_routes_use_actual_hook(app, route):
    ns, cm, dpg, _, _, events, _ = app
    if route == 'initial':
        cm.update_profile_dropdown(select_first=True)
        assert events == []  # Running same profile is inert.
        ns['running'] = False
        cm.update_profile_dropdown(select_first=True)
        assert events == [('load', 'Global')]
        return
    if route == 'startup':
        cm.profileonstartup = True
        cm.settings_config['GlobalSettings']['profileonstartup_name'] = 'gameA'
        cm.startup_profile_selection()
    elif route == 'tray':
        # Compile the actual tray route without importing pystray's native backend.
        tree = ast.parse((APP.parent / 'tray_functions.py').read_text())
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'TrayManager')
        fn = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == '_select_profile_from_tray')
        scope = {}
        exec(compile(ast.Module(body=[fn], type_ignores=[]), 'tray-route', 'exec'), scope)
        scope[fn.name](NS(cm=cm, _update_menu=lambda: None, update_hover_text=lambda: None), 'gameA')
    elif route == 'save':
        cm.save_profile('new')
    elif route == 'add':
        dpg.set_value('new_profile_input', 'new')
        cm.add_new_profile_callback()
    else:
        dpg.set_value('LastProcess', 'new')
        cm.add_process_profile_callback()
    target = 'gameA' if route in ('startup', 'tray') else 'new'
    assert cm.current_profile == target
    assert [e[0] for e in events] == ['write', 'load', 'write']
    assert ns['profile_revision'] == 1


def test_worker_request_is_deferred_and_stale_after_real_stop_start(app):
    ns, cm, dpg, queue, _, events, _ = app
    calls = len(dpg.calls)
    thread, errors = worker(lambda: cm.load_profile_callback(None, 'gameA', None))
    finish(thread, errors)
    assert not events and len(queue) == 1 and len(dpg.calls) == calls
    restart(ns)
    before = state(ns), list(events), cm.current_profile
    queue.drain()
    assert (state(ns), list(events), cm.current_profile) == before


def test_worker_request_runs_on_queue_owner(app):
    ns, cm, dpg, queue, _, events, _ = app
    calls = len(dpg.calls)
    thread, errors = worker(lambda: cm.load_profile_callback(None, 'gameA', None))
    finish(thread, errors)
    assert not events and len(dpg.calls) == calls
    queue.drain()
    assert cm.current_profile == 'gameA' and ns['profile_revision'] == 1
    assert all(c[3] == threading.current_thread().name for c in dpg.calls[calls:])


def test_deleted_queued_target_does_not_touch_caps(app):
    ns, cm, dpg, queue, _, events, _ = app
    thread, errors = worker(lambda: cm.load_profile_callback(None, 'gameA', None))
    finish(thread, errors)
    cm.profiles_config.remove_section('gameA')
    before = state(ns), dict(dpg.values)
    queue.drain()
    assert not events and (state(ns), dict(dpg.values)) == before


def test_fractional_wrapper_exposes_failed_native_property(rtss_stub):
    rtss_stub.set_profile_property = lambda *a, **kw: False
    assert rtss_stub.set_fractional_framerate('Global', Decimal('59.94')) is False


def test_gui_submit_captures_autopilot_load_generation(app):
    ns, cm, _, queue, _, events, _ = app
    tree = ast.parse(APP.read_text())
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_gui_submit')
    ns['gui_queue'] = queue
    exec(compile(ast.Module(body=[fn], type_ignores=[]), str(APP), 'exec'), ns)
    ns['_gui_submit'](cm.load_profile_callback, None, 'gameA', None)
    restart(ns)
    before = state(ns), list(events), cm.current_profile
    queue.drain()
    assert (state(ns), list(events), cm.current_profile) == before


def test_failed_selected_delete_preserves_section_and_never_zeroes(app):
    ns, cm, dpg, _, _, events, _ = app
    cm.load_profile_raw('gameA')
    cm.apply_current_input_values()
    events.clear()
    ns['rtss'].set_fractional_framerate = lambda *args: False
    cm.rtss.set_profile_property = lambda *args, **kw: pytest.fail('failed handoff must not delete/reset')
    before = state(ns), dict(dpg.values)
    cm.delete_selected_profile_callback()
    assert 'gameA' in cm.profiles_config and cm.current_profile == 'gameA'
    assert (state(ns), dict(dpg.values)) == before
    assert not events


def test_refresh_exception_does_not_publish_handoff(app):
    ns, cm, dpg, _, caps, _, _ = app
    before = state(ns), dict(dpg.values), cm.current_profile
    def fail():
        raise RuntimeError('UI apply failed')
    cm.refresh_ui_callbacks = fail
    assert cm.load_profile_callback(None, 'gameA', None) is False
    assert (state(ns), dict(dpg.values), cm.current_profile) == before
    assert caps['Global'] == 90


def test_revision_changes_only_after_incoming_native_write(app):
    ns, cm, _, _, _, _, _ = app
    before = state(ns)
    original = ns['rtss'].set_fractional_framerate
    def write(profile, cap):
        assert state(ns) == before
        assert cm.current_profile == 'Global'
        return original(profile, cap)
    ns['rtss'].set_fractional_framerate = write
    assert cm.load_profile_callback(None, 'gameA', None) is True
    assert state(ns) == (1, 0, 0, [], [], [], False)


def test_actual_autopilot_startup_load_is_deferred_and_validated(app):
    from core.autopilot import autopilot_on_check
    ns, cm, dpg, queue, _, events, _ = app
    tree = ast.parse(APP.read_text())
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_gui_submit')
    ns['gui_queue'] = queue
    exec(compile(ast.Module(body=[fn], type_ignores=[]), str(APP), 'exec'), ns)
    rtss_manager = NS(is_rtss_running=lambda: True,
                      get_fps_for_active_window=lambda: (Decimal(60), 'gameA'))
    cm.autopilot_only_profiles = False
    calls = len(dpg.calls)
    autopilot_on_check(cm, rtss_manager, dpg, ns['logger'], True,
                       ns['start_stop_callback'], gui_submit=ns['_gui_submit'],
                       foreground_reader=lambda: 'gameA')
    assert not events and len(dpg.calls) == calls and len(queue) == 1
    queue.drain()
    assert [e[0] for e in events] == ['write', 'load', 'write']
    assert cm.current_profile == 'gameA' and ns['profile_revision'] == 1


def test_unselected_delete_keeps_active_profile_label(app):
    ns, cm, dpg, _, caps, _, _ = app
    cm.load_profile_raw('gameA')
    cm.apply_current_input_values()
    dpg.set_value('profile_dropdown', 'gameB')
    cm.rtss.set_profile_property = lambda *args, **kwargs: True
    cm.delete_selected_profile_callback()
    assert cm.current_profile == dpg.get_value('profile_dropdown') == 'gameA'
    assert dpg.get_value('game_name') == 'gameA'


def test_render_owner_callback_failure_keeps_later_jobs_and_frames(app, tmp_path, caplog):
    import logging
    ns, cm, dpg, queue, _, _, _ = app
    # Real profile-save callback fails at its persistence boundary (e.g. unavailable disk).
    cm.profiles_path = str(tmp_path)
    callback_jobs = [[lambda: cm.save_profile('new')], [lambda: events.append('later-callback')]]
    events = []
    frames = []
    dpg.is_dearpygui_running = lambda: len(frames) < 2
    dpg.render_dearpygui_frame = lambda: frames.append(None)
    dpg.get_callback_queue = lambda: callback_jobs if len(frames) == 1 else None
    def run_callbacks(jobs):
        for job in jobs or []:
            job[0](*job[1:])
    dpg.run_callbacks = run_callbacks
    queue.submit(events.append, 'queued')
    ns.update(logging=logging, gui_queue=queue, _acceptance_runtime=None, _instance_lease=None)
    tree = ast.parse(APP.read_text())
    loop = next(n for n in tree.body if isinstance(n, ast.While)
                and isinstance(n.test, ast.Call)
                and isinstance(n.test.func, ast.Attribute)
                and n.test.func.attr == 'is_dearpygui_running')
    with caplog.at_level(logging.ERROR):
        exec(compile(ast.Module(body=[loop], type_ignores=[]), str(APP), 'exec'), ns)
    assert len(frames) == 2
    assert events == ['later-callback', 'queued']
    assert any(record.exc_info for record in caplog.records)


def test_render_owner_activation_failure_keeps_callbacks_queue_and_frames(app, caplog):
    import logging
    ns, _, dpg, queue, _, _, _ = app
    events = []
    frames = []
    polls = []
    def poll(tray):
        polls.append(threading.get_ident())
        raise RuntimeError('activation failure')
    dpg.is_dearpygui_running = lambda: len(frames) < 2
    dpg.render_dearpygui_frame = lambda: frames.append(None)
    dpg.get_callback_queue = lambda: [[lambda: events.append('callback')]]
    dpg.run_callbacks = lambda jobs: jobs[0][0]()
    queue.submit(events.append, 'queued')
    ns.update(logging=logging, gui_queue=queue, _acceptance_runtime=None,
              _instance_lease=NS(poll_activation=poll))
    loop = next(n for n in ast.parse(APP.read_text()).body if isinstance(n, ast.While)
                and ast.unparse(n.test) == 'dpg.is_dearpygui_running()')
    with caplog.at_level(logging.ERROR):
        exec(compile(ast.Module(body=[loop], type_ignores=[]), str(APP), 'exec'), ns)
    assert len(frames) == 2 and polls == [threading.get_ident()] * 2
    assert events == ['callback', 'queued', 'callback']
    assert len(caplog.records) == 2
    assert all(r.message == 'Instance activation dispatch failed' and r.exc_info
               for r in caplog.records)
