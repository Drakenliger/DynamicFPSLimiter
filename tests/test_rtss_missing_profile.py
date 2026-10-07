"""C2 regression tests: handle missing RTSS game profile .cfg creation and denominator setting.

Verifies that setting a fractional framerate for a missing game profile:
- Creates the .cfg file (or retries denominator after creation via SaveProfile)
- Successfully sets both Limit and LimitDenominator in the .cfg file
- Reads back the correct fractional FPS limit (e.g. 59.94)
- Propagates False if profile creation or denominator application fails
- Preserves unrelated settings when profile already exists
"""
import ctypes
from pathlib import Path
import pytest


def _profile_file(rtss_stub, name="Global"):
    if name.lower() == "global":
        return Path(rtss_stub.rtss_install_path) / "Profiles" / "Global"
    return Path(rtss_stub.rtss_install_path) / "Profiles" / f"{name}.cfg"


def test_missing_profile_fractional_fps_creation_and_readback(rtss_stub):
    """Fake DLL SaveProfile creates missing file; actual final cfg/API 59.94 means 5994/100."""
    profile_name = "NewGame.exe"
    cfg_path = _profile_file(rtss_stub, profile_name)
    assert not cfg_path.exists()

    def fake_save_profile(pname_bytes):
        name = pname_bytes.decode("latin1")
        pfile = _profile_file(rtss_stub, name)
        if not pfile.exists():
            pfile.write_text("[Framerate]\nLimit=5994\n", encoding="latin1")

    rtss_stub.SaveProfile = fake_save_profile

    def fake_get_property(prop, ptr, size):
        if prop == b"FramerateLimit":
            val = (5994).to_bytes(size, byteorder="little", signed=True)
            ctypes.memmove(ptr, val, size)
            return True
        return False

    rtss_stub.GetProfileProperty = fake_get_property

    result = rtss_stub.set_fractional_framerate(profile_name, 59.94, update=False)
    assert result == (5994, 100)

    assert cfg_path.exists()
    content = cfg_path.read_text(encoding="latin1")
    assert "LimitDenominator=100" in content
    assert rtss_stub.get_framerate_limit(profile_name, get_denominator=True) == 59.94


def test_missing_profile_creation_failure_returns_false(rtss_stub):
    """When profile creation / SaveProfile fails to create the file, denominator set and method return False."""
    profile_name = "UncreatableGame.exe"
    cfg_path = _profile_file(rtss_stub, profile_name)
    assert not cfg_path.exists()

    # SaveProfile does not create file (creation failure)
    rtss_stub.SaveProfile = lambda pname_bytes: None

    result = rtss_stub.set_fractional_framerate(profile_name, 59.94, update=False)
    assert result is False


def test_set_profile_property_failure_returns_false(rtss_stub):
    """When SetProfileProperty returns False, set_fractional_framerate returns False."""
    rtss_stub.SetProfileProperty = lambda *args, **kwargs: False

    result = rtss_stub.set_fractional_framerate("Global", 60, update=False)
    assert result is False


def test_set_limit_denominator_direct_creates_file_via_save_profile(rtss_stub):
    """set_limit_denominator on missing profile calls SaveProfile to ensure file exists."""
    profile_name = "DirectGame.exe"
    cfg_path = _profile_file(rtss_stub, profile_name)
    assert not cfg_path.exists()

    def fake_save_profile(pname_bytes):
        name = pname_bytes.decode("latin1")
        pfile = _profile_file(rtss_stub, name)
        if not pfile.exists():
            pfile.write_text("[Framerate]\nLimit=6000\n", encoding="latin1")

    rtss_stub.SaveProfile = fake_save_profile

    success = rtss_stub.set_limit_denominator(profile_name, 100, update=False)
    assert success is True
    assert cfg_path.exists()
    content = cfg_path.read_text(encoding="latin1")
    assert "LimitDenominator=100" in content


def test_set_limit_denominator_direct_creation_failure_returns_false(rtss_stub):
    """set_limit_denominator returns False if SaveProfile fails to create the file."""
    profile_name = "MissingDirect.exe"
    cfg_path = _profile_file(rtss_stub, profile_name)
    assert not cfg_path.exists()

    rtss_stub.SaveProfile = lambda pname_bytes: None

    success = rtss_stub.set_limit_denominator(profile_name, 100, update=False)
    assert success is False


def test_existing_profile_preserves_unrelated_settings(rtss_stub):
    """Updating fractional framerate on existing profile preserves unrelated sections and keys."""
    profile_name = "ExistingGame.exe"
    cfg_path = _profile_file(rtss_stub, profile_name)
    initial_content = "[OSD]\nPositionX=100\nPositionY=200\nLabel=Test\n[Framerate]\nLimit=60\n"
    cfg_path.write_text(initial_content, encoding="latin1")

    def fake_get_property(prop, ptr, size):
        if prop == b"FramerateLimit":
            val = (5994).to_bytes(size, byteorder="little", signed=True)
            ctypes.memmove(ptr, val, size)
            return True
        return False

    rtss_stub.GetProfileProperty = fake_get_property

    result = rtss_stub.set_fractional_framerate(profile_name, 59.94, update=False)
    assert result == (5994, 100)

    content = cfg_path.read_text(encoding="latin1")
    assert "[OSD]" in content
    assert "PositionX=100" in content
    assert "PositionY=200" in content
    assert "Label=Test" in content
    assert "LimitDenominator=100" in content
    assert rtss_stub.get_framerate_limit(profile_name, get_denominator=True) == 59.94
