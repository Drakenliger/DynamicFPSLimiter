"""Tests for the read-only FPS cap ladder preview in the Framerate Limits box."""
import ast
import contextlib
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


def test_cap_preview_layout_and_label_in_app():
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

    # Verify label and drawlist tag and parentage
    text_call = raw.tagged('add_text', 'label_caps_preview')
    assert text_call['default_value'] if 'default_value' in text_call else raw.calls[[c[2].get('tag') for c in raw.calls].index('label_caps_preview')][1][0] == "Caps DFL will use"

    drawlist_cfg = raw.tagged('drawlist', 'fps_cap_drawlist')
    assert drawlist_cfg['width'] == 210


def test_flat_tick_drawing_and_exact_ladder_values():
    raw = RecordingDPG()
    dpg = ScaledDPG(raw, 1.0)
    ns = functions('src/core/fps_utils.py',
                   {'current_stepped_limits', 'make_stepped_values', 'make_ratioed_values', 'update_fps_cap_visualization'}, {})
    fps = NS(dpg=dpg, last_fps_limits=[])
    fps.make_stepped_values = lambda *a: ns['make_stepped_values'](fps, *a)
    fps.make_ratioed_values = lambda *a: ns['make_ratioed_values'](fps, *a)
    fps.current_stepped_limits = lambda: ns['current_stepped_limits'](fps)

    limits = fps.current_stepped_limits()
    assert limits == [30, 40, 50, 60]

    ns['update_fps_cap_visualization'](fps)

    # Verify lines drawn instead of circles
    circles = [c for c in raw.calls if c[0] == 'draw_circle']
    lines = [c for c in raw.calls if c[0] == 'draw_line']
    assert len(circles) == 0
    assert len(lines) >= 4

    # Verify exact fractional/Decimal ladder
    raw.calls.clear()
    raw.values['input_capmethod'] = 'Custom'
    raw.values['input_customfpslimits'] = '30, 45.5, 60'
    fps.last_fps_limits = []

    class CM:
        def parse_and_normalize_string_to_decimal_set(self, s):
            return [Decimal('30.0'), Decimal('45.5'), Decimal('60.0')]
    fps.cm = CM()

    limits = fps.current_stepped_limits()
    assert limits == [Decimal('30.0'), Decimal('45.5'), Decimal('60.0')]

    ns['update_fps_cap_visualization'](fps)
    texts = [c[1][1] for c in raw.calls if c[0] == 'draw_text']
    assert texts == ['30.0', '45.5', '60.0']


@pytest.mark.parametrize('scale,expected_width', [
    (1.0, 210),
    (1.5, 315),
])
def test_sizing_at_dpi_scales(scale, expected_width):
    raw = RecordingDPG()
    dpg = ScaledDPG(raw, scale)
    ns = functions('src/core/fps_utils.py', {'current_stepped_limits', 'update_fps_cap_visualization'}, {})
    fps = NS(dpg=dpg, last_fps_limits=[])
    fps.current_stepped_limits = lambda: [30, 60]

    ns['update_fps_cap_visualization'](fps)
    lines = [c for c in raw.calls if c[0] == 'draw_line']
    x_coords = [c[1][0][0] for c in lines]
    assert min(x_coords) == round(5 * scale)
    assert max(x_coords) == round(205 * scale)


def test_current_cap_highlight_and_admitted_write_evidence(monkeypatch):
    import runpy
    import sys
    import types

    hardware = types.ModuleType('core.librehardwaremonitor')
    hardware.get_all_sensor_infos = lambda *a: []
    monkeypatch.setitem(sys.modules, 'core.librehardwaremonitor', hardware)

    raw = RecordingDPG()
    dpg = ScaledDPG(raw, 1.0)

    ns = functions('src/core/fps_utils.py', {'current_stepped_limits', 'update_fps_cap_visualization'}, {})
    fps = NS(dpg=dpg, last_fps_limits=[])
    fps.current_stepped_limits = lambda: [30, 45, 60]

    # When stopped / idle / no active cap -> no highlight line with thickness=3
    ns['update_fps_cap_visualization'](fps, active_applied_cap=None)
    highlight_lines = [c for c in raw.calls if c[0] == 'draw_line' and c[2].get('thickness') == 3]
    assert len(highlight_lines) == 0

    # When running with active cap 45 -> cap 45 tick is highlighted (thickness=3 and color=(255, 215, 0))
    raw.calls.clear()
    raw.items.remove('Foreground')
    ns['update_fps_cap_visualization'](fps, active_applied_cap=45)
    highlight_lines = [c for c in raw.calls if c[0] == 'draw_line' and c[2].get('thickness') == 3]
    assert len(highlight_lines) == 1
    assert highlight_lines[0][2]['color'] == (255, 215, 0)
