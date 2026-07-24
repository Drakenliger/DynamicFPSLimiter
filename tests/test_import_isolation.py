"""TEST-001 discovery and pure-module import-isolation checks."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _flatten_suite(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from _flatten_suite(item)
        else:
            yield item


class TestDiscoveryAndIsolationTests(unittest.TestCase):
    def test_TEST_001_unittest_discovery_finds_suite_without_import_failures(self):
        suite = unittest.TestLoader().discover(
            str(REPOSITORY_ROOT / "tests"),
            top_level_dir=str(REPOSITORY_ROOT),
        )
        discovered = list(_flatten_suite(suite))

        self.assertGreaterEqual(len(discovered), 20)
        self.assertFalse(
            any(test.__class__.__name__ == "_FailedTest" for test in discovered)
        )

    def test_TEST_001_pure_modules_import_without_application_runtime_modules(self):
        script = f"""
import json
import sys
sys.path.insert(0, {str(REPOSITORY_ROOT)!r})
forbidden_runtime_prefixes = (
    "dearpygui",
    "clr",
    "System",
    "LibreHardwareMonitor",
    "winreg",
    "psutil",
)
for loaded_name in tuple(sys.modules):
    if any(
        loaded_name == prefix or loaded_name.startswith(prefix + ".")
        for prefix in forbidden_runtime_prefixes
    ):
        del sys.modules[loaded_name]
startup_modules = set(sys.modules)
import src.core.cap_selection
import src.core.controller_contracts
imported_modules = set(sys.modules) - startup_modules
allowed_application_modules = {{
    "src.core.cap_selection",
    "src.core.controller_contracts",
}}
unexpected_application_modules = sorted(
    name for name in imported_modules
    if (
        name.startswith("core.")
        or name.startswith("src.core.")
    )
    and name not in allowed_application_modules
)
unexpected_runtime_modules = sorted(
    name for name in imported_modules
    if any(
        name == prefix or name.startswith(prefix + ".")
        for prefix in forbidden_runtime_prefixes
    )
)
print(json.dumps({{
    "application_modules": unexpected_application_modules,
    "runtime_modules": unexpected_runtime_modules,
}}))
"""
        result = subprocess.run(
            [sys.executable, "-I", "-c", script],
            check=True,
            capture_output=True,
            text=True,
            cwd=REPOSITORY_ROOT,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "application_modules": [],
                "runtime_modules": [],
            },
        )
