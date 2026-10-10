import sys
import os
import ast
import importlib.util
import logging
import threading
import ntpath
import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch, MagicMock, ANY

# Add src directory to python path
_original_sys_path = sys.path[:]
try:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
    from core.autostart import AutoStartManager
finally:
    sys.path[:] = _original_sys_path
    del _original_sys_path

MOCK_ENV_ROOTS = {
    "ProgramFiles": r"C:\Program Files",
    "ProgramFiles(x86)": r"C:\Program Files (x86)",
    "ProgramW6432": r"C:\Program Files",
}


class TestAutoStartInstallWarning(unittest.TestCase):
    def setUp(self):
        patcher = patch("core.autostart.current_user_id", return_value="DOMAIN\\User")
        patcher.start()
        self.addCleanup(patcher.stop)


    @patch.dict(os.environ, MOCK_ENV_ROOTS, clear=True)
    @patch("core.autostart.subprocess.run")
    def test_production_constructor_warning_visible_with_error_logging(self, mock_run):
        app_source = Path(__file__).resolve().parents[1] / "src/core/app.py"
        # Load the real logger without importing the GUI app or changing sys.modules.
        logger_spec = importlib.util.spec_from_file_location(
            "autostart_test_logger", app_source.with_name("logger.py"),
        )
        app_logger = importlib.util.module_from_spec(logger_spec)
        logger_spec.loader.exec_module(app_logger)
        tree = ast.parse(app_source.read_text(encoding="utf-8"))
        constructors = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "AutoStartManager"
        ]
        self.assertEqual(len(constructors), 1)
        constructor = compile(ast.Expression(constructors[0]), str(app_source), "eval")
        root = logging.getLogger()
        # Run the real app logging initializer with fresh handlers, as at startup.
        # Patch module state and close only the handlers this test creates.
        with tempfile.TemporaryDirectory() as temp_dir, \
                patch.object(root, "handlers", []), \
                patch.object(root, "level", logging.NOTSET), \
                patch.object(sys, "excepthook"), \
                patch.object(threading, "excepthook", threading.excepthook), \
                patch.object(app_logger, "log_messages", []), \
                patch.object(app_logger, "_gui_queue", None), \
                patch.object(app_logger, "_dpg", None), \
                patch.object(app_logger, "add_log", wraps=app_logger.add_log) as gui_log:
            try:
                app_logger.init_logging(str(Path(temp_dir) / "error.log"))
                self.assertEqual(root.level, logging.ERROR)
                self.assertFalse(root.isEnabledFor(logging.WARNING))
                with patch.object(root.handlers[0], "emit") as standard_emit:
                    manager = eval(constructor, {
                        "AutoStartManager": AutoStartManager,
                        "os": SimpleNamespace(path=ntpath),
                        "Base_dir": r"C:\Users\Public\DynamicFPSLimiter\src",
                        "logger": app_logger,
                    })
                    self.assertIs(manager.logger, app_logger)
                    manager.create()
                    standard_emit.assert_not_called()
                gui_log.assert_called_once()
                self.assertIn("outside Program Files", gui_log.call_args.args[0])
                self.assertEqual(app_logger.log_messages, [gui_log.call_args.args[0]])
                mock_run.assert_called_once_with([
                    "schtasks", "/Create", "/TN", "DynamicFPSLimiter",
                    "/XML", ANY, "/F",
                ], creationflags=0x08000000, check=True)
            finally:
                for handler in root.handlers:
                    handler.close()
                if hasattr(app_logger, "close_fatal_sink"):
                    app_logger.close_fatal_sink()
                # Restore level through the public API to clear logging's cache.
                root.setLevel(logging.NOTSET)

    @patch.dict(os.environ, MOCK_ENV_ROOTS, clear=True)
    @patch("core.autostart.subprocess.run")
    @patch("core.autostart.logging.warning", side_effect=RuntimeError("Logging failure"))
    def test_standard_logging_failure_still_reaches_gui(self, mock_warning, mock_run):
        gui_logger = MagicMock()
        manager = AutoStartManager(
            app_path=r"C:\Users\Public\DynamicFPSLimiter.exe", logger=gui_logger,
        )
        manager.create()
        mock_warning.assert_called_once()
        gui_logger.add_log.assert_called_once_with(f"Warning: {mock_warning.call_args.args[0]}")
        mock_run.assert_called_once()
        self.assertEqual(mock_run.call_args.args[0][1], "/Create")

    @patch.dict(os.environ, MOCK_ENV_ROOTS, clear=True)
    def test_is_in_program_files_inside(self):
        inside_paths = [
            r"C:\Program Files\DynamicFPSLimiter\DynamicFPSLimiter.exe",
            r"C:\Program Files (x86)\DynamicFPSLimiter\DynamicFPSLimiter.exe",
            r"c:\program files\app\app.exe",
            r"C:\Program Files\app.exe",
        ]
        for path in inside_paths:
            mgr = AutoStartManager(app_path=path)
            self.assertTrue(
                mgr.is_in_program_files(),
                f"Expected '{path}' to be detected inside configured Program Files roots",
            )

    @patch.dict(os.environ, {
        "ProgramFiles": r"D:\Applications",
        "ProgramFiles(x86)": r"E:\Applications32",
        "ProgramW6432": r"F:\Applications64",
    }, clear=True)
    def test_configured_alternate_drives_are_inside(self):
        for path in (
            r"D:\Applications\app.exe",
            r"E:\Applications32\app.exe",
            r"F:\Applications64\app.exe",
        ):
            with self.subTest(path=path):
                self.assertTrue(AutoStartManager(app_path=path).is_in_program_files())

    @patch.dict(os.environ, MOCK_ENV_ROOTS, clear=True)
    def test_is_in_program_files_outside_regressions(self):
        outside_paths = [
            r"D:\Program Files\App\app.exe",                 # Other drive same folder name
            r"\\share\Program Files\app.exe",                # UNC share
            r"\\Program Files\app.exe",                       # UNC root share
            r"C:Program Files\app.exe",                       # Drive-relative path
            r"Program Files\App\app.exe",                    # Relative path
            r"C:\Program FilesPayload\app.exe",               # Prefix sibling
            r"C:\Program Files Extra\app.exe",                # Prefix sibling with space
            r"C:\Program Files\..\Desktop\app.exe",           # Directory traversal
            r"C:\Users\Public\DynamicFPSLimiter.exe",        # User directory
            r"C:\Games\DynamicFPSLimiter.exe",               # Custom folder
            r"C:\Windows\Temp\app.exe",                       # Temp directory
            r"E:\Portable\app.exe",                           # Portable drive
        ]
        for path in outside_paths:
            mgr = AutoStartManager(app_path=path)
            self.assertFalse(
                mgr.is_in_program_files(),
                f"Expected '{path}' to be detected outside configured Program Files roots",
            )

    @patch.dict(os.environ, {}, clear=True)
    def test_is_in_program_files_missing_env_roots(self):
        # When environment variables are missing/unverifiable, should return False (warn)
        path = r"C:\Program Files\DynamicFPSLimiter\app.exe"
        mgr = AutoStartManager(app_path=path)
        self.assertFalse(
            mgr.is_in_program_files(),
            "Expected False when environment roots are unavailable/unverifiable",
        )

    @patch("subprocess.run")
    @patch.dict(os.environ, MOCK_ENV_ROOTS, clear=True)
    def test_create_warning_emitted_outside_program_files(self, mock_run):
        mock_logger = MagicMock()
        app_path = r"C:\Users\Public\DynamicFPSLimiter.exe"
        mgr = AutoStartManager(app_path=app_path, logger=mock_logger)

        with self.assertLogs("root", level="WARNING") as cm:
            mgr.create()

        # Check warning log emitted in standard logging
        self.assertTrue(any("outside Program Files" in log for log in cm.output))
        # Check logger add_log called
        mock_logger.add_log.assert_called_once()
        self.assertIn("outside Program Files", mock_logger.add_log.call_args[0][0])

        # Verify schtasks invocation was preserved
        mock_run.assert_called_once()
        expected_cmd = [
            "schtasks", "/Create", "/TN", "DynamicFPSLimiter", "/XML", ANY, "/F",
        ]
        self.assertEqual(mock_run.call_args[0][0], expected_cmd)

    @patch("subprocess.run")
    @patch.dict(os.environ, MOCK_ENV_ROOTS, clear=True)
    def test_create_no_warning_inside_program_files(self, mock_run):
        mock_logger = MagicMock()
        app_path = r"C:\Program Files\DynamicFPSLimiter\DynamicFPSLimiter.exe"
        mgr = AutoStartManager(app_path=app_path, logger=mock_logger)

        # Ensure no WARNING logs emitted
        with self.assertNoLogs("root", level="WARNING"):
            mgr.create()

        mock_logger.add_log.assert_not_called()

        # Verify schtasks invocation was preserved
        mock_run.assert_called_once()
        expected_cmd = [
            "schtasks", "/Create", "/TN", "DynamicFPSLimiter", "/XML", ANY, "/F",
        ]
        self.assertEqual(mock_run.call_args[0][0], expected_cmd)

    @patch("subprocess.run")
    @patch.dict(os.environ, MOCK_ENV_ROOTS, clear=True)
    def test_create_raising_logger_nonfatal(self, mock_run):
        # Verify that if logger.add_log raises an exception, schtasks creation is still executed
        raising_logger = MagicMock()
        raising_logger.add_log.side_effect = RuntimeError("Logging pipeline failure")

        app_path = r"C:\Users\Public\DynamicFPSLimiter.exe"
        mgr = AutoStartManager(app_path=app_path, logger=raising_logger)

        # Should not raise exception
        mgr.create()

        # Verify schtasks invocation was still preserved
        mock_run.assert_called_once()
        expected_cmd = [
            "schtasks", "/Create", "/TN", "DynamicFPSLimiter", "/XML", ANY, "/F",
        ]
        self.assertEqual(mock_run.call_args[0][0], expected_cmd)


if __name__ == "__main__":
    unittest.main()
