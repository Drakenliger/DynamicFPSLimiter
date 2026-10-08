"""Version single-source-of-truth tests.

Bump the version in exactly one place — ``src/core/version.py`` — and these
tests guarantee every derived artifact stays consistent:

- ``src/metadata/version.txt`` (the PyInstaller ``--version-file`` resource)
  matches what the build regenerates (``src/__main__.py --build``).
- the committed ``version.txt`` actually parses through PyInstaller's own
  deserializer, so the exe version metadata can never be broken.
- ``app.py`` shows the version only via ``display_version()`` (nothing
  hardcoded).
"""
import ast
import os
from types import SimpleNamespace
import subprocess
import sys
from pathlib import Path

import pytest

from core.version import VERSION, display_version, full_version, version_file_text, write_version_txt

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
VERSION_TXT = SRC_DIR / "metadata" / "version.txt"
APP = SRC_DIR / "core" / "app.py"


def test_version_is_a_four_part_tuple():
    assert VERSION == (5, 1, 0, 0)
    assert len(VERSION) == 4
    assert all(isinstance(part, int) and part >= 0 for part in VERSION)


def test_version_strings_follow_the_version():
    assert full_version() == "5.1.0.0"
    assert display_version() == "v5.1.0"


def test_version_txt_in_sync_with_single_source():
    assert VERSION_TXT.read_text(encoding="utf-8") == version_file_text()


def test_version_txt_release_metadata_and_identity():
    text = VERSION_TXT.read_text(encoding="utf-8")
    assert "filevers=(5, 1, 0, 0)" in text
    assert "prodvers=(5, 1, 0, 0)" in text
    for key, value in {
        "FileVersion": "5.1.0.0",
        "ProductVersion": "5.1.0.0",
        "CompanyName": "SameSalamander5710",
        "FileDescription": "DynamicFPSLimiter",
        "InternalName": "DynamicFPSLimiter",
        "OriginalFilename": "DynamicFPSLimiter.exe",
        "ProductName": "DynamicFPSLimiter",
    }.items():
        assert f"StringStruct('{key}', '{value}')" in text


def test_write_version_txt(tmp_path):
    path = tmp_path / "version.txt"
    write_version_txt(path)
    assert path.read_bytes() == VERSION_TXT.read_bytes()


def _execute_call(call, namespace):
    # Execute only the selected real call, without importing the native app.
    expression = ast.Expression(body=call)
    return eval(compile(expression, str(APP), "eval"), namespace)


def test_actual_app_titlebar_and_loading_version():
    tree = ast.parse(APP.read_text(encoding="utf-8"))
    assert any(isinstance(node, ast.ImportFrom) and node.module == "core.version"
               and any(alias.name == "display_version" for alias in node.names)
               for node in tree.body)
    primary = next(node for node in ast.walk(tree) if isinstance(node, ast.With)
                   and any(isinstance(item.context_expr, ast.Call)
                           and any(kw.arg == "tag" and isinstance(kw.value, ast.Constant)
                                   and kw.value.value == "Primary Window"
                                   for kw in item.context_expr.keywords)
                           for item in node.items))
    titlebar = next(node for node in primary.body if isinstance(node, ast.With))
    texts = []
    namespace = {"display_version": display_version, "app_title": "Dynamic FPS Limiter",
                 "dpg": SimpleNamespace(add_text=lambda value, **kw: texts.append(value))}
    for node in titlebar.body:
        if (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Attribute)
                and node.value.func.attr == "add_text"):
            _execute_call(node.value, namespace)
    assert texts == ["Dynamic FPS Limiter", "v5.1.0"]
    loading = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
               and isinstance(node.func, ast.Name) and node.func.id == "show_loading_popup"]
    assert len(loading) == 1
    messages = []
    namespace.update(show_loading_popup=lambda message, **kw: messages.append(message),
                     Base_dir="unused")
    _execute_call(loading[0], namespace)
    assert messages == ["Loading Dynamic FPS Limiter v5.1.0..."]
    identity = next(node for node in tree.body if isinstance(node, ast.Assign)
                    and any(isinstance(target, ast.Name) and target.id == "app_title"
                            for target in node.targets))
    assert ast.literal_eval(identity.value) == "Dynamic FPS Limiter"
    viewport = next(node for node in ast.walk(tree) if isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute) and node.func.attr == "create_viewport")
    assert ast.literal_eval(next(kw.value for kw in viewport.keywords if kw.arg == "title")) == "Dynamic FPS Limiter"


def test_build_regenerates_and_uses_metadata(monkeypatch, tmp_path):
    import core.version as version

    build_path = SRC_DIR / "__main__.py"
    tree = ast.parse(build_path.read_text(encoding="utf-8"))
    build = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                 and node.name == "build_executable")
    events = []
    generated = tmp_path / "version.txt"

    def regenerate(path):
        assert Path(path) == VERSION_TXT
        write_version_txt(generated)
        events.append("metadata")

    def package(args):
        assert events == ["metadata"]
        assert generated.read_bytes() == VERSION_TXT.read_bytes()
        assert args[args.index("--version-file") + 1] == "src/metadata/version.txt"
        assert args[args.index("--name") + 1] == "DynamicFPSLimiter"
        events.append("package")

    monkeypatch.setattr(version, "write_version_txt", regenerate)
    namespace = {"__file__": str(build_path),
                 "os": SimpleNamespace(path=os.path, walk=lambda path: [], pathsep=os.pathsep),
                 "PyInstaller": SimpleNamespace(__main__=SimpleNamespace(run=package))}
    module = ast.Module(body=[build], type_ignores=[])
    exec(compile(module, str(build_path), "exec"), namespace)
    namespace["build_executable"]()
    assert events == ["metadata", "package"]


@pytest.mark.win32
def test_version_txt_deserializes_with_pyinstaller():
    code = (
        "import sys\n"
        "from PyInstaller.utils.win32.versioninfo import "
        "load_version_info_from_text_file\n"
        "info = load_version_info_from_text_file(sys.argv[1])\n"
        "print(info.ffi.fileVersionMS, info.ffi.fileVersionLS, "
        "info.ffi.productVersionMS, info.ffi.productVersionLS)\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code, str(VERSION_TXT)],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert proc.returncode == 0, proc.stderr
    assert tuple(int(v) for v in proc.stdout.split()) == (327681, 0, 327681, 0)
