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
        if "default_open" in kwargs and node.tag:
            self.values[node.tag] = kwargs["default_open"]
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

    def is_effectively_visible(self, tag_or_node):
        node = self.items_by_tag[tag_or_node] if isinstance(tag_or_node, str) else tag_or_node
        curr = node
        while curr and curr.item_type != "root":
            if curr.tag and self.shown_states.get(curr.tag) is False:
                return False
            curr = curr.parent
        return True


def _extract_lhm_block_ast():
    app_text = (SRC_DIR / "app.py").read_text(encoding="utf-8")
    tree = ast.parse(app_text)

    target_node = None
    for node in ast.walk(tree):
        if isinstance(node, ast.With):
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
        # GPU 0 (RTX 4090) - Multi-type (Temperature, Load)
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
        # GPU 1 (RTX 4090 - SAME HW NAME!) - Multi-type (Temperature, Load, Power)
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
    """Verify LHM group layout parent stack hierarchy, exact child ordering, and scaled gaps."""
    sensors = _make_sample_sensors()
    raw_dpg = RecordingDPG()
    _run_lhm_block(raw_dpg, scale, sensors)

    # 1. Reverse hardware order check
    collapsing_headers = [
        node for node in raw_dpg.items_by_tag.values() if node.item_type == "collapsing_header"
    ]
    assert len(collapsing_headers) == 3
    # Hardware insertion in sensors array: gpu_0, gpu_1, cpu_0. Reversed iteration produces: cpu_0, gpu_1, gpu_0
    assert [h.tag for h in collapsing_headers] == ["input_collapsing_cpu_0", "input_collapsing_gpu_1", "input_collapsing_gpu_0"]

    # Check same-named GPUs have distinct hw_ids and headers
    gpu0_header = raw_dpg.items_by_tag["input_collapsing_gpu_0"]
    gpu1_header = raw_dpg.items_by_tag["input_collapsing_gpu_1"]
    cpu0_header = raw_dpg.items_by_tag["input_collapsing_cpu_0"]

    assert gpu0_header.kwargs["label"] == "NVIDIA GeForce RTX 4090"
    assert gpu1_header.kwargs["label"] == "NVIDIA GeForce RTX 4090"
    assert cpu0_header.kwargs["label"] == "Intel Core i9-13900K"

    # 2. Assert parent stack hierarchy and child order inside each header
    for hw_id, expected_types in [
        ("gpu_0", ["Temperature", "Load"]),
        ("gpu_1", ["Temperature", "Load", "Power"]),
        ("cpu_0", ["Load"]),
    ]:
        header = raw_dpg.items_by_tag[f"input_collapsing_{hw_id}"]
        # Direct children of header are section groups
        sec_groups = [c for c in header.children if c.item_type == "group"]
        assert len(sec_groups) == len(expected_types)

        for idx, st_str in enumerate(expected_types):
            sec_group = sec_groups[idx]
            sec_tag = f"title_section_{hw_id}_{st_str}"
            assert sec_group.tag == sec_tag
            assert sec_group.parent == header

            # Check exact section child node order
            if idx == 0:
                # First section: [add_text, table]
                assert len(sec_group.children) == 2
                assert sec_group.children[0].item_type == "add_text"
                assert sec_group.children[1].item_type == "table"
                text_node = sec_group.children[0]
                table_node = sec_group.children[1]
            else:
                # Later sections: [add_spacer, add_text, table]
                assert len(sec_group.children) == 3
                assert sec_group.children[0].item_type == "add_spacer"
                assert sec_group.children[1].item_type == "add_text"
                assert sec_group.children[2].item_type == "table"

                spacer_node = sec_group.children[0]
                text_node = sec_group.children[1]
                table_node = sec_group.children[2]

                # Assert exactly one scaled 6/9px gap for every later section (including gpu_1 3rd type Power)
                expected_gap_height = int(6 * scale)
                assert spacer_node.kwargs["height"] == expected_gap_height

            # Heading text assertion
            assert text_node.kwargs["text"] == f"{st_str} Sensors:"
            assert text_node.parent == sec_group
            assert table_node.parent == sec_group

            # Check table rows and controls hierarchy
            rows = [c for c in table_node.children if c.item_type == "table_row"]
            assert len(rows) > 0
            for row in rows:
                assert row.parent == table_node
                assert row.tag.startswith("param_row_")
                # Check controls inside table row
                controls = row.children
                for ctrl in controls:
                    assert ctrl.parent == row

    # 3. Verify single-type group cpu_0 has zero gap
    sec_cpu_group = raw_dpg.items_by_tag["title_section_cpu_0_Load"]
    cpu_spacers = [c for c in sec_cpu_group.children if c.item_type == "add_spacer"]
    assert len(cpu_spacers) == 0

    # 4. Check for duplicate headers or headings
    all_headers = [c for c in raw_dpg.calls if c[0] == "collapsing_header"]
    assert len(all_headers) == 3

    text_headings = [
        c[1]["text"] for c in raw_dpg.calls
        if c[0] == "add_text" and c[1].get("text", "").endswith("Sensors:")
    ]
    assert len(text_headings) == 6


def test_hide_unselected_effective_visibility_and_state(tmp_path):
    """Test ConfigManager hide_unselected_callback effective visibility, parameters retention, and collapse setting stability."""
    sensors = _make_sample_sensors()
    raw_dpg = RecordingDPG()

    from core.config_manager import ConfigManager

    cm = ConfigManager(
        logger_instance=type("Logger", (), {"add_log": lambda *a, **k: None})(),
        dpg_instance=ScaledDPG(raw_dpg, 1.0),
        rtss_instance=None,
        tray_instance=None,
        themes_manager=type("Themes", (), {"themes": {}})(),
        base_dir=str(tmp_path / "core" / "app.py")
    )
    cm.sensor_infos = sensors
    cm.ui_initialized = True

    _run_lhm_block(raw_dpg, scale=1.0, sensor_infos=sensors, cm_mock=cm)

    # Initial state: hide_unselected is False -> all sections, headings, tables, spacers, rows effectively visible
    cm.hide_unselected_callback(app_data=False)
    for hw_id, types in [("gpu_0", ["Temperature", "Load"]), ("gpu_1", ["Temperature", "Load", "Power"]), ("cpu_0", ["Load"])]:
        for st in types:
            sec_tag = f"title_section_{hw_id}_{st}"
            assert raw_dpg.is_effectively_visible(sec_tag) is True
            sec_node = raw_dpg.items_by_tag[sec_tag]
            for child in sec_node.children:
                assert raw_dpg.is_effectively_visible(child) is True

    # 1. False -> True with ALL off -> False cleanly restores heading, table, gap, and rows
    cm.hide_unselected_callback(app_data=True)
    # When all off and hide=True, all sections are hidden
    for hw_id, types in [("gpu_0", ["Temperature", "Load"]), ("gpu_1", ["Temperature", "Load", "Power"]), ("cpu_0", ["Load"])]:
        for st in types:
            sec_tag = f"title_section_{hw_id}_{st}"
            assert raw_dpg.is_effectively_visible(sec_tag) is False
            sec_node = raw_dpg.items_by_tag[sec_tag]
            for child in sec_node.children:
                assert raw_dpg.is_effectively_visible(child) is False

    # Toggle back to False -> restores visibility
    cm.hide_unselected_callback(app_data=False)
    for hw_id, types in [("gpu_0", ["Temperature", "Load"]), ("gpu_1", ["Temperature", "Load", "Power"]), ("cpu_0", ["Load"])]:
        for st in types:
            sec_tag = f"title_section_{hw_id}_{st}"
            assert raw_dpg.is_effectively_visible(sec_tag) is True
            sec_node = raw_dpg.items_by_tag[sec_tag]
            for child in sec_node.children:
                assert raw_dpg.is_effectively_visible(child) is True

    # 2. Enable gpu0_load_0, gpu1_power_0, and cpu0_load_0
    raw_dpg.set_value("input_gpu0_load_0_enable", True)
    raw_dpg.set_value("input_gpu1_power_0_enable", True)
    raw_dpg.set_value("input_cpu0_load_0_enable", True)

    # Set custom lower/upper values on enabled controls to verify threshold values are retained
    raw_dpg.set_value("input_gpu0_load_0_lower", "25")
    raw_dpg.set_value("input_gpu0_load_0_upper", "85")

    # Capture initial collapse open values of headers
    header_collapse_values = {
        hw_id: raw_dpg.get_value(f"input_collapsing_{hw_id}")
        for hw_id in ["gpu_0", "gpu_1", "cpu_0"]
    }

    # Toggle hide_unselected to True
    cm.hide_unselected_callback(app_data=True)

    # Same-named hardware items are independent:
    # gpu_0: Load section visible, Temperature section hidden
    assert raw_dpg.is_effectively_visible("title_section_gpu_0_Load") is True
    assert raw_dpg.is_effectively_visible("title_section_gpu_0_Temperature") is False

    # gpu_1: Power section visible, Temperature and Load sections hidden
    assert raw_dpg.is_effectively_visible("title_section_gpu_1_Power") is True
    assert raw_dpg.is_effectively_visible("title_section_gpu_1_Temperature") is False
    assert raw_dpg.is_effectively_visible("title_section_gpu_1_Load") is False

    # cpu_0: Load section visible
    assert raw_dpg.is_effectively_visible("title_section_cpu_0_Load") is True

    # Verify control enable and threshold values are retained
    assert raw_dpg.get_value("input_gpu0_load_0_enable") is True
    assert raw_dpg.get_value("input_gpu0_load_0_lower") == "25"
    assert raw_dpg.get_value("input_gpu0_load_0_upper") == "85"

    # Callback must not reopen or alter header collapse settings
    for hw_id in ["gpu_0", "gpu_1", "cpu_0"]:
        assert raw_dpg.get_value(f"input_collapsing_{hw_id}") == header_collapse_values[hw_id]


def test_internal_spacing_regression_fails_on_old_format():
    """Verify that layout hierarchy and effective visibility regression rejects bare title layout."""
    sensors = _make_sample_sensors()
    raw_dpg = RecordingDPG()
    _run_lhm_block(raw_dpg, scale=1.0, sensor_infos=sensors)

    sec_load_gpu0 = raw_dpg.items_by_tag["title_section_gpu_0_Load"]
    assert sec_load_gpu0.item_type == "group", "New format wraps section in container group"

    text_node = next(c for c in sec_load_gpu0.children if c.item_type == "add_text")
    assert text_node.kwargs["text"] == "Load Sensors:"

    # Verify effective visibility modeling on container group rejects orphaned bare text
    raw_dpg.configure_item("title_section_gpu_0_Load", show=False)
    assert raw_dpg.is_effectively_visible("title_section_gpu_0_Load") is False
    assert raw_dpg.is_effectively_visible(text_node) is False
