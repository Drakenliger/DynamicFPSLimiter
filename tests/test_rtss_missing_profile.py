"""C2 regression tests: handle missing RTSS game profile .cfg creation and denominator setting.

Verifies that setting a fractional framerate for a missing game profile:
- Selects Global/base profile before calling SaveProfile
- Inherits intended Global default settings rather than last loaded game settings
- Sets both Limit (numerator 5994) and LimitDenominator (100) in file/DLL
- Reads back correct fractional FPS (59.94)
- Leaves Global and other profile settings unchanged
- Propagates False on creation or denominator failure without misleading success log
- Preserves unrelated settings for existing profiles
"""
import ctypes
import os
import re
from pathlib import Path
import pytest


def _profile_file(rtss_stub, name="Global"):
    if not name or name.lower() == "global":
        return Path(rtss_stub.rtss_install_path) / "Profiles" / "Global"
    return Path(rtss_stub.rtss_install_path) / "Profiles" / f"{name}.cfg"


class StatefulDLLMock:
    """Stateful mock of RTSS DLL profile API.

    Tracks active loaded profile state and property dictionaries across
    LoadProfile, SetProfileProperty, GetProfileProperty, and SaveProfile calls.
    Updates .cfg files on disk while preserving non-DLL managed keys (e.g. LimitDenominator).
    """

    def __init__(self, rtss_stub):
        self.rtss_stub = rtss_stub
        self.profiles = {
            b"": {"FramerateLimit": 0, "OSDPositionX": 0},
        }
        self.active_profile = b""
        self.active_properties = dict(self.profiles[b""])
        self.allow_save = True

    def load_profile(self, name_bytes):
        self.active_profile = name_bytes
        if name_bytes in self.profiles:
            self.active_properties = dict(self.profiles[name_bytes])

    def set_profile_property(self, prop_bytes, ptr, size):
        prop_str = prop_bytes.decode("latin1")
        val = int.from_bytes(ctypes.string_at(ptr, size), byteorder="little", signed=True)
        self.active_properties[prop_str] = val
        return True

    def get_profile_property(self, prop_bytes, ptr, size):
        prop_str = prop_bytes.decode("latin1")
        if prop_str in self.active_properties:
            val = self.active_properties[prop_str]
            val_bytes = val.to_bytes(size, byteorder="little", signed=True)
            ctypes.memmove(ptr, val_bytes, size)
            return True
        return False

    def save_profile(self, name_bytes):
        if not self.allow_save:
            return
        name = name_bytes.decode("latin1")
        self.profiles[name_bytes] = dict(self.active_properties)

        pfile = _profile_file(self.rtss_stub, name)
        limit = self.active_properties.get("FramerateLimit", 0)

        if pfile.exists():
            text = pfile.read_text(encoding="latin1")
            # Update Limit= in [Framerate] section or add section if missing
            if re.search(r"^Limit=\d+", text, flags=re.MULTILINE):
                text = re.sub(r"^Limit=\d+", f"Limit={limit}", text, flags=re.MULTILINE)
            elif "[Framerate]" in text:
                text = text.replace("[Framerate]\n", f"[Framerate]\nLimit={limit}\n")
            else:
                text += f"\n[Framerate]\nLimit={limit}\n"

            osd_x = self.active_properties.get("OSDPositionX")
            if osd_x is not None:
                if re.search(r"^OSDPositionX=\d+", text, flags=re.MULTILINE):
                    text = re.sub(r"^OSDPositionX=\d+", f"OSDPositionX={osd_x}", text, flags=re.MULTILINE)
                elif "[OSD]" in text:
                    text = text.replace("[OSD]\n", f"[OSD]\nOSDPositionX={osd_x}\n")
                else:
                    text = f"[OSD]\nOSDPositionX={osd_x}\n" + text
            pfile.write_text(text, encoding="latin1")
        else:
            lines = []
            osd_x = self.active_properties.get("OSDPositionX")
            if osd_x is not None and osd_x != 0:
                lines.append(f"[OSD]\nOSDPositionX={osd_x}\n")

            lines.append(f"[Framerate]\nLimit={limit}\n")
            pfile.write_text("".join(lines), encoding="latin1")


def _install_stateful_mock(rtss_stub):
    mock = StatefulDLLMock(rtss_stub)
    rtss_stub.LoadProfile = mock.load_profile
    rtss_stub.SetProfileProperty = mock.set_profile_property
    rtss_stub.GetProfileProperty = mock.get_profile_property
    rtss_stub.SaveProfile = mock.save_profile
    return mock


def test_missing_profile_inherits_global_defaults_and_sets_fractional_fps(rtss_stub):
    """Missing profile inherits Global defaults (not previously loaded game) and sets 5994/100."""
    mock = _install_stateful_mock(rtss_stub)

    # 1. Mutate OtherGame.exe to have custom OSD setting
    rtss_stub.set_profile_property("OtherGame.exe", "OSDPositionX", 999)
    other_cfg = _profile_file(rtss_stub, "OtherGame.exe")
    assert "OSDPositionX=999" in other_cfg.read_text(encoding="latin1")

    new_cfg = _profile_file(rtss_stub, "NewGame.exe")
    assert not new_cfg.exists()

    # 2. Set fractional framerate for missing NewGame.exe
    result = rtss_stub.set_fractional_framerate("NewGame.exe", 59.94, update=False)
    assert result == (5994, 100)

    # 3. Verify NewGame.exe created and inherited Global defaults (no OSDPositionX=999)
    assert new_cfg.exists()
    content = new_cfg.read_text(encoding="latin1")
    assert "LimitDenominator=100" in content
    assert "Limit=5994" in content
    assert "OSDPositionX=999" not in content

    # 4. Verify readback
    assert rtss_stub.get_framerate_limit("NewGame.exe", get_denominator=True) == 59.94

    # 5. Verify Global and OtherGame settings remain unchanged
    assert "OSDPositionX=999" in other_cfg.read_text(encoding="latin1")
    global_cfg = _profile_file(rtss_stub, "Global")
    assert "OSDPositionX=999" not in global_cfg.read_text(encoding="latin1")


def test_missing_profile_creation_failure_returns_false_and_no_success_log(rtss_stub):
    """Creation failure returns False and suppresses misleading success log."""
    mock = _install_stateful_mock(rtss_stub)
    mock.allow_save = False  # SaveProfile fails to write file

    profile_name = "UncreatableGame.exe"
    result = rtss_stub.set_fractional_framerate(profile_name, 59.94, update=False)

    assert result is False
    assert not any(f"Set {profile_name}" in msg for msg in rtss_stub.logger.messages)


def test_direct_set_limit_denominator_on_missing_profile(rtss_stub):
    """Direct set_limit_denominator on missing profile loads Global base and creates file."""
    mock = _install_stateful_mock(rtss_stub)

    # Mutate OtherGame first
    rtss_stub.set_profile_property("OtherGame.exe", "OSDPositionX", 888)

    profile_name = "DirectGame.exe"
    cfg_path = _profile_file(rtss_stub, profile_name)
    assert not cfg_path.exists()

    success = rtss_stub.set_limit_denominator(profile_name, 100, update=False)
    assert success is True
    assert cfg_path.exists()

    content = cfg_path.read_text(encoding="latin1")
    assert "LimitDenominator=100" in content
    assert "OSDPositionX=888" not in content


def test_existing_profile_preserves_unrelated_settings(rtss_stub):
    """Updating fractional framerate on existing profile preserves unrelated sections and keys."""
    mock = _install_stateful_mock(rtss_stub)

    profile_name = "ExistingGame.exe"
    cfg_path = _profile_file(rtss_stub, profile_name)
    initial_content = "[OSD]\nPositionX=100\nPositionY=200\nLabel=Test\n[Framerate]\nLimit=60\n"
    cfg_path.write_text(initial_content, encoding="latin1")

    result = rtss_stub.set_fractional_framerate(profile_name, 59.94, update=False)
    assert result == (5994, 100)

    content = cfg_path.read_text(encoding="latin1")
    assert "[OSD]" in content
    assert "PositionX=100" in content
    assert "PositionY=200" in content
    assert "Label=Test" in content
    assert "LimitDenominator=100" in content
    assert rtss_stub.get_framerate_limit(profile_name, get_denominator=True) == 59.94
