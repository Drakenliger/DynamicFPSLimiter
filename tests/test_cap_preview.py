"""Read-only cap preview: layout calls/geometry, not native visual acceptance."""
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
        self.configurations = {}
        self.component_types = {}
        self.live_draws = {}
        self.call_threads = []
        self.next_id = 0
        self.width = 610
        self.font_height = 18
        self.metric_scale = 1
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
                    self.configurations.pop(item, None)
                    self.live_draws.pop(item, None)
                return
            if name == 'get_item_configuration':
                return self.configurations[args[0]]
            if name == 'configure_item':
                self.configurations.setdefault(args[0], {}).update(kwargs)
                return
            if name == 'get_text_size':
                # Proportional numeric advances, a narrow decimal point, and a
                # physical font height. No full-em-per-character approximation.
                width = sum(8 if c.isdigit() or c.isupper() else 4 if c in '. :,' else 6.7 for c in args[0])
                return (width * self.metric_scale, self.font_height * self.metric_scale)
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
                self.configurations[item] = dict(kwargs)
                self.parents[item] = kwargs.get('parent', self.stack[-1][1] if self.stack else None)
                if name == 'theme_component':
                    self.component_types[item] = args[0]
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


@pytest.mark.parametrize('dpi', [96, 120, 144, 168, 192, 240, 288])
def test_ui_construction_parent_stack_and_no_old_drawlist(dpi, monkeypatch):
    from core.themes import ThemesManager
    monkeypatch.setenv('WINDIR', '/windows')
    raw = RecordingDPG()
    dpg = ScaledDPG(raw, dpi / 96)
    raw.metric_scale = dpg.scale
    themes = ThemesManager('/app', dpg)
    themes.create_themes()
    themes.create_fonts()
    raw.metric_scale = round(18 * dpg.scale) / 18
    tree = ast.parse((ROOT / 'src/core/app.py').read_text())

    main_window = next(n for n in tree.body if isinstance(n, ast.With)
                       and isinstance(n.items[0].context_expr, ast.Call)
                       and any(k.arg == 'tag' and isinstance(k.value, ast.Constant)
                               and k.value.value == 'Primary Window' for k in n.items[0].context_expr.keywords))

    noop = lambda *a, **kw: None
    # Typed Global profile defaults from ConfigManager, shared by the controls
    # and plot attributes. Missing data must raise rather than become a callback.
    settings = dict(maxcap=114, mincap=40, capratio=10, capstep=5,
                    gpucutofffordecrease=85, gpucutoffforincrease=70,
                    cpucutofffordecrease=105, cpucutoffforincrease=101,
                    delaybeforedecrease=2, delaybeforeincrease=10,
                    capmethod='ratio', customfpslimits='30.01, 45.00, 59.99',
                    monitoring_method='LibreHM')
    # Construction registers these callbacks without invoking them.
    cm = NS(settings=settings, **settings, sensor_infos=[],
            autopilot=False, hide_unselected=False,
            load_profile_callback=noop, delete_selected_profile_callback=noop,
            add_new_profile_callback=noop, add_process_profile_callback=noop,
            monitoring_method_callback=noop, current_method_callback=noop,
            sort_customfpslimits_callback=noop, quick_save_settings=noop,
            quick_load_settings=noop, reset_to_program_default=noop,
            save_to_profile=noop, hide_unselected_callback=noop)
    ns = dict(dpg=dpg, cm=cm,
              themes_manager=themes, bold_font=themes.fonts['bold_font'], app_title='Test',
              display_version=lambda: '1.0', textures=defaultdict(lambda: 'raw'),
              tray=NS(minimize_to_tray=noop, drag_viewport=noop, on_mouse_release=noop, on_mouse_click=noop),
              exit_gui=noop, start_stop_callback=noop, toggle_luid_selection=noop,
              autopilot_checkbox_callback=noop,
              fps_utils=NS(reset_custom_limits=noop, copy_from_plot=noop), Viewport_width=610)

    functions('src/core/app.py', {'build_profile_section', 'build_plot_window'}, ns)
    exec(compile(ast.Module(body=[main_window], type_ignores=[]), 'app.py', 'exec'), ns)

    text_call = next(c for c in raw.calls if c[0] == 'add_text' and c[2].get('tag') == 'label_caps_preview')
    assert (text_call[1][0] if text_call[1] else text_call[2]['default_value']) == "Caps DFL will use"
    drawlist_cfg = raw.tagged('drawlist', 'fps_cap_drawlist')
    assert drawlist_cfg['width'] == round(590 * dpg.scale)
    assert drawlist_cfg['height'] == round(60 * dpg.scale)
    for tag in ('label_caps_preview', 'fps_cap_drawlist'):
        record = next(c for c in raw.ancestry if c[2].get('tag') == tag)
        assert not any(parent[0] == 'child_window' for parent in record[3])
        assert raw.parents[tag] == 'caps_preview_strip'
    primary = raw.tagged('window', 'Primary Window')
    assert primary['no_scrollbar'] and primary['no_scroll_with_mouse']
    columns = raw.tagged('group', 'limits_and_monitoring')
    strip = raw.tagged('group', 'caps_preview_strip')
    assert 'pos' not in columns and 'pos' not in strip  # Native flow prevents collisions.
    assert raw.calls.index(('group', (), columns)) < raw.calls.index(('group', (), strip))
    assert raw.parents['caps_preview_strip'] == 'Primary Window'

    # Budget the actual AST's emitted outer sizes against its actual viewport.
    # Use loaded font sizes and emitted theme spacing (physical units), including
    # table cell padding, rather than the failed attempt's absolute coordinates.
    viewport_nodes = [n for n in tree.body if isinstance(n, ast.Expr)
                      and isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Attribute)
                      and n.value.func.attr == 'create_viewport']
    ns.update(Viewport_height=700, viewport_x_pos=0, viewport_y_pos=0)
    exec(compile(ast.Module(body=viewport_nodes, type_ignores=[]), 'app.py', 'exec'), ns)
    viewport = next(k for n, a, k in raw.calls if n == 'create_viewport')
    styles = {}
    for n, a, k, parents in raw.ancestry:
        if n == 'add_theme_style' and any(p[1] == themes.themes['main_theme'] for p in parents):
            styles.setdefault(a[0], a[1:])
    padding_x, padding_y = styles['mvStyleVar_WindowPadding']
    spacing = styles['mvStyleVar_ItemSpacing'][1]
    font = next(a[1] for n, a, k in raw.calls if n == 'add_font')
    profile = next(k for n, a, k in raw.calls if n == 'child_window' and k.get('height') == round(140 * dpg.scale))
    method_row = font + 2 * styles['mvStyleVar_FramePadding'][1] + 2 * styles['mvStyleVar_CellPadding'][1]
    column_height = max(raw.tagged('child_window', 'legacy_childwindow')['height'],
                        raw.tagged('child_window', 'LHwM_childwindow')['height'],
                        raw.tagged('child_window', 'limits_childwindow')['height'] +
                        raw.tagged('child_window', 'limit_actions_childwindow')['height'] +
                        round(dpg.scale) + 2 * spacing)
    # Title, spacer, real profile section, two method rows, spacer, columns,
    # preview heading and drawlist: seven inter-item gaps plus the heading gap.
    total_height = (2 * padding_y + max(font, round(20 * dpg.scale)) + round(5 * dpg.scale)
                    + profile['height'] + 2 * method_row + round(dpg.scale) + column_height
                    + font + drawlist_cfg['height'] + 8 * spacing)
    assert total_height <= viewport['height']
    assert drawlist_cfg['width'] + 2 * padding_x <= viewport['width'] + 1
    assert raw.tagged('plot', 'plot')['height'] == round(190 * dpg.scale)
    table = raw.tagged('table', 'limits_table')
    assert table['width'] == -1 and table['policy'] == raw.mvTable_SizingStretchProp
    table_records = [c for c in raw.ancestry if any(p[1] == 'limits_table' for p in c[3])]
    columns_cfg = [k for n, a, k, parents in table_records if n == 'add_table_column']
    assert columns_cfg == [dict(width_fixed=True), dict(width_stretch=True, init_width_or_weight=1)]
    inputs = [k for n, a, k, parents in table_records if n == 'add_input_int']
    assert len(inputs) == 6 and all(k['width'] == -1 and k['step'] == 1 and k['step_fast'] == 10 for k in inputs)
    label_width = max(raw.get_text_size(a[0])[0] for n, a, k, parents in table_records if n == 'add_text')
    available = (raw.tagged('child_window', 'limits_childwindow')['width'] - 2 * padding_x
                 - styles['mvStyleVar_ScrollbarSize'][0] - round(dpg.scale)
                 - 4 * styles['mvStyleVar_CellPadding'][0] - label_width)
    # InputInt subtracts two square frame-height buttons and two inner gaps
    # from this total width. Even with the child scrollbar, both buttons and
    # a text field fit; the native text editor handles long numeric values.
    internals = 2 * (font + 2 * styles['mvStyleVar_FramePadding'][1]) + 2 * styles['mvStyleVar_ItemInnerSpacing'][0]
    assert available > internals + 2 * styles['mvStyleVar_FramePadding'][0]
    for tag in ('input_delaybeforedecrease', 'input_delaybeforeincrease'):
        cfg = raw.tagged('add_input_int', tag)
        assert cfg['min_clamped'] and cfg['max_clamped'] and cfg['max_value'] == 99
    # Editing/reset/copy, profile/Start, settings and save actions still exist.
    for tag in ('input_customfpslimits', 'rest_fps_cap_button', 'autofill_fps_caps',
                'profile_dropdown', 'start_stop_button', 'show_settings_button',
                'quick_save', 'quick_load', 'Reset_Default', 'SaveToProfile'):
        assert tag in raw.items
    assert raw.stack == []

    drawlist_calls = [c for c in raw.calls if c[0] == 'drawlist']
    fps_cap_drawlists = [c for c in drawlist_calls if c[2].get('tag') == 'fps_cap_drawlist']
    assert len(fps_cap_drawlists) == 1

    fps = FPSUtils.__new__(FPSUtils)
    fps.dpg, fps.last_fps_limits, fps.logger = dpg, [], None
    fps.cm = NS(parse_and_normalize_string_to_decimal_set=lambda text: sorted({Decimal(v) for v in text.split(',')}))
    raw.values.update(input_capmethod='Custom', input_customfpslimits='24,36,48,60,72,90,120,144')
    fps.update_fps_cap_visualization(active_applied_cap=144)
    assert_label_bounds(raw)
    texts = [c for c in raw.live_draws.values() if c[0] == 'draw_text']
    assert [c[1][1] for c in texts] == ['24', '36', '48', '60', '72', '90', '120', '144']
    assert texts[-1][2]['color'] == (255, 215, 0)


def assert_label_bounds(raw):
    """Independent measured glyph envelopes, with one physical-pixel rounding slack."""
    cfg = raw.configurations['fps_cap_drawlist']
    texts = [c for c in raw.live_draws.values() if c[0] == 'draw_text']
    bounds = []
    for _, (pos, label), options in texts:
        width, height = raw.get_text_size(label)
        extent = width / height * options['size']
        assert pos[0] >= -0.5
        assert pos[0] + extent <= cfg['width'] + 0.5
        assert pos[1] >= 0
        assert pos[1] + options['size'] <= cfg['height'] + 0.5
        bounds.append((pos[0], pos[1], pos[0] + extent, pos[1] + options['size']))
    for i, (left, top, right, bottom) in enumerate(bounds):
        for other_left, other_top, other_right, other_bottom in bounds[i + 1:]:
            assert (right < other_left or other_right < left or bottom < other_top or other_bottom < top)


@pytest.mark.parametrize('dpi', [96, 120, 144, 168, 192, 240, 288])
@pytest.mark.parametrize('caps', ['24,36,48,60,72,90,120,144',
                                  '23.976,59.94,119.88,143.999',
                                  '143.999', '23.976,23.977,23.978,144',
                                  '23.976,23.977,23.978,23.979,59.940,119.880,143.999'])
def test_full_glyph_bounds_and_container_metric_cache(dpi, caps):
    raw, fps = preview(dpi / 96)
    fps.dpg.configure_item('fps_cap_drawlist', width=590, height=60)
    raw.values.update(input_capmethod='Custom', input_customfpslimits=caps)
    active = Decimal(caps.split(',')[-1])
    fps.update_fps_cap_visualization(active_applied_cap=active)
    assert_label_bounds(raw)
    labels = [c[1][1] for c in raw.live_draws.values() if c[0] == 'draw_text']
    assert labels == caps.split(',')
    assert fps._last_ladder_geometry[0] == raw.configurations['fps_cap_drawlist']['width'] / fps.dpg.scale
    raw.calls.clear()  # Configuration is persistent state, not the cleared call log.
    fps.update_fps_cap_visualization(active_applied_cap=active)
    assert not any(c[0] == 'draw_text' for c in raw.calls)
    # Width changes with identical caps, scale and observer must redraw.
    for width in (570, 180, 90):
        fps.dpg.configure_item('fps_cap_drawlist', width=width)
        raw.calls.clear()
        fps.update_fps_cap_visualization(active_applied_cap=active)
        assert any(c[0] == 'draw_text' for c in raw.calls)
        assert_label_bounds(raw)
        assert fps._last_ladder_geometry[0] == round(width * fps.dpg.scale) / fps.dpg.scale
        assert [c[1][1] for c in raw.live_draws.values() if c[0] == 'draw_text'] == labels
    # Changing proportional font advances also invalidates the cache.
    raw.font_height = 16
    raw.calls.clear()
    fps.update_fps_cap_visualization(active_applied_cap=active)
    assert any(c[0] == 'draw_text' for c in raw.calls)
    assert_label_bounds(raw)


def test_measurement_not_ready_is_retried_without_guessing():
    raw, fps = preview()
    raw.get_text_size = lambda label: None
    fps.update_fps_cap_visualization()
    assert not any(c[0] == 'draw_text' for c in raw.calls)
    assert fps.last_fps_limits == []
    del raw.get_text_size
    fps.update_fps_cap_visualization()
    assert fps.last_fps_limits == [30, 40, 50, 60]


@pytest.mark.parametrize('scale', [1, 1.25, 1.5, 1.75, 2, 2.5, 3])
@pytest.mark.parametrize('theme_name', ['disabled_text_theme', 'enabled_text_theme'])
@pytest.mark.parametrize('component_type', ['mvInputInt', 'mvInputText'])
def test_cap_method_theme_contrast_and_disabled_enforcement(scale, theme_name, component_type, monkeypatch):
    from core.themes import ThemesManager, bg_colour_2_child
    monkeypatch.setenv('WINDIR', '/windows')
    raw = RecordingDPG()
    manager = ThemesManager('/app', ScaledDPG(raw, scale))
    manager.create_themes()

    def contrast(color):
        alpha = color[3] / 255
        rgb = [((c * alpha + b * (1 - alpha)) / 255) for c, b in zip(color[:3], bg_colour_2_child)]
        def luminance(values):
            linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in values]
            return sum(v * w for v, w in zip(linear, (.2126, .7152, .0722)))
        return (luminance(rgb) + .05) / (luminance([c / 255 for c in bg_colour_2_child[:3]]) + .05)

    disabled_theme = manager.themes['disabled_text_theme']
    colors = [a[1] for n, a, k, parents in raw.ancestry
              if n == 'add_theme_color' and a[0] == raw.mvThemeCol_Text
              and any(p[1] == disabled_theme for p in parents)]
    assert colors and all(contrast(color) >= 4.5 for color in colors)
    components = [item for item, parent in raw.parents.items()
                  if parent == manager.themes[theme_name]
                  and raw.component_types.get(item) == getattr(raw, component_type)
                  and raw.configurations[item].get('enabled_state') is False]
    assert len(components) == 1, f'{theme_name} lacks a unique disabled {component_type} component'
    records = [c for c in raw.ancestry if c[3] and c[3][-1][1] == components[0]]
    assert [a for n, a, k, parents in records
            if n == 'add_theme_color' and a[0] == raw.mvThemeCol_Text] == [
                (raw.mvThemeCol_Text, (170, 174, 184, 255))]
    assert [a for n, a, k, parents in records
            if n == 'add_theme_style' and a[0] == raw.mvStyleVar_DisabledAlpha] == [
                (raw.mvStyleVar_DisabledAlpha, 1.0)]

    ns = functions('src/core/config_manager.py', {'current_method_callback'}, {})
    cm = NS(dpg=manager.dpg, themes=manager.themes, tray=None, logger=NS(add_log=lambda *a: None))
    expected_tags = {'input_capratio', 'label_capratio', 'label_capstep', 'input_capstep',
                     'input_customfpslimits', 'label_maxcap', 'label_mincap', 'input_maxcap', 'input_mincap'}
    for method in ('Ratio', 'Step', 'Custom'):
        raw.calls.clear()
        ns['current_method_callback'](cm, app_data=method)
        bindings = {a[0]: a[1] for n, a, k in raw.calls if n == 'bind_item_theme'}
        assert set(bindings) == expected_tags  # Every consumer of these two themes.
        assert not any(n == 'configure_item' for n, a, k in raw.calls)
        # An already disabled control stays disabled through a method/theme change.
        for tag in ('input_maxcap', 'input_customfpslimits'):
            manager.dpg.configure_item(tag, enabled=False)
        ns['current_method_callback'](cm, app_data=method)
        for tag in ('input_maxcap', 'input_customfpslimits'):
            assert raw.configurations[tag]['enabled'] is False


def preview(scale=1):
    """Use real FPSUtils drawing/ladder methods without initializing .NET hardware."""
    raw = RecordingDPG()
    fps = FPSUtils.__new__(FPSUtils)
    fps.dpg = ScaledDPG(raw, scale)
    raw.metric_scale = scale
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
    assert fps._last_ladder_geometry[:3] == (210, scale, active)
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
