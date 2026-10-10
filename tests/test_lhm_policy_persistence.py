"""Persist LibreHM policies by stable Identifier across native rediscovery.

Only native boundaries are fake. Discovery, dynamic configuration, INI writes,
reloads, polling and FPS evaluation execute full production modules.
"""
import runpy
import sys
import types
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

from core.config_io import new_config, read_config


CORE = Path(__file__).resolve().parents[1] / "src" / "core"
PROFILE = "SensorPolicy.exe"
FIRST = "/amdcpu/0/temperature/0"
SECOND = "/amdcpu/0/temperature/1"
POLICIES = {
    FIRST: {"enable": True, "lower": 20, "upper": 60},
    SECOND: {"enable": False, "lower": 70, "upper": 95},
}


class _Sensor:
    def __init__(self, identifier):
        self.Identifier = identifier
        self.Name = "Core"
        self.SensorType = "Temperature"
        self.Value = 90.0 if identifier == FIRST else 10.0


class _Hardware:
    def __init__(self, order):
        self.Name = "CPU"
        self.HardwareType = "Cpu"
        self.Sensors = [_Sensor(identifier) for identifier in order]

    def Update(self):
        pass


class _Computer:
    def __init__(self, order):
        self.Hardware = [_Hardware(order)]
        self.IsCpuEnabled = False
        self.IsGpuEnabled = False

    def Open(self):
        pass

    def Close(self):
        pass


def _startup(manager_cls, dpg_cls, logger, tmp_path):
    """Model app.py's widget defaults, dynamic setup and profile selection."""
    dpg = dpg_cls()
    cm = manager_cls(
        logger, dpg, NS(set_profile_property=lambda *a, **k: True), None,
        NS(themes={"enabled_text_theme": 1, "disabled_text_theme": 2}),
        str(tmp_path / "core"),
    )
    for key in cm.input_field_keys:
        dpg.set_value(f"input_{key}", cm.settings[key])
    for info in cm.sensor_infos:
        for suffix, value in (("enable", False), ("lower", "0"), ("upper", "100")):
            dpg.set_value(f"input_{info['parameter_id']}_{suffix}", value)
        dpg.set_value(f"input_collapsing_{info['hw_id']}", True)
    dpg.set_value("profile_dropdown", "Global")

    # Keep the actual app startup order: widgets precede dynamic registration;
    # registration and typing precede first-launch save and profile selection.
    cm.update_dynamic_input_field_keys()
    cm.update_dynamic_default_settings()
    cm.update_dynamic_key_type_map()
    if not cm.first_launch_done:
        cm.save_to_profile()
    cm.update_profile_dropdown(select_first=True)
    cm.startup_profile_selection()
    return cm


def _policies_by_identifier(cm):
    return {
        info["identifier"]: {
            suffix: cm.dpg.get_value(f"input_{info['parameter_id']}_{suffix}")
            for suffix in ("enable", "lower", "upper")
        }
        for info in cm.sensor_infos
    }


@pytest.mark.parametrize("reverse", [False, True], ids=["same-order", "reversed-order"])
@pytest.mark.parametrize("save_method", ["save_profile", "save_to_profile"])
def test_saved_policy_follows_identifier_after_restart(
    reverse, save_method, tmp_path, monkeypatch, fake_dpg, stub_logger
):
    order = [FIRST, SECOND]
    sensor_type = NS(Load="Load", Temperature="Temperature", Power="Power")
    hardware_type = NS(Cpu="Cpu", GpuAmd="GpuAmd", GpuNvidia="GpuNvidia")
    loader = types.ModuleType("core.lhm_loader")
    loader.LHMLoadError = RuntimeError
    loader.get_types = lambda base_dir=None: (
        lambda: _Computer(order), sensor_type, hardware_type
    )
    loader.ensure_loaded = lambda base_dir=None, logger=None: loader.get_types(base_dir)
    monkeypatch.setitem(sys.modules, "core.lhm_loader", loader)

    # Like test_config_compat, isolate native imports with runpy. Unlike a
    # discovery stub, this module contains the real get_all_sensor_infos body.
    lhm = types.ModuleType("core.librehardwaremonitor")
    lhm.__dict__.update(runpy.run_path(str(CORE / "librehardwaremonitor.py")))
    monkeypatch.setitem(sys.modules, "core.librehardwaremonitor", lhm)
    manager_cls = runpy.run_path(str(CORE / "config_manager.py"))["ConfigManager"]
    fps_cls = runpy.run_path(str(CORE / "fps_utils.py"))["FPSUtils"]
    assert manager_cls.__init__.__globals__["get_all_sensor_infos"] is lhm.get_all_sensor_infos

    original = _startup(manager_cls, type(fake_dpg), stub_logger, tmp_path)
    assert [info["identifier"] for info in original.sensor_infos] == [FIRST, SECOND]
    assert len({info["parameter_id"] for info in original.sensor_infos}) == 2
    # A completed first launch must not overwrite the saved profile on restart.
    original.update_preference_setting("first_launch_done", None, True, None)
    if save_method == "save_to_profile":
        # Create an existing named profile through the real production method.
        original.save_profile(PROFILE)
    for info in original.sensor_infos:
        for suffix, value in POLICIES[info["identifier"]].items():
            # Match input_text boundaries; production parsing converts to ints.
            original.dpg.set_value(
                f"input_{info['parameter_id']}_{suffix}",
                value if suffix == "enable" else str(value),
            )
    if save_method == "save_profile":
        original.save_profile(PROFILE)
    else:
        original.save_to_profile()
    original.select_default_profile_callback(None, None, None)

    # Confirm the real profiles.ini contains each policy before rediscovery.
    persisted = new_config()
    read_config(persisted, original.profiles_path)
    for info in original.sensor_infos:
        for suffix, value in POLICIES[info["identifier"]].items():
            assert persisted[PROFILE][f"{info['parameter_id']}_{suffix}"] == str(value)
    saved_bytes = Path(original.profiles_path).read_bytes()

    if reverse:
        order = [SECOND, FIRST]
    restarted = _startup(manager_cls, type(fake_dpg), stub_logger, tmp_path)
    assert restarted.dpg is not original.dpg
    assert restarted.profiles_config is not original.profiles_config
    assert [info["identifier"] for info in restarted.sensor_infos] == order
    assert restarted.current_profile == PROFILE
    assert restarted.load_profile_raw(PROFILE) is True
    assert Path(restarted.profiles_path).read_bytes() == saved_bytes

    # Evaluate real polled samples with the reloaded widgets. Stable FIRST is
    # enabled and over its upper threshold; stable SECOND must remain disabled.
    monitor = lhm.LHMSensor(
        lambda: False, stub_logger, restarted.dpg, NS(themes={}),
        base_dir=str(tmp_path / "core"),
    )
    try:
        fps = fps_cls(restarted, monitor, logger=stub_logger, dpg=restarted.dpg)
        with monitor._lock:
            monitor._poll_pass()
        assert monitor.cpu_percentiles[FIRST] == 90.0
        assert monitor.cpu_percentiles[SECOND] == 10.0
        decision = fps.evaluate_cap_change([], [], "LibreHM")
    finally:
        monitor.stop()

    # IDs and widget tags may change: the assertion is solely by Identifier.
    assert (_policies_by_identifier(restarted), decision) == (POLICIES, (True, False)), (
        "Saved enabled/lower/upper policy must follow the stable LHM Identifier "
        "when enumeration changes; it must not transfer to the ordinal sibling"
    )
