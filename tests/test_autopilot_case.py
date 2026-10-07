from core.autopilot import autopilot_on_check


class DummyProfilesConfig:
    def __init__(self, sections):
        self._sections = list(sections)

    def sections(self):
        return list(self._sections)


class DummyConfigManager:
    def __init__(self, sections, autopilot_only_profiles=False):
        self.profiles_config = DummyProfilesConfig(sections)
        self.autopilot_only_profiles = autopilot_only_profiles
        self.loaded_profiles = []

    def load_profile_callback(self, sender, app_data, user_data):
        self.loaded_profiles.append((sender, app_data, user_data))


class DummyRTSSManager:
    def __init__(self, active_process_name, fps=60, rtss_running=True):
        self.active_process_name = active_process_name
        self.fps = fps
        self.rtss_running = rtss_running

    def is_rtss_running(self):
        return self.rtss_running

    def get_fps_for_active_window(self):
        return (self.fps, self.active_process_name)


class DummyDPG:
    def __init__(self):
        self.values = {}

    def set_value(self, item, value):
        self.values[item] = value


class DummyLogger:
    def __init__(self):
        self.logs = []

    def add_log(self, message):
        self.logs.append(message)


class DummyStartStopCallback:
    def __init__(self):
        self.calls = []

    def __call__(self, sender, app_data, user_data):
        self.calls.append((sender, app_data, user_data))


def test_case_insensitive_match_only_profiles_mode():
    cm = DummyConfigManager(["Global", "Game.exe"], autopilot_only_profiles=True)
    rtss = DummyRTSSManager("game.exe")
    dpg = DummyDPG()
    logger = DummyLogger()
    start_stop = DummyStartStopCallback()

    autopilot_on_check(cm, rtss, dpg, logger, running=False, start_stop_callback=start_stop, foreground_reader=lambda: rtss.active_process_name)

    assert dpg.values.get("profile_dropdown") == "Game.exe"
    assert cm.loaded_profiles == [(None, "Game.exe", None)]
    assert len(start_stop.calls) == 1
    assert any("Switched to profile 'Game.exe'" in log for log in logger.logs)


def test_case_insensitive_match_default_mode():
    cm = DummyConfigManager(["Global", "Cyberpunk2077.exe"], autopilot_only_profiles=False)
    rtss = DummyRTSSManager("cyberpunk2077.exe")
    dpg = DummyDPG()
    logger = DummyLogger()
    start_stop = DummyStartStopCallback()

    autopilot_on_check(cm, rtss, dpg, logger, running=False, start_stop_callback=start_stop, foreground_reader=lambda: rtss.active_process_name)

    assert dpg.values.get("profile_dropdown") == "Cyberpunk2077.exe"
    assert cm.loaded_profiles == [(None, "Cyberpunk2077.exe", None)]
    assert len(start_stop.calls) == 1
    assert any("Switched to profile 'Cyberpunk2077.exe'" in log for log in logger.logs)


def test_queued_gui_submit_preserves_original_profile_name():
    cm = DummyConfigManager(["Global", "Game.exe"], autopilot_only_profiles=False)
    rtss = DummyRTSSManager("GAME.EXE")
    dpg = DummyDPG()
    logger = DummyLogger()
    start_stop = DummyStartStopCallback()

    queued_calls = []

    def gui_submit(fn, *args, **kwargs):
        queued_calls.append((fn, args, kwargs))

    autopilot_on_check(
        cm, rtss, dpg, logger, running=False, start_stop_callback=start_stop, gui_submit=gui_submit, foreground_reader=lambda: rtss.active_process_name
    )

    assert len(queued_calls) == 3
    assert queued_calls[0] == (dpg.set_value, ("profile_dropdown", "Game.exe"), {})
    assert queued_calls[1] == (cm.load_profile_callback, (None, "Game.exe", None), {})
    assert queued_calls[2] == (start_stop, (None, None, cm), {})


def test_exact_match_priority_over_case_insensitive_collision_only_profiles_mode():
    cm = DummyConfigManager(["Global", "Game.exe", "game.exe"], autopilot_only_profiles=True)
    rtss = DummyRTSSManager("game.exe")
    dpg = DummyDPG()
    logger = DummyLogger()
    start_stop = DummyStartStopCallback()

    autopilot_on_check(cm, rtss, dpg, logger, running=False, start_stop_callback=start_stop, foreground_reader=lambda: rtss.active_process_name)

    assert dpg.values.get("profile_dropdown") == "game.exe"
    assert cm.loaded_profiles == [(None, "game.exe", None)]
    assert len(start_stop.calls) == 1
    assert any("Switched to profile 'game.exe'" in log for log in logger.logs)


def test_exact_match_priority_over_case_insensitive_collision_default_mode():
    cm = DummyConfigManager(["Global", "Game.exe", "game.exe"], autopilot_only_profiles=False)
    rtss = DummyRTSSManager("game.exe")
    dpg = DummyDPG()
    logger = DummyLogger()
    start_stop = DummyStartStopCallback()

    autopilot_on_check(cm, rtss, dpg, logger, running=False, start_stop_callback=start_stop, foreground_reader=lambda: rtss.active_process_name)

    assert dpg.values.get("profile_dropdown") == "game.exe"
    assert cm.loaded_profiles == [(None, "game.exe", None)]
    assert len(start_stop.calls) == 1
    assert any("Switched to profile 'game.exe'" in log for log in logger.logs)


def test_queued_gui_submit_selects_exact_case_when_later_in_sections():
    cm = DummyConfigManager(["Global", "Game.exe", "game.exe"], autopilot_only_profiles=False)
    rtss = DummyRTSSManager("game.exe")
    dpg = DummyDPG()
    logger = DummyLogger()
    start_stop = DummyStartStopCallback()

    queued_calls = []

    def gui_submit(fn, *args, **kwargs):
        queued_calls.append((fn, args, kwargs))

    autopilot_on_check(
        cm, rtss, dpg, logger, running=False, start_stop_callback=start_stop, gui_submit=gui_submit, foreground_reader=lambda: rtss.active_process_name
    )

    assert len(queued_calls) == 3
    assert queued_calls[0] == (dpg.set_value, ("profile_dropdown", "game.exe"), {})
    assert queued_calls[1] == (cm.load_profile_callback, (None, "game.exe", None), {})
    assert queued_calls[2] == (start_stop, (None, None, cm), {})


def test_unmatched_only_profiles_mode_does_nothing():
    cm = DummyConfigManager(["Global", "Game.exe"], autopilot_only_profiles=True)
    rtss = DummyRTSSManager("unmatched.exe")
    dpg = DummyDPG()
    logger = DummyLogger()
    start_stop = DummyStartStopCallback()

    autopilot_on_check(cm, rtss, dpg, logger, running=False, start_stop_callback=start_stop, foreground_reader=lambda: rtss.active_process_name)

    assert dpg.values == {}
    assert cm.loaded_profiles == []
    assert len(start_stop.calls) == 0


def test_unmatched_default_mode_uses_global():
    cm = DummyConfigManager(["Global", "Game.exe"], autopilot_only_profiles=False)
    rtss = DummyRTSSManager("unmatched.exe")
    dpg = DummyDPG()
    logger = DummyLogger()
    start_stop = DummyStartStopCallback()

    autopilot_on_check(cm, rtss, dpg, logger, running=False, start_stop_callback=start_stop, foreground_reader=lambda: rtss.active_process_name)

    assert dpg.values.get("profile_dropdown") == "Global"
    assert cm.loaded_profiles == [(None, "Global", None)]
    assert len(start_stop.calls) == 1
    assert any("starting with 'Global' profile" in log for log in logger.logs)
