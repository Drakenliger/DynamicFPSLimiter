import os
import sys
import mmap
import struct
from pathlib import Path
from decimal import Decimal
import pytest

from core.rtss_functions import RTSSController, PROFILE_ENCODING
from core.rtss_interface import RTSSInterface, RTSS_PROCESS_ENCODING


def test_encoding_constants_platform_policy():
    """Verify core encoding policy matches platform expectation on both Windows and Linux."""
    if sys.platform == "win32":
        assert PROFILE_ENCODING == "mbcs"
        assert RTSS_PROCESS_ENCODING == "mbcs"
    else:
        assert PROFILE_ENCODING == "latin1"
        assert RTSS_PROCESS_ENCODING == "cp1252"


def test_profile_non_utf8_bytes_get_framerate_limit(rtss_stub):
    """Reading framerate limit from profile containing non-UTF8 byte 0xb0 works without UnicodeDecodeError."""
    global_file = Path(rtss_stub.rtss_install_path) / "Profiles" / "Global"
    global_file.write_bytes(
        b"[OSD]\nComment=Degree \xb0 symbol\n[Framerate]\nLimit=60\nLimitDenominator=1\n"
    )

    rtss_stub.get_profile_property = lambda *a, **k: (60).to_bytes(4, byteorder="little", signed=True)
    limit = rtss_stub.get_framerate_limit("Global", get_denominator=True)
    assert limit == 60.0


def test_profile_non_utf8_bytes_set_limit_denominator(rtss_stub):
    """set_limit_denominator updates LimitDenominator while preserving non-UTF8 bytes like 0xb0."""
    global_file = Path(rtss_stub.rtss_install_path) / "Profiles" / "Global"
    raw_content = b"[OSD]\nComment=Degree \xb0 symbol\n[Framerate]\nLimit=60\nLimitDenominator=1\n"
    global_file.write_bytes(raw_content)

    assert rtss_stub.set_limit_denominator("Global", 100, update=False) is True

    updated_bytes = global_file.read_bytes()
    assert b"LimitDenominator=100\n" in updated_bytes
    assert b"Comment=Degree \xb0 symbol\n" in updated_bytes


def test_profile_non_utf8_bytes_set_fractional_fps_direct(rtss_stub):
    """set_fractional_fps_direct updates Limit and LimitDenominator while preserving non-UTF8 bytes."""
    global_file = Path(rtss_stub.rtss_install_path) / "Profiles" / "Global"
    global_file.write_bytes(
        b"[OSD]\nSetting=Caf\xe9 \xb0\n[Framerate]\nLimit=30\nLimitDenominator=1\n"
    )

    assert rtss_stub.set_fractional_fps_direct("Global", 59.94, update=False) is True

    updated_bytes = global_file.read_bytes()
    assert b"Limit=5994\n" in updated_bytes
    assert b"LimitDenominator=100\n" in updated_bytes
    assert b"Setting=Caf\xe9 \xb0\n" in updated_bytes


def test_profile_non_utf8_bytes_set_fractional_framerate(rtss_stub):
    """set_fractional_framerate handles profiles with non-UTF8 bytes without error."""
    global_file = Path(rtss_stub.rtss_install_path) / "Profiles" / "Global"
    global_file.write_bytes(
        b"[OSD]\nSetting=Caf\xe9 \xb0\n[Framerate]\nLimit=30\nLimitDenominator=1\n"
    )

    limit, denom = rtss_stub.set_fractional_framerate("Global", 143.95, update=False)
    assert (limit, denom) == (14395, 100)

    updated_bytes = global_file.read_bytes()
    assert b"LimitDenominator=100\n" in updated_bytes
    assert b"Setting=Caf\xe9 \xb0\n" in updated_bytes


def test_process_name_decoding_cafe_accent_preserved(stub_logger, fake_dpg, monkeypatch):
    """Shared-memory process names containing ANSI characters (Café.exe) decode without losing accents."""
    interface = RTSSInterface(stub_logger, fake_dpg)

    monkeypatch.setattr(interface, "is_rtss_running", lambda: True)
    monkeypatch.setattr(interface, "_get_foreground_window_process_id", lambda: 1234)

    # Header size: 36 bytes (<4s8I)
    # Signature b'RTSS' packed as 4s -> dwSignature[::-1] in [b'RTSS', b'SSTR']
    hdr = struct.pack('<4s8I', b'RTSS', 0x00020000, 284, 36, 1, 0, 0, 0, 0)
    raw_name = b'C:\\Games\\Caf\xe9.exe\x00' + b'\x00' * (260 - len(b'C:\\Games\\Caf\xe9.exe\x00'))
    app_entry = struct.pack('<I260s5I', 1234, raw_name, 0, 100, 1100, 60, 16)

    mmap_data = bytearray(hdr + app_entry + b'\x00' * 1000)

    class MockMMap:
        def __getitem__(self, item):
            return mmap_data[item]

    monkeypatch.setattr(mmap, "mmap", lambda *args, **kwargs: MockMMap())

    fps, process_name = interface.get_fps_for_active_window()
    assert fps == Decimal(60), f"Logs: {stub_logger.messages}"
    assert process_name == "Café.exe"


def test_profile_api_string_encoding_non_ascii(rtss_stub):
    """DLL profile API methods encode non-ASCII profile/property names using PROFILE_ENCODING."""
    calls = []

    def _load_profile(pname):
        calls.append(("LoadProfile", pname))

    def _save_profile(pname):
        calls.append(("SaveProfile", pname))

    def _get_prop(prop, ptr, size):
        calls.append(("GetProfileProperty", prop))
        return True

    def _set_prop(prop, ptr, size):
        calls.append(("SetProfileProperty", prop))
        return True

    def _delete_profile(pname):
        calls.append(("DeleteProfile", pname))

    def _reset_profile(pname):
        calls.append(("ResetProfile", pname))

    rtss_stub.LoadProfile = _load_profile
    rtss_stub.SaveProfile = _save_profile
    rtss_stub.GetProfileProperty = _get_prop
    rtss_stub.SetProfileProperty = _set_prop
    rtss_stub.DeleteProfile = _delete_profile
    rtss_stub.ResetProfile = _reset_profile

    # Test get_profile_property with non-ASCII profile name
    rtss_stub.get_profile_property("Café.exe", "FramerateLimit")
    assert ("LoadProfile", b"Caf\xe9.exe") in calls
    assert ("GetProfileProperty", b"FramerateLimit") in calls

    calls.clear()
    # Test set_profile_property with non-ASCII profile name
    rtss_stub.set_profile_property("Café.exe", "FramerateLimit", 60)
    assert ("LoadProfile", b"Caf\xe9.exe") in calls
    assert ("SetProfileProperty", b"FramerateLimit") in calls
    assert ("SaveProfile", b"Caf\xe9.exe") in calls

    calls.clear()
    # Test delete_profile
    rtss_stub.delete_profile("Café.exe")
    assert ("DeleteProfile", b"Caf\xe9.exe") in calls

    calls.clear()
    # Test reset_profile
    rtss_stub.reset_profile("Café.exe")
    assert ("ResetProfile", b"Caf\xe9.exe") in calls

    calls.clear()
    # Test create_profile
    rtss_stub.create_profile("Café.exe", {"FramerateLimit": 60})
    assert ("SetProfileProperty", b"FramerateLimit") in calls
    assert ("SaveProfile", b"Caf\xe9.exe") in calls
