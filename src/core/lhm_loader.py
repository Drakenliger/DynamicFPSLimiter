#Note: Primarily made with AI, check properly in case of error

import os
try:
    import clr
    _clr_import_error = None
except Exception as _exc:
    clr = None
    _clr_import_error = _exc
import subprocess
import re


class LHMLoadError(RuntimeError):
    """Raised when the LibreHardwareMonitor .NET assembly cannot be loaded."""

    def __init__(self, message, dll_path=None):
        super().__init__(message)
        self.dll_path = dll_path


_LOADED = False
_Computer = None
_SensorType = None
_HardwareType = None

# new helpers for runtime detection and dll selection
def _detect_dotnet_framework():
    """Return .NET Framework version string like '4.7.2' or None (Windows only)."""
    try:
        import winreg
    except Exception:
        return None
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full")
        release, _ = winreg.QueryValueEx(key, "Release")
    except Exception:
        return None

    release_map = [
        (528040, "4.8"),
        (461808, "4.7.2"),
        (461308, "4.7.1"),
        (460798, "4.7"),
        (394802, "4.6.2"),
        (394254, "4.6.1"),
        (393295, "4.6"),
        (379893, "4.5.2"),
        (378675, "4.5.1"),
        (378389, "4.5"),
    ]
    for rel_val, ver in release_map:
        if release >= rel_val:
            return ver
    return None


def _detect_dotnet_core():
    """Return highest installed .NET Core / .NET 5+ runtime version string (e.g. '6.0.21') or None."""
    pf = os.environ.get("ProgramFiles", r"C:\Program Files")
    dotnet_dir = os.path.join(pf, "dotnet")

    # Try finding absolute dotnet executable under ProgramFiles
    dotnet_exe = None
    for name in ("dotnet.exe", "dotnet"):
        candidate = os.path.join(dotnet_dir, name)
        if os.path.isfile(candidate):
            dotnet_exe = candidate
            break

    if dotnet_exe:
        try:
            out = subprocess.check_output([dotnet_exe, "--list-runtimes"], stderr=subprocess.DEVNULL, text=True)
            versions = []
            for line in out.splitlines():
                m = re.match(r"^(?:Microsoft\.NETCore\.App|Microsoft\.AspNetCore\.App|Microsoft\.WindowsDesktop\.App)\s+([\d\.]+)", line)
                if m:
                    versions.append(m.group(1))
            if versions:
                # pick highest by tuple comparison
                versions.sort(key=lambda s: tuple(int(p) for p in s.split('.')), reverse=True)
                return versions[0]
        except Exception:
            pass

    # fallback: scan C:\Program Files\dotnet\shared
    shared = os.path.join(dotnet_dir, "shared")
    if os.path.isdir(shared):
        max_ver = None
        for folder in os.listdir(shared):
            folder_path = os.path.join(shared, folder)
            if os.path.isdir(folder_path):
                for v in os.listdir(folder_path):
                    try:
                        # simple validation
                        tuple(map(int, v.split('.')[:3]))
                        if max_ver is None or tuple(map(int, v.split('.'))) > tuple(map(int, max_ver.split('.'))):
                            max_ver = v
                    except Exception:
                        continue
        return max_ver
    return None

def _get_lhm_package_dir(base_dir):
    """Return the path to the LHM package folder inside assets (e.g. assets/LHM_0.9.6_lib or assets)."""
    if not base_dir:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    assets_root = os.path.join(base_dir, "assets") if base_dir else None
    if not assets_root or not os.path.isdir(assets_root):
        return None
    pkg_dir = os.path.join(assets_root, "LHM_0.9.6_lib")
    if os.path.isdir(pkg_dir):
        return pkg_dir
    # check if assets itself contains variant directories directly or a single subfolder
    children = [n for n in os.listdir(assets_root) if os.path.isdir(os.path.join(assets_root, n))]
    if len(children) == 1:
        nested = os.path.join(assets_root, children[0])
        nested_children = [n for n in os.listdir(nested) if os.path.isdir(os.path.join(nested, n))]
        if nested_children:
            return nested
    return assets_root


def _get_active_clr_info():
    """
    Detect active .NET runtime initialized by pythonnet (clr).
    Returns dict like {'is_core': False, 'major': 4, 'version': '4.0.30319.42000'}
    or None if clr is None or active runtime detection fails.
    """
    if clr is None:
        return None

    if hasattr(clr, "_active_runtime_info"):
        info = getattr(clr, "_active_runtime_info")
        if isinstance(info, dict):
            return info

    try:
        import System
        ver = System.Environment.Version
        major = getattr(ver, "Major", 4)
        is_core = major >= 5
        version_str = f"{ver.Major}.{ver.Minor}.{getattr(ver, 'Build', 0)}"
        return {
            "is_core": is_core,
            "major": major,
            "version": version_str,
        }
    except Exception:
        pass

    return None


def _choose_asset_variant(base_dir):
    """
    Pick best asset variant folder name (e.g. 'net472', 'net8.0', 'netstandard2.0').
    Returns folder name (string) or None.
    """
    pkg_dir = _get_lhm_package_dir(base_dir)
    available = set()
    if pkg_dir and os.path.isdir(pkg_dir):
        available = set(n for n in os.listdir(pkg_dir) if os.path.isdir(os.path.join(pkg_dir, n)))

    clr_info = _get_active_clr_info()

    if clr_info is not None:
        if clr_info.get("is_core"):
            major = clr_info.get("major")
            ver_str = clr_info.get("version", "")
            candidates = []
            if major:
                candidates.append(f"net{major}.0")
                candidates.append(f"net{major}")
            if ver_str:
                candidates.append(f"net{ver_str}")
            candidates.append("netstandard2.0")
            for c in candidates:
                if c in available:
                    return c
        else:
            if "net472" in available:
                return "net472"
            if "net48" in available:
                return "net48"
            if "netstandard2.0" in available:
                return "netstandard2.0"
            for a in sorted(available):
                if "472" in a or "48" in a:
                    return a

    # fallback if clr_info is None:
    core_ver = _detect_dotnet_core()
    if core_ver:
        major = core_ver.split('.')[0]
        candidates = [f"net{major}.0", f"net{core_ver}", "netstandard2.0"]
        for c in candidates:
            if c in available:
                return c

    # fallback to .NET Framework detection
    fx = _detect_dotnet_framework()
    if fx:
        variant = "net" + fx.replace('.', '')
        if variant in available:
            return variant
        if "net48" in available:
            return "net48"
        if "net472" in available:
            return "net472"

    if "netstandard2.0" in available:
        return "netstandard2.0"
    if "net472" in available:
        return "net472"
    for a in sorted(available, reverse=True):
        if a.startswith("net"):
            return a
    return None


def ensure_loaded(base_dir=None, logger=None):
    """
    Ensure the LibreHardwareMonitor assembly is loaded and return (Computer, SensorType, HardwareType).
    Call with base_dir from the main module (Base_dir) when available.
    """
    global _LOADED, _Computer, _SensorType, _HardwareType
    if _LOADED:
        return _Computer, _SensorType, _HardwareType

    # choose appropriate dll variant under assets
    if base_dir is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # project root guess

    variant = _choose_asset_variant(base_dir)
    msg = f"Loading LibreHardwareMonitorLib.dll variant: {variant or 'default'}"

    if logger is not None and hasattr(logger, "add_log"):
        try:
            logger.add_log(msg)
        except Exception:
            # swallow logger errors to avoid breaking loading
            pass

    pkg_dir = _get_lhm_package_dir(base_dir)
    if not pkg_dir:
        pkg_dir = os.path.join(base_dir, 'assets', 'LHM_0.9.6_lib')
    if variant:
        dll_path = os.path.join(pkg_dir, variant, 'LibreHardwareMonitorLib.dll')
        if not os.path.isfile(dll_path):
            dll_path = os.path.join(pkg_dir, 'net472', 'LibreHardwareMonitorLib.dll')  # fallback
    else:
        dll_path = os.path.join(pkg_dir, 'net472', 'LibreHardwareMonitorLib.dll')

    if clr is None:
        if isinstance(_clr_import_error, (ImportError, ModuleNotFoundError)):
            msg = f"pythonnet (clr) module is not installed, cannot load {dll_path}"
        else:
            msg = f"pythonnet (clr) import failed: {_clr_import_error}"
        raise LHMLoadError(
            msg,
            dll_path=str(dll_path),
        ) from _clr_import_error

    try:
        clr.AddReference(str(dll_path))
    except Exception as exc:
        raise LHMLoadError(
            f"clr.AddReference failed for {dll_path}: {exc}",
            dll_path=str(dll_path),
        ) from exc

    try:
        from LibreHardwareMonitor.Hardware import Computer, SensorType, HardwareType
    except Exception as exc:
        raise LHMLoadError(
            f"import LibreHardwareMonitor.Hardware failed after loading {dll_path}: {exc}",
            dll_path=str(dll_path),
        ) from exc

    _Computer, _SensorType, _HardwareType = Computer, SensorType, HardwareType
    _LOADED = True
    return _Computer, _SensorType, _HardwareType

def get_types(base_dir=None):
    return ensure_loaded(base_dir)