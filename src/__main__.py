import sys
import os
import argparse
import subprocess

def _get_error_log_file():
    acc = globals().get("_acceptance_runtime")
    if acc is not None and hasattr(acc, "error_log_file"):
        return acc.error_log_file
    is_frozen = getattr(sys, 'frozen', False)
    if is_frozen:
        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        parent_dir = os.path.dirname(base_dir)
        return os.path.join(parent_dir, "error_log.txt")
    else:
        src_dir = os.path.abspath(os.path.dirname(__file__))
        return os.path.join(src_dir, "error_log.txt")

def _init_early_main_logging():
    src_dir = os.path.abspath(os.path.dirname(__file__))
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)
    parent_dir = os.path.dirname(src_dir)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    log_path = _get_error_log_file()
    from core import logger
    logger.init_logging(log_path)

def is_admin():
    """Check if the script is running with administrator privileges."""
    try:
        import ctypes
        windll = getattr(ctypes, "windll", None)
        if windll is not None:
            return bool(windll.shell32.IsUserAnAdmin())
        return False
    except Exception:
        return False

def relaunch_as_admin():
    """Relaunch the script with administrator privileges."""
    is_frozen = getattr(sys, 'frozen', False)
    if is_frozen:
        executable = sys.executable
        cmd_args = sys.argv[1:]
    else:
        cmd_args = [os.path.abspath(__file__)] + sys.argv[1:]
        if '--debug' in sys.argv[1:]:
            executable = sys.executable
        else:
            exe_dir = os.path.dirname(sys.executable)
            sibling_pythonw = os.path.join(exe_dir, "pythonw.exe")
            if os.path.isfile(sibling_pythonw):
                executable = sibling_pythonw
            else:
                executable = sys.executable

    params = subprocess.list2cmdline(cmd_args)
    import ctypes
    windll = getattr(ctypes, "windll", None)
    if windll is not None:
        ret = windll.shell32.ShellExecuteW(
            None, "runas", executable, params, None, 1
        )
        if isinstance(ret, int) and ret <= 32:
            raise OSError(f"ShellExecuteW elevation failed with error code {ret}")
    sys.exit(0)

def run_app():
    try:
        import ctypes
        windll = getattr(ctypes, "windll", None)
        if windll is not None:
            windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass

    # Import and run the app directly
    import core.app

def build_executable():
    import PyInstaller.__main__ as pyi_main
    from core.version import write_version_txt

    # Regenerate the PyInstaller version resource from the single source
    # (src/core/version.py) so the exe metadata can never drift.
    write_version_txt(os.path.join(os.path.dirname(__file__), 'metadata', 'version.txt'))

    assets_dir = os.path.join(os.path.dirname(__file__), 'core', 'assets')
    add_data_args = []

    for root, _, files in os.walk(assets_dir):
        for fname in files:
            src_path = os.path.join(root, fname)
            rel_dir = os.path.relpath(root, assets_dir)
            if rel_dir == '.' or rel_dir == os.curdir:
                dest = 'assets'
            else:
                dest = os.path.join('assets', rel_dir)
            # Use os.pathsep so this works on Windows (PyInstaller expects ';' on Windows)
            add_data_args.extend(['--add-data', f'{src_path}{os.pathsep}{dest}'])

    base_args = [
        'src/core/app.py',
        '--onedir',
        '--uac-admin',
        '--clean',
        '--noconfirm',
        '--noconsole',
        '--name', 'DynamicFPSLimiter',
        '--icon', 'src/core/assets/DynamicFPSLimiter.ico',
        '--version-file', 'src/metadata/version.txt',
        '--distpath', 'output/dist',
        '--workpath', 'output/build',
    ]

    pyi_main.run(base_args + add_data_args)

parser = argparse.ArgumentParser(description='Dynamic FPS Limiter')
parser.add_argument('--build', action='store_true', help='Build executable')
parser.add_argument('--debug', action='store_true', help='Retain console for debugging')

if __name__ == '__main__':
    _init_early_main_logging()
    args, unknown = parser.parse_known_args()

    if args.build:
        print("Building executable...")
        build_executable()
    else:
        if not is_admin():
            relaunch_as_admin()
        run_app()
