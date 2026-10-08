"""Tests for sensor-type subheadings and internal section spacing inside LibreHardwareMonitor groups.

Executes actual production app.py AST code block with a recording DPG and real context stack.
"""
import ast
from collections import defaultdict, OrderedDict
from pathlib import Path
import pytest

from core.ui_scale import ScaledDPG

SRC_DIR = Path(__file__).resolve().parents[1] / "src" / "core"


class DPGNode:
    def __init__(self, item_type, tag=None, kwargs=None, parent=None):
        self.item_type = item_type
        self.tag = tag or f"item_{id(self)}"
        self.kwargs = kwargs or {}
        self.parent = parent
        self.children = []
        if parent:
            parent.children.append(self)


class RecordingDPG:
    mvTable_SizingFixedFit = 0

    def __init__(self):
        self.root = DPGNode("root")
        self.stack = [self.root]
        self.items_by_tag = {self.root.tag: self.root}
        self.calls = []
        self.shown_states = {}
        self.values = {}

    def _add_item(self, item_type, kwargs):
        tag = kwargs.get("tag")
        node = DPGNode(item_type, tag=tag, kwargs=kwargs, parent=self.stack[-1])
        if tag:
            self.items_by_tag[tag] = node
            self.shown_states[tag] = kwargs.get("show", True)
            if "default_value" in kwargs:
                self.values[tag] = kwargs["default_value"]
        self.calls.append((item_type, kwargs, node.parent.tag))
        return node

    class Context:
        def __init__(self, dpg, node):
            self.dpg = dpg
            self.node = node

        def __enter__(self):
            self.dpg.stack.append(self.node)
            return self.node

        def __exit__(self, exc_type, exc_val, exc_tb):
            self.dpg.stack.pop()

    def collapsing_header(self, **kwargs):
        node = self._add_item("collapsing_header", kwargs)
        return self.Context(self, node)

    def group(self, **kwargs):
        node = self._add_item("group", kwargs)
        return self.Context(self, node)

    def table(self, **kwargs):
        node = self._add_item("table", kwargs)
        return self.Context(self, node)

    def table_row(self, **kwargs):
        node = self._add_item("table_row", kwargs)
        return self.Context(self, node)

    def child_window(self, **kwargs):
        node = self._add_item("child_window", kwargs)
        return self.Context(self, node)

    def add_text(self, text, **kwargs):
        kwargs["text"] = text
        return self._add_item("add_text", kwargs)

    def add_spacer(self, **kwargs):
        return self._add_item("add_spacer", kwargs)

    def add_checkbox(self, **kwargs):
        return self._add_item("add_checkbox", kwargs)

    def add_input_text(self, **kwargs):
        return self._add_item("add_input_text", kwargs)

    def add_table_column(self, **kwargs):
        return self._add_item("add_table_column", kwargs)

    def add_button(self, **kwargs):
        return self._add_item("add_button", kwargs)

    def configure_item(self, tag, **kwargs):
        if "show" in kwargs:
            self.shown_states[tag] = kwargs["show"]
        self.calls.append(("configure_item", {"tag": tag, **kwargs}, None))

    def does_item_exist(self, tag):
        return tag in self.items_by_tag

    def get_value(self, tag):
        return self.values.get(tag, False)

    def set_value(self, tag, val):
        self.values[tag] = val


def _extract_lhm_block_ast():
    app_text = (SRC_DIR / "app.py").read_text(encoding="utf-8")
    tree = ast.parse(app_text)

    # Find the with block in app.py that performs sensors_by_hw grouping
    target_node = None
    for node in ast.walk(tree):
        if isinstance(node, ast.With):
            # Check if this with statement contains 'sensors_by_hw' assignment
            for stmt in node.body:
                if isinstance(stmt, ast.Assign):
                    for target in stmt.targets:
                        if isinstance(target, ast.Name) and target.id == "sensors_by_hw":
                            target_node = node
                            break
            if target_node:
                break

    assert target_node is not None, "Could not find LHwM construction AST block in app.py"
    return ast.Module(body=[target_node], type_ignores=[])


def _run_lhm_block(raw_dpg, scale, sensor_infos, cm_mock=None):
    scaled_dpg = ScaledDPG(raw_dpg, scale=scale)

    if cm_mock is None:
        class ConfigMock:
            def __init__(self):
                self.sensor_infos = sensor_infos
                self.hide_unselected = False
                self.hide_unselected_callback = lambda *a, **k: None

        cm_mock = ConfigMock()

    ns = {
        "dpg": scaled_dpg,
        "cm": cm_mock,
        "mid_window_height": 285,
        "reversed": reversed,
        "list": list,
        "str": str,
        "hasattr": hasattr,
    }

    ast_mod = _extract_lhm_block_ast()
    exec(compile(ast_mod, "<app_lhm_block>", "exec"), ns)
    return raw_dpg, cm_mock


def _make_sample_sensors():
    # Two same-named hardware items with distinct hw_ids and multiple sensor types
    # Plus one single-type group (cpu)
    class FakeSensorType:
        def __init__(self, name):
            self.name = name

        def ToString(self):
            return self.name

        def __str__(self):
            return self.name

    st_temp = FakeSensorType("Temperature")
    st_load = FakeSensorType("Load")
    st_power = FakeSensorType("Power")

    sensors = [
        # GPU 1 (RTX 4090) - Multi-type (Temperature, Load)
        {
            "hw_id": "gpu_0",
            "hw_name": "NVIDIA GeForce RTX 4090",
            "sensor_type": st_temp,
            "parameter_id": "gpu0_temp_0",
            "sensor_name": "GPU Core Temp",
        },
        {
            "hw_id": "gpu_0",
            "hw_name": "NVIDIA GeForce RTX 4090",
            "sensor_type": st_load,
            "parameter_id": "gpu0_load_0",
            "sensor_name": "GPU Core Load",
        },
        # GPU 2 (RTX 4090 - SAME HW NAME!) - Multi-type (Temperature, Load, Power)
        {
            "hw_id": "gpu_1",
            "hw_name": "NVIDIA GeForce RTX 4090",
            "sensor_type": st_temp,
            "parameter_id": "gpu1_temp_0",
            "sensor_name": "GPU Core Temp",
        },
        {
            "hw_id": "gpu_1",
            "hw_name": "NVIDIA GeForce RTX 4090",
            "sensor_type": st_load,
            "parameter_id": "gpu1_load_0",
            "sensor_name": "GPU Core Load",
        },
        {
            "hw_id": "gpu_1",
            "hw_name": "NVIDIA GeForce RTX 4090",
            "sensor_type": st_power,
            "parameter_id": "gpu1_power_0",
            "sensor_name": "GPU Power",
        },
        # CPU - Single-type (Load only)
        {
            "hw_id": "cpu_0",
            "hw_name": "Intel Core i9-13900K",
            "sensor_type": st_load,
            "parameter_id": "cpu0_load_0",
            "sensor_name": "CPU Total Load",
        },
    ]
    return sensors


@pytest.mark.parametrize("dpi,scale", [(96, 1.0), (144, 1.5)])
def test_lhm_group_layout_structure_and_subheadings(dpi, scale):
    """Verify LHM group layout structure, clarified subheadings, scaled gaps, and single-type separators."""
    sensors = _make_sample_sensors()
    raw_dpg = RecordingDPG()
    _run_lhm_block(raw_dpg, scale, sensors)

    # 1. Assert exactly one collapsing header per hw_id
    collapsing_headers = [
        node for node in raw_dpg.items_by_tag.values() if node.item_type == "collapsing_header"
    ]
    header_tags = {node.tag for node in collapsing_headers}
    assert header_tags == {"input_collapsing_gpu_0", "input_collapsing_gpu_1", "input_collapsing_cpu_0"}
    assert len(collapsing_headers) == 3

    # Check same-named GPUs have distinct hw_ids and headers
    gpu0_header = raw_dpg.items_by_tag["input_collapsing_gpu_0"]
    gpu1_header = raw_dpg.items_by_tag["input_collapsing_gpu_1"]
    cpu0_header = raw_dpg.items_by_tag["input_collapsing_cpu_0"]

    assert gpu0_header.kwargs["label"] == "NVIDIA GeForce RTX 4090"
    assert gpu1_header.kwargs["label"] == "NVIDIA GeForce RTX 4090"
    assert cpu0_header.kwargs["label"] == "Intel Core i9-13900K"

    # 2. Check clarified subheadings inside sections ("... Sensors:")
    for hw_id, expected_types in [
        ("gpu_0", ["Temperature", "Load"]),
        ("gpu_1", ["Temperature", "Load", "Power"]),
        ("cpu_0", ["Load"]),
    ]:
        for st_str in expected_types:
            sec_tag = f"title_section_{hw_id}_{st_str}"
            assert sec_tag in raw_dpg.items_by_tag, f"Missing section container group {sec_tag}"
            sec_group = raw_dpg.items_by_tag[sec_tag]
            assert sec_group.item_type == "group"

            # Find the heading text inside section group
            text_node = next(
                (c for c in sec_group.children if c.item_type == "add_text"), None
            )
            assert text_node is not None, f"Heading text missing in {sec_tag}"
            assert text_node.kwargs["text"] == f"{st_str} Sensors:", (
                f"Heading text '{text_node.kwargs['text']}' not clarified"
            )

    # 3. Check section gaps and single-type separator rules
    # Multi-type group gpu_0 (2 types: Temperature, Load)
    sec_temp_gpu0 = raw_dpg.items_by_tag["title_section_gpu_0_Temperature"]
    sec_load_gpu0 = raw_dpg.items_by_tag["title_section_gpu_0_Load"]

    # First section in multi-type group should have no leading spacer
    spacers_sec0 = [c for c in sec_temp_gpu0.children if c.item_type == "add_spacer"]
    assert len(spacers_sec0) == 0

    # Second section in multi-type group should have exactly 1 scaled internal spacer at top
    spacers_sec1 = [c for c in sec_load_gpu0.children if c.item_type == "add_spacer"]
    assert len(spacers_sec1) == 1
    expected_gap_height = int(6 * scale)
    assert spacers_sec1[0].kwargs["height"] == expected_gap_height

    # Single-type group cpu_0 (1 type: Load)
    sec_load_cpu0 = raw_dpg.items_by_tag["title_section_cpu_0_Load"]
    cpu_spacers = [c for c in sec_load_cpu0.children if c.item_type == "add_spacer"]
    assert len(cpu_spacers) == 0, "Single-type group must not have redundant internal section separators"

    # 4. Check parameter rows, tags, and controls
    for param_id in ["gpu0_temp_0", "gpu0_load_0", "gpu1_temp_0", "gpu1_load_0", "gpu1_power_0", "cpu0_load_0"]:
        row_tag = f"param_row_{param_id}"
        assert row_tag in raw_dpg.items_by_tag
        enable_tag = f"input_{param_id}_enable"
        lower_tag = f"input_{param_id}_lower"
        upper_tag = f"input_{param_id}_upper"

        assert enable_tag in raw_dpg.items_by_tag
        assert lower_tag in raw_dpg.items_by_tag
        assert upper_tag in raw_dpg.items_by_tag

        assert raw_dpg.items_by_tag[enable_tag].kwargs["default_value"] is False
        assert raw_dpg.items_by_tag[lower_tag].kwargs["default_value"] == 0
        assert raw_dpg.items_by_tag[upper_tag].kwargs["default_value"] == 100


def test_hide_unselected_behavior_on_groups_and_spacing():
    """Test actual ConfigManager hide_unselected_callback logic on section groups and row tags."""
    sensors = _make_sample_sensors()
    raw_dpg = RecordingDPG()

    from core.config_manager import ConfigManager

    class MockCM(ConfigManager):
        def __init__(self, dpg_inst, sensor_infos):
            self.dpg = dpg_inst
            self.sensor_infos = sensor_infos
            self.hide_unselected = False
            self.ui_initialized = True
            self.logger = type("Logger", (), {"add_log": lambda *a, **k: None})()

        def update_preference_setting(self, key, sender, hide, user_data):
            self.hide_unselected = hide

    cm = MockCM(ScaledDPG(raw_dpg, 1.0), sensors)
    _run_lhm_block(raw_dpg, scale=1.0, sensor_infos=sensors, cm_mock=cm)

    # Initial state: hide_unselected is False
    cm.hide_unselected_callback(app_data=False)
    for hw_id in ["gpu_0", "gpu_1", "cpu_0"]:
        for sec_tag in [f"title_section_{hw_id}_Temperature", f"title_section_{hw_id}_Load", f"title_section_{hw_id}_Power"]:
            if sec_tag in raw_dpg.items_by_tag:
                assert raw_dpg.shown_states.get(sec_tag, True) is True

    # Enable one sensor in gpu_0 Load section
    raw_dpg.set_value("input_gpu0_load_0_enable", True)

    # Toggle hide_unselected to True
    cm.hide_unselected_callback(app_data=True)

    # Section gpu_0 Temperature has 0 enabled params -> title_section_gpu_0_Temperature shown = False
    assert raw_dpg.shown_states.get("title_section_gpu_0_Temperature") is False
    # Section gpu_0 Load has 1 enabled param -> title_section_gpu_0_Load shown = True
    assert raw_dpg.shown_states.get("title_section_gpu_0_Load") is True

    # Check that when section title_section_gpu_0_Temperature is hidden, its container group is hidden,
    # ensuring no orphaned heading or empty section gaps are left visible.
    sec_temp_group = raw_dpg.items_by_tag["title_section_gpu_0_Temperature"]
    assert raw_dpg.shown_states[sec_temp_group.tag] is False

    # Check param rows in hidden section
    assert raw_dpg.shown_states.get("param_row_gpu0_temp_0") is False
    assert raw_dpg.shown_states.get("param_row_gpu0_load_0") is True


def test_internal_spacing_regression_fails_on_old_format():
    """Verify that layout subheadings and section gap structure assertion fails if legacy main format is used."""
    sensors = _make_sample_sensors()
    raw_dpg = RecordingDPG()
    _run_lhm_block(raw_dpg, scale=1.0, sensor_infos=sensors)

    sec_load_gpu0 = raw_dpg.items_by_tag["title_section_gpu_0_Load"]
    text_node = next(c for c in sec_load_gpu0.children if c.item_type == "add_text")

    # Asserting clarified heading format vs legacy heading format
    assert text_node.kwargs["text"] != "Load:", "Old main format used 'Load:' instead of 'Load Sensors:'"
    assert text_node.kwargs["text"] == "Load Sensors:"

    # Asserting internal section spacer presence
    spacers = [c for c in sec_load_gpu0.children if c.item_type == "add_spacer"]
    assert len(spacers) == 1, "Old main had no internal section spacers"
    assert spacers[0].kwargs["height"] == 6
