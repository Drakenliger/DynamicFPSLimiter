import os
import sys
import subprocess
import logging
import ntpath
import pathlib

TASK_NAME = "DynamicFPSLimiter"

class AutoStartManager:
    def __init__(self, app_path=None, task_name=TASK_NAME, logger=None):
        self.app_path = app_path or self.get_current_app_path()
        self.task_name = task_name
        self.logger = logger

    @staticmethod
    def get_current_app_path():
        return os.path.abspath(sys.argv[0])

    def is_in_program_files(self, path=None):
        target = path or self.app_path
        if not target:
            return False

        if not ntpath.isabs(target):
            return False

        drive, _ = ntpath.splitdrive(target)
        if not drive or drive.startswith("\\\\") or drive.startswith("//"):
            return False

        norm_target = ntpath.normpath(target)
        pure_target = pathlib.PureWindowsPath(norm_target.lower())

        roots = []
        for var in ("ProgramFiles", "ProgramFiles(x86)", "ProgramW6432"):
            val = os.environ.get(var)
            if val and ntpath.isabs(val):
                r_drive, _ = ntpath.splitdrive(val)
                if r_drive and not r_drive.startswith("\\\\") and not r_drive.startswith("//"):
                    norm_root = ntpath.normpath(val)
                    roots.append(pathlib.PureWindowsPath(norm_root.lower()))

        if not roots:
            return False

        for root in roots:
            try:
                pure_target.relative_to(root)
                return True
            except ValueError:
                continue

        return False

    def task_exists(self):
        result = subprocess.run(["schtasks", "/Query", "/TN", self.task_name],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return result.returncode == 0

    def create(self):
        if not self.is_in_program_files():
            msg = (
                f"Autostart executable path '{self.app_path}' is outside Program Files. "
                "It is recommended to install under Program Files before enabling autostart."
            )
            try:
                logging.warning(msg)
            except Exception:
                pass
            try:
                if self.logger and hasattr(self.logger, "add_log"):
                    self.logger.add_log(f"Warning: {msg}")
            except Exception:
                pass

        cmd = [
            "schtasks",
            "/Create",
            "/SC", "ONLOGON",
            "/TN", self.task_name,
            "/TR", f'"{self.app_path}"',
            "/RL", "HIGHEST",
            "/F"
        ]
        subprocess.run(cmd)

    def delete(self):
        if self.task_exists():
            subprocess.run(["schtasks", "/Delete", "/TN", self.task_name, "/F"])

    def update_if_needed(self, startup_checkbox):
        if startup_checkbox:
            if self.task_exists():
                result = subprocess.run(["schtasks", "/Query", "/TN", self.task_name, "/XML"],
                                        stdout=subprocess.PIPE, text=True)
                if self.app_path.lower() not in result.stdout.lower():
                    self.delete()
                    self.create()
            else:
                self.create()
        else:
            if self.task_exists():
                self.delete()




