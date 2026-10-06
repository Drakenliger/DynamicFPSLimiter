import ctypes
import os
import sys
import types
from decimal import Decimal
from pathlib import Path

import pytest


class FakeDLLCalls:
    """Records DLL invocation sequence and parameters for contract verification."""

    def __init__(self):
        self.calls = []

    def load_profile(self, profile_bytes):
        self.calls.append(("LoadProfile", profile_bytes))

    def save_profile(self, profile_bytes):
        self.calls.append(("SaveProfile", profile_bytes))

    def get_profile_property(self, prop_bytes, ptr, size):
        self.calls.append(("GetProfileProperty", prop_bytes, size))
        return True

    def set_profile_property(self, prop_bytes, ptr, size):
        val = None
        if ptr:
            try:
                val = ctypes.cast(ptr, ctypes.POINTER(ctypes.c_int)).contents.value
            except Exception:
                val = None
        self.calls.append(("SetProfileProperty", prop_bytes, val, size))
        return True

    def delete_profile(self, profile_bytes):
        self.calls.append(("DeleteProfile", profile_bytes))

    def reset_profile(self, profile_bytes):
        self.calls.append(("ResetProfile", profile_bytes))

    def update_profiles(self):
        self.calls.append(("UpdateProfiles",))

    def set_flags(self, and_mask, xor_mask):
        self.calls.append(("SetFlags", and_mask, xor_mask))
        return 0


class StubLogger:
    def __init__(self):
        self.messages = []

    def add_log(self, message):
        self.messages.append(str(message))


@pytest.fixture
def rtss_controller_fake_dll(tmp_path, monkeypatch):
    import threading

    if sys.platform != "win32" and "winreg" not in sys.modules:
        monkeypatch.setitem(sys.modules, "winreg", types.ModuleType("winreg"))

    was_rtss_imported = "core.rtss_functions" in sys.modules

    from core.rtss_functions import RTSSController

    ctrl = object.__new__(RTSSController)
    rtss_dir = tmp_path / "RTSS"
    profiles_dir = rtss_dir / "Profiles"
    profiles_dir.mkdir(parents=True)
    (profiles_dir / "Global").write_text(
        "FramerateLimit=0\nLimitDenominator=1\n", encoding="utf-8"
    )

    ctrl.rtss_install_path = str(rtss_dir)
    ctrl.rtss_path = str(rtss_dir / "RTSSHooks64.dll")
    ctrl.logger = StubLogger()
    ctrl._profile_lock = threading.RLock()

    fake = FakeDLLCalls()
    ctrl.LoadProfile = fake.load_profile
    ctrl.SaveProfile = fake.save_profile
    ctrl.GetProfileProperty = fake.get_profile_property
    ctrl.SetProfileProperty = fake.set_profile_property
    ctrl.DeleteProfile = fake.delete_profile
    ctrl.ResetProfile = fake.reset_profile
    ctrl.UpdateProfiles = fake.update_profiles
    ctrl.SetFlags = fake.set_flags

    try:
        yield ctrl, fake
    finally:
        if not was_rtss_imported and "core.rtss_functions" in sys.modules:
            del sys.modules["core.rtss_functions"]


def test_global_decimal_5994_refresh_contract(rtss_controller_fake_dll):
    ctrl, fake = rtss_controller_fake_dll
    global_file = Path(ctrl.rtss_install_path) / "Profiles" / "Global"

    limit, denominator = ctrl.set_fractional_framerate("Global", Decimal("59.94"), update=False)

    assert limit == 5994
    assert denominator == 100

    content = global_file.read_text(encoding="utf-8")
    assert "LimitDenominator=100\n" in content

    # Contract: "Global" profile maps to empty API profile name b"" in LoadProfile,
    # SetProfileProperty, and SaveProfile calls, followed by UpdateProfiles.
    expected_calls = [
        ("LoadProfile", b""),
        ("SetProfileProperty", b"FramerateLimit", 5994, 4),
        ("SaveProfile", b""),
        ("UpdateProfiles",),
    ]
    assert fake.calls == expected_calls


def test_global_float_5994_refresh_contract(rtss_controller_fake_dll):
    ctrl, fake = rtss_controller_fake_dll
    global_file = Path(ctrl.rtss_install_path) / "Profiles" / "Global"

    limit, denominator = ctrl.set_fractional_framerate("Global", 59.94, update=False)

    assert limit == 5994
    assert denominator == 100

    content = global_file.read_text(encoding="utf-8")
    assert "LimitDenominator=100\n" in content

    # Ensure float 59.94 accurately rounds float(59.94)*100 to 5994 and does not truncate
    assert fake.calls == [
        ("LoadProfile", b""),
        ("SetProfileProperty", b"FramerateLimit", 5994, 4),
        ("SaveProfile", b""),
        ("UpdateProfiles",),
    ]


@pytest.mark.parametrize("global_name", ["global", "GLOBAL", ""])
def test_case_insensitive_global_profile_uses_empty_api_name(rtss_controller_fake_dll, global_name):
    ctrl, fake = rtss_controller_fake_dll
    global_file = Path(ctrl.rtss_install_path) / "Profiles" / "Global"

    limit, denominator = ctrl.set_fractional_framerate(global_name, Decimal("59.94"), update=False)

    assert (limit, denominator) == (5994, 100)

    content = global_file.read_text(encoding="utf-8")
    assert "LimitDenominator=100\n" in content

    assert fake.calls == [
        ("LoadProfile", b""),
        ("SetProfileProperty", b"FramerateLimit", 5994, 4),
        ("SaveProfile", b""),
        ("UpdateProfiles",),
    ]


def test_non_global_profile_uses_given_api_name(rtss_controller_fake_dll):
    ctrl, fake = rtss_controller_fake_dll
    game_file = Path(ctrl.rtss_install_path) / "Profiles" / "Game.exe.cfg"
    game_file.write_text("FramerateLimit=0\n", encoding="utf-8")

    limit, denominator = ctrl.set_fractional_framerate("Game.exe", Decimal("59.94"), update=False)

    assert (limit, denominator) == (5994, 100)
    assert "LimitDenominator=100\n" in game_file.read_text(encoding="utf-8")

    # Non-global profile passes encoded profile name to API
    assert fake.calls == [
        ("LoadProfile", b"Game.exe"),
        ("SetProfileProperty", b"FramerateLimit", 5994, 4),
        ("SaveProfile", b"Game.exe"),
        ("UpdateProfiles",),
    ]


def test_fractional_framerate_update_true_sequence(rtss_controller_fake_dll):
    ctrl, fake = rtss_controller_fake_dll
    global_file = Path(ctrl.rtss_install_path) / "Profiles" / "Global"

    limit, denominator = ctrl.set_fractional_framerate("Global", Decimal("59.94"), update=True)

    assert (limit, denominator) == (5994, 100)

    content = global_file.read_text(encoding="utf-8")
    assert "LimitDenominator=100\n" in content

    # When update=True, set_limit_denominator calls UpdateProfiles,
    # and set_profile_property calls UpdateProfiles.
    assert fake.calls == [
        ("UpdateProfiles",),
        ("LoadProfile", b""),
        ("SetProfileProperty", b"FramerateLimit", 5994, 4),
        ("SaveProfile", b""),
        ("UpdateProfiles",),
    ]


def test_integer_framerate_refresh_contract(rtss_controller_fake_dll):
    ctrl, fake = rtss_controller_fake_dll

    limit, denominator = ctrl.set_fractional_framerate("Global", 60, update=False)

    assert limit == 60
    assert denominator == 1

    content = (Path(ctrl.rtss_install_path) / "Profiles" / "Global").read_text(encoding="utf-8")
    assert "LimitDenominator=1\n" in content
    assert fake.calls == [
        ("LoadProfile", b""),
        ("SetProfileProperty", b"FramerateLimit", 60, 4),
        ("SaveProfile", b""),
        ("UpdateProfiles",),
    ]


def test_three_decimal_places_refresh_contract(rtss_controller_fake_dll):
    ctrl, fake = rtss_controller_fake_dll

    limit, denominator = ctrl.set_fractional_framerate("Global", Decimal("143.955"), update=False)

    assert limit == 143955
    assert denominator == 1000

    content = (Path(ctrl.rtss_install_path) / "Profiles" / "Global").read_text(encoding="utf-8")
    assert "LimitDenominator=1000\n" in content
    assert fake.calls == [
        ("LoadProfile", b""),
        ("SetProfileProperty", b"FramerateLimit", 143955, 4),
        ("SaveProfile", b""),
        ("UpdateProfiles",),
    ]
