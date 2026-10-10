"""Process lifetime admission and render-thread activation for the Windows app."""
import atexit
import ctypes
from ctypes import wintypes
import sys

MUTEX = r'Local\DynamicFPSLimiter.Instance'
EVENT = r'Local\DynamicFPSLimiter.Activate'
TITLE = 'Dynamic FPS Limiter'


class Native:
    def __init__(self):
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        self.user = ctypes.WinDLL('user32', use_last_error=True)
        self.kernel.CompareObjectHandles = ctypes.WinDLL(
            'kernelbase', use_last_error=True).CompareObjectHandles
        signatures = {
            'CreateMutexW': ([ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR], wintypes.HANDLE),
            'OpenMutexW': ([wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR], wintypes.HANDLE),
            'CreateEventW': ([ctypes.c_void_p, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR], wintypes.HANDLE),
            'CloseHandle': ([wintypes.HANDLE], wintypes.BOOL),
            'SetEvent': ([wintypes.HANDLE], wintypes.BOOL),
            'WaitForSingleObject': ([wintypes.HANDLE, wintypes.DWORD], wintypes.DWORD),
            'CompareObjectHandles': ([wintypes.HANDLE, wintypes.HANDLE], wintypes.BOOL),
            'SetHandleInformation': ([wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD], wintypes.BOOL),
        }
        for name, (args, result) in signatures.items():
            fn = getattr(self.kernel, name)
            fn.argtypes, fn.restype = args, result
        for name, args, result in [
            ('FindWindowW', [wintypes.LPCWSTR, wintypes.LPCWSTR], wintypes.HWND),
            ('ShowWindow', [wintypes.HWND, ctypes.c_int], wintypes.BOOL),
            ('SetForegroundWindow', [wintypes.HWND], wintypes.BOOL),
        ]:
            fn = getattr(self.user, name)
            fn.argtypes, fn.restype = args, result

    def foreground(self):
        hwnd = self.user.FindWindowW(None, TITLE)
        if hwnd:
            self.user.ShowWindow(hwnd, 9)  # SW_RESTORE
            self.user.SetForegroundWindow(hwnd)


class Lease:
    def __init__(self, native, handle, event=None):
        self.native, self.handle, self.event = native, handle, event
        atexit.register(self.close)

    def close(self):
        for attr in ('event', 'handle'):
            handle = getattr(self, attr)
            setattr(self, attr, None)
            if handle:
                self.native.kernel.CloseHandle(handle)

    def activation_event(self):
        if not self.event:
            self.event = self.native.kernel.CreateEventW(None, False, False, EVENT)
            if not self.event:
                raise OSError('Cannot create DFL activation event')
        return self.event

    def poll_activation(self, tray):
        if self.native.kernel.WaitForSingleObject(self.activation_event(), 0) == 0:
            tray.restore_from_tray()
            self.native.foreground()

    def inheritable(self, enabled):
        if not self.native.kernel.SetHandleInformation(self.handle, 1, int(enabled)):
            raise OSError('Cannot set DFL lease inheritance')


def acquire(native=None, inherited=None):
    """Return a retained lease, or None for a duplicate; errors fail closed."""
    if native is None:
        if sys.platform != 'win32':
            return None  # Portable app fixtures do not acquire Windows objects.
        native = Native()
    kernel = native.kernel
    if inherited is not None:
        # A numeric argument alone never grants admission: verify object identity.
        named = kernel.OpenMutexW(0x100000, False, MUTEX)
        try:
            if not named or not kernel.CompareObjectHandles(inherited, named):
                raise OSError('Invalid inherited DFL lease')
        except BaseException:
            kernel.CloseHandle(inherited)
            raise
        finally:
            if named:
                kernel.CloseHandle(named)
        event = kernel.CreateEventW(None, False, False, EVENT)
        if not event:
            kernel.CloseHandle(inherited)
            raise OSError('Cannot create DFL activation event')
        return Lease(native, inherited, event=event)
    event = kernel.CreateEventW(None, False, False, EVENT)
    if not event:
        raise OSError('Cannot create DFL activation event')
    handle = kernel.CreateMutexW(None, False, MUTEX)
    get_last_error = getattr(ctypes, 'get_last_error', None)
    error = get_last_error() if (sys.platform == 'win32' and get_last_error) else native.last_error
    if not handle:
        kernel.CloseHandle(event)
        raise OSError(error, 'Cannot acquire DFL instance lease')
    if error == 183:
        kernel.CloseHandle(handle)
        try:
            kernel.SetEvent(event)
        finally:
            kernel.CloseHandle(event)
        return None
    return Lease(native, handle, event=event)


def app_lease(inherited=None):
    lease = acquire(inherited=inherited)
    if sys.platform == 'win32' and lease is None:
        raise SystemExit(0)
    if lease:
        try:
            lease.activation_event()
        except BaseException:
            lease.close()
            raise
    return lease
