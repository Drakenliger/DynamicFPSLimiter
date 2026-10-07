import ast
import ctypes
from pathlib import Path
from types import SimpleNamespace

import pytest
from core import single_instance as si

ROOT = Path(__file__).resolve().parents[1]
BIG = 0x1234567887654321


class Native:
    def __init__(self, error=0, handle=BIG):
        self.last_error = error
        self.closed = []
        self.signals = []
        self.foregrounds = 0
        self.kernel = SimpleNamespace(
            CreateMutexW=lambda *a: handle,
            CreateEventW=lambda *a: BIG + 1,
            CloseHandle=self.closed.append,
            SetEvent=self.signals.append,
            WaitForSingleObject=lambda *a: 0,
            OpenMutexW=lambda *a: BIG + 2,
            CompareObjectHandles=lambda *a: True,
            SetHandleInformation=lambda *a: True)

    def foreground(self):
        self.foregrounds += 1


def test_retained_pointer_width_and_close_once():
    native = Native()
    lease = si.acquire(native)
    assert lease.handle == BIG
    lease.activation_event()
    lease.close()
    lease.close()
    assert native.closed == [BIG + 1, BIG]


def test_duplicate_signals_and_closes_only_own_handles():
    native = Native(183)
    assert si.acquire(native) is None
    assert native.closed == [BIG, BIG + 1]
    assert native.signals == [BIG + 1]
    assert native.foregrounds == 1


def test_null_fails_closed():
    native = Native(5, None)
    with pytest.raises(OSError):
        si.acquire(native)
    assert native.closed == []


def test_inherited_validation_and_ownership():
    native = Native(183)
    lease = si.acquire(native, BIG)
    assert native.closed == [BIG + 2]
    lease.close()
    assert native.closed == [BIG + 2, BIG]
    native = Native()
    native.kernel.CompareObjectHandles = lambda *a: False
    with pytest.raises(OSError):
        si.acquire(native, BIG)
    assert native.closed == [BIG, BIG + 2]


def test_activation_uses_real_tray_restore_on_poll_thread():
    import threading
    native = Native()
    lease = si.acquire(native)
    calls = []
    tray = SimpleNamespace(is_tray_active=True)
    def restore():
        calls.append(threading.get_ident())
        tray.is_tray_active = False
    tray.restore_from_tray = restore
    lease.poll_activation(tray)
    assert calls == [threading.get_ident()]
    assert not tray.is_tray_active
    assert native.foregrounds == 1
    lease.close()


def test_native_handle_signatures(monkeypatch):
    class Function:
        pass
    class DLL:
        def __getattr__(self, name):
            fn = Function()
            setattr(self, name, fn)
            return fn
    monkeypatch.setattr(ctypes, 'WinDLL', lambda *a, **k: DLL(), raising=False)
    native = si.Native()
    for name in ('CreateMutexW', 'OpenMutexW', 'CreateEventW'):
        assert getattr(native.kernel, name).restype is ctypes.c_void_p
    assert native.kernel.CloseHandle.argtypes == [ctypes.c_void_p]
    assert native.kernel.WaitForSingleObject.argtypes[0] is ctypes.c_void_p


def test_app_duplicate_exits_before_imports(monkeypatch):
    source = (ROOT / 'src/core/app.py').read_text()
    prefix = source[:source.index('import dearpygui.dearpygui')]
    monkeypatch.setattr(si, 'app_lease', lambda *a: (_ for _ in ()).throw(SystemExit(0)))
    with pytest.raises(SystemExit):
        exec(compile(prefix, 'app.py', 'exec'), {'__file__': str(ROOT / 'src/core/app.py')})
    assert source.index('app_lease(') < source.index('from core.pre_launch')
    entry = (ROOT / 'src/__main__.py').read_text()
    assert "'src/core/app.py'" in entry
    assert 'single_instance' not in entry  # UAC parent/build never holds admission.


def test_acceptance_supervisor_lease_covers_restore(monkeypatch):
    source = (ROOT / 'tests/acceptance_windows.py').read_text()
    tree = ast.parse(source)
    run = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'run')
    order = []
    lease = SimpleNamespace(close=lambda: order.append('close'))
    monkeypatch.setattr(si, 'app_lease', lambda: order.append('acquire') or lease)
    def work(value):
        assert value is lease
        order.extend(['controller', 'snapshot', 'write', 'child_exit', 'restore'])
        raise RuntimeError('restore failure')
    namespace = {'sys': SimpleNamespace(platform='win32'), '_run_with_lease': work}
    exec(compile(ast.Module(body=[run], type_ignores=[]), 'acceptance', 'exec'), namespace)
    with pytest.raises(RuntimeError):
        namespace['run']()
    assert order == ['acquire', 'controller', 'snapshot', 'write', 'child_exit', 'restore', 'close']
    assert "'handle_list': [lease.handle]" in source
    assert 'close_fds=True' in source
    assert "'_single_instance_handle': instance_handle" in source
