import os
import sys
import types
import tempfile
import configparser
import pytest

# Non-Windows import isolation for Linux test execution
if "clr" not in sys.modules:
    sys.modules["clr"] = types.ModuleType("clr")
if "winreg" not in sys.modules:
    sys.modules["winreg"] = types.ModuleType("winreg")
if "numpy" not in sys.modules:
    np_mock = types.ModuleType("numpy")
    np_mock.array = lambda *a, **k: []
    sys.modules["numpy"] = np_mock

from core.config_manager import ConfigManager


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
    def __init__(self, profiles_path):
        self.profiles_path = profiles_path
        self.set_fractional_calls = []

    def delete_profile(self, profile_name):
        raise AssertionError(f"delete_profile was called for {profile_name}, but it is forbidden!")

    def set_fractional_framerate(self, profile_name, framerate, update=False, denominator=False):
        # Verify that profiles.ini on disk already has profile_name removed BEFORE this call!
        assert os.path.exists(self.profiles_path), "profiles.ini does not exist on disk"
        cp = configparser.ConfigParser()
        cp.read(self.profiles_path)
        assert profile_name not in cp.sections(), (
            f"profiles.ini on disk still contains deleted section '{profile_name}' when RTSS call occurred!"
        )
        self.set_fractional_calls.append((profile_name, framerate))
        return 0, 1


def create_test_config_manager(tmpdir, initial_profiles=None):
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
    rtss = FakeRTSSForbiddingDelete(profiles_path)
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
        assert len(rtss.set_fractional_calls) == 0


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
        assert len(rtss.set_fractional_calls) == 0


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

        # RTSS set_fractional_framerate was called with ("Game.exe", 0)
        assert len(rtss.set_fractional_calls) == 1
        assert rtss.set_fractional_calls[0] == ("Game.exe", 0)


def test_failing_rtss_call_cannot_resurrect_removed_ini_section():
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

        # Force RTSS call to raise an exception
        def failing_set_fractional(profile_name, framerate, **kwargs):
            raise RuntimeError("RTSS DLL error simulation")

        rtss.set_fractional_framerate = failing_set_fractional

        cm.delete_selected_profile_callback()

        # Section is still removed from memory and disk INI
        assert "Game.exe" not in cm.profiles_config
        cp = configparser.ConfigParser()
        cp.read(profiles_path)
        assert "Game.exe" not in cp.sections()

        # Error was logged
        assert any("Error resetting RTSS cap for profile 'Game.exe'" in log for log in logger.logs)


def test_cap_reset_keeps_unrelated_settings_file_behavior():
    """Verify non-destructive cap reset behavior on RTSS profile cfg files."""
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
            "Limit=144000\n"
            "LimitDenominator=1000\n"
        )
        with open(game_cfg, "w", encoding="utf-8") as f:
            f.write(initial_cfg_content)

        # Mock RTSS object that resets cap non-destructively on the cfg file
        class MockNonDestructiveRTSS:
            def delete_profile(self, profile_name):
                raise AssertionError("delete_profile should not be called!")

            def set_fractional_framerate(self, profile_name, framerate, update=False):
                cfg_path = os.path.join(profiles_dir, f"{profile_name}.cfg")
                if os.path.exists(cfg_path):
                    with open(cfg_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                    new_lines = []
                    for line in lines:
                        if line.startswith("Limit="):
                            new_lines.append(f"Limit={int(framerate)}\n")
                        elif line.startswith("LimitDenominator="):
                            new_lines.append("LimitDenominator=1\n")
                        else:
                            new_lines.append(line)
                    with open(cfg_path, "w", encoding="utf-8") as f:
                        f.writelines(new_lines)

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
        assert "Limit=0" in content
        assert "LimitDenominator=1" in content
