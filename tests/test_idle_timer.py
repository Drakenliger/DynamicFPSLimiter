"""GUI-004 long-uptime idle timer types and tick wraparound regression tests."""

import ctypes
import ctypes.wintypes
import unittest
from unittest.mock import MagicMock

from src.core.idle_timer import LASTINPUTINFO, Win32IdleAPI, get_idle_duration


def baseline_get_idle_duration(win32_api, mock_undeclared_signed_tick64=None):
    """Simulates the uncorrected baseline get_idle_duration logic for failure demonstration."""
    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(LASTINPUTINFO)

    if not win32_api.user32.GetLastInputInfo(ctypes.byref(lii)):
        win_error = getattr(ctypes, "WinError", OSError)
        raise win_error()

    try:
        if mock_undeclared_signed_tick64 is not None:
            ticks = mock_undeclared_signed_tick64
        else:
            ticks = win32_api.kernel32.GetTickCount64()
        delta_ms = (int(ticks) - int(lii.dwTime)) & ((1 << 64) - 1)
    except AttributeError:
        ticks = win32_api.kernel32.GetTickCount()
        delta_ms = (int(ticks) - int(lii.dwTime)) & 0xFFFFFFFF
    return delta_ms / 1000.0


class TestIdleTimerRegressions(unittest.TestCase):
    def _create_mock_win32_api(
        self,
        dw_time=0,
        ticks_64=None,
        ticks_32=None,
        last_input_success=True,
        has_get_tick_count_64=True,
    ):
        user32 = MagicMock()
        kernel32 = MagicMock()

        def mock_get_last_input_info(lii_ptr):
            if not last_input_success:
                return 0
            lii = getattr(lii_ptr, "_obj", getattr(lii_ptr, "contents", None))
            if lii is not None:
                lii.dwTime = dw_time & 0xFFFFFFFF
            return 1

        user32.GetLastInputInfo = MagicMock(side_effect=mock_get_last_input_info)

        if has_get_tick_count_64:
            kernel32.GetTickCount64 = MagicMock(
                return_value=ticks_64 if ticks_64 is not None else dw_time
            )
        else:
            del kernel32.GetTickCount64  # Ensure AttributeError on access

        if ticks_32 is not None or not has_get_tick_count_64:
            kernel32.GetTickCount = MagicMock(
                return_value=ticks_32 if ticks_32 is not None else dw_time
            )

        return Win32IdleAPI(user32=user32, kernel32=kernel32)

    def test_declarations_applied_to_win32_functions(self):
        user32 = MagicMock()
        kernel32 = MagicMock()

        api = Win32IdleAPI(user32=user32, kernel32=kernel32)

        self.assertEqual(
            user32.GetLastInputInfo.argtypes, [ctypes.POINTER(LASTINPUTINFO)]
        )
        self.assertEqual(
            user32.GetLastInputInfo.restype,
            getattr(ctypes.wintypes, "BOOL", ctypes.c_long),
        )

        self.assertEqual(kernel32.GetTickCount64.argtypes, [])
        self.assertEqual(kernel32.GetTickCount64.restype, ctypes.c_ulonglong)

        self.assertEqual(kernel32.GetTickCount.argtypes, [])
        self.assertEqual(kernel32.GetTickCount.restype, ctypes.c_ulong)

    def test_get_last_input_info_bool_return_256_truncation_regression(self):
        # Create a C function returning 256 (0x100)
        c_func_proto = ctypes.CFUNCTYPE(ctypes.c_int32, ctypes.c_void_p)

        def mock_c_func(lii_ptr):
            if lii_ptr:
                lii = ctypes.cast(lii_ptr, ctypes.POINTER(LASTINPUTINFO)).contents
                lii.dwTime = 1_000_000
            return 256  # Win32 BOOL non-zero return value 256

        raw_c_func = c_func_proto(mock_c_func)
        addr = ctypes.cast(raw_c_func, ctypes.c_void_p).value

        # Wrap address with CFUNCTYPE function pointer
        c_bool_func = ctypes.CFUNCTYPE(
            ctypes.c_bool, ctypes.POINTER(LASTINPUTINFO)
        )(addr)
        win_bool_func = ctypes.CFUNCTYPE(
            ctypes.wintypes.BOOL, ctypes.POINTER(LASTINPUTINFO)
        )(addr)

        user32_c_bool = MagicMock()
        user32_c_bool.GetLastInputInfo = c_bool_func

        user32_win_bool = MagicMock()
        user32_win_bool.GetLastInputInfo = win_bool_func

        kernel32 = MagicMock()
        kernel32.GetTickCount64 = MagicMock(return_value=1_005_000)

        api_c_bool = Win32IdleAPI(user32=user32_c_bool, kernel32=kernel32)
        # Explicitly test c_bool restype truncation
        api_c_bool.user32.GetLastInputInfo.restype = ctypes.c_bool

        api_win_bool = Win32IdleAPI(user32=user32_win_bool, kernel32=kernel32)

        # Demonstrate c_bool failure: returns False for 256, raising WinError
        with self.assertRaises(OSError):
            get_idle_duration(win32_api=api_c_bool)

        # Demonstrate wintypes.BOOL fix: returns 256 (truthy), succeeding with 5.0s
        result = get_idle_duration(win32_api=api_win_bool)
        self.assertEqual(result, 5.0)

    def test_near_2_to_31_sign_boundary(self):
        # 2^31 = 2,147,483,648 ms. Input was 5000 ms ago.
        tick_val = 0x80000000  # 2,147,483,648
        dw_time_val = tick_val - 5000

        # With undeclared restype (c_int), GetTickCount64 returned signed int -2147483648
        undeclared_signed_tick = -2147483648

        api = self._create_mock_win32_api(dw_time=dw_time_val, ticks_64=tick_val)

        # Confirm baseline failure with undeclared restype
        baseline_result = baseline_get_idle_duration(
            api, mock_undeclared_signed_tick64=undeclared_signed_tick
        )
        self.assertGreater(baseline_result, 1e12)  # Huge fictitious idle time

        # Confirm fix
        result = get_idle_duration(win32_api=api)
        self.assertEqual(result, 5.0)

    def test_uptime_above_2_to_32_and_multiple_wraps_with_recent_input(self):
        # Case A: Uptime > 2^32 ms (5,000,000,000 ms = ~57.8 days)
        # Input 100 seconds (100,000 ms) ago -> dwTime wraps to 704,932,704
        ticks_64_a = 5_000_000_000
        dw_time_a = (ticks_64_a - 100_000) & 0xFFFFFFFF

        api_a = self._create_mock_win32_api(dw_time=dw_time_a, ticks_64=ticks_64_a)

        # Baseline failed by returning ~49.7 days of idle time (> 4,000,000s)
        baseline_a = baseline_get_idle_duration(api_a)
        self.assertGreater(baseline_a, 4_000_000.0)

        # Fix correctly computes 100.0s
        result_a = get_idle_duration(win32_api=api_a)
        self.assertEqual(result_a, 100.0)

        # Case B: Multiple wraps (> 2 * 2^32 ms = 10,000,000,000 ms = ~115.7 days)
        # Input 50 seconds (50,000 ms) ago
        ticks_64_b = 10_000_000_000
        dw_time_b = (ticks_64_b - 50_000) & 0xFFFFFFFF

        api_b = self._create_mock_win32_api(dw_time=dw_time_b, ticks_64=ticks_64_b)

        # Baseline failed by returning ~99.4 days of idle time (> 8,000,000s)
        baseline_b = baseline_get_idle_duration(api_b)
        self.assertGreater(baseline_b, 8_000_000.0)

        # Fix correctly computes 50.0s
        result_b = get_idle_duration(win32_api=api_b)
        self.assertEqual(result_b, 50.0)

    def test_input_just_before_32bit_wrap_and_current_tick_just_after(self):
        # Input dwTime = 0xFFFFFF00 (4,294,967,040 ms)
        # Current tick = 0x00000100 (256 ms) -> elapsed delta = 512 ms
        dw_time = 0xFFFFFF00
        ticks_32 = 0x00000100

        # Test both 64-bit tick count wrapping or 32-bit tick count wrapping
        api = self._create_mock_win32_api(dw_time=dw_time, ticks_64=ticks_32)

        # Baseline with current tick 256 and dwTime 0xFFFFFF00 computes 64-bit negative overflow
        baseline = baseline_get_idle_duration(api)
        self.assertGreater(baseline, 1e12)

        # Fix correctly computes 0.512s
        result = get_idle_duration(win32_api=api)
        self.assertEqual(result, 0.512)

    def test_zero_and_ordinary_idle(self):
        # Zero idle duration
        api_zero = self._create_mock_win32_api(dw_time=1_000_000, ticks_64=1_000_000)
        self.assertEqual(get_idle_duration(win32_api=api_zero), 0.0)

        # Ordinary 5 second idle duration
        api_ordinary = self._create_mock_win32_api(
            dw_time=1_000_000, ticks_64=1_005_000
        )
        self.assertEqual(get_idle_duration(win32_api=api_ordinary), 5.0)

    def test_32bit_fallback_when_get_tick_count_64_unavailable(self):
        # GetTickCount64 unavailable (raises AttributeError), falls back to GetTickCount
        api_fallback = self._create_mock_win32_api(
            dw_time=1_000_000,
            ticks_32=1_005_000,
            has_get_tick_count_64=False,
        )
        self.assertEqual(get_idle_duration(win32_api=api_fallback), 5.0)

    def test_get_last_input_info_failure_propagation(self):
        api_fail = self._create_mock_win32_api(
            dw_time=1_000_000,
            ticks_64=1_005_000,
            last_input_success=False,
        )
        with self.assertRaises(OSError):
            get_idle_duration(win32_api=api_fail)

    def test_non_windows_import_isolation(self):
        # Instantiating Win32IdleAPI without ctypes.windll on non-Windows raises OSError
        if not hasattr(ctypes, "windll"):
            with self.assertRaises(OSError):
                Win32IdleAPI()


if __name__ == "__main__":
    unittest.main()
