"""Actual button registration/lifecycle with FakeDPG and no native workers/RTSS.

The dispatcher below transcribes only DearPyGui 2.0.0's pure-Python
run_callbacks helper. It deliberately counts defaulted parameters too; it is
not FakeDPG's permissive fallback and does not import DearPyGui's native module.
"""
import ast
from contextlib import nullcontext
from decimal import Decimal
import inspect
import threading

from core.gui_queue import GuiQueue
from test_app_session import APP, load_app


def run_callbacks(jobs):
    """ New in 1.2. Runs callbacks from the callback queue and checks arguments. """

    if jobs is None:
        pass
    else:
        for job in jobs:
            if job[0] is None:
                pass
            else:
                sig = inspect.signature(job[0])
                args = []
                for arg in range(len(sig.parameters)):
                    args.append(job[arg+1])
                job[0](*args)


def registered_start_button(fake_dpg, monkeypatch):
    # Existing helper compiles the actual lifecycle and _write_cap functions;
    # its Thread/RTSS stubs record calls without starting native/background work.
    ns, writes, submitted, spawned = load_app()
    ns.update(dpg=fake_dpg, running=False, session_number=0)
    noop = lambda *a, **kw: None
    for name in ('load_profile_callback', 'delete_selected_profile_callback',
                 'add_new_profile_callback', 'add_process_profile_callback'):
        setattr(ns['cm'], name, noop)
    ns['autopilot_checkbox_callback'] = noop  # Unrelated checkbox is not clicked.
    ns['themes_manager'].themes.update(no_padding_theme=3, transparent_input_theme_2=4)
    ns['themes_manager'].bind_font_to_item = noop

    # FakeDPG records these APIs but does not model their context managers.
    def context_api(name):
        def context(*args, **kwargs):
            fake_dpg._record(name, args, kwargs)
            return nullcontext()
        return context

    for name in ('child_window', 'group', 'table', 'table_row'):
        monkeypatch.setattr(fake_dpg, name, context_api(name))

    tree = ast.parse(APP.read_text())
    selected = ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef)
                               and n.name in {'build_profile_section', 'reset_stats'}],
                          type_ignores=[])
    exec(compile(selected, str(APP), 'exec'), ns)
    ns['build_profile_section']()
    buttons = [kwargs for name, args, kwargs, thread in fake_dpg.calls
               if name == 'add_button' and kwargs.get('tag') == 'start_stop_button']
    assert len(buttons) == 1
    button = buttons[0]
    assert button['label'] == 'Start'
    assert button['user_data'] is ns['cm']
    return ns, writes, submitted, spawned, button


def test_registered_button_dispatches_start_then_stop(fake_dpg, monkeypatch):
    ns, writes, submitted, spawned, button = registered_start_button(fake_dpg, monkeypatch)
    tray_states, sensor_starts, applied, rows = [], [], [], []
    ns['tray'].set_running_state = tray_states.append
    ns['lhm_sensor'].start = lambda: sensor_starts.append(ns['session_number'])
    ns['cm'].apply_current_input_values = lambda: applied.append(ns['session_number'])
    ns['cap_change_log'].record = rows.append
    ns['rtss'].get_framerate_limit = lambda *a, **kw: Decimal(60)

    # The ordinary native job has only sender/app_data/user_data after callback.
    # No fourth slot is supplied for the internal expected_autopilot argument.
    job = (button['callback'], 'start_stop_button', None, button['user_data'])
    for session, running, label, reason in ((1, True, 'Stop', 'start'),
                                            (2, False, 'Start', 'stop')):
        ns.update(fps_values=[80], gpu_values=[90], cpu_values=[70],
                  fps_mean=80, CurrentFPSOffset=-30, idle_state=True)
        run_callbacks([job])
        assert (ns['session_number'], ns['running']) == (session, running)
        labels = [kwargs['label'] for name, args, kwargs, thread in fake_dpg.calls
                  if name == 'configure_item' and args == ('start_stop_button',)
                  and 'label' in kwargs]
        assert labels == (['Stop'] if running else ['Stop', 'Start'])
        assert labels[-1] == label
        assert tray_states == ([True] if running else [True, False])
        assert applied == list(range(1, session + 1))
        assert sensor_starts == [1]
        assert [(s['target'], s['args'], s['daemon']) for s in spawned] == [
            (ns['monitoring_loop'], (1,), True), (ns['plotting_loop'], (1,), True)]
        assert [w[1:] for w in writes[-2:]] == [
            (('Global', Decimal(90)), session), (('Global', Decimal(90)), session)]
        assert [row[5] for row in rows[-2:]] == [reason, reason + '_refresh']
        assert (ns['fps_values'], ns['gpu_values'], ns['cpu_values'],
                ns['fps_mean'], ns['CurrentFPSOffset'], ns['idle_state']) == (
                    [], [], [], 0, 0, False)
    assert len(writes) == 4
    assert [row[1] for row in rows] == ['1', '1', '2', '2']
    assert not submitted
    assert all(thread == threading.current_thread().name
               for name, args, kwargs, thread in fake_dpg.calls)


def test_internal_callback_keeps_freshness_token_after_gui_retirement(fake_dpg, monkeypatch):
    ns, writes, submitted, spawned, button = registered_start_button(fake_dpg, monkeypatch)
    cm = ns['cm']
    cm.autopilot = cm.autopilot_only_profiles = True
    expected = (0, ns['profile_revision'], False, True, 'Global')
    errors = []
    queue = GuiQueue(on_error=lambda fn, exc: errors.append(exc))
    # Internal/autopilot jobs still take the fourth argument through GuiQueue.
    queue.submit(ns['start_stop_callback'], None, None, cm, expected)
    assert not writes and len(queue) == 1

    # Retire that request with real Start/Stop transitions from the registered
    # GUI callback; restore autopilot before drain to isolate session freshness.
    cm.autopilot = False
    job = (button['callback'], 'start_stop_button', None, button['user_data'])
    run_callbacks([job])
    run_callbacks([job])
    cm.autopilot = True
    before = (ns['session_number'], ns['running'], list(writes), list(fake_dpg.calls))
    queue.drain()
    assert not errors and len(queue) == 0
    assert (ns['session_number'], ns['running'], writes, fake_dpg.calls) == before

    # A current token is still admitted; the ordinary three-argument call used
    # by tray/checkbox callers still stops the same production lifecycle.
    current = (2, ns['profile_revision'], False, True, 'Global')
    ns['start_stop_callback'](None, None, cm, current)
    assert ns['running'] and ns['session_number'] == 3 and len(writes) == 6
    ns['start_stop_callback'](None, None, cm)
    assert not ns['running'] and ns['session_number'] == 4 and len(writes) == 8
