"""Atomic config file writing tests and regressions for settings.ini and profiles.ini."""
import runpy
import sys
import types
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

from core.config_io import new_config, read_config, write_config
from test_config_compat import manager


class FailingConfigWriter:
    """Simulates a ConfigParser writer that writes a partial fragment then raises OSError."""

    def write(self, stream):
        stream.write("[PartialSection]\nkey=")
        stream.flush()
        raise OSError("Simulated write failure mid-serialization")


@pytest.mark.parametrize("filename", ["settings.ini", "profiles.ini"])
def test_partial_write_failure_preserves_bytes_and_cleans_up(tmp_path, filename):
    target_path = tmp_path / filename
    original_bytes = b"[OriginalSection]\nkey=original_value\n"
    target_path.write_bytes(original_bytes)

    failing_config = FailingConfigWriter()

    with pytest.raises(OSError, match="Simulated write failure mid-serialization"):
        write_config(failing_config, target_path)

    assert target_path.read_bytes() == original_bytes
    assert list(tmp_path.glob("*.tmp")) == []


def test_simulated_os_replace_failure(tmp_path, monkeypatch):
    target_path = tmp_path / "settings.ini"
    original_bytes = b"[OriginalSection]\nkey=original_value\n"
    target_path.write_bytes(original_bytes)

    cfg = new_config()
    cfg.add_section("NewSection")
    cfg["NewSection"]["key"] = "new_value"

    def failing_replace(src, dst):
        raise OSError("Simulated os.replace failure")

    monkeypatch.setattr("os.replace", failing_replace)

    with pytest.raises(OSError, match="Simulated os.replace failure"):
        write_config(cfg, target_path)

    assert target_path.read_bytes() == original_bytes
    assert list(tmp_path.glob("*.tmp")) == []


def test_successful_creation_and_replacement_with_unicode_percent_unknown(tmp_path):
    target_path = tmp_path / "settings.ini"

    # Initial creation
    cfg = new_config()
    cfg.add_section("Preferences")
    cfg["Preferences"]["ui_scale"] = "150%"
    cfg.add_section("UnknownSection")
    cfg["UnknownSection"]["key"] = "雪100%"

    write_config(cfg, target_path)

    assert target_path.exists()
    assert list(tmp_path.glob("*.tmp")) == []

    read_cfg = new_config()
    read_config(read_cfg, target_path)
    assert read_cfg["Preferences"]["ui_scale"] == "150%"
    assert read_cfg["UnknownSection"]["key"] == "雪100%"

    # Replacement
    cfg["Preferences"]["ui_scale"] = "100%"
    write_config(cfg, target_path)

    assert list(tmp_path.glob("*.tmp")) == []
    read_cfg2 = new_config()
    read_config(read_cfg2, target_path)
    assert read_cfg2["Preferences"]["ui_scale"] == "100%"
    assert read_cfg2["UnknownSection"]["key"] == "雪100%"


def test_production_path_failure_handling(manager, tmp_path, monkeypatch, fake_dpg):
    cm = manager()

    def failing_write_config(config, path):
        raise OSError("Simulated production write failure")

    monkeypatch.setitem(cm.save_profile.__globals__, "write_config", failing_write_config)

    # Pre-populate settings and profiles files so we can check they stay unchanged
    settings_bytes = Path(cm.settings_path).read_bytes()
    profiles_bytes = Path(cm.profiles_path).read_bytes()

    # Callback 1: update_preference_setting
    with pytest.raises(OSError, match="Simulated production write failure"):
        cm.update_preference_setting("showtooltip", None, False, None)

    # Callback 2: save_profile
    for key in cm.input_field_keys:
        fake_dpg.set_value("input_" + key, cm.Default_settings_original[key])

    with pytest.raises(OSError, match="Simulated production write failure"):
        cm.save_profile("FailedProfile")

    assert Path(cm.settings_path).read_bytes() == settings_bytes
    assert Path(cm.profiles_path).read_bytes() == profiles_bytes
    assert list((tmp_path / "config").glob("*.tmp")) == []


def test_partial_write_regression_fails_pre_fix_path(tmp_path):
    target_path = tmp_path / "settings.ini"
    original_bytes = b"[OriginalSection]\nkey=original_value\n"
    target_path.write_bytes(original_bytes)

    failing_config = FailingConfigWriter()

    # Demonstrating the pre-fix path behavior
    def pre_fix_write(config, path):
        with open(path, "w", encoding="utf-8") as stream:
            config.write(stream)

    with pytest.raises(OSError):
        pre_fix_write(failing_config, target_path)

    # Pre-fix path truncated the file on failure!
    truncated_bytes = target_path.read_bytes()
    assert truncated_bytes != original_bytes
    assert truncated_bytes == b"[PartialSection]\nkey="

    # Reset target path bytes
    target_path.write_bytes(original_bytes)

    # Post-fix atomic path preserves original bytes
    with pytest.raises(OSError):
        write_config(failing_config, target_path)

    assert target_path.read_bytes() == original_bytes
