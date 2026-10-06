import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Add src directory to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from core.autostart import AutoStartManager

MOCK_ENV_ROOTS = {
    "ProgramFiles": r"C:\Program Files",
    "ProgramFiles(x86)": r"C:\Program Files (x86)",
    "ProgramW6432": r"C:\Program Files",
}


class TestAutoStartInstallWarning(unittest.TestCase):

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
            "schtasks",
            "/Create",
            "/SC", "ONLOGON",
            "/TN", "DynamicFPSLimiter",
            "/TR", f'"{app_path}"',
            "/RL", "HIGHEST",
            "/F",
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
            "schtasks",
            "/Create",
            "/SC", "ONLOGON",
            "/TN", "DynamicFPSLimiter",
            "/TR", f'"{app_path}"',
            "/RL", "HIGHEST",
            "/F",
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
            "schtasks",
            "/Create",
            "/SC", "ONLOGON",
            "/TN", "DynamicFPSLimiter",
            "/TR", f'"{app_path}"',
            "/RL", "HIGHEST",
            "/F",
        ]
        self.assertEqual(mock_run.call_args[0][0], expected_cmd)


if __name__ == "__main__":
    unittest.main()
