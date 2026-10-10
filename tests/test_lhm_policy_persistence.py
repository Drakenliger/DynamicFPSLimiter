"""Persist LibreHM policies by stable Identifier across native rediscovery.

Only native boundaries are fake. Discovery, dynamic configuration, INI writes,
reloads, polling and FPS evaluation execute full production modules.
"""
import runpy
import json
import sys
import types
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

from core.config_io import new_config, read_config, write_config


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
        if identifier == "missing-attribute":
            del self.Identifier


class _Hardware:
    def __init__(self, order):
        self.Name = "CPU"
        self.HardwareType = "Cpu"
        self.Sensors = [_Sensor(identifier) for identifier in order]

    def Update(self):
        pass


class _Computer:
    def __init__(self, order):
        groups = order if order and isinstance(order[0], list) else [order]
        self.Hardware = [_Hardware(group) for group in groups]
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


@pytest.fixture
def backend(tmp_path, monkeypatch, fake_dpg, stub_logger):
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
    return NS(order=order, start=lambda: _startup(manager_cls, type(fake_dpg), stub_logger, tmp_path),
              lhm=lhm, fps_cls=fps_cls, logger=stub_logger, base_dir=str(tmp_path / "core"))


def _set_policies(cm, policies=POLICIES):
    for info in cm.sensor_infos:
        for suffix, value in policies[info["identifier"]].items():
            cm.dpg.set_value(f"input_{info['parameter_id']}_{suffix}",
                             value if suffix == "enable" else str(value))


def _save(cm, method, profile=PROFILE):
    cm.dpg.set_value("profile_dropdown", profile)
    cm.save_profile(profile) if method == "save_profile" else cm.save_to_profile()


def _decision(backend, cm):
    monitor = backend.lhm.LHMSensor(lambda: False, backend.logger, cm.dpg, NS(themes={}),
                                   base_dir=backend.base_dir)
    try:
        fps = backend.fps_cls(cm, monitor, logger=backend.logger, dpg=cm.dpg)
        with monitor._lock:
            monitor._poll_pass()
        assert monitor.cpu_percentiles[FIRST] == 90.0
        assert monitor.cpu_percentiles[SECOND] == 10.0
        return fps.evaluate_cap_change([], [], "LibreHM")
    finally:
        monitor.stop()


@pytest.mark.parametrize("hardware", [False, True], ids=["sensors", "hardware"])
@pytest.mark.parametrize("reverse", [False, True], ids=["same-order", "reversed-order"])
@pytest.mark.parametrize("save_method", ["save_profile", "save_to_profile"])
def test_saved_policy_follows_identifier_after_restart(backend, hardware, reverse, save_method):
    if hardware:
        backend.order[:] = [[FIRST], [SECOND]]

    original = backend.start()
    assert [info["identifier"] for info in original.sensor_infos] == [FIRST, SECOND]
    assert len({info["parameter_id"] for info in original.sensor_infos}) == 2
    # A completed first launch must not overwrite the saved profile on restart.
    original.update_preference_setting("first_launch_done", None, True, None)
    if save_method == "save_to_profile":
        # Create an existing named profile through the real production method.
        original.save_profile(PROFILE)
    _set_policies(original)
    _save(original, save_method)
    original.select_default_profile_callback(None, None, None)

    # Confirm the real profiles.ini contains each policy before rediscovery.
    persisted = new_config()
    read_config(persisted, original.profiles_path)
    for info in original.sensor_infos:
        for suffix, value in POLICIES[info["identifier"]].items():
            assert persisted[PROFILE][f"{info['parameter_id']}_{suffix}"] == str(value)
    saved_bytes = Path(original.profiles_path).read_bytes()

    if reverse:
        backend.order.reverse()
    restarted = backend.start()
    assert restarted.dpg is not original.dpg
    assert restarted.profiles_config is not original.profiles_config
    assert [info["identifier"] for info in restarted.sensor_infos] == ([SECOND, FIRST] if reverse else [FIRST, SECOND])
    assert restarted.current_profile == PROFILE
    assert restarted.load_profile_raw(PROFILE) is True
    assert Path(restarted.profiles_path).read_bytes() == saved_bytes

    # Evaluate real polled samples with the reloaded widgets. Stable FIRST is
    # enabled and over its upper threshold; stable SECOND must remain disabled.
    decision = _decision(backend, restarted)

    # IDs and widget tags may change: the assertion is solely by Identifier.
    assert (_policies_by_identifier(restarted), decision) == (POLICIES, (True, False)), (
        "Saved enabled/lower/upper policy must follow the stable LHM Identifier "
        "when enumeration changes; it must not transfer to the ordinal sibling"
    )


@pytest.mark.parametrize("save_method", ["save_profile", "save_to_profile"])
@pytest.mark.parametrize("first_launch", [False, True])
def test_legacy_read_migration_and_initial_quick_snapshot(backend, save_method, first_launch):
    seed = backend.start()
    seed.update_preference_setting("first_launch_done", None, not first_launch, None)
    legacy = "[Global]\nunknown=雪100%\n"
    for info in seed.sensor_infos:
        legacy += "".join(f"{info['parameter_id']}_{suffix}={value}\n"
                          for suffix, value in POLICIES[info["identifier"]].items())
    Path(seed.profiles_path).write_text(legacy, encoding="utf-8")
    cm = backend.start()
    assert _policies_by_identifier(cm) == POLICIES
    assert cm.get_setting("cpu1_temperature_01_upper") == 60
    if not first_launch:
        assert Path(cm.profiles_path).read_text(encoding="utf-8") == legacy
    cm.quick_load_settings()  # Initial dynamic snapshot, before any quick save.
    assert _policies_by_identifier(cm) == POLICIES
    _save(cm, save_method, "Global")
    assert json.loads(cm.profiles_config["Global"]["lhm_sensor_policies"]) == POLICIES
    assert cm.profiles_config["Global"]["unknown"] == "雪100%"
    cm.update_preference_setting("first_launch_done", None, True, None)
    backend.order.reverse()
    restarted = backend.start()
    assert _policies_by_identifier(restarted) == POLICIES
    assert restarted.get_setting("cpu1_temperature_02_upper") == 60
    assert _decision(backend, restarted) == (True, False)


@pytest.mark.parametrize("save_method", ["save_profile", "save_to_profile"])
def test_absent_return_new_and_ambiguous_identifiers(backend, save_method):
    original = backend.start()
    original.update_preference_setting("first_launch_done", None, True, None)
    _set_policies(original)
    original.save_profile(PROFILE)
    original.select_default_profile_callback(None, None, None)
    new = "/amdcpu/1/temperature/0"
    default = {"enable": False, "lower": 0, "upper": 100}
    backend.order[:] = [SECOND, new]
    absent = backend.start()
    assert _policies_by_identifier(absent) == {SECOND: POLICIES[SECOND], new: default}
    _save(absent, save_method)
    saved = json.loads(absent.profiles_config[PROFILE]["lhm_sensor_policies"])
    assert saved == {**POLICIES, new: default}
    backend.order[:] = [FIRST, FIRST, None, "", "  ", "missing-attribute", SECOND]
    ambiguous = backend.start()
    for info in ambiguous.sensor_infos[:-1]:
        assert {suffix: ambiguous.dpg.get_value(f"input_{info['parameter_id']}_{suffix}")
                for suffix in default} == default
    assert _policies_by_identifier(ambiguous)[SECOND] == POLICIES[SECOND]
    # Even deliberately entered ambiguous values cannot overwrite stable policy.
    for info in ambiguous.sensor_infos[:-1]:
        ambiguous.dpg.set_value(f"input_{info['parameter_id']}_enable", True)
        ambiguous.dpg.set_value(f"input_{info['parameter_id']}_upper", "1")
    _save(ambiguous, save_method)
    assert json.loads(ambiguous.profiles_config[PROFILE]["lhm_sensor_policies"]) == saved
    assert any("Ambiguous LibreHM Identifier" in message for message in backend.logger.messages)
    backend.order[:] = [new, SECOND, FIRST]
    returned = backend.start()
    assert _policies_by_identifier(returned) == saved
    assert _decision(backend, returned) == (True, False)
    backend.order[:] = []
    empty = backend.start()
    _save(empty, save_method)
    backend.order[:] = [FIRST, SECOND, new]
    assert _policies_by_identifier(backend.start()) == saved


@pytest.mark.parametrize("save_method", ["save_profile", "save_to_profile"])
def test_profiles_case_unicode_quick_copy_and_ini_preservation(backend, save_method):
    upper, lower = "/雪/Load%/A", "/雪/load%/a"
    backend.order[:] = [upper, lower]
    policies = {upper: POLICIES[FIRST], lower: POLICIES[SECOND]}
    cm = backend.start()
    cm.update_preference_setting("first_launch_done", None, True, None)
    first, second = "雪100%.exe", "雪100%.EXE"
    _set_policies(cm, policies)
    cm.save_profile(first)
    cm.profiles_config[first]["unknown"] = "雪100% %(maxcap)s"
    cm.profiles_config["Unrelated"] = {"opaque": "雪100%"}
    cm.quick_save_settings()
    swapped = {upper: policies[lower], lower: policies[upper]}
    _set_policies(cm, swapped)
    cm.save_profile(second)
    _save(cm, save_method, second)  # Existing section replacement path.
    cm.load_profile_raw(first)
    _save(cm, save_method, first)
    cm.select_default_profile_callback(None, None, None)
    backend.order.reverse()
    restarted = backend.start()
    assert restarted.current_profile == first
    assert _policies_by_identifier(restarted) == policies
    assert restarted.load_profile_raw(second)
    assert _policies_by_identifier(restarted) == swapped
    restarted.quick_save_settings()
    restarted.load_profile_raw(first)
    restarted.quick_load_settings()
    assert _policies_by_identifier(restarted) == swapped
    _save(restarted, save_method, first)
    disk = new_config()
    read_config(disk, restarted.profiles_path)
    assert disk[first]["unknown"] == "雪100% %(maxcap)s"
    assert disk["Unrelated"]["opaque"] == "雪100%"
    assert json.loads(disk[first]["lhm_sensor_policies"]) == swapped
    assert json.loads(disk[second]["lhm_sensor_policies"]) == swapped
    assert disk[first]["cpu1_temperature_01_upper"] == "60"
    assert disk[first]["cpu1_temperature_02_upper"] == "95"


@pytest.mark.parametrize("save_method", ["save_profile", "save_to_profile"])
@pytest.mark.parametrize("first_launch", [False, True])
@pytest.mark.parametrize("discovery", [[], [FIRST], [None, None], [FIRST, FIRST]], ids=["empty", "partial", "missing", "duplicate"])
def test_legacy_save_without_discovery_preserves_policy_on_return(backend, save_method, first_launch, discovery):
    seed = backend.start()
    seed.update_preference_setting("first_launch_done", None, not first_launch, None)
    legacy_values = {
        f"{info['parameter_id']}_{suffix}": str(value)
        for info in seed.sensor_infos
        for suffix, value in POLICIES[info["identifier"]].items()
    }
    Path(seed.profiles_path).write_text(
        "[Global]\n" + "".join(f"{key}={value}\n" for key, value in legacy_values.items()),
        encoding="utf-8",
    )
    backend.order[:] = discovery
    unavailable = backend.start()
    for info in unavailable.sensor_infos:
        for suffix in ("enable", "lower", "upper"):
            key = f"{info['parameter_id']}_{suffix}"
            expected = unavailable.parse_input_value(key, legacy_values[key])
            assert unavailable.dpg.get_value(f"input_{key}") == expected
            assert unavailable.get_setting(key) == expected
            # An incomplete save must retain the stored ordinal values exactly,
            # even if widgets have been edited while discovery is ambiguous.
            unavailable.dpg.set_value(f"input_{key}", False if suffix == "enable" else "1")
    unavailable.dpg.set_value("input_maxcap", "99")
    _save(unavailable, save_method, "Global")
    disk = new_config()
    read_config(disk, unavailable.profiles_path)
    assert "lhm_sensor_policies" not in disk["Global"]
    assert {key: disk["Global"][key] for key in legacy_values} == legacy_values
    assert disk["Global"]["maxcap"] == "99"
    assert any("migration deferred" in message for message in backend.logger.messages)
    backend.order[:] = [FIRST, SECOND]
    returned = backend.start()
    assert _policies_by_identifier(returned) == POLICIES
    _save(returned, save_method, "Global")
    assert json.loads(returned.profiles_config["Global"]["lhm_sensor_policies"]) == POLICIES


@pytest.mark.parametrize("save_method", ["save_profile", "save_to_profile"])
def test_deferred_migration_does_not_bind_new_sensor_or_drop_missing_hardware(backend, save_method):
    backend.order[:] = [[FIRST], [SECOND]]
    seed = backend.start()
    seed.update_preference_setting("first_launch_done", None, True, None)
    legacy_values = {
        f"{info['parameter_id']}_{suffix}": str(value)
        for info in seed.sensor_infos
        for suffix, value in POLICIES[info["identifier"]].items()
    }
    Path(seed.profiles_path).write_text(
        "[Global]\n" + "".join(f"{key}={value}\n" for key, value in legacy_values.items()),
        encoding="utf-8",
    )
    new = "/amdcpu/0/temperature/2"
    backend.order[:] = [FIRST, new]
    partial = backend.start()
    assert _policies_by_identifier(partial) == {
        FIRST: POLICIES[FIRST], new: {"enable": False, "lower": 0, "upper": 100},
    }
    partial.dpg.set_value("input_cpu1_temperature_02_enable", True)
    _save(partial, save_method, "Global")
    disk = new_config()
    read_config(disk, partial.profiles_path)
    assert "lhm_sensor_policies" not in disk["Global"]
    assert {key: disk["Global"][key] for key in legacy_values} == legacy_values
    assert "cpu1_temperature_02_enable" not in disk["Global"]
    backend.order[:] = [[FIRST], [SECOND]]
    assert _policies_by_identifier(backend.start()) == POLICIES


@pytest.mark.parametrize("save_method", ["save_profile", "save_to_profile"])
@pytest.mark.parametrize("first_launch", [False, True])
@pytest.mark.parametrize("raw", [
    "", "[", "[]", '{"unknown": {}}', "null",
    json.dumps({FIRST: {"enable": "False", "lower": 20, "upper": 60}}),
    json.dumps({FIRST: {"enable": True, "lower": None, "upper": 60}}),
    json.dumps({"": POLICIES[FIRST]}),
])
def test_invalid_mapping_does_not_crash_or_replace_saved_data(backend, save_method, first_launch, raw):
    seed = backend.start()
    seed.update_preference_setting("first_launch_done", None, not first_launch, None)
    _set_policies(seed)
    _save(seed, save_method, "Global")
    legacy_values = {
        f"{info['parameter_id']}_{suffix}": str(value)
        for info in seed.sensor_infos
        for suffix, value in POLICIES[info["identifier"]].items()
    }
    seed.profiles_config["Global"]["lhm_sensor_policies"] = raw
    write_config(seed.profiles_config, seed.profiles_path)
    cm = backend.start()
    default = {"enable": False, "lower": 0, "upper": 100}
    assert _policies_by_identifier(cm) == {FIRST: default, SECOND: default}
    for key in legacy_values:
        assert cm.get_setting(key) == default[key.rsplit("_", 1)[1]]
    cm.quick_load_settings()
    assert _policies_by_identifier(cm) == {FIRST: default, SECOND: default}
    _set_policies(cm)  # Widget edits must not replace corrupt persisted data.
    cm.dpg.set_value("input_maxcap", "99")
    _save(cm, save_method, "Global")
    disk = new_config()
    read_config(disk, cm.profiles_path)
    assert disk["Global"]["lhm_sensor_policies"] == raw
    assert {key: disk["Global"][key] for key in legacy_values} == legacy_values
    assert disk["Global"]["maxcap"] == "99"
    assert any("Error parsing lhm_sensor_policies" in message for message in backend.logger.messages)
    restarted = backend.start()
    assert _policies_by_identifier(restarted) == {FIRST: default, SECOND: default}
