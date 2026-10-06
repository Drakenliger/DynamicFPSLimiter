import ctypes


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]


def get_idle_duration():
    """Return seconds since last user input (mouse/keyboard) on Windows."""

    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(LASTINPUTINFO)

    get_last_input_info = ctypes.windll.user32.GetLastInputInfo
    get_last_input_info.argtypes = [ctypes.POINTER(LASTINPUTINFO)]
    get_last_input_info.restype = ctypes.c_int32  # Win32 BOOL is four bytes
    if not get_last_input_info(ctypes.byref(lii)):
        raise ctypes.WinError()

    # Prefer GetTickCount64 if available
    try:
        get_ticks = ctypes.windll.kernel32.GetTickCount64
        get_ticks.restype = ctypes.c_uint64
    except AttributeError:
        # fallback to 32-bit GetTickCount
        get_ticks = ctypes.windll.kernel32.GetTickCount
        get_ticks.restype = ctypes.c_uint32
    get_ticks.argtypes = []
    ticks = get_ticks()
    # dwTime is a DWORD; subtract in its unsigned 32-bit domain across wrap.
    delta_ms = (int(ticks) - int(lii.dwTime)) & 0xFFFFFFFF
    return delta_ms / 1000.0

def monitor_idle(threshold=5):
    """Return True if the user has been idle for at least *threshold* seconds."""
    try:
        return get_idle_duration() >= threshold
    except Exception:
        return False

if __name__ == "__main__":

    print(monitor_idle(5))
