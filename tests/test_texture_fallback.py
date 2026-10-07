"""Linux regression test executing actual load_and_create_textures without app.py import side effects."""
import ast
import contextlib
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "src/core/app.py"


def load_actual_function():
    tree = ast.parse(APP_PATH.read_text())
    nodes = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "load_and_create_textures"]
    ns = {"os": os}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "app.py", "exec"), ns)
    return ns["load_and_create_textures"]


class FakeDPG:
    def __init__(self, image_map=None):
        self.image_map = image_map or {}
        self.texture_calls = []

    @contextlib.contextmanager
    def texture_registry(self):
        yield

    def load_image(self, path):
        # Return mapped result or None if path not in image_map
        return self.image_map.get(path, None)

    def add_static_texture(self, width, height, data, tag):
        self.texture_calls.append((width, height, data, tag))
        return tag


def test_texture_fallback_valid_none_and_mixed():
    load_and_create_textures = load_actual_function()
    base_dir = "/app_base"

    valid_path = os.path.join(base_dir, "assets/valid_icon.png")
    missing_path = os.path.join(base_dir, "assets/missing_icon.png")
    non_ascii_missing_path = os.path.join(base_dir, "assets/non_ascii_ñ_icon.png")

    valid_data = [0.1, 0.2, 0.3, 1.0] * 100
    image_map = {
        valid_path: (10, 10, 4, valid_data),
        missing_path: None,
        non_ascii_missing_path: None,
    }

    fake_dpg = FakeDPG(image_map)

    image_files = [
        "valid_icon.png",
        "missing_icon.png",
        "non_ascii_ñ_icon.png",
    ]

    textures = load_and_create_textures(image_files, base_dir, fake_dpg)

    # All expected keys are preserved
    assert set(textures.keys()) == {"valid_icon", "missing_icon", "non_ascii_ñ_icon"}
    assert textures["valid_icon"] == "valid_icon_texture"
    assert textures["missing_icon"] == "missing_icon_texture"
    assert textures["non_ascii_ñ_icon"] == "non_ascii_ñ_icon_texture"

    # Verify call parameters for valid image
    assert fake_dpg.texture_calls[0] == (10, 10, valid_data, "valid_icon_texture")
    # Exact data identity preserved for valid image
    assert fake_dpg.texture_calls[0][2] is valid_data

    # Verify call parameters for None / inaccessible images
    assert fake_dpg.texture_calls[1] == (1, 1, [1.0, 1.0, 1.0, 1.0], "missing_icon_texture")
    assert fake_dpg.texture_calls[2] == (1, 1, [1.0, 1.0, 1.0, 1.0], "non_ascii_ñ_icon_texture")


def test_texture_fallback_all_missing():
    load_and_create_textures = load_actual_function()
    base_dir = "/app_base"

    fake_dpg = FakeDPG({})  # All load_image calls return None

    image_files = ["close_button.png", "minimize_button.png", "icon_reset.png"]
    textures = load_and_create_textures(image_files, base_dir, fake_dpg)

    assert set(textures.keys()) == {"close_button", "minimize_button", "icon_reset"}
    for name in image_files:
        base = os.path.splitext(name)[0]
        assert textures[base] == f"{base}_texture"

    for call in fake_dpg.texture_calls:
        width, height, data, tag = call
        assert width == 1
        assert height == 1
        assert data == [1.0, 1.0, 1.0, 1.0]
