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

        norm = ntpath.normpath(target)
        win_path = pathlib.PureWindowsPath(norm)

        pf_env_paths = []
        for var in ("ProgramFiles", "ProgramFiles(x86)", "ProgramW6432"):
            val = os.environ.get(var)
            if val:
                pf_env_paths.append(pathlib.PureWindowsPath(ntpath.normpath(val)))

        norm_lower = norm.lower()
        for pf in pf_env_paths:
            pf_lower = str(pf).lower()
            if norm_lower.startswith(pf_lower + "\\") or norm_lower == pf_lower:
                return True

        parts = [p.lower() for p in win_path.parts]
        if not parts:
            return False

        if (win_path.is_absolute() or parts[0].endswith("\\") or parts[0].endswith(":")) and len(parts) >= 2:
            top_folder = parts[1]
        else:
            top_folder = parts[0]

        return top_folder in ("program files", "program files (x86)")

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
            logging.warning(msg)
            if self.logger and hasattr(self.logger, "add_log"):
                self.logger.add_log(f"Warning: {msg}")

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





