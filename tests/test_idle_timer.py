"""A6: monitor_idle is a stateless, non-blocking idle check wired into app.py.

The low-level get_idle_duration() stays as the raw utility; monitor_idle wraps it
with threshold comparison and error tolerance. app.py must call monitor_idle
instead of get_idle_duration directly. These tests cover the behavior and guard
the source invariants.
"""
from pathlib import Path
import ctypes
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace

import pytest

from core import idle_timer

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
IDLE_TIMER = SRC_DIR / "core" / "idle_timer.py"
APP = SRC_DIR / "core" / "app.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_monitor_idle_returns_true_when_idle_past_threshold(monkeypatch):
    monkeypatch.setattr(idle_timer, "get_idle_duration", lambda: 20.0)
    assert idle_timer.monitor_idle(15) is True
    assert idle_timer.monitor_idle(30) is False


def test_monitor_idle_boundary_inclusive(monkeypatch):
    monkeypatch.setattr(idle_timer, "get_idle_duration", lambda: 5.0)
    assert idle_timer.monitor_idle(5) is True


def test_monitor_idle_error_tolerant_returns_false(monkeypatch):
    def _boom():
        raise RuntimeError("no user input info")

    monkeypatch.setattr(idle_timer, "get_idle_duration", _boom)
    assert idle_timer.monitor_idle(5) is False


def test_monitor_idle_non_blocking_no_debug_print_loop():
    src = _read(IDLE_TIMER)
    assert "while True:" not in src
    assert "get_idle_duration() >= threshold" in src
    assert "monitor_idle()" not in src


def test_app_uses_monitor_idle():
    src = _read(APP)
    assert "monitor_idle(cm.idle_fps_delay)" in src
    assert "idle_secs =" not in src
    assert "get_idle_duration" not in src


class FakeWin32Function:
    """Model ctypes' default signed 32-bit DLL return conversion."""

    def __init__(self, implementation):
        self.implementation = implementation
        self.restype = ctypes.c_int32
        self.argtypes = None
        self.calls = 0

    def __call__(self, *args):
        self.calls += 1
        return self.restype(self.implementation(*args)).value


def fake_idle_dlls(monkeypatch, ticks, last_input, *, fallback=False, success=1):
    def get_last_input(pointer):
        lii = pointer._obj
        assert lii.cbSize == ctypes.sizeof(lii) == 8
        lii.dwTime = last_input
        return success

    last = FakeWin32Function(get_last_input)
    tick = FakeWin32Function(lambda: ticks)
    kernel = SimpleNamespace(**{
        "GetTickCount" if fallback else "GetTickCount64": tick,
    })
    monkeypatch.setattr(idle_timer.ctypes, "windll", SimpleNamespace(
        user32=SimpleNamespace(GetLastInputInfo=last), kernel32=kernel,
    ), raising=False)
    return last, tick


@pytest.mark.parametrize("ticks,last_input,expected", [
    (0x80000010, 0x80000000, 0.016),  # default signed return would be negative
    ((1 << 32) + 5000, 4000, 1.0),  # uptime beyond the DWORD tick period
    ((3 << 32) + 20, 0xFFFFFFF0, 0.036),  # last input before wrap
    (1 << 32, 0xFFFFFFFF, 0.001),  # exact wrap boundary
])
def test_get_idle_duration_tick64(monkeypatch, ticks, last_input, expected):
    last, tick = fake_idle_dlls(monkeypatch, ticks, last_input, success=0x100)
    assert idle_timer.get_idle_duration() == expected
    assert tick.restype is ctypes.c_uint64
    assert tick.argtypes == []
    assert last.restype is ctypes.c_int32  # Windows BOOL, not one-byte c_bool
    assert len(last.argtypes) == 1
    assert issubclass(last.argtypes[0]._type_, ctypes.Structure)


@pytest.mark.parametrize("ticks,last_input,expected", [
    (0x80000010, 0x80000000, 0.016),
    (20, 0xFFFFFFF0, 0.036),
    (0, 0xFFFFFFFF, 0.001),
])
def test_get_idle_duration_tick32_fallback(monkeypatch, ticks, last_input, expected):
    _, tick = fake_idle_dlls(monkeypatch, ticks, last_input, fallback=True)
    assert idle_timer.get_idle_duration() == expected
    assert tick.restype is ctypes.c_uint32
    assert tick.argtypes == []


def test_get_idle_duration_failed_input(monkeypatch):
    last, tick = fake_idle_dlls(monkeypatch, 5000, 4000, success=0)
    error = OSError("GetLastInputInfo failed")
    monkeypatch.setattr(idle_timer.ctypes, "WinError", lambda: error, raising=False)
    with pytest.raises(OSError, match="GetLastInputInfo failed") as caught:
        idle_timer.get_idle_duration()
    assert caught.value is error
    assert idle_timer.monitor_idle() is False
    assert last.calls == 2
    assert tick.calls == 0


def test_get_idle_duration_concurrent_ctypes_conversion(monkeypatch):
    barrier = Barrier(2)

    class ConcurrentLastInputInfo(FakeWin32Function):
        def __call__(self, pointer):
            barrier.wait(timeout=5)
            self.argtypes[0].from_param(pointer)
            pointer._obj.dwTime = 4000
            return self.restype(1).value

    last = ConcurrentLastInputInfo(None)
    tick = FakeWin32Function(lambda: 5000)
    monkeypatch.setattr(idle_timer.ctypes, "windll", SimpleNamespace(
        user32=SimpleNamespace(GetLastInputInfo=last),
        kernel32=SimpleNamespace(GetTickCount64=tick),
    ), raising=False)

    with ThreadPoolExecutor(max_workers=2) as executor:
        calls = [executor.submit(idle_timer.get_idle_duration) for _ in range(2)]
        assert [call.result(timeout=10) for call in calls] == [1.0, 1.0]
