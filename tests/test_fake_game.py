import csv
import importlib.util
import io
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
        '--preset', 'heavy',
        '--title', 'custom', '--width', '640', '--height', '480', '--load', '12',
        '--fps-file', 'fps', '--ready-file', 'ready', '--duration', '2',
        '--no-vsync', '--frametime-file', 'frames'])
    assert vars(args) == dict(preset='heavy', title='custom', width=640, height=480, load=12,
                             fps_file='fps', ready_file='ready', duration=2,
                             no_vsync=True, frametime_file='frames')


class FakeDPG(types.ModuleType):
    def __init__(self, mode, ready):
        super().__init__('dearpygui.dearpygui')
        self.mode, self.ready = mode, ready
        self.count = 0
        self.clock = 10.0
        self.destroyed = self.stopped = False
        self.context_created = False
        self.create_calls = self.destroy_calls = 0
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

    def create_context(self):
        self.create_calls += 1
        assert not self.context_created
        if self.mode == 'create_error':
            raise RuntimeError('context creation failed')
        self.context_created = True

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
        self.destroy_calls += 1
        assert self.context_created
        self.context_created = False
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
    fps_records = [json.loads(line) for line in fps.read_text().splitlines() if line]
    assert len(fps_records) == 2
    for record in fps_records:
        assert set(record) == {'fps', 'frames', 't'}
    assert fps_records[0] == {'fps': 100.0, 'frames': 1, 't': 1000}
    assert fps_records[1] == {'fps': 1.67, 'frames': 1, 't': -1000}
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
    with pytest.raises(FileNotFoundError) as error:
        game.main()
    assert error.value.filename == str(tmp_path / 'missing' / 'frames')
    assert dpg.create_calls == dpg.destroy_calls == 0
    assert not dpg.context_created
    assert not dpg.destroyed


def test_context_creation_failure_closes_frame_file(monkeypatch, tmp_path):
    dpg = FakeDPG('create_error', tmp_path / 'ready')
    monkeypatch.setitem(sys.modules, 'dearpygui', types.ModuleType('dearpygui'))
    monkeypatch.setitem(sys.modules, 'dearpygui.dearpygui', dpg)
    frame_file = io.StringIO()
    monkeypatch.setattr(game, 'open', lambda *a, **kw: frame_file, raising=False)
    monkeypatch.setattr(sys, 'argv', ['fake_game', '--frametime-file', 'frames'])
    with pytest.raises(RuntimeError, match='context creation failed'):
        game.main()
    assert frame_file.closed
    assert dpg.create_calls == 1
    assert dpg.destroy_calls == 0
    assert not dpg.context_created
    assert not dpg.destroyed


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


def test_options_default_resolution_and_no_preset():
    args = game.build_arg_parser().parse_args([])
    assert args.preset is None
    assert args.width is None
    assert args.height is None
    assert args.load is None
    assert args.no_vsync is False
    resolved = game.resolve_options(args)
    assert resolved.width == 1024
    assert resolved.height == 768
    assert resolved.load == 8
    assert resolved.preset is None

    res_dict = game.resolve_options()
    assert res_dict == {"preset": None, "width": 1024, "height": 768, "load": 8}


@pytest.mark.parametrize("preset,expected_width,expected_height,expected_load", [
    ("light", 1280, 720, 2),
    ("medium", 1920, 1080, 8),
    ("heavy", 1920, 1080, 24),
    ("extreme", 1920, 1080, 48),
])
def test_preset_definitions_and_resolution(preset, expected_width, expected_height, expected_load):
    assert game.PRESETS[preset] == {"width": expected_width, "height": expected_height, "load": expected_load}
    args = game.build_arg_parser().parse_args(["--preset", preset])
    resolved = game.resolve_options(args)
    assert resolved.width == expected_width
    assert resolved.height == expected_height
    assert resolved.load == expected_load
    assert resolved.preset == preset

    pure = game.resolve_options(preset=preset)
    assert pure == {"preset": preset, "width": expected_width, "height": expected_height, "load": expected_load}


def test_invalid_preset_rejected():
    with pytest.raises(SystemExit):
        game.build_arg_parser().parse_args(["--preset", "invalid_choice"])

    with pytest.raises(ValueError, match="Unknown preset: 'not_a_preset'"):
        game.resolve_options(preset="not_a_preset")


def test_preset_override_precedence():
    # Explicit load overrides preset load
    args = game.build_arg_parser().parse_args(["--preset", "heavy", "--load", "16"])
    resolved = game.resolve_options(args)
    assert resolved.width == 1920
    assert resolved.height == 1080
    assert resolved.load == 16
    assert resolved.preset == "heavy"

    # Explicit width overrides preset width
    args = game.build_arg_parser().parse_args(["--preset", "light", "--width", "800"])
    resolved = game.resolve_options(args)
    assert resolved.width == 800
    assert resolved.height == 720
    assert resolved.load == 2

    # Explicit height overrides preset height
    args = game.build_arg_parser().parse_args(["--preset", "extreme", "--height", "900"])
    resolved = game.resolve_options(args)
    assert resolved.width == 1920
    assert resolved.height == 900
    assert resolved.load == 48

    # Explicit width and height and load override everything
    args = game.build_arg_parser().parse_args([
        "--preset", "medium", "--width", "640", "--height", "480", "--load", "3"
    ])
    resolved = game.resolve_options(args)
    assert resolved.width == 640
    assert resolved.height == 480
    assert resolved.load == 3

    # Pure kwargs override
    pure = game.resolve_options(preset="heavy", load=10, width=1280)
    assert pure == {"preset": "heavy", "width": 1280, "height": 1080, "load": 10}

    # Dict input override
    d = {"preset": "light", "load": 5}
    res_d = game.resolve_options(d)
    assert res_d == {"preset": "light", "width": 1280, "height": 720, "load": 5}


class MultiSampleFakeDPG(types.ModuleType):
    def __init__(self):
        super().__init__('dearpygui.dearpygui')
        self.count = 0
        self.clock = 100.0
        self.destroyed = self.stopped = False
        self.context_created = False

    def __getattr__(self, name):
        if name == 'window':
            return lambda **kw: nullcontext()
        if name == 'get_viewport_client_width':
            return lambda: 1920
        if name == 'get_viewport_client_height':
            return lambda: 1080
        if name in ('add_text', 'add_drawlist'):
            return lambda *a, **kw: name
        return lambda *a, **kw: None

    def create_context(self):
        self.context_created = True

    def is_dearpygui_running(self):
        return self.count < 5 and not self.stopped

    def render_dearpygui_frame(self):
        self.clock += 0.6
        self.count += 1

    def destroy_context(self):
        self.context_created = False
        self.destroyed = True


def test_main_fps_file_writes_multiple_ordered_jsonl(monkeypatch, tmp_path):
    dpg = MultiSampleFakeDPG()
    monkeypatch.setitem(sys.modules, 'dearpygui', types.ModuleType('dearpygui'))
    monkeypatch.setitem(sys.modules, 'dearpygui.dearpygui', dpg)
    monkeypatch.setattr(game.time, 'perf_counter', lambda: dpg.clock)
    wall_clock = iter([1000.0, 1001.0, 1002.0, 1003.0, 1004.0, 1005.0])
    monkeypatch.setattr(game.time, 'time', lambda: next(wall_clock))

    fps_path = tmp_path / "telemetry.jsonl"
    ready_path = tmp_path / "ready.json"
    monkeypatch.setattr(sys, 'argv', [
        'fake_game', '--preset', 'heavy',
        '--fps-file', str(fps_path),
        '--ready-file', str(ready_path),
    ])

    ret = game.main()
    assert ret == 0
    assert dpg.destroyed

    ready_data = json.loads(ready_path.read_text(encoding="utf-8"))
    assert ready_data["ready"] is True
    assert ready_data["width"] == 1920
    assert ready_data["height"] == 1080
    assert ready_data["load"] == 24

    raw_text = fps_path.read_text(encoding="utf-8")
    assert raw_text.endswith("\n")
    lines = raw_text.splitlines()
    assert len(lines) == 5

    parsed = [json.loads(line) for line in lines]
    timestamps = [sample["t"] for sample in parsed]
    assert timestamps == [1000.0, 1001.0, 1002.0, 1003.0, 1004.0]
    for sample in parsed:
        assert set(sample) == {"fps", "frames", "t"}
        assert sample["frames"] == 1
        assert sample["fps"] > 0


def test_main_fps_file_appends_to_existing_history(monkeypatch, tmp_path):
    dpg = MultiSampleFakeDPG()
    monkeypatch.setitem(sys.modules, 'dearpygui', types.ModuleType('dearpygui'))
    monkeypatch.setitem(sys.modules, 'dearpygui.dearpygui', dpg)
    monkeypatch.setattr(game.time, 'perf_counter', lambda: dpg.clock)
    wall_clock = iter([2000.0, 2001.0, 2002.0, 2003.0, 2004.0, 2005.0])
    monkeypatch.setattr(game.time, 'time', lambda: next(wall_clock))

    fps_path = tmp_path / "history.jsonl"
    existing_line = '{"fps": 60.0, "frames": 30, "t": 1999.0}\n'
    fps_path.write_text(existing_line, encoding="utf-8")

    monkeypatch.setattr(sys, 'argv', [
        'fake_game', '--preset', 'light',
        '--fps-file', str(fps_path),
    ])

    assert game.main() == 0

    lines = fps_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 6
    assert json.loads(lines[0]) == {"fps": 60.0, "frames": 30, "t": 1999.0}
    new_samples = [json.loads(line) for line in lines[1:]]
    assert len(new_samples) == 5
    assert all(set(s) == {"fps", "frames", "t"} for s in new_samples)
    assert [s["t"] for s in new_samples] == [2000.0, 2001.0, 2002.0, 2003.0, 2004.0]


def test_main_fps_file_io_error_handling(monkeypatch, tmp_path):
    dpg = FakeDPG('close', tmp_path / 'ready')
    monkeypatch.setitem(sys.modules, 'dearpygui', types.ModuleType('dearpygui'))
    monkeypatch.setitem(sys.modules, 'dearpygui.dearpygui', dpg)
    monkeypatch.setattr(game.time, 'perf_counter', lambda: dpg.clock)
    monkeypatch.setattr(game.time, 'time', lambda: 1000)

    bad_fps_path = tmp_path / "non_existent_subdir" / "fps.jsonl"
    monkeypatch.setattr(sys, 'argv', ['fake_game', '--fps-file', str(bad_fps_path)])

    assert game.main() == 0
    assert dpg.destroyed


def test_main_ready_file_io_error_handling(monkeypatch, tmp_path, capsys):
    dpg = FakeDPG('close', tmp_path / 'ready')
    monkeypatch.setitem(sys.modules, 'dearpygui', types.ModuleType('dearpygui'))
    monkeypatch.setitem(sys.modules, 'dearpygui.dearpygui', dpg)
    monkeypatch.setattr(game.time, 'perf_counter', lambda: dpg.clock)
    monkeypatch.setattr(game.time, 'time', lambda: 1000)

    bad_ready_path = tmp_path / "non_existent_subdir" / "ready.json"
    monkeypatch.setattr(sys, 'argv', ['fake_game', '--ready-file', str(bad_ready_path)])

    assert game.main() == 0
    assert dpg.destroyed
    captured = capsys.readouterr()
    assert "[fake_game] failed to write ready-file:" in captured.out
