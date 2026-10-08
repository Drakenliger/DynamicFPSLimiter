"""Test that select_default_profile_callback updates live attribute and logs newly selected startup profile."""
import sys
import types
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

from core.config_io import new_config, read_config


@pytest.fixture
def make_config_manager(tmp_path, monkeypatch, fake_dpg, stub_logger):
    hardware = types.ModuleType("core.librehardwaremonitor")
    hardware.get_all_sensor_infos = lambda *a: []
    monkeypatch.setitem(sys.modules, "core.librehardwaremonitor", hardware)

    from core.config_manager import ConfigManager

    def _create():
        return ConfigManager(
            logger_instance=stub_logger,
            dpg_instance=fake_dpg,
            rtss_instance=NS(set_profile_property=lambda *a, **k: True),
            tray_instance=None,
            themes_manager=NS(themes={}),
            base_dir=str(tmp_path / "src"),
        )

    return _create


@pytest.mark.parametrize("profile_name", ["Game.exe", "Game100%雪.exe"])
def test_select_default_profile_updates_attribute_ui_config_file_and_log(
    make_config_manager, tmp_path, fake_dpg, stub_logger, profile_name
):
    cm = make_config_manager()

    # Set old startup profile to Global (as load_preferences loads from settings_config["Preferences"])
    # cm.profileonstartup_name attribute is loaded during load_preferences or set manually here
    cm.profileonstartup_name = "Global"

    # Add profile to profiles_config so it exists
    cm.profiles_config[profile_name] = {}

    # Set profile_dropdown in fake_dpg to the target profile
    fake_dpg.set_value("profile_dropdown", profile_name)

    # Invoke real callback
    cm.select_default_profile_callback(None, None, None)

    # Assert live attribute updated
    assert cm.profileonstartup_name == profile_name

    # Assert UI field updated in fake_dpg
    assert fake_dpg.get_value("profileonstartup_name") == profile_name

    # Assert settings ConfigParser updated
    assert cm.settings_config["GlobalSettings"]["profileonstartup_name"] == profile_name

    # Assert reread UTF-8 settings.ini contains profile_name
    reread_config = new_config()
    read_config(reread_config, cm.settings_path)
    assert reread_config["GlobalSettings"]["profileonstartup_name"] == profile_name

    # Assert exact log message
    expected_log = f"Profile on Startup set to: {profile_name}"
    assert expected_log in stub_logger.messages
