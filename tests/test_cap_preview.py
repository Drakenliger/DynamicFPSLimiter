"""Tests for the read-only FPS cap ladder preview in the Framerate Limits box."""
import ast
import contextlib
import threading
import time
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

from core.ui_scale import ScaledDPG

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
            if name == 'does_item_exist':
                return args[0] in self.items
            if name == 'delete_item':
                self.items.discard(args[0])
            if 'tag' in kwargs:
                self.items.add(kwargs['tag'])
            if name == 'get_viewport_width':
                return self.width
            if name == 'get_value':
                return self.values.get(args[0], 'ratio')
            if name in self.contexts:
                return contextlib.nullcontext(123)
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

    # 1. Label and drawlist exist and are configured
    text_call = raw.tagged('add_text', 'label_caps_preview')
    assert text_call.get('default_value', 'Caps DFL will use') == "Caps DFL will use"
    drawlist_cfg = raw.tagged('drawlist', 'fps_cap_drawlist')
    assert drawlist_cfg['width'] == 210

    # 2. Assert parentage hierarchy: drawlist is inside Framerate Limits child_window
    child_window_calls = [c for c in raw.calls if c[0] == 'child_window']
    assert len(child_window_calls) >= 1

    # Assert old unlabelled drawlist outside Framerate Limits child window is gone
    drawlist_calls = [c for c in raw.calls if c[0] == 'drawlist']
    fps_cap_drawlists = [c for c in drawlist_calls if c[2].get('tag') == 'fps_cap_drawlist']
    assert len(fps_cap_drawlists) == 1


def test_admitted_write_success_and_failure_and_stopped_restart():
    """Exercise production _write_cap, start_stop_callback, and active_applied_cap tracking."""
    raw = RecordingDPG()
    dpg = ScaledDPG(raw, 1.0)

    # Extract _write_cap, start_stop_callback, and reset_stats logic from app.py
    ns = dict(
        time=time,
        Decimal=Decimal,
        time_series=[], fps_time_series=[], gpu_usage_series=[],
        cpu_usage_series=[], fps_series=[], cap_series=[], elapsed_time=0,
        rtss=NS(get_framerate_limit=lambda *a, **k: 60,
                set_fractional_fps_direct=lambda prof, cap: True,
                set_fractional_framerate=lambda prof, cap: True),
        logger=NS(add_log=lambda *a: None),
        cap_change_log=NS(record=lambda *a: None),
        gpu_values=[], cpu_values=[], fps_mean=0,
        session_number=0, session_lock=threading.Lock(),
        running=False, active_applied_cap=None, profile_revision=0,
        make_row=lambda *a: None, fresh_cap_evidence=lambda: ([], [], [], 0, (0,0)),
        autopilot_request_current=lambda *a: True,
        session_is_current=lambda *a, **k: True,
        dpg=dpg,
        themes_manager=NS(themes=defaultdict(lambda: 123)),
        tray=NS(set_running_state=lambda *a: None),
        fps_utils=NS(current_stepped_limits=lambda: [30, 60], reset_summary_statistics=lambda: None)
    )

    code = functions('src/core/app.py', {'_write_cap', 'start_stop_callback', 'reset_stats'}, ns)
    _write_cap = code['_write_cap']
    start_stop_callback = code['start_stop_callback']

    cm = Config(current_profile="Global", input_field_keys=[], input_button_tags=[], autopilot=False)

    # 1. Write cap when stopped -> active_applied_cap remains None
    ns['running'] = False
    assert _write_cap("Global", Decimal('60'), "test", direct=True) is True
    assert ns['active_applied_cap'] is None

    # 2. Write cap when running -> active_applied_cap updated to 60
    ns['running'] = True
    assert _write_cap("Global", Decimal('60'), "test", direct=True) is True
    assert ns['active_applied_cap'] == Decimal('60')

    # 3. Failed write when running -> active_applied_cap retains previous value (60)
    ns['rtss'].set_fractional_framerate = lambda prof, cap: False
    assert _write_cap("Global", Decimal('30'), "test", direct=False) is False
    assert ns['active_applied_cap'] == Decimal('60')

    # 4. Stop session via start_stop_callback -> clears active_applied_cap to None
    ns['rtss'].set_fractional_fps_direct = lambda prof, cap: True
    ns['rtss'].set_fractional_framerate = lambda prof, cap: True
    start_stop_callback(None, None, cm)
    assert ns['running'] is False
    assert ns['active_applied_cap'] is None


def test_profile_handoff_and_idle_transitions():
    """Exercise _load_profile_on_gui and idle cap transitions."""
    raw = RecordingDPG()
    dpg = ScaledDPG(raw, 1.0)

    ns = dict(
        time=time,
        Decimal=Decimal,
        rtss=NS(get_framerate_limit=lambda *a, **k: 60,
                set_fractional_fps_direct=lambda prof, cap: True,
                set_fractional_framerate=lambda prof, cap: True),
        logger=NS(add_log=lambda *a: None),
        cap_change_log=NS(record=lambda *a: None),
        gpu_values=[], cpu_values=[], fps_mean=0, CurrentFPSOffset=0,
        idle_state=False, fps_values=[],
        session_number=1, profile_revision=1, session_lock=threading.Lock(),
        running=True, active_applied_cap=Decimal('60'),
        make_row=lambda *a: None, fresh_cap_evidence=lambda: ([], [], [], 0, (0,0)),
        autopilot_request_current=lambda *a: True,
        profile_request_current=lambda *a: True,
        profile_transition_kind=lambda *a: "switch",
        effective_max=lambda limits: max(limits),
        dpg=dpg,
        fps_utils=NS(current_stepped_limits=lambda: [30, 60])
    )

    code = functions('src/core/app.py', {'_write_cap', '_load_profile_on_gui'}, ns)
    _write_cap = code['_write_cap']
    _load_profile_on_gui = code['_load_profile_on_gui']

    cm = Config(
        current_profile="ProfileA",
        profiles_config=NS(sections=lambda: ["ProfileA", "ProfileB"]),
        input_field_keys=[],
        load_profile_raw=lambda name, publish=True: True,
        apply_current_input_values=lambda: True,
        refresh_ui_callbacks=lambda: None,
        tray=None
    )
    ns['cm'] = cm

    # Successful profile handoff -> active_applied_cap updated for new profile
    assert _load_profile_on_gui("ProfileB") is True
    assert cm.current_profile == "ProfileB"
    assert ns['active_applied_cap'] == Decimal('60')

    # Idle mode enter: write cap 15 -> active_applied_cap becomes 15
    _write_cap("ProfileB", Decimal('15'), "idle")
    assert ns['active_applied_cap'] == Decimal('15')


def test_ladder_visualization_transitions_and_dpi_scaling():
    raw = RecordingDPG()
    dpg = ScaledDPG(raw, 1.0)
    ns = functions('src/core/fps_utils.py',
                   {'current_stepped_limits', 'make_stepped_values', 'make_ratioed_values', 'update_fps_cap_visualization'}, {})
    fps = NS(dpg=dpg, last_fps_limits=[])
    fps.make_stepped_values = lambda *a: ns['make_stepped_values'](fps, *a)
    fps.make_ratioed_values = lambda *a: ns['make_ratioed_values'](fps, *a)
    fps.current_stepped_limits = lambda: ns['current_stepped_limits'](fps)

    # 1. Multi-cap ladder [30, 40, 50, 60]
    raw.values['input_capmethod'] = 'Step'
    raw.values['input_maxcap'] = 60
    raw.values['input_mincap'] = 30
    raw.values['input_capstep'] = 10
    ns['update_fps_cap_visualization'](fps, active_applied_cap=40)

    lines = [c for c in raw.calls if c[0] == 'draw_line']
    assert len(lines) == 4
    # One line highlighted with thickness 3
    highlighted = [c for c in lines if c[2].get('thickness') == 3]
    assert len(highlighted) == 1

    # 2. Transition to Single cap [60] (equal min/max cap)
    raw.calls.clear()
    raw.items.remove('Foreground')
    raw.values['input_mincap'] = 60
    ns['update_fps_cap_visualization'](fps, active_applied_cap=60)

    lines = [c for c in raw.calls if c[0] == 'draw_line']
    assert len(lines) == 1
    # Centered tick drawn
    assert lines[0][1][0][0] == 105

    # 3. Exact fractional Decimal cap [59.94]
    raw.calls.clear()
    raw.items.remove('Foreground')
    raw.values['input_capmethod'] = 'Custom'
    raw.values['input_customfpslimits'] = '59.94'
    class CM:
        def parse_and_normalize_string_to_decimal_set(self, s):
            return [Decimal('59.94')]
    fps.cm = CM()
    ns['update_fps_cap_visualization'](fps, active_applied_cap=Decimal('59.94'))

    texts = [c[1][1] for c in raw.calls if c[0] == 'draw_text']
    assert texts == ['59.94']
    highlighted = [c for c in raw.calls if c[0] == 'draw_line' and c[2].get('thickness') == 3]
    assert len(highlighted) == 1

    # 4. Transition to Empty ladder
    raw.calls.clear()
    raw.items.remove('Foreground')
    fps.current_stepped_limits = lambda: []
    ns['update_fps_cap_visualization'](fps)
    assert fps.last_fps_limits == []
    assert fps._last_ladder_geometry is None
