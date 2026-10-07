import os
import sys
import types
import tempfile
import configparser
import contextlib
import pytest


_SCOPED_MODULES = (
    "clr", "winreg", "numpy",
    "core.config_manager", "core.librehardwaremonitor", "core.lhm_loader",
)
_MISSING = object()


@contextlib.contextmanager
def isolated_config_manager_import():
    """Import the actual class and restore only its temporary dependency scope."""
    saved_modules = {name: sys.modules.get(name, _MISSING) for name in _SCOPED_MODULES}
    parent = sys.modules.get("core")
    saved_attrs = {
        name.rsplit(".", 1)[1]: (
            vars(parent).get(name.rsplit(".", 1)[1], _MISSING)
            if parent is not None else _MISSING
        )
        for name in _SCOPED_MODULES if name.startswith("core.")
    }
    try:
        # Setup must unwind even if only some stubs were created.
        for name in ("clr", "winreg", "numpy"):
            if name not in sys.modules:
                stub = types.ModuleType(name)
                stub._is_test_stub = True
                if name == "numpy":
                    stub.array = lambda *a, **k: []
                sys.modules[name] = stub
        from core.config_manager import ConfigManager
        yield ConfigManager
    finally:
        # Keep a fresh core package but clear its fake-dependent children.
        current_parent = sys.modules.get("core")
        for attr, original in saved_attrs.items():
            if current_parent is not None:
                vars(current_parent).pop(attr, None)
            if parent is not None:
                if original is _MISSING:
                    vars(parent).pop(attr, None)
                else:
                    setattr(parent, attr, original)
        for name, original in saved_modules.items():
            if original is _MISSING:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original


@pytest.fixture
def fresh_import_scope(monkeypatch):
    for name in (*_SCOPED_MODULES, "core"):
        monkeypatch.delitem(sys.modules, name, raising=False)


@pytest.mark.parametrize("fail_in_body", [False, True])
def test_context_cleans_fresh_parent(fresh_import_scope, monkeypatch, fail_in_body):
    import importlib

    monkeypatch.delitem(sys.modules, "fractions", raising=False)
    try:
        with isolated_config_manager_import() as manager_class:
            parent = sys.modules["core"]
            assert parent.config_manager.ConfigManager is manager_class
            assert parent.librehardwaremonitor.np._is_test_stub
            assert parent.lhm_loader.clr._is_test_stub
            unrelated = importlib.import_module("fractions")
            if fail_in_body:
                raise RuntimeError("body failed")
    except RuntimeError as exc:
        assert fail_in_body and str(exc) == "body failed"
    assert sys.modules["fractions"] is unrelated
    assert sys.modules["core"] is parent
    for name in _SCOPED_MODULES:
        assert name not in sys.modules
        if name.startswith("core."):
            assert name.rsplit(".", 1)[1] not in vars(parent)


def test_context_restores_existing_identity(fresh_import_scope, monkeypatch):
    with isolated_config_manager_import() as manager_class:
        cached = {name: sys.modules[name] for name in _SCOPED_MODULES}
        parent = sys.modules["core"]
    attrs = {}
    for name, module in cached.items():
        monkeypatch.setitem(sys.modules, name, module)
        if name.startswith("core."):
            attr = name.rsplit(".", 1)[1]
            attrs[attr] = object()  # Parent attributes can differ from the cache.
            monkeypatch.setattr(parent, attr, attrs[attr], raising=False)
    with pytest.raises(RuntimeError, match="body failed"):
        with isolated_config_manager_import() as actual_class:
            assert actual_class is manager_class
            for name in _SCOPED_MODULES:
                sys.modules.pop(name)
            for attr in attrs:
                setattr(parent, attr, object())
            raise RuntimeError("body failed")
    for name, module in cached.items():
        assert sys.modules[name] is module
    for attr, original in attrs.items():
        assert vars(parent)[attr] is original


def test_context_unwinds_setup_failure(fresh_import_scope, monkeypatch):
    module_type = types.ModuleType

    def fail_on_winreg(name):
        if name == "winreg":
            raise RuntimeError("setup failed")
        return module_type(name)

    monkeypatch.setattr(types, "ModuleType", fail_on_winreg)
    with pytest.raises(RuntimeError, match="setup failed"):
        with isolated_config_manager_import():
            pytest.fail("setup should fail before yielding")
    for name in _SCOPED_MODULES:
        assert name not in sys.modules


def test_context_unwinds_import_failure(fresh_import_scope, monkeypatch):
    import builtins
    original_import = builtins.__import__
    parents = []

    def fail_after_dependencies(name, *args, **kwargs):
        if name == "core.config_manager":
            original_import("core.librehardwaremonitor", fromlist=["get_all_sensor_infos"])
            parents.append(sys.modules["core"])
            assert parents[-1].librehardwaremonitor.np._is_test_stub
            raise ImportError("config import failed")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fail_after_dependencies)
    with pytest.raises(ImportError, match="config import failed"):
        with isolated_config_manager_import():
            pytest.fail("import should fail before yielding")
    assert sys.modules["core"] is parents[0]
    for name in _SCOPED_MODULES:
        assert name not in sys.modules
        if name.startswith("core."):
            assert name.rsplit(".", 1)[1] not in vars(parents[0])


def test_collection_leaves_sys_modules_unchanged():
    """Regression test 1: Collection of this test module must not leave
    fake clr, winreg, or numpy stubs in sys.modules."""
    for mod_name in ["clr", "winreg", "numpy"]:
        mod = sys.modules.get(mod_name)
        if mod is not None:
            assert not getattr(mod, "_is_test_stub", False), (
                f"Fake stub '{mod_name}' found in sys.modules after collection!"
            )


class DummyLogger:
    def __init__(self):
        self.logs = []

    def add_log(self, msg):
        self.logs.append(str(msg))


class DummyDPG:
    def __init__(self):
        self.values = {}
        self.items = {}

    def get_value(self, tag):
        return self.values.get(tag, "")

    def set_value(self, tag, val):
        self.values[tag] = val

    def configure_item(self, tag, **kwargs):
        self.items[tag] = kwargs

    def bind_item_theme(self, tag, theme):
        pass

    def does_item_exist(self, tag):
        return tag in self.items or tag in self.values


class DummyThemesManager:
    def __init__(self):
        self.themes = {
            "enabled_text_theme": "enabled",
            "disabled_text_theme": "disabled",
        }


class FakeRTSSForbiddingDelete:
    def __init__(self, profiles_path, return_success=True):
        self.profiles_path = profiles_path
        self.return_success = return_success
        self.set_property_calls = []

    def delete_profile(self, profile_name):
        raise AssertionError(f"delete_profile was called for {profile_name}, but it is forbidden!")

    def set_profile_property(self, profile_name, property_name, value, size=4, update=True):
        # Verify that profiles.ini on disk already has profile_name removed BEFORE this call!
        assert os.path.exists(self.profiles_path), "profiles.ini does not exist on disk"
        cp = configparser.ConfigParser()
        cp.read(self.profiles_path)
        assert profile_name not in cp.sections(), (
            f"profiles.ini on disk still contains deleted section '{profile_name}' when RTSS call occurred!"
        )
        self.set_property_calls.append((profile_name, property_name, value, update))
        return self.return_success


def create_test_config_manager(tmpdir, initial_profiles=None, return_success=True):
    with isolated_config_manager_import() as ConfigManager:
        base_dir = os.path.join(tmpdir, "src")
        os.makedirs(base_dir, exist_ok=True)
        config_dir = os.path.join(tmpdir, "config")
        os.makedirs(config_dir, exist_ok=True)

        profiles_path = os.path.join(config_dir, "profiles.ini")
        cp = configparser.ConfigParser()
        cp["Global"] = {
            "maxcap": "114",
            "mincap": "40",
            "capratio": "10",
            "capstep": "5",
            "gpucutofffordecrease": "85",
            "gpucutoffforincrease": "70",
            "cpucutofffordecrease": "105",
            "cpucutoffforincrease": "101",
            "delaybeforedecrease": "2",
            "delaybeforeincrease": "10",
            "capmethod": "ratio",
            "customfpslimits": "30.01, 45.00, 59.99",
            "monitoring_method": "LibreHM",
        }
        if initial_profiles:
            for p_name, p_data in initial_profiles.items():
                cp[p_name] = p_data

        with open(profiles_path, "w") as f:
            cp.write(f)

        logger = DummyLogger()
        dpg = DummyDPG()
        rtss = FakeRTSSForbiddingDelete(profiles_path, return_success=return_success)
        themes = DummyThemesManager()

        cm = ConfigManager(logger, dpg, rtss, None, themes, base_dir)
        return cm, logger, dpg, rtss, profiles_path


def test_global_refusal():
    with tempfile.TemporaryDirectory() as tmpdir:
        cm, logger, dpg, rtss, profiles_path = create_test_config_manager(tmpdir)
        dpg.set_value("profile_dropdown", "Global")

        cm.delete_selected_profile_callback()

        # Global section must remain in profiles_config and on disk
        assert "Global" in cm.profiles_config
        cp = configparser.ConfigParser()
        cp.read(profiles_path)
        assert "Global" in cp.sections()

        # Log must indicate Global refusal
        assert any("Cannot delete the default 'Global' profile." in log for log in logger.logs)
        # No RTSS call should occur
        assert len(rtss.set_property_calls) == 0


def test_global_refusal_case_insensitive():
    with tempfile.TemporaryDirectory() as tmpdir:
        cm, logger, dpg, rtss, profiles_path = create_test_config_manager(tmpdir)
        dpg.set_value("profile_dropdown", "global")

        cm.delete_selected_profile_callback()

        assert "Global" in cm.profiles_config
        cp = configparser.ConfigParser()
        cp.read(profiles_path)
        assert "Global" in cp.sections()
        assert any("Cannot delete the default 'Global' profile." in log for log in logger.logs)
        assert len(rtss.set_property_calls) == 0


def test_delete_profile_forbids_delete_profile_and_persists_ini_first():
    with tempfile.TemporaryDirectory() as tmpdir:
        cm, logger, dpg, rtss, profiles_path = create_test_config_manager(
            tmpdir,
            initial_profiles={
                "Game.exe": {
                    "maxcap": "120",
                    "mincap": "60",
                }
            },
        )
        dpg.set_value("profile_dropdown", "Game.exe")

        cm.delete_selected_profile_callback()

        # Game.exe section must be gone from memory config and disk INI
        assert "Game.exe" not in cm.profiles_config
        cp = configparser.ConfigParser()
        cp.read(profiles_path)
        assert "Game.exe" not in cp.sections()

        # RTSS set_profile_property was called with ("Game.exe", "FramerateLimit", 0, True)
        assert len(rtss.set_property_calls) == 1
        assert rtss.set_property_calls[0] == ("Game.exe", "FramerateLimit", 0, True)


def test_rejected_dll_write_handles_false_visibly_without_resurrecting_ini():
    """Regression test 2: When set_profile_property returns False (rejected DLL write),
    it must log the reset failure visibly and must not resurrect the removed INI section."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cm, logger, dpg, rtss, profiles_path = create_test_config_manager(
            tmpdir,
            initial_profiles={
                "Game.exe": {
                    "maxcap": "120",
                    "mincap": "60",
                }
            },
            return_success=False,  # DLL returns False!
        )
        dpg.set_value("profile_dropdown", "Game.exe")

        cm.delete_selected_profile_callback()

        # Section is still removed from memory and disk INI
        assert "Game.exe" not in cm.profiles_config
        cp = configparser.ConfigParser()
        cp.read(profiles_path)
        assert "Game.exe" not in cp.sections()

        # Failure was logged visibly
        assert any("Error resetting RTSS cap for profile 'Game.exe'" in log for log in logger.logs)


def test_cap_reset_keeps_unrelated_settings_file_behavior():
    """Verify non-destructive cap reset behavior preserves unrelated RTSS profile settings."""
    with tempfile.TemporaryDirectory() as tmpdir:
        profiles_dir = os.path.join(tmpdir, "Profiles")
        os.makedirs(profiles_dir, exist_ok=True)
        game_cfg = os.path.join(profiles_dir, "Game.exe.cfg")

        # Simulate existing RTSS profile with unrelated settings + cap settings
        initial_cfg_content = (
            "[Base]\n"
            "PositionX=10\n"
            "PositionY=20\n"
            "OSDFormat=1\n"
            "FramerateLimit=144000\n"
        )
        with open(game_cfg, "w", encoding="utf-8") as f:
            f.write(initial_cfg_content)

        class MockNonDestructiveRTSS:
            def delete_profile(self, profile_name):
                raise AssertionError("delete_profile should not be called!")

            def set_profile_property(self, profile_name, prop_name, val, size=4, update=True):
                cfg_path = os.path.join(profiles_dir, f"{profile_name}.cfg")
                if os.path.exists(cfg_path):
                    with open(cfg_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                    new_lines = []
                    for line in lines:
                        if line.startswith(f"{prop_name}="):
                            new_lines.append(f"{prop_name}={val}\n")
                        else:
                            new_lines.append(line)
                    with open(cfg_path, "w", encoding="utf-8") as f:
                        f.writelines(new_lines)
                return True

        cm, logger, dpg, _, profiles_path = create_test_config_manager(
            tmpdir,
            initial_profiles={"Game.exe": {"maxcap": "120"}},
        )
        cm.rtss = MockNonDestructiveRTSS()
        dpg.set_value("profile_dropdown", "Game.exe")

        cm.delete_selected_profile_callback()

        # Verify cfg file still exists and unrelated settings are preserved!
        assert os.path.exists(game_cfg)
        with open(game_cfg, "r", encoding="utf-8") as f:
            content = f.read()

        assert "PositionX=10" in content
        assert "PositionY=20" in content
        assert "OSDFormat=1" in content
        assert "FramerateLimit=0" in content
