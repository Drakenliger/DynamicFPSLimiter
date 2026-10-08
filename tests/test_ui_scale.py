"""Execute production UI calls on Linux; expected geometry is independent."""
import ast
import contextlib
import ctypes
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

from core.ui_scale import (ScaledDPG, UI_SCALE_CHOICES, enable_native_dpi,
                           primary_monitor_dpi, resolve_scale, normalize_preference,
                           pixels, titlebar_hit, read_preference)

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
        self.values = {}

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
        if 'callback' in name or name.startswith('update_'):
            return lambda *a, **kw: None
        return 1


@pytest.mark.parametrize('choice,viewport,plot,child,font,mono,large,ladder', [
    ('100%', (610, 700), 190, (590, 450), 18, 14, 24, (5, 205, 9, 21, 14)),
    ('150%', (915, 1050), 285, (885, 675), 27, 21, 36, (8, 308, 14, 32, 21)),
    ('200%', (1220, 1400), 380, (1180, 900), 36, 28, 48, (10, 410, 18, 42, 28)),
    ('300%', (1830, 2100), 570, (1770, 1350), 54, 42, 72, (15, 615, 27, 63, 42)),
])
def test_actual_app_theme_and_ladder_calls(choice, viewport, plot, child, font, mono, large, ladder, monkeypatch):
    from core.themes import ThemesManager
    monkeypatch.setenv('WINDIR', '/windows')
    raw = RecordingDPG()
    themes = ThemesManager('/app', raw)
    cm = Config(ui_scale=choice, sensor_infos=[], settings={},
                update_ui_scale_preference=lambda *a: None)
    ns = functions('src/core/app.py', {'configure_ui_scale', 'build_plot_window',
                   'build_readings_window', 'build_settings_window', 'build_profile_section', 'load_and_create_textures'},
                   dict(ScaledDPG=ScaledDPG, resolve_scale=resolve_scale, UI_SCALE_CHOICES=UI_SCALE_CHOICES))
    dpg = ns['configure_ui_scale'](raw, cm, themes, 288)
    assert cm.dpg is dpg and themes.dpg is dpg
    themes.create_themes()
    fonts = themes.create_fonts()
    assert [a[1] for n, a, k in raw.calls if n == 'add_font'] == [font, font, mono, large]
    style = next(a for n, a, k in raw.calls if n == 'add_theme_style' and a[0] == 'mvStyleVar_WindowPadding')
    assert style[1:] == (10 * dpg.scale, 8 * dpg.scale)
    alpha = next(a for n, a, k in raw.calls if n == 'add_theme_style' and a[0] == 'mvPlotStyleVar_MinorAlpha')
    assert alpha[1] == .2
    ns.update(dpg=dpg, cm=cm, themes_manager=themes,
              autostart_checkbox_callback=lambda *a: None,
              tooltip_checkbox_callback=lambda *a: None,
              autopilot_checkbox_callback=lambda *a: None,
              questions=[], FAQs={}, logger=NS(refresh_log_display=lambda: None))
    ns['build_plot_window']()
    assert raw.tagged('plot', 'plot')['height'] == plot
    assert raw.tagged('child_window', 'plot_childwindow')['width'] == -1
    # Late-created windows use the same adapter, even after other GUI calls.
    ns['build_settings_window']()
    ns['build_readings_window']()
    for tag in ('settings_window', 'readings_popup_window'):
        cfg = raw.tagged('window', tag)
        assert (cfg['width'], cfg['height']) == child
        assert cfg['pos'] == {'100%': (10,195), '150%': (15,292), '200%': (20,390), '300%': (30,585)}[choice]
    assert 'restart required' in raw.tagged('add_combo', 'ui_scale_preference')['label']
    # Execute the actual viewport setup statements from app.py.
    tree = ast.parse((ROOT / 'src/core/app.py').read_text())
    viewport_nodes = [n for n in tree.body if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
                      and isinstance(n.value.func, ast.Attribute) and n.value.func.attr in
                      {'create_viewport', 'set_viewport_max_width', 'set_viewport_max_height'}]
    ns.update(Viewport_width=610, Viewport_height=700, viewport_x_pos=500, viewport_y_pos=100)
    exec(compile(ast.Module(body=viewport_nodes, type_ignores=[]), 'app.py', 'exec'), ns)
    cfg = next(k for n, a, k in raw.calls if n == 'create_viewport')
    assert (cfg['width'], cfg['height']) == viewport
    assert (cfg['x_pos'], cfg['y_pos']) == (500, 100)
    # Run the main window body too, including sensor tables and embedded children.
    noop = lambda *a, **kw: None
    cm.settings = defaultdict(lambda: 40, customfpslimits='30, 60')
    cm.sensor_infos = [dict(hw_id='cpu', hw_name='CPU', sensor_type='Load',
                            parameter_id='cpu_load', sensor_name='CPU load')]
    ns.update(app_title='App', display_version=lambda: 'test', bold_font=123,
              Viewport_width=610, textures=defaultdict(lambda: 'raw'),
              tray=NS(minimize_to_tray=noop, drag_viewport=noop, on_mouse_release=noop, on_mouse_click=noop),
              exit_gui=noop, start_stop_callback=noop, toggle_luid_selection=noop,
              fps_utils=NS(reset_custom_limits=noop, copy_from_plot=noop))
    main_window = next(n for n in tree.body if isinstance(n, ast.With)
                       and isinstance(n.items[0].context_expr, ast.Call)
                       and any(k.arg == 'tag' and isinstance(k.value, ast.Constant)
                               and k.value.value == 'Primary Window' for k in n.items[0].context_expr.keywords))
    exec(compile(ast.Module(body=[main_window], type_ignores=[]), 'app.py', 'exec'), ns)
    assert raw.tagged('drawlist', 'fps_cap_drawlist')['width'] == {
        '100%': 210, '150%': 315, '200%': 420, '300%': 630}[choice]
    assert raw.tagged('child_window', 'LHwM_childwindow')['height'] == {
        '100%': 385, '150%': 578, '200%': 770, '300%': 1155}[choice]
    assert raw.tagged('add_image', 'icon')['width'] == {
        '100%': 20, '150%': 30, '200%': 40, '300%': 60}[choice]
    assert raw.tagged('add_input_text', 'input_cpu_load_upper')['default_value'] == 100
    assert raw.tagged('add_input_text', 'input_cpu_load_upper')['width'] == {
        '100%': 40, '150%': 60, '200%': 80, '300%': 120}[choice]
    assert raw.tagged('add_input_int', 'input_maxcap')['step_fast'] == 10
    # Only the dynamic ladder calls below are counted.
    raw.calls.clear()
    raw.width = viewport[0]
    ladder_ns = functions('src/core/fps_utils.py', {'update_fps_cap_visualization'}, {})
    fps = NS(dpg=dpg, viewport_width=viewport[0], last_fps_limits=[30, 60],
             current_stepped_limits=lambda: [30, 60])
    ladder_ns['update_fps_cap_visualization'](fps)
    lines = [(a, k) for n, a, k in raw.calls if n == 'draw_line']
    x1, x2, y1, y2, text_size = ladder
    assert [a for a, k in lines] == [((x1, y1), (x1, y2)), ((x2, y1), (x2, y2))]
    assert [k['thickness'] for a, k in lines] == [dpg.scale, dpg.scale]
    texts = [(a, k) for n, a, k in raw.calls if n == 'draw_text']
    assert texts[0][0] == ((round(-3 * dpg.scale), round(23 * dpg.scale)), '30')
    assert texts[0][1]['size'] == text_size
    before = len(lines)
    ladder_ns['update_fps_cap_visualization'](fps)
    assert sum(n == 'draw_line' for n, a, k in raw.calls) == before
    raw.items.remove('Foreground')
    ladder_ns['update_fps_cap_visualization'](fps)
    assert sum(n == 'draw_line' for n, a, k in raw.calls) == before + 2
    raw.width += 100
    ladder_ns['update_fps_cap_visualization'](fps)
    assert sum(n == 'draw_line' for n, a, k in raw.calls) == before + 2


def test_adapter_sentinels_data_and_other_api_passthrough():
    raw = RecordingDPG()
    dpg = ScaledDPG(ScaledDPG(raw, 3), 2)
    dpg.add_input_int(width=-1, height=0, default_value=70, step=5)
    assert raw.calls[-1][2] == dict(width=-1, height=0, default_value=70, step=5)
    dpg.configure_item('late', width=100, pos=(-10, 0), label='unchanged')
    assert raw.calls[-1] == ('configure_item', ('late',), dict(width=200, pos=(-20, 0), label='unchanged'))
    dpg.add_table_column(init_width_or_weight=100)
    assert raw.calls[-1][2]['init_width_or_weight'] == 200
    dpg.add_table_column(width_stretch=True, init_width_or_weight=2)
    assert raw.calls[-1][2]['init_width_or_weight'] == 2
    data = [1, 2, 3, 4]
    dpg.add_static_texture(1, 1, data, tag='raw')
    assert raw.calls[-1][1] == (1, 1, data) and raw.calls[-1][1][2] is data
    dpg.set_axis_limits('axis', 0, 100)
    assert raw.calls[-1][1] == ('axis', 0, 100)
    dpg.add_mouse_drag_handler(threshold=0, callback=data)
    assert raw.calls[-1][2] == dict(threshold=0, callback=data)
    dpg.set_viewport_pos((100, -100))
    assert raw.calls[-1][1] == ((100, -100),)
    dpg.draw_line((0, 15), (100, 15), color=(1, 2, 3), thickness=2)
    assert raw.calls[-1] == ('draw_line', ((0, 30), (200, 30)), dict(color=(1, 2, 3), thickness=4))
    dpg.add_image('raw', width=20, height=20)
    assert raw.calls[-1] == ('add_image', ('raw',), dict(width=40, height=40))


def test_actual_texture_loader_preserves_raw_data():
    raw = RecordingDPG()
    data = [0.1] * 16
    raw.load_image = lambda path: (2, 2, 4, data)
    ns = functions('src/core/app.py', {'load_and_create_textures'}, {'os': __import__('os')})
    ns['load_and_create_textures'](['icon.png'], '/app', ScaledDPG(raw, 3))
    assert raw.calls[-1] == ('add_static_texture', (2, 2, data), {'tag': 'icon_texture'})
    assert raw.calls[-1][1][2] is data


def test_old_config_default_and_persisted_choice(tmp_path):
    from core.config_io import new_config, write_config
    cfg = new_config()
    cfg.read_string('[Preferences]\nshowtooltip=True\n[GlobalSettings]\nminvalidfps=14\n')
    ns = functions('src/core/config_manager.py', {'load_preferences', 'update_ui_scale_preference'},
                   {'normalize_preference': normalize_preference, 'write_config': write_config})
    path = tmp_path / 'settings.ini'
    cm = NS(settings_config=cfg, key_type_map={'showtooltip': bool}, settings_path=path,
            logger=NS(add_log=lambda message: None))
    ns['load_preferences'](cm)
    assert cm.ui_scale == 'Auto' and cm.showtooltip
    assert 'ui_scale' not in cfg['Preferences']
    for choice in UI_SCALE_CHOICES:
        ns['update_ui_scale_preference'](cm, None, choice)
        assert read_preference(path) == choice
    assert dict(cfg['GlobalSettings']) == {'minvalidfps': '14'}
    assert resolve_scale('Auto', 192) == 2
    assert resolve_scale('150%', 288) == 1.5


class Fn:
    def __init__(self, result=0, callback=None):
        self.result, self.callback, self.calls = result, callback, []
    def __call__(self, *args):
        self.calls.append(args)
        return self.callback(*args) if self.callback else self.result


def test_pointer_safe_windows_awareness_and_monitor_fallback():
    context = Fn(1)
    handle = 0x123456789AB
    monitor = Fn(handle)
    def dpi(h, kind, x, y):
        assert h == handle
        ctypes.cast(x, ctypes.POINTER(ctypes.c_uint))[0] = 192
        return 0
    getdpi = Fn(callback=dpi)
    loader = NS(user32=NS(SetProcessDpiAwarenessContext=context, MonitorFromPoint=monitor),
                shcore=NS(GetDpiForMonitor=getdpi))
    assert enable_native_dpi(loader)
    assert context.argtypes == [ctypes.c_void_p]
    assert context.calls[0][0].value == ctypes.c_void_p(-4).value
    assert primary_monitor_dpi(loader) == 192
    assert monitor.restype is ctypes.c_void_p
    assert getdpi.argtypes[0] is ctypes.c_void_p
    legacy = Fn(0)
    system = Fn(144)
    loader = NS(user32=NS(SetProcessDpiAwarenessContext=Fn(0), GetDpiForSystem=system),
                shcore=NS(SetProcessDpiAwareness=legacy))
    assert enable_native_dpi(loader)
    assert legacy.argtypes == [ctypes.c_int]
    assert primary_monitor_dpi(loader) == 144
    assert primary_monitor_dpi(NS()) == 96
    assert not enable_native_dpi(NS())


@pytest.mark.parametrize('scale,width,inside,outside', [(1,610,(100,39),(535,20)),
    (1.5,915,(800,59),(803,20)), (2,1220,(100,79),(1070,20)),
    (3,1830,(100,119),(1605,20))])
def test_titlebar_physical_hit_test(scale, width, inside, outside):
    ns = functions('src/core/tray_functions.py', {'on_mouse_click'},
                   dict(titlebar_hit=titlebar_hit, get_mouse_screen_pos=lambda: (900, 800)))
    raw = RecordingDPG()
    raw.get_mouse_pos = lambda **kw: inside
    raw.is_mouse_button_down = lambda _: True
    raw.get_viewport_pos = lambda: (500, 100)
    tray = NS(dpg=ScaledDPG(raw, scale), viewport_width=width)
    ns['on_mouse_click'](tray, None, None, None)
    assert tray._dragging_viewport and tray._drag_start_viewport_pos == (500,100)
    raw.get_mouse_pos = lambda **kw: outside
    ns['on_mouse_click'](tray, None, None, None)
    assert not tray._dragging_viewport
    assert not titlebar_hit((-1, 10), width, scale)
    assert not titlebar_hit((10, -1), width, scale)


def test_fallback_font_scaled_without_rescaling_loaded_font(monkeypatch):
    from core.themes import ThemesManager
    monkeypatch.setenv('WINDIR', '/windows')
    raw = RecordingDPG()
    def fail(*args, **kwargs):
        raise OSError('missing font')
    raw.add_font = fail
    ThemesManager('/app', ScaledDPG(raw, 2)).create_fonts()
    assert raw.calls[-1] == ('set_global_font_scale', (2,), {})


def test_actual_centering_uses_physical_dimensions_once():
    metrics = Fn(callback=lambda index: (3840, 2160)[index])
    ns = functions('src/core/tray_functions.py', {'get_centered_viewport_position'},
                   {'ctypes': NS(windll=NS(user32=NS(GetSystemMetrics=metrics)), c_int=ctypes.c_int)})
    assert ns['get_centered_viewport_position'](1220, 1400) == (1310, 380)
    assert metrics.argtypes == [ctypes.c_int] and metrics.restype is ctypes.c_int


def test_awareness_precedes_actual_loading_call_and_acceptance_reads_no_real_preference():
    import os
    tree = ast.parse((ROOT / 'src/core/app.py').read_text())
    start = next(i for i, n in enumerate(tree.body) if isinstance(n, ast.Expr)
                 and ast.unparse(n) == 'enable_native_dpi()')
    end = next(i for i, n in enumerate(tree.body[start:], start) if isinstance(n, ast.If)
               and any(isinstance(x, ast.Name) and x.id == 'show_loading_popup' for x in ast.walk(n)))
    startup = ast.Module(body=tree.body[start:end+1], type_ignores=[])
    for acceptance in (None, object()):
        events = []
        raw = RecordingDPG()
        ns = dict(enable_native_dpi=lambda: events.append('awareness'),
                  primary_monitor_dpi=lambda: 192, resolve_scale=resolve_scale,
                  ScaledDPG=ScaledDPG, os=os, parent_dir='/private', Base_dir='/private/core',
                  _acceptance_runtime=acceptance, dpg=raw,
                  logger=NS(set_dpg=lambda dpg: None), display_version=lambda: 'test')
        def preference(path):
            assert acceptance is None
            events.append('read')
            return '150%'
        def loading(*args, **kwargs):
            events.append('HWND')
            assert kwargs['dpg'].scale == 1.5
        ns.update(read_preference=preference, show_loading_popup=loading)
        exec(compile(startup, 'app.py', 'exec'), ns)
        assert events == (['awareness', 'read', 'HWND'] if acceptance is None else ['awareness'])
        assert ns['dpg'].scale == (1.5 if acceptance is None else 2)


def test_actual_scaled_popup_contexts_and_hit_test(monkeypatch):
    with isolated_popup_modules(), monkeypatch.context() as monkeypatch:
        import sys
        import types
        # Only OS tray imports are replaced, never popup implementation or DPG calls.
        pystray = types.ModuleType('pystray')
        pystray.Icon = pystray.MenuItem = pystray.Menu = lambda *a, **k: None
        monkeypatch.setitem(sys.modules, 'pystray', pystray)
        from core import launch_popup as lp
        monkeypatch.setenv('WINDIR', '/windows')
        centers = []
        monkeypatch.setattr(lp.TrayManager, 'get_centered_viewport_position',
                            staticmethod(lambda w, h: centers.append((w, h)) or (100, 200)))
        monkeypatch.setattr(lp.tray_functions, 'get_mouse_screen_pos', lambda: (500, 100))
        raw = RecordingDPG()
        dpg = ScaledDPG(raw, 2)
        lp._loading_popup_active = False
        lp.show_loading_popup('loading', Base_dir='/not-real', dpg=dpg)
        assert centers[-1] == (600, 100)
        loading = next(k for n,a,k in raw.calls if n == 'create_viewport')
        assert (loading['width'], loading['height'], loading['x_pos']) == (600,100,100)
        with pytest.raises(SystemExit):
            lp.show_rtss_error_and_exit('/not-real.dll', dpg=dpg)
        names = [n for n,a,k in raw.calls]
        assert names.index('destroy_context') < names.index('create_context', names.index('create_context') + 1)
        assert centers[-1] == (840,640)
        handler = lp.ScaledPopupDragHandler(840, dpg)
        raw.get_mouse_pos = lambda **kw: (600,79)
        raw.is_mouse_button_down = lambda _: True
        raw.get_viewport_pos = lambda: (100,200)
        handler.on_mouse_click(None,None,None)
        assert handler._dragging_viewport
        raw.get_mouse_pos = lambda **kw: (690,79)
        handler.on_mouse_click(None,None,None)
        assert not handler._dragging_viewport


def test_actual_new_config_defaults_auto(tmp_path, monkeypatch):
    # Run ConfigManager initialization, with only hardware enumeration replaced.
    import runpy
    import sys
    import types
    module = types.ModuleType('core.librehardwaremonitor')
    module.get_all_sensor_infos = lambda *a: []
    monkeypatch.setitem(sys.modules, 'core.librehardwaremonitor', module)
    config_class = runpy.run_path(str(ROOT / 'src/core/config_manager.py'))['ConfigManager']
    cm = config_class(NS(add_log=lambda *a: None), RecordingDPG(), NS(), None,
                      NS(themes={}), str(tmp_path / 'core'))
    assert cm.ui_scale == 'Auto'
    assert read_preference(cm.settings_path) == 'Auto'
    cm.update_ui_scale_preference(None, '200%')
    restarted = config_class(NS(add_log=lambda *a: None), RecordingDPG(), NS(), None,
                             NS(themes={}), str(tmp_path / 'core'))
    assert restarted.ui_scale == '200%'


@contextlib.contextmanager
def isolated_popup_modules():
    """Fresh popup imports, restoring exact cached modules and package attributes."""
    import sys
    import core
    names = ('tray_functions', 'drag_helper', 'launch_popup')
    absent = object()
    modules = {name: sys.modules.get('core.' + name, absent) for name in names}
    attrs = {name: vars(core).get(name, absent) for name in names}
    try:
        for name in names:
            sys.modules.pop('core.' + name, None)
            vars(core).pop(name, None)
        yield
    finally:
        for name in names:
            if modules[name] is absent:
                sys.modules.pop('core.' + name, None)
            else:
                sys.modules['core.' + name] = modules[name]
            if attrs[name] is absent:
                vars(core).pop(name, None)
            else:
                setattr(core, name, attrs[name])


@pytest.mark.parametrize('preloaded', [False, True])
def test_popup_import_cleanup_and_later_import(preloaded, monkeypatch):
    import sys
    import types
    import core
    import importlib
    with isolated_popup_modules(), monkeypatch.context() as mp:
        originals = {}
        if preloaded:
            dependency = types.ModuleType('pystray')
            dependency.Icon = dependency.MenuItem = dependency.Menu = type('OriginalMenu', (), {})
            mp.setitem(sys.modules, 'pystray', dependency)
            for name in ('tray_functions', 'drag_helper', 'launch_popup'):
                module = importlib.import_module('core.' + name)
                originals[name] = module
            originals['launch_popup']._loading_popup_active = True
        original_globals = {name: dict(vars(module)) for name, module in originals.items()}
        test_actual_scaled_popup_contexts_and_hit_test(monkeypatch)
        for name in ('tray_functions', 'drag_helper', 'launch_popup'):
            if preloaded:
                assert sys.modules['core.' + name] is originals[name]
                assert getattr(core, name) is originals[name]
                assert vars(originals[name]) == original_globals[name]
            else:
                assert 'core.' + name not in sys.modules
                assert name not in vars(core)
        # Later imports execute the production tray source with the new dependency,
        # rather than retaining the previous test's lambda Menu.
        with isolated_popup_modules():
            dependency = types.ModuleType('pystray')
            class Menu:
                pass
            dependency.Menu = dependency.Icon = dependency.MenuItem = Menu
            with monkeypatch.context() as later:
                later.setitem(sys.modules, 'pystray', dependency)
                tray = importlib.import_module('core.tray_functions')
                assert tray.Menu is Menu


@pytest.mark.parametrize('scale,width,expected', [
    (1, 610, [5, 108, 205]), (1.5, 915, [8, 162, 308]),
    (2, 1220, [10, 216, 410]), (3, 1830, [15, 324, 615])])
def test_actual_decimal_parser_and_ladder(scale, width, expected, monkeypatch):
    import runpy
    import sys
    import types
    from decimal import Decimal
    hardware = types.ModuleType('core.librehardwaremonitor')
    hardware.get_all_sensor_infos = lambda *a: []
    monkeypatch.setitem(sys.modules, 'core.librehardwaremonitor', hardware)
    cls = runpy.run_path(str(ROOT / 'src/core/config_manager.py'))['ConfigManager']
    cm = cls.__new__(cls)
    cm.logger = NS(add_log=lambda *a: None)
    raw = RecordingDPG()
    raw.width = width
    raw.values.update(input_maxcap=60, input_mincap=30, input_capstep=5,
                      input_capratio=10, input_capmethod='Custom',
                      input_customfpslimits='30, 45.5, 59.99')
    ns = functions('src/core/fps_utils.py',
                   {'current_stepped_limits', 'update_fps_cap_visualization'}, {})
    fps = NS(cm=cm, dpg=ScaledDPG(raw, scale), viewport_width=610, last_fps_limits=[])
    fps.current_stepped_limits = lambda: ns['current_stepped_limits'](fps)
    caps = fps.current_stepped_limits()
    assert caps == [Decimal('30.00'), Decimal('45.50'), Decimal('59.99')]
    assert all(isinstance(cap, Decimal) for cap in caps)
    ns['update_fps_cap_visualization'](fps)
    assert [a[0][0] for n,a,k in raw.calls if n == 'draw_line'] == expected
    assert fps.last_fps_limits == caps
    assert [a[1] for n,a,k in raw.calls if n == 'draw_text'] == ['30.00', '45.50', '59.99']


class NumericStyleDPG(RecordingDPG):
    # DPG 2.0 values from its pinned ImGui/ImPlot enums.
    mvThemeCat_Core, mvThemeCat_Plots, mvThemeCat_Nodes = 0, 1, 2
    mvStyleVar_Alpha = mvPlotStyleVar_LineWeight = 0
    mvStyleVar_PopupBorderSize = mvPlotStyleVar_MinorAlpha = 10
    mvStyleVar_WindowPadding = 2
    mvPlotStyleVar_Marker = 1
    mvPlotStyleVar_FitPadding = 24
    mvPlotStyleVar_MajorTickSize = 13
    mvPlotStyleVar_MajorGridSize = 15


def test_numeric_style_categories_and_real_call_forms():
    raw = NumericStyleDPG()
    dpg = ScaledDPG(raw, 2)
    for target, value, category in [(0, .5, 0), (10, .2, 1), (24, .25, 1), (1, 3, 1), (10, 4, 2)]:
        dpg.add_theme_style(target, value, category=category)
        assert raw.calls[-1][1] == (target, value)
    dpg.add_theme_style(0, 2, -1, category=1)
    assert raw.calls[-1][1] == (0, 4, -1)
    dpg.add_theme_style(target=24, x=.1, y=.2, category=1)
    assert raw.calls[-1][2] == dict(target=24, x=.1, y=.2, category=1)
    dpg.add_theme_style(target=10, x=3, y=-1)
    assert raw.calls[-1][2] == dict(target=10, x=6, y=-1)
    dpg.add_theme_style(2, x=10, y=8)
    assert raw.calls[-1][1] == (2,)
    assert raw.calls[-1][2] == dict(x=20, y=16)
    dpg.add_theme_style(target=13, x=1, y=2, category=1)
    assert raw.calls[-1][2] == dict(target=13, x=2, y=4, category=1)
    dpg.add_theme_style(15, 1, 2, category=1)
    assert raw.calls[-1][1] == (15, 2, 4)


@pytest.mark.parametrize('stored,expected', [('150%', '150%'), ('150%%', '150%'),
                                            ('unknown', 'Auto'), (None, 'Auto')])
def test_actual_config_and_startup_raw_scale(tmp_path, monkeypatch, stored, expected):
    import runpy
    import sys
    import types
    hardware = types.ModuleType('core.librehardwaremonitor')
    hardware.get_all_sensor_infos = lambda *a: []
    monkeypatch.setitem(sys.modules, 'core.librehardwaremonitor', hardware)
    cls = runpy.run_path(str(ROOT / 'src/core/config_manager.py'))['ConfigManager']
    cm = cls(NS(add_log=lambda *a: None), RecordingDPG(), NS(), None,
             NS(themes={}), str(tmp_path / 'core'))
    path = Path(cm.settings_path)
    text = path.read_text()
    text = text.replace('ui_scale = Auto', '' if stored is None else 'ui_scale = ' + stored)
    path.write_text(text)
    restarted = cls(NS(add_log=lambda *a: None), RecordingDPG(), NS(), None,
                    NS(themes={}), str(tmp_path / 'core'))
    assert restarted.ui_scale == read_preference(path) == expected
    assert restarted.showtooltip is True
    restarted.update_ui_scale_preference(None, '150%')
    assert 'ui_scale = 150%' in path.read_text()
    assert 'ui_scale = 150%%' not in path.read_text()
    assert read_preference(path) == '150%'
    restarted.load_preferences()
    assert restarted.ui_scale == '150%'


def test_actual_popup_main_block(monkeypatch):
    import sys
    with isolated_popup_modules(), monkeypatch.context() as mp:
        import types
        dependency = types.ModuleType('pystray')
        dependency.Icon = dependency.MenuItem = dependency.Menu = lambda *a, **k: None
        mp.setitem(sys.modules, 'pystray', dependency)
        from core import launch_popup as lp
        mp.setenv('WINDIR', '/windows')
        raw = RecordingDPG()
        events = []
        mp.setattr(lp, 'enable_native_dpi', lambda: events.append('dpi'))
        mp.setattr(lp, 'primary_monitor_dpi', lambda: 192)
        centers = []
        mp.setattr(lp.TrayManager, 'get_centered_viewport_position',
                   staticmethod(lambda w,h: centers.append((w,h)) or (123,456)))
        ns = dict(vars(lp), __name__='__main__', _default_dpg=lambda: raw)
        tree = ast.parse((ROOT / 'src/core/launch_popup.py').read_text())
        main = next(n for n in tree.body if isinstance(n, ast.If)
                    and isinstance(n.test, ast.Compare)
                    and isinstance(n.test.left, ast.Name) and n.test.left.id == '__name__')
        exec(compile(ast.Module(body=[main], type_ignores=[]), 'launch_popup.py', 'exec'), ns)
        assert events == ['dpi']
        assert isinstance(ns['dpg_mod'], ScaledDPG)
        assert centers == [(840, 640)]
        viewport = next(k for n,a,k in raw.calls if n == 'create_viewport')
        assert (viewport['width'], viewport['height']) == (840,640)
        assert (viewport['x_pos'], viewport['y_pos']) == (123,456)
        assert next(n for n,a,k in raw.calls) == 'create_context'
        assert [a[1] for n,a,k in raw.calls if n == 'add_font'] == [36,36,28,48]
