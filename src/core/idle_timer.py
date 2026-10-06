import ctypes
import ctypes.wintypes
import time


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]


class Win32IdleAPI:
    """Provides typed Win32 user32 and kernel32 functions for idle measurement."""

    def __init__(self, user32=None, kernel32=None):
        if user32 is None or kernel32 is None:
            if not hasattr(ctypes, "windll"):
                raise OSError("ctypes.windll is not available on this platform")
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32

        self.user32 = user32
        self.kernel32 = kernel32

        if hasattr(user32, "GetLastInputInfo"):
            user32.GetLastInputInfo.argtypes = [ctypes.POINTER(LASTINPUTINFO)]
            user32.GetLastInputInfo.restype = getattr(
                ctypes.wintypes, "BOOL", ctypes.c_long
            )

        if hasattr(kernel32, "GetTickCount64"):
            kernel32.GetTickCount64.argtypes = []
            kernel32.GetTickCount64.restype = ctypes.c_ulonglong

        if hasattr(kernel32, "GetTickCount"):
            kernel32.GetTickCount.argtypes = []
            kernel32.GetTickCount.restype = ctypes.c_ulong


def get_idle_duration(win32_api=None):
    """Return seconds since last user input (mouse/keyboard) on Windows.

    Note:
        LASTINPUTINFO.dwTime is a 32-bit millisecond tick count supplied by Windows,
        which wraps every 2^32 milliseconds (~49.7 days). Both the current tick count
        and dwTime are evaluated in the same 32-bit unsigned tick domain using
        modular arithmetic ((ticks_32 - dwtime_32) & 0xFFFFFFFF).

        Because dwTime alone is a 32-bit value, dwTime alone cannot disambiguate
        actual idle intervals of 2^32 milliseconds (~49.7 days) or longer from
        shorter intervals with the same 32-bit tick residue.
    """
    if win32_api is None:
        win32_api = Win32IdleAPI()

    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(LASTINPUTINFO)

    if not win32_api.user32.GetLastInputInfo(ctypes.byref(lii)):
        win_error = getattr(ctypes, "WinError", OSError)
        raise win_error()

    try:
        ticks = win32_api.kernel32.GetTickCount64()
    except AttributeError:
        ticks = win32_api.kernel32.GetTickCount()

    ticks_32 = int(ticks) & 0xFFFFFFFF
    dwtime_32 = int(lii.dwTime) & 0xFFFFFFFF
    delta_ms = (ticks_32 - dwtime_32) & 0xFFFFFFFF

    return delta_ms / 1000.0


def monitor_idle(threshold=5, interval=0.5):
    """Monitor idle time."""
    while True:
        try:
            idle = get_idle_duration()
        except Exception as exc:
            print(f"[error] get_idle_duration() raised: {exc!r}", flush=True)
            time.sleep(max(0.5, interval))
            continue

        # always-print for debugging; keep verbose behavior for less output later
        print(f"[debug] idle={idle:.1f}s (threshold={threshold}s)", flush=True)

        if idle >= threshold:
            print(f"User idle for {int(idle)} seconds — triggering idle event.", flush=True)

        time.sleep(interval)


if __name__ == "__main__":
    monitor_idle()
