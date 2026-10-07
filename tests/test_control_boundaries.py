"""Boundary and regression tests for 3-sample FPS mean, LibreHM upper threshold, and running autopilot."""
import ast
from decimal import Decimal
from pathlib import Path
import statistics
from types import SimpleNamespace as NS

from core.autopilot import autopilot_on_check
from core.cap_policy import evaluate_legacy_cap_change
from test_app_session import load_app


def load_real_evaluate_cap_change(ns, enabled=True, upper=90, value=90):
    """Load actual evaluate_cap_change function body from fps_utils.py."""
    fps_utils_path = Path(__file__).resolve().parents[1] / "src/core/fps_utils.py"
    tree = ast.parse(fps_utils_path.read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "FPSUtils")
    method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "evaluate_cap_change")
    helper = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "evaluate_librehm_decision")
    scope = {"statistics": statistics, "evaluate_legacy_cap_change": evaluate_legacy_cap_change}
    exec(compile(ast.Module(body=[helper, method], type_ignores=[]), "<FPSUtils>", "exec"), scope)

    values = {
        "input_monitoring_method": "LibreHM",
        "input_load_enable": enabled,
        "input_load_upper": upper,
        "input_load_lower": 70,
    }
    ns["dpg"].get_value = values.get
    ns["dpg"].does_item_exist = lambda tag: tag in values
    ns["cm"].sensor_infos = [
        dict(
            parameter_id="load",
            sensor_type="Load",
            sensor_name="GPU",
            sensor_name_indexed="1 GPU",
            hw_type="Gpu",
            hw_name="card",
        )
    ]
    sensor = NS(
        gpu_percentiles={("Load", "1 GPU"): value},
        gpu_history_long={("Load", "1 GPU"): [value, value]},
        cpu_percentiles={},
        cpu_history_long={},
    )
    obj = NS(
        cm=ns["cm"],
        dpg=ns["dpg"],
        lhm_sensor=sensor,
        HardwareType=NS(Cpu="Cpu"),
        logger=ns["logger"],
    )
    return lambda *args: scope["evaluate_cap_change"](obj, *args)


def run_monitoring_passes(ns, samples):
    """Run monitoring_loop for the specified FPS samples."""
    ticks = []
    ns["rtss_manager"].get_fps_for_active_window = lambda: samples[len(ticks)]

    def sleep(seconds):
        ticks.append(None)
        if len(ticks) == len(samples):
            ns["running"] = False

    ns["time"].sleep = sleep
    ns["monitoring_loop"](ns["session_number"])


def test_fps_mean_three_sample_window_boundary():
    """Verify that fps_mean calculates hard-coded 3-sample average after 4 samples."""
    ns, _, _, _ = load_app()
    samples = [
        (Decimal("10"), "game"),
        (Decimal("20"), "game"),
        (Decimal("30"), "game"),
        (Decimal("40"), "game"),
    ]
    run_monitoring_passes(ns, samples)
    # Expected: 3-sample window of [20, 30, 40] -> (20 + 30 + 40) / 3 = 30
    expected_fps_mean = Decimal("30")
    assert ns["fps_mean"] == expected_fps_mean


def test_librehm_exact_upper_threshold_qualifies_decrease():
    """Verify LibreHM sensor value equal to upper threshold qualifies decrease via >=."""
    ns, _, _, _ = load_app()
    eval_fn = load_real_evaluate_cap_change(ns, enabled=True, upper=90, value=90)
    should_decrease, should_increase = eval_fn([], [], "LibreHM")
    assert should_decrease is True
    assert should_increase is False


def test_autopilot_running_session_not_toggled_off():
    """Verify that autopilot_on_check does not call start_stop_callback when session is already running."""
    calls = []

    def dummy_start_stop_callback(*args, **kwargs):
        calls.append((args, kwargs))

    class DummyProfilesConfig:
        def sections(self):
            return ["GameApp"]

    class DummyConfigManager:
        def __init__(self):
            self.profiles_config = DummyProfilesConfig()
            self.autopilot_only_profiles = False
            self.loaded_profiles = []

        def load_profile_callback(self, sender, app_data, user_data):
            self.loaded_profiles.append((sender, app_data, user_data))

    class DummyRTSSManager:
        def is_rtss_running(self):
            return True

        def get_fps_for_active_window(self):
            return (60, "GameApp")

    class DummyDPG:
        def set_value(self, item, value):
            pass

    class DummyLogger:
        def add_log(self, message):
            pass

    cm = DummyConfigManager()
    rtss = DummyRTSSManager()
    dpg = DummyDPG()
    logger = DummyLogger()

    # Pass running=True
    autopilot_on_check(
        cm=cm,
        rtss_manager=rtss,
        dpg=dpg,
        logger=logger,
        running=True,
        start_stop_callback=dummy_start_stop_callback,
    )

    # Must NOT call start_stop_callback when session is already running
    assert len(calls) == 0
