import ctypes
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

    # Scope cleanup to the import under test; unrelated imports must survive.
    missing = object()
    names = ("winreg", "core", "core.rtss_functions")
    saved_modules = {name: sys.modules.get(name, missing) for name in names}
    core_mod = sys.modules.get("core")
    saved_attr = (
        core_mod.__dict__.get("rtss_functions", missing)
        if core_mod is not None else missing
    )

    try:
        if sys.platform != "win32" and "winreg" not in sys.modules:
            sys.modules["winreg"] = types.ModuleType("winreg")
        # Test the real source freshly, even if another test cached it already.
        sys.modules.pop("core.rtss_functions", None)
        if core_mod is not None:
            core_mod.__dict__.pop("rtss_functions", None)

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

        yield ctrl, fake
    finally:
        # Also clear a fresh parent retained by a caller after cache removal.
        imported_core = sys.modules.get("core")
        if imported_core is not None and imported_core is not core_mod:
            imported_core.__dict__.pop("rtss_functions", None)
        if core_mod is not None:
            if saved_attr is missing:
                core_mod.__dict__.pop("rtss_functions", None)
            else:
                core_mod.rtss_functions = saved_attr
        for name, previous in saved_modules.items():
            if previous is missing:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous


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


@pytest.mark.parametrize("existing_parent", [False, True])
@pytest.mark.parametrize("existing_winreg", [False, True])
@pytest.mark.parametrize("failure", [None, "mkdir", "write_text"])
def test_fixture_restores_import_state_on_success_and_setup_failure(
    tmp_path, monkeypatch, existing_parent, existing_winreg, failure
):
    # Exercise the actual generator, including failures before its yield.
    parent = types.ModuleType("core") if existing_parent else None
    cached_module = types.ModuleType("core.rtss_functions")
    saved_attr = object()
    registry = types.ModuleType("winreg")
    unrelated_module = types.ModuleType("t6_unrelated_import")
    unrelated_attr = object()
    retained_parents = []
    imported_modules = []
    original_mkdir = Path.mkdir
    original_write_text = Path.write_text

    with monkeypatch.context() as isolated:
        if existing_parent:
            parent.__path__ = [str(Path(__file__).resolve().parents[1] / "src" / "core")]
            parent.rtss_functions = saved_attr
            isolated.setitem(sys.modules, "core", parent)
            isolated.setitem(sys.modules, "core.rtss_functions", cached_module)
        else:
            isolated.delitem(sys.modules, "core", raising=False)
            isolated.delitem(sys.modules, "core.rtss_functions", raising=False)
        if existing_winreg:
            isolated.setitem(sys.modules, "winreg", registry)
        else:
            isolated.delitem(sys.modules, "winreg", raising=False)

        # Register undo before simulating an unrelated import during setup.
        isolated.setitem(sys.modules, "t6_unrelated_import", unrelated_module)
        isolated.delitem(sys.modules, "t6_unrelated_import")

        def mkdir(path, *args, **kwargs):
            imported_parent = sys.modules["core"]
            imported_module = sys.modules["core.rtss_functions"]
            retained_parents.append(imported_parent)
            imported_modules.append(imported_module)
            assert imported_parent.rtss_functions is imported_module
            assert imported_module is not cached_module
            if existing_winreg or sys.platform != "win32":
                assert imported_module.winreg is sys.modules["winreg"]
            sys.modules["t6_unrelated_import"] = unrelated_module
            imported_parent.unrelated_t6_attr = unrelated_attr
            if failure == "mkdir":
                raise OSError("injected mkdir failure")
            return original_mkdir(path, *args, **kwargs)

        def write_text(path, *args, **kwargs):
            if failure == "write_text":
                raise OSError("injected write_text failure")
            return original_write_text(path, *args, **kwargs)

        isolated.setattr(Path, "mkdir", mkdir)
        isolated.setattr(Path, "write_text", write_text)
        gen = rtss_controller_fake_dll.__wrapped__(tmp_path, isolated)
        try:
            if failure:
                with pytest.raises(OSError, match=f"injected {failure} failure"):
                    next(gen)
            else:
                ctrl, fake = next(gen)
                assert type(ctrl) is imported_modules[0].RTSSController
                assert isinstance(fake, FakeDLLCalls)
                with pytest.raises(StopIteration):
                    next(gen)
        finally:
            gen.close()

        # Check before monkeypatch undo, so it cannot conceal fixture leaks.
        assert retained_parents
        assert sys.modules["t6_unrelated_import"] is unrelated_module
        for retained_parent in retained_parents:
            assert retained_parent.unrelated_t6_attr is unrelated_attr
            if existing_parent:
                assert retained_parent is parent
                assert retained_parent.rtss_functions is saved_attr
            else:
                assert "rtss_functions" not in retained_parent.__dict__
        if existing_parent:
            assert sys.modules["core"] is parent
            assert sys.modules["core.rtss_functions"] is cached_module
        else:
            assert "core" not in sys.modules
            assert "core.rtss_functions" not in sys.modules
        if existing_winreg:
            assert sys.modules["winreg"] is registry
        else:
            assert "winreg" not in sys.modules
