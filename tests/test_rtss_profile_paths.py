"""Profile names must be rejected before file access or RTSS DLL calls.

Exercise real controller methods; native spies never create Windows paths.
"""
import builtins
import ctypes
from pathlib import Path

import pytest

from core import rtss_functions as backend
from test_app_session import load_app


SEED = b"[Framerate]\nLimit=30\nLimitDenominator=1\n[Other]\nKeep=sentinel\n"
WINDOWS_UNSAFE = [
    r"C:\outside", "C:foo", r"\\server\share\outside", r"..\outside",
    "sub/outside", r"sub\outside", "Game.exe:stream", "Game\0.exe",
]
UNSAFE = ["../outside", "absolute", *WINDOWS_UNSAFE]
VALID = ["Game.exe", "Game.v1..exe", "Game Name.exe", "100%.exe", "Café.exe"]


@pytest.fixture
def paths(rtss_stub, monkeypatch):
    outside = Path(rtss_stub.rtss_install_path) / "outside.cfg"
    outside.write_bytes(SEED)
    native, access = [], []

    def spy(method):
        def call(*args):
            native.append((method, args))
            if method == "GetProfileProperty":
                ctypes.memmove(args[1], ctypes.byref(ctypes.c_int(6000)), args[2])
                return True
            if method == "SetProfileProperty":
                return True
            if method == "UpdateProfiles":
                rtss_stub.update_profiles_calls += 1
        return call

    for method in ("LoadProfile", "SaveProfile", "GetProfileProperty",
                   "SetProfileProperty", "DeleteProfile", "ResetProfile", "UpdateProfiles"):
        monkeypatch.setattr(rtss_stub, method, spy(method))

    real_isfile = backend.os.path.isfile

    def isfile(path):
        access.append(("isfile", str(path)))
        # Do not discover real C:/UNC files on a Windows runner. Only fixture
        # files exist for this test; every attempted lookup is still recorded.
        try:
            confined = Path(path).resolve().is_relative_to(outside.parent)
        except ValueError:  # Embedded NUL is intentionally part of the input.
            confined = False
        return confined and real_isfile(path)

    def open_profile(path, *args, **kwargs):
        access.append(("open", str(path)))
        return builtins.open(path, *args, **kwargs)

    monkeypatch.setattr(backend.os.path, "isfile", isfile)
    monkeypatch.setattr(backend, "open", open_profile, raising=False)
    return rtss_stub, outside, native, access


def unsafe_name(name, outside):
    return str(outside.with_suffix("")) if name == "absolute" else name


def assert_untouched(paths):
    ctrl, outside, native, access = paths
    # Check real bytes first: the existing file must not be silently replaced.
    assert outside.read_bytes() == SEED
    assert native == [], f"Unsafe name reached native RTSS: {native!r}"
    assert access == [], f"Unsafe name reached filesystem: {access!r}"
    assert ctrl.update_profiles_calls == 0
    assert not outside.with_suffix(".cfg.tmp").exists()


@pytest.mark.parametrize("method", ["set_fractional_fps_direct", "set_limit_denominator"])
@pytest.mark.parametrize("name", ["../outside", "absolute"])
def test_existing_outside_writers_reject_before_access(paths, method, name):
    ctrl, outside, _, _ = paths
    value = 59.94 if method == "set_fractional_fps_direct" else 100
    result = getattr(ctrl, method)(unsafe_name(name, outside), value)
    assert_untouched(paths)
    assert result is False


@pytest.mark.parametrize("name", WINDOWS_UNSAFE)
@pytest.mark.parametrize("method", ["set_fractional_fps_direct", "set_limit_denominator"])
def test_missing_windows_path_rejected_before_native_save(paths, method, name):
    """On Linux these can look like basenames; SaveProfile still must not see them."""
    ctrl, _, _, _ = paths
    # No unsafe file is seeded. SaveProfile only records, never writes anything.
    value = 59.94 if method == "set_fractional_fps_direct" else 100
    result = getattr(ctrl, method)(name, value)
    assert_untouched(paths)
    assert result is False


@pytest.mark.parametrize("name", UNSAFE)
@pytest.mark.parametrize("operation", [
    "fractional", "set", "create", "delete", "reset", "property", "limit", "ratio",
])
def test_unsafe_api_names_have_no_side_effects(paths, name, operation):
    ctrl, outside, _, _ = paths
    name = unsafe_name(name, outside)
    calls = {
        "fractional": lambda: ctrl.set_fractional_framerate(name, 59.94),
        "set": lambda: ctrl.set_profile_property(name, "FramerateLimit", 60),
        "create": lambda: ctrl.create_profile(name, {"FramerateLimit": 60}),
        "delete": lambda: ctrl.delete_profile(name),
        "reset": lambda: ctrl.reset_profile(name),
        "property": lambda: ctrl.get_profile_property(name, "FramerateLimit"),
        "limit": lambda: ctrl.get_framerate_limit(name),
        "ratio": lambda: ctrl.get_framerate_limit(name, get_denominator=True),
    }
    result = calls[operation]()
    assert_untouched(paths)
    if operation in ("property", "limit", "ratio"):
        assert result is None
    else:
        assert result is False


def test_actual_app_start_direct_then_api_rejects_outside(paths, monkeypatch):
    ctrl, _, _, _ = paths
    ns, _, _, spawned = load_app()
    ns["rtss"] = ctrl
    ns["cm"].current_profile = "../outside"
    ns["running"] = False
    attempts = []

    def record(method):
        actual = getattr(ctrl, method)

        def call(*args, **kwargs):
            result = actual(*args, **kwargs)
            attempts.append((method, args[0], result))
            return result
        monkeypatch.setattr(ctrl, method, call)

    for method in ("set_fractional_fps_direct", "set_fractional_framerate"):
        record(method)
    # app.py start_stop_callback -> _write_cap: old-cap read, direct, API refresh.
    # Existing AST fixture keeps the actual functions and prevents worker launch.
    ns["start_stop_callback"](None, None, ns["cm"])
    assert_untouched(paths)
    assert attempts == [
        ("set_fractional_fps_direct", "../outside", False),
        ("set_fractional_framerate", "../outside", False),
    ]
    assert ns["running"] and len(spawned) == 2


@pytest.mark.parametrize("name", VALID)
def test_valid_file_names_keep_spelling_encoding_and_contents(paths, name):
    ctrl, outside, native, _ = paths
    profile = outside.parent / "Profiles" / f"{name}.cfg"
    profile.write_bytes(SEED)
    assert ctrl.set_fractional_fps_direct(name, 59.94) is True
    assert ctrl.set_limit_denominator(name, 10) is True
    assert ctrl.set_fractional_framerate(name, 59.94) == (5994, 100)
    assert ctrl.get_framerate_limit(name) == 6000
    assert ctrl.get_framerate_limit(name, get_denominator=True) == 60
    content = profile.read_bytes()
    assert b"Limit=5994\n" in content and b"LimitDenominator=100\n" in content
    assert b"[Other]\nKeep=sentinel\n" in content
    encoded = name.encode(backend.PROFILE_ENCODING)
    assert [args[0] for method, args in native if method == "SaveProfile"] == [encoded]
    assert all(args[0] == encoded for method, args in native if method == "LoadProfile")
    assert ctrl.update_profiles_calls == 3
    assert outside.read_bytes() == SEED


@pytest.mark.parametrize("name", [*VALID, "", "Global", "gLoBaL"])
def test_native_wrappers_preserve_literal_valid_names(paths, name):
    ctrl, _, native, _ = paths
    encoded = name.encode(backend.PROFILE_ENCODING)
    assert ctrl.set_profile_property(name, "FramerateLimit", 60) is True
    assert ctrl.get_profile_property(name, "FramerateLimit") == (6000).to_bytes(4, "little")
    assert ctrl.create_profile(name, {"FramerateLimit": 60}) is None
    assert ctrl.delete_profile(name) is None
    assert ctrl.reset_profile(name) is None
    assert [args[0] for method, args in native if method == "LoadProfile"] == [encoded, encoded, b""]
    assert [args[0] for method, args in native if method == "SaveProfile"] == [encoded, encoded]
    assert ("DeleteProfile", (encoded,)) in native
    assert ("ResetProfile", (encoded,)) in native


@pytest.mark.parametrize("name", [None, "", "Global", "global", "gLoBaL"])
def test_higher_level_global_aliases_still_use_global_file_and_empty_api(paths, name):
    ctrl, outside, native, access = paths
    global_file = outside.parent / "Profiles" / "Global"
    global_file.write_bytes(SEED)
    assert ctrl.set_fractional_fps_direct(name, 59.94) is True
    assert ctrl.set_limit_denominator(name, 10) is True
    assert ctrl.set_fractional_framerate(name, 59.94) == (5994, 100)
    assert ctrl.get_framerate_limit(name) == 6000
    assert ctrl.get_framerate_limit(name, get_denominator=True) == 60
    assert b"LimitDenominator=100\n" in global_file.read_bytes()
    assert all(args[0] == b"" for method, args in native
               if method in ("LoadProfile", "SaveProfile"))
    assert all(Path(path) == global_file for _, path in access)
    assert outside.read_bytes() == SEED
