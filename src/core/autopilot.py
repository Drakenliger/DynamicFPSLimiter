import ctypes
import ntpath

# Fixed-width Windows types, independent of the host's C long width.
DWORD = ctypes.c_uint32
BOOL = ctypes.c_int
HANDLE = ctypes.c_void_p


def get_foreground_process_name(user32=None, kernel32=None):
    """Read the foreground executable with limited query rights; failure is unknown."""
    handle = None
    try:
        if user32 is None:
            user32 = ctypes.windll.user32
        if kernel32 is None:
            kernel32 = ctypes.windll.kernel32
        user32.GetForegroundWindow.argtypes = []
        user32.GetForegroundWindow.restype = HANDLE
        user32.GetWindowThreadProcessId.argtypes = [HANDLE, ctypes.POINTER(DWORD)]
        user32.GetWindowThreadProcessId.restype = DWORD
        kernel32.OpenProcess.argtypes = [DWORD, BOOL, DWORD]
        kernel32.OpenProcess.restype = HANDLE
        kernel32.QueryFullProcessImageNameW.argtypes = [HANDLE, DWORD, ctypes.POINTER(ctypes.c_wchar), ctypes.POINTER(DWORD)]
        kernel32.QueryFullProcessImageNameW.restype = BOOL
        kernel32.CloseHandle.argtypes = [HANDLE]
        kernel32.CloseHandle.restype = BOOL
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return None
        pid = DWORD()
        if not user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid)) or not pid.value:
            return None
        handle = kernel32.OpenProcess(0x1000, False, pid.value)
        if not handle:
            return None
        path = ctypes.create_unicode_buffer(32768)
        size = DWORD(len(path))
        if not kernel32.QueryFullProcessImageNameW(handle, 0, path, ctypes.byref(size)):
            return None
        if not 0 < size.value < len(path):
            return None
        return ntpath.basename(path[:size.value]) or None
    except Exception:
        return None
    finally:
        if handle:
            kernel32.CloseHandle(handle)


def canonical_profile(name, sections):
    """Preserve stored spelling and exact-match priority."""
    if not name:
        return None
    if name in sections:
        return name
    return next((p for p in sections if p.lower() == name.lower()), None)


def autopilot_decision(foreground, sections, current, running, only_profiles):
    """Return at most one (action, target); unknown identity never acts."""
    if not foreground:
        return None
    matched = canonical_profile(foreground, sections)
    current = canonical_profile(current, sections)
    if not running:
        target = matched or (None if only_profiles else canonical_profile('Global', sections))
        return ('start', target) if target else None
    if current and current.lower() == 'global':
        return ('select', matched) if matched and matched != current else None
    if matched == current:
        return None
    if only_profiles:
        return ('stop', current) if current else None
    target = canonical_profile('Global', sections)
    return ('select', target) if target else None


def autopilot_request_current(expected, session, revision, running, cm):
    """Execution admission; caller holds the app session lock."""
    old_session, old_revision, old_running, only_profiles, target = expected
    return (session == old_session and revision == old_revision
            and running == old_running and cm.autopilot
            and cm.autopilot_only_profiles == only_profiles
            and target in cm.profiles_config.sections())


def autopilot_on_check(cm, rtss_manager, dpg, logger, running, start_stop_callback, gui_submit=None, foreground_reader=None):
    """
    Checks if the active process matches a profile and switches profile/running state if needed.
    Behavior depends on cm.autopilot_only_profiles:
      - If True: only start/stop when a specific profile is detected (legacy behavior).
      - If False: when a specific profile is detected, switch to it; otherwise start/continue with the Global profile.

    ``gui_submit`` (e.g. app's GuiQueue ``submit``) defers every dpg.* call and the
    start/stop callback to the main render thread, where DearPyGui is safe to call.
    If it is ``None`` (tests / legacy callers) the calls run directly.
    """
    if not (cm and rtss_manager and rtss_manager.is_rtss_running()):
        return

    def _gui(fn, *args, **kwargs):
        if gui_submit is not None:
            gui_submit(fn, *args, **kwargs)
        else:
            fn(*args, **kwargs)

    def _select_profile(profile):
        # The app hook owns membership validation and the dropdown publication.
        # Legacy standalone callers keep their existing UI selection behavior.
        if getattr(cm, "profile_transition_hook", None) is None:
            _gui(dpg.set_value, "profile_dropdown", profile)
        _gui(cm.load_profile_callback, None, profile, None)

    process_name = (foreground_reader or get_foreground_process_name)()
    if not process_name:
        return

    profiles = cm.profiles_config.sections() if hasattr(cm, "profiles_config") else []
    
    logger.add_log(f"Autopilot detected active process: {process_name}")

    matched_profile = canonical_profile(process_name, profiles)

    if cm.autopilot_only_profiles:
        # Legacy behavior: only act when a specific profile matches the active process
        if matched_profile:
            _select_profile(matched_profile)
            if not running:
                logger.add_log(f"AutoPilot: Switched to profile '{matched_profile}' and started monitoring.")
                _gui(start_stop_callback, None, None, cm)
    else:
        # New default: start with detected specific profile if present; otherwise start with Global
        if matched_profile:
            _select_profile(matched_profile)
            if not running:
                logger.add_log(f"AutoPilot: Switched to profile '{matched_profile}' and started monitoring.")
                _gui(start_stop_callback, None, None, cm)
        else:
            # No specific profile for the active process -> start with Global when not running
            if not running:
                _select_profile("Global")
                logger.add_log("AutoPilot: No specific profile detected; starting with 'Global' profile.")
                _gui(start_stop_callback, None, None, cm)