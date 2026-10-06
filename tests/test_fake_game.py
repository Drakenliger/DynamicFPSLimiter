import csv
import importlib.util
import json
from pathlib import Path
import sys
import types
from contextlib import nullcontext

import pytest

spec = importlib.util.spec_from_file_location('fake_game', Path(__file__).with_name('fake_game.py'))
game = importlib.util.module_from_spec(spec)
spec.loader.exec_module(game)


def test_absolute_motion_and_late_jump():
    sequences = [[0, .01, .02, .5], [0, .1, .5]]
    results = [[game.motion(t, 1000) for t in sequence] for sequence in sequences]
    assert results[0][-1] == results[1][-1]
    before = game.motion(.1, 1000)
    after = game.motion(.6, 1000)
    assert after[0] - before[0] == pytest.approx(250)
    assert after[1] - before[1] == pytest.approx(3.141592653589793)


def test_timing_wall_separation_and_scrolling():
    timing = game.FrameTiming(10, history_size=3)
    assert timing.completed(10.01, 1000)['t'] == 1000
    assert timing.last_ms == pytest.approx(10)
    assert timing.completed(10.03, -1000) is None
    assert timing.last_ms == pytest.approx(20)
    timing.completed(10.06, 9000)
    old = game.graph_points(timing.history, 200, 100)
    timing.completed(10.10, 0)
    points = game.graph_points(timing.history, 200, 100)
    assert len(timing.history) == len(points) == 3
    assert points[-1] == pytest.approx((200, 60))
    assert points[0][1] == old[1][1]
    assert points[0][0] < old[1][0]


def test_parser_preserves_options():
    args = game.build_arg_parser().parse_args([
        '--title', 'custom', '--width', '640', '--height', '480', '--load', '12',
        '--fps-file', 'fps', '--ready-file', 'ready', '--duration', '2',
        '--no-vsync', '--frametime-file', 'frames'])
    assert vars(args) == dict(title='custom', width=640, height=480, load=12,
                             fps_file='fps', ready_file='ready', duration=2,
                             no_vsync=True, frametime_file='frames')


class FakeDPG(types.ModuleType):
    def __init__(self, mode, ready):
        super().__init__('dearpygui.dearpygui')
        self.mode, self.ready = mode, ready
        self.count = 0
        self.clock = 10.0
        self.destroyed = self.stopped = False
        self.values = []
        self.quads = 0

    def __getattr__(self, name):
        if name == 'window':
            return lambda **kw: nullcontext()
        if name == 'get_viewport_client_width':
            return lambda: 640
        if name == 'get_viewport_client_height':
            return lambda: 480
        if name in ('add_text', 'add_drawlist'):
            return lambda *a, **kw: name
        return lambda *a, **kw: None

    def is_dearpygui_running(self):
        return self.count < 3 and not self.stopped

    def render_dearpygui_frame(self):
        if self.count == 0:
            assert not self.ready.exists()
        if self.count == 2 and self.mode in ('error', 'interrupt'):
            raise RuntimeError('render failed') if self.mode == 'error' else KeyboardInterrupt()
        self.clock += (.01, .6, .02)[self.count]
        self.count += 1

    def set_value(self, item, value):
        self.values.append(value)

    def draw_rectangle(self, *a, **kw):
        self.quads += 1

    def stop_dearpygui(self):
        self.stopped = True

    def destroy_context(self):
        self.destroyed = True


@pytest.mark.parametrize('mode,rows', [('close', 3), ('duration', 2), ('error', 2), ('interrupt', 2)])
def test_real_main_telemetry_and_cleanup(monkeypatch, tmp_path, mode, rows):
    ready, fps, frames = [tmp_path / name for name in ('ready', 'fps', 'frames')]
    dpg = FakeDPG(mode, ready)
    monkeypatch.setitem(sys.modules, 'dearpygui', types.ModuleType('dearpygui'))
    monkeypatch.setitem(sys.modules, 'dearpygui.dearpygui', dpg)
    monkeypatch.setattr(game.time, 'perf_counter', lambda: dpg.clock)
    walls = iter([1000, -1000, 9000])
    monkeypatch.setattr(game.time, 'time', lambda: next(walls))
    monkeypatch.setattr(sys, 'argv', ['fake_game', '--ready-file', str(ready),
        '--fps-file', str(fps), '--frametime-file', str(frames), '--load', '4',
        '--duration', '.5' if mode == 'duration' else '0'])
    if mode == 'error':
        with pytest.raises(RuntimeError, match='render failed'):
            game.main()
    else:
        assert game.main() == 0
    assert dpg.destroyed
    assert dpg.stopped == (mode == 'duration')
    assert json.loads(ready.read_text())['ready'] is True
    payload = json.loads(fps.read_text())
    assert set(payload) == {'fps', 'frames', 't'}
    assert payload == {'fps': 1.67, 'frames': 1, 't': -1000}
    with frames.open() as f:
        records = list(csv.DictReader(f))
    assert len(records) == rows
    assert [float(r['timestamp']) for r in records] == [1000, -1000, 9000][:rows]
    assert [float(r['frame_time_ms']) for r in records] == pytest.approx([10, 600, 20][:rows])
    assert ('10.00 ms' if mode == 'duration' else '600.00 ms') in dpg.values[-1]
    assert dpg.quads >= rows * 6


def test_frame_file_failure_is_not_success(monkeypatch, tmp_path):
    dpg = FakeDPG('close', tmp_path / 'ready')
    monkeypatch.setitem(sys.modules, 'dearpygui', types.ModuleType('dearpygui'))
    monkeypatch.setitem(sys.modules, 'dearpygui.dearpygui', dpg)
    monkeypatch.setattr(sys, 'argv', ['fake_game', '--frametime-file', str(tmp_path / 'missing' / 'frames')])
    with pytest.raises(OSError):
        game.main()
    assert dpg.destroyed


def test_metrics_without_fps_file_and_close_failure(monkeypatch, tmp_path):
    dpg = FakeDPG('close', tmp_path / 'ready')
    monkeypatch.setitem(sys.modules, 'dearpygui', types.ModuleType('dearpygui'))
    monkeypatch.setitem(sys.modules, 'dearpygui.dearpygui', dpg)
    monkeypatch.setattr(game.time, 'perf_counter', lambda: dpg.clock)
    monkeypatch.setattr(game.time, 'time', lambda: 1000)
    monkeypatch.setattr(sys, 'argv', ['fake_game'])
    assert game.main() == 0
    assert 'FPS: 1.7' in dpg.values[-1]
    assert '600.00 ms' in dpg.values[-1]

    class BrokenClose:
        def write(self, value):
            return len(value)

        def close(self):
            raise OSError('frame CSV close failed')

    dpg.count = 0
    dpg.destroyed = False
    monkeypatch.setattr(game, 'open', lambda *a, **kw: BrokenClose(), raising=False)
    monkeypatch.setattr(sys, 'argv', ['fake_game', '--frametime-file', 'frames'])
    with pytest.raises(OSError, match='frame CSV close failed'):
        game.main()
    assert dpg.destroyed
