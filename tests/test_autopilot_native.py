"""Portable ABI and handle-lifetime checks; no Windows DLL is loaded."""
import ctypes
from types import SimpleNamespace as NS

import pytest
from core.autopilot import BOOL, DWORD, HANDLE, get_foreground_process_name


class NativeCall:
    def __init__(self, signature, result, body):
        self.signature, self.result, self.body = signature, result, body
        self.argtypes = self.restype = None

    def __call__(self, *args):
        assert self.argtypes == self.signature
        assert self.restype is self.result
        # Exercise ctypes conversions, including pointer-size handle admission.
        converted = [kind.from_param(arg) for kind, arg in zip(self.argtypes, args)]
        assert len(converted) == len(args)
        return self.body(*args)


@pytest.mark.parametrize('failure', [None, 'hwnd', 'thread', 'pid', 'open', 'query', 'exception', 'empty'])
def test_foreground_abi_and_close(failure):
    assert ctypes.sizeof(DWORD) == ctypes.sizeof(BOOL) == 4
    assert ctypes.sizeof(HANDLE) == ctypes.sizeof(ctypes.c_size_t)
    hwnd, handle = 0x123456789AB, 0x23456789ABC
    closed, opened = [], []
    path = 'C:\\' + '長' * 300 + '\\遊戲.exe'
    def pid(window, pointer):
        assert window == hwnd
        ctypes.cast(pointer, ctypes.POINTER(DWORD))[0] = 0 if failure == 'pid' else 54321
        return 0 if failure == 'thread' else 99
    def open_process(rights, inherit, process):
        assert (rights, inherit, process) == (0x1000, False, 54321)
        opened.append(process)
        return 0 if failure == 'open' else handle
    def query(process, flags, buffer, pointer):
        assert (process, flags) == (handle, 0)
        size = ctypes.cast(pointer, ctypes.POINTER(DWORD))
        assert size[0] == 32768
        if failure == 'exception':
            raise RuntimeError('native query failure')
        buffer.value = '' if failure == 'empty' else path
        size[0] = len(buffer.value)
        return 0 if failure == 'query' else 1
    user = NS(GetForegroundWindow=NativeCall([], HANDLE, lambda: 0 if failure == 'hwnd' else hwnd),
              GetWindowThreadProcessId=NativeCall([HANDLE, ctypes.POINTER(DWORD)], DWORD, pid))
    kernel = NS(OpenProcess=NativeCall([DWORD, BOOL, DWORD], HANDLE, open_process),
                QueryFullProcessImageNameW=NativeCall([HANDLE, DWORD, ctypes.POINTER(ctypes.c_wchar), ctypes.POINTER(DWORD)], BOOL, query),
                CloseHandle=NativeCall([HANDLE], BOOL, lambda h: closed.append(h) or 1))
    assert get_foreground_process_name(user, kernel) == ('遊戲.exe' if failure is None else None)
    assert closed == ([handle] if failure in (None, 'query', 'exception', 'empty') else [])
    assert opened == ([] if failure in ('hwnd', 'thread', 'pid') else [54321])
