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


@pytest.fixture
def native_factory(monkeypatch):
    # Model use_last_error=True: each fake mutex call publishes its own error.
    last_error = 0
    monkeypatch.setattr(ctypes, 'get_last_error', lambda: last_error, raising=False)

    def make(error=0, handle=BIG):
        native = Native(error, handle)

        def create_mutex(*args):
            nonlocal last_error
            last_error = native.last_error
            return handle

        native.kernel.CreateMutexW = create_mutex
        return native

    return make


@pytest.mark.parametrize('error, handle', [(0, BIG), (183, BIG), (5, None)])
def test_fake_mutex_publishes_error_on_win32(monkeypatch, native_factory, error, handle):
    monkeypatch.setattr(si.sys, 'platform', 'win32')
    native = native_factory(error, handle)
    assert ctypes.get_last_error() == 0
    if error == 5:
        with pytest.raises(OSError) as exc:
            si.acquire(native)
        assert exc.value.errno == 5
        assert native.closed == [BIG + 1]
        assert native.signals == []
    elif error == 183:
        assert si.acquire(native) is None
        assert native.closed == [BIG, BIG + 1]
        assert native.signals == [BIG + 1]
        assert native.foregrounds == 0
    else:
        lease = si.acquire(native)
        assert lease.handle == BIG
        assert native.closed == []
        assert native.signals == []
        lease.close()
        assert native.closed == [BIG + 1, BIG]
    assert ctypes.get_last_error() == error


def test_retained_pointer_width_and_close_once(native_factory):
    native = native_factory()
    lease = si.acquire(native)
    assert lease.handle == BIG
    lease.activation_event()
    lease.close()
    lease.close()
    assert native.closed == [BIG + 1, BIG]


def test_duplicate_signals_and_closes_only_own_handles(native_factory):
    native = native_factory(183)
    assert si.acquire(native) is None
    assert native.closed == [BIG, BIG + 1]
    assert native.signals == [BIG + 1]
    assert native.foregrounds == 0


def test_null_fails_closed(native_factory):
    native = native_factory(5, None)
    with pytest.raises(OSError):
        si.acquire(native)
    assert native.closed == [BIG + 1]


def test_inherited_validation_and_ownership(native_factory):
    native = native_factory(183)
    lease = si.acquire(native, BIG)
    assert native.closed == [BIG + 2]
    lease.close()
    assert native.closed == [BIG + 2, BIG + 1, BIG]
    native = native_factory()
    native.kernel.CompareObjectHandles = lambda *a: False
    with pytest.raises(OSError):
        si.acquire(native, BIG)
    assert native.closed == [BIG, BIG + 2]


def test_event_creation_failure_fails_closed(native_factory):
    native = native_factory()
    native.kernel.CreateEventW = lambda *a: None
    with pytest.raises(OSError) as exc:
        si.acquire(native)
    assert 'Cannot create DFL activation event' in str(exc.value)

    native_inherited = native_factory()
    native_inherited.kernel.CreateEventW = lambda *a: None
    with pytest.raises(OSError) as exc:
        si.acquire(native_inherited, BIG)
    assert 'Cannot create DFL activation event' in str(exc.value)
    assert native_inherited.closed == [BIG + 2, BIG]


class KernelEvent:
    def __init__(self, name, manual_reset=False, initial_state=False):
        self.name = name
        self.manual_reset = manual_reset
        self.signaled = initial_state
        self.refcount = 0


class KernelMutex:
    def __init__(self, name):
        self.name = name
        self.refcount = 0


class SharedFakeKernel:
    def __init__(self):
        self.named_objects = {}
        self.handles = {}
        self.next_handle = 1000

    def alloc_handle(self, kobj):
        h = self.next_handle
        self.next_handle += 1
        kobj.refcount += 1
        self.handles[h] = kobj
        return h

    def CreateMutexW(self, native, lpMutexAttributes, bInitialOwner, lpName):
        if lpName in self.named_objects:
            kobj = self.named_objects[lpName]
            native.last_error = 183
        else:
            kobj = KernelMutex(lpName)
            self.named_objects[lpName] = kobj
            native.last_error = 0
        return self.alloc_handle(kobj)

    def CreateEventW(self, native, lpEventAttributes, bManualReset, bInitialState, lpName):
        if lpName in self.named_objects:
            kobj = self.named_objects[lpName]
            native.last_error = 183
        else:
            kobj = KernelEvent(lpName, bManualReset, bInitialState)
            self.named_objects[lpName] = kobj
            native.last_error = 0
        return self.alloc_handle(kobj)

    def OpenMutexW(self, native, dwDesiredAccess, bInheritHandle, lpName):
        if lpName in self.named_objects:
            kobj = self.named_objects[lpName]
            native.last_error = 0
            return self.alloc_handle(kobj)
        native.last_error = 2
        return 0

    def SetEvent(self, native, h):
        if h in self.handles:
            kobj = self.handles[h]
            if isinstance(kobj, KernelEvent):
                kobj.signaled = True
                return True
        return False

    def WaitForSingleObject(self, native, h, dwMilliseconds):
        if h in self.handles:
            kobj = self.handles[h]
            if isinstance(kobj, KernelEvent):
                if kobj.signaled:
                    if not kobj.manual_reset:
                        kobj.signaled = False
                    return 0
                return 258
        return 258

    def CloseHandle(self, native, h):
        if h not in self.handles:
            return False
        kobj = self.handles[h]
        del self.handles[h]
        kobj.refcount -= 1
        if kobj.refcount == 0:
            if kobj.name in self.named_objects and self.named_objects[kobj.name] is kobj:
                del self.named_objects[kobj.name]
        return True

    def CompareObjectHandles(self, native, h1, h2):
        return self.handles.get(h1) is not None and self.handles.get(h1) is self.handles.get(h2)

    def SetHandleInformation(self, native, h, dwMask, dwFlags):
        return h in self.handles


class FakeNativeShared:
    def __init__(self, shared_kernel):
        self.shared = shared_kernel
        self.last_error = 0
        self.foregrounds = 0
        self.kernel = SimpleNamespace(
            CreateMutexW=lambda *a: self.shared.CreateMutexW(self, *a),
            CreateEventW=lambda *a: self.shared.CreateEventW(self, *a),
            OpenMutexW=lambda *a: self.shared.OpenMutexW(self, *a),
            CloseHandle=lambda h: self.shared.CloseHandle(self, h),
            SetEvent=lambda h: self.shared.SetEvent(self, h),
            WaitForSingleObject=lambda h, ms: self.shared.WaitForSingleObject(self, h, ms),
            CompareObjectHandles=lambda h1, h2: self.shared.CompareObjectHandles(self, h1, h2),
            SetHandleInformation=lambda h, m, f: self.shared.SetHandleInformation(self, h, m, f),
        )

    def foreground(self):
        self.foregrounds += 1


def test_retained_activation_event_prevents_lost_signal_on_duplicate_interleaving(monkeypatch):
    import threading
    monkeypatch.setattr(si.sys, 'platform', 'win32')

    last_error = 0
    monkeypatch.setattr(ctypes, 'get_last_error', lambda: last_error, raising=False)

    shared = SharedFakeKernel()
    primary_native = FakeNativeShared(shared)
    duplicate_native = FakeNativeShared(shared)

    def make_mutex_wrapper(native):
        orig_mutex = native.kernel.CreateMutexW
        def create_mutex(*args):
            nonlocal last_error
            res = orig_mutex(*args)
            last_error = native.last_error
            return res
        return create_mutex

    primary_native.kernel.CreateMutexW = make_mutex_wrapper(primary_native)
    duplicate_native.kernel.CreateMutexW = make_mutex_wrapper(duplicate_native)

    primary_lease = si.acquire(primary_native)
    assert primary_lease is not None

    dup_lease = si.acquire(duplicate_native)
    assert dup_lease is None

    calls = []
    tray = SimpleNamespace(is_tray_active=True)

    def restore():
        calls.append(threading.get_ident())
        tray.is_tray_active = False

    tray.restore_from_tray = restore

    def foreground():
        calls.append('foreground')
        primary_native.foregrounds += 1

    primary_native.foreground = foreground

    primary_lease.poll_activation(tray)
    assert calls == [threading.get_ident(), 'foreground']
    assert not tray.is_tray_active
    assert primary_native.foregrounds == 1

    primary_lease.poll_activation(tray)
    assert calls == [threading.get_ident(), 'foreground']
    assert primary_native.foregrounds == 1

    primary_lease.close()
    assert shared.handles == {}
    assert shared.named_objects == {}


def test_activation_uses_real_tray_restore_on_poll_thread(native_factory):
    import threading
    native = native_factory()
    lease = si.acquire(native)
    calls = []
    tray = SimpleNamespace(is_tray_active=True)
    def restore():
        calls.append(threading.get_ident())
        tray.is_tray_active = False
    tray.restore_from_tray = restore
    duplicate = native_factory(183)
    assert si.acquire(duplicate) is None
    assert duplicate.foregrounds == 0
    assert tray.is_tray_active
    def foreground():
        assert not tray.is_tray_active
        calls.append('foreground')
        native.foregrounds += 1
    native.foreground = foreground
    lease.poll_activation(tray)
    assert calls == [threading.get_ident(), 'foreground']
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
    monkeypatch.setattr(si, 'acquire', lambda: order.append('acquire') or lease)
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


@pytest.mark.parametrize('frozen', [False, True])
def test_production_duplicate_activates_and_exits_zero(monkeypatch, frozen, native_factory):
    native = native_factory(183)
    monkeypatch.setattr(si, 'Native', lambda: native)
    monkeypatch.setattr(si.sys, 'platform', 'win32')
    monkeypatch.setattr(si.sys, 'frozen', frozen, raising=False)
    with pytest.raises(SystemExit) as exc:
        si.app_lease()
    assert exc.value.code == 0
    assert native.signals == [BIG + 1]
    assert native.closed == [BIG, BIG + 1]
    assert native.foregrounds == 0
