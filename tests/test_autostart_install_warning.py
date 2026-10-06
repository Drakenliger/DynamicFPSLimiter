import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Add src directory to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from core.autostart import AutoStartManager


class TestAutoStartInstallWarning(unittest.TestCase):

    def test_is_in_program_files_inside(self):
        inside_paths = [
            r"C:\Program Files\DynamicFPSLimiter\DynamicFPSLimiter.exe",
            r"C:\Program Files (x86)\DynamicFPSLimiter\DynamicFPSLimiter.exe",
            r"c:\program files\app.exe",
            r"D:\Program Files\App\app.exe",
            r"Program Files\App\app.exe",
        ]
        for path in inside_paths:
            mgr = AutoStartManager(app_path=path)
            self.assertTrue(
                mgr.is_in_program_files(),
                f"Expected '{path}' to be detected inside Program Files",
            )

    def test_is_in_program_files_outside(self):
        outside_paths = [
            r"C:\Users\Public\DynamicFPSLimiter.exe",
            r"C:\Games\DynamicFPSLimiter.exe",
            r"C:\Program Files Payload\app.exe",
            r"C:\Program Files\..\Desktop\app.exe",
            r"C:\Windows\Temp\app.exe",
            r"E:\Portable\app.exe",
        ]
        for path in outside_paths:
            mgr = AutoStartManager(app_path=path)
            self.assertFalse(
                mgr.is_in_program_files(),
                f"Expected '{path}' to be detected outside Program Files",
            )

    @patch("subprocess.run")
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


if __name__ == "__main__":
    unittest.main()
