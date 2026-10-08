"""F3: tray callbacks are deferred to the main DPG thread via the GuiQueue.

pystray menu actions fire on a background thread where DearPyGui is not safe, so
every action that touches DPG (directly or via the ConfigManager callbacks it
triggers) must be routed through the queue and run on the main thread.
"""
import configparser
import threading

import core.tray_functions as tray_functions
from core.gui_queue import GuiQueue


class _CmStub:
    def __init__(self, profile="Global", method="ratio"):
        self.current_profile = profile
        self.current_method = method
        self.autopilot = False
        self.profiles_config = None


class _FpsUtilsStub:
    """Mimics fps_utils.current_stepped_limits performing a DPG read."""

    def __init__(self, dpg):
        self.dpg = dpg

    def current_stepped_limits(self):
        self.dpg.get_value("input_capmethod")  # simulate the real DPG read
        return [60, 120]


def _make_tray(cm=None, fps_utils=None, queue=None, dpg=None):
    return tray_functions.TrayManager(
        app_name="TestApp",
        icon_path="",
        on_restore=None,
        on_exit=None,
        viewport_width=100,
        config_manager_instance=cm,
        hover_text="TestApp",
        start_stop_callback=None,
        fps_utils=fps_utils,
        gui_queue=queue,
        dpg=dpg,
    )


def test_run_on_main_defers_to_queue(fake_dpg):
    queue = GuiQueue()
    tray = _make_tray(queue=queue, dpg=fake_dpg)
    called = []
    tray._run_on_main(lambda: called.append(1))
    assert called == []
    assert len(queue) == 1
    queue.drain()
    assert called == [1]


def test_run_on_main_inline_without_queue(fake_dpg):
    tray = _make_tray(dpg=fake_dpg)
    assert tray.gui_queue is None
    called = []
    tray._run_on_main(lambda: called.append(1))
    assert called == [1]


def test_update_hover_text_defers_off_main_thread(fake_dpg):
    queue = GuiQueue()
    cm = _CmStub(profile="MyProfile", method="step")
    fps = _FpsUtilsStub(fake_dpg)
    tray = _make_tray(cm=cm, fps_utils=fps, queue=queue, dpg=fake_dpg)
    fake_dpg.calls.clear()

    def _bg():
        tray.update_hover_text()

    t = threading.Thread(target=_bg)
    t.start()
    t.join()

    # No DPG reads on the background thread (deferred to the queue).
    get_value_calls = [c for c in fake_dpg.calls if c[0] == "get_value"]
    assert get_value_calls == []
    assert len(queue) == 1

    queue.drain()

    get_value_calls = [c for c in fake_dpg.calls if c[0] == "get_value"]
    assert len(get_value_calls) >= 1
    assert all(c[3] == threading.main_thread().name for c in get_value_calls)
    # Hover text built from the ConfigManager snapshot.
    assert "Profile: MyProfile" in tray.hover_text
    assert "Method: Step" in tray.hover_text
    assert "Max FPS: 120" in tray.hover_text


def test_update_hover_text_inline_on_main_thread(fake_dpg):
    cm = _CmStub(profile="Global", method="ratio")
    fps = _FpsUtilsStub(fake_dpg)
    tray = _make_tray(cm=cm, fps_utils=fps, queue=GuiQueue(), dpg=fake_dpg)
    fake_dpg.calls.clear()

    tray.update_hover_text()  # called from the main thread

    get_value_calls = [c for c in fake_dpg.calls if c[0] == "get_value"]
    assert len(get_value_calls) >= 1
    assert "Profile: Global" in tray.hover_text
    assert "Method: Ratio" in tray.hover_text


def test_profile_menu_lambda_defers_to_queue(fake_dpg):
    queue = GuiQueue()
    cm = _CmStub()
    callback_calls = []

    def load_profile_callback(sender, app_data, user_data):
        callback_calls.append(
            ((sender, app_data, user_data), threading.current_thread())
        )
        cm.current_profile = app_data
        fake_dpg.set_value("profile_dropdown", app_data)

    cm.load_profile_callback = load_profile_callback
    cfg = configparser.ConfigParser()
    cfg["Global"] = {}
    cfg["GameA"] = {}
    cm.profiles_config = cfg
    tray = _make_tray(cm=cm, queue=queue, dpg=fake_dpg)
    fake_dpg.calls.clear()

    items = tray._profile_menu_items()
    assert [item.text for item in items] == ["Global", "GameA"]

    # Invoke GameA's action as pystray would (from the tray thread).
    def _bg():
        items[1]._action(None, None)

    t = threading.Thread(target=_bg)
    t.start()
    t.join()

    # Both the ConfigManager callback and its DPG update are deferred.
    assert callback_calls == []
    assert fake_dpg.calls == []
    assert len(queue) == 1

    queue.drain()

    assert callback_calls == [((None, "GameA", None), threading.main_thread())]
    assert cm.current_profile == "GameA"
    assert fake_dpg.values["profile_dropdown"] == "GameA"
    assert len(queue) == 0
    set_value_calls = [c for c in fake_dpg.calls if c[0] == "set_value"]
    assert len(set_value_calls) == 1
    assert set_value_calls[0][1][0] == "profile_dropdown"
    assert set_value_calls[0][1][1] == "GameA"
    assert set_value_calls[0][3] == threading.main_thread().name


def test_method_menu_lambda_defers_to_queue(fake_dpg):
    queue = GuiQueue()
    cm = _CmStub()
    tray = _make_tray(cm=cm, queue=queue, dpg=fake_dpg)
    fake_dpg.calls.clear()

    items = list(tray._method_menu_items())
    assert [item.text for item in items] == ["Ratio", "Step", "Custom"]
    step_item = items[1]

    def _bg():
        step_item._action(None, None)

    t = threading.Thread(target=_bg)
    t.start()
    t.join()

    set_value_calls = [c for c in fake_dpg.calls if c[0] == "set_value"]
    assert set_value_calls == []
    assert len(queue) == 1

    queue.drain()

    set_value_calls = [c for c in fake_dpg.calls if c[0] == "set_value"]
    assert len(set_value_calls) == 1
    assert set_value_calls[0][1][0] == "input_capmethod"
    assert set_value_calls[0][1][1] == "Step"


def test_exit_app_defers_to_queue(fake_dpg):
    queue = GuiQueue()
    ran = []
    tray = _make_tray(queue=queue, dpg=fake_dpg)
    tray.on_exit = lambda: ran.append("exit")

    tray._exit_app(None, None)

    # Deferred: on_exit not called on the tray thread.
    assert ran == []
    assert len(queue) == 1

    queue.drain()
    assert ran == ["exit"]


def test_restore_window_defers_to_queue(monkeypatch, fake_dpg):
    queue = GuiQueue()
    ran = []
    tray = _make_tray(queue=queue, dpg=fake_dpg)
    tray.on_restore = lambda: ran.append("restore")
    # Avoid a real Win32 ShowWindow call during the test.
    monkeypatch.setattr(tray_functions, "show_to_taskbar", lambda: None)

    tray._restore_window(None, None)

    assert ran == []
    assert len(queue) == 1
    assert tray.is_tray_active is False

    queue.drain()
    assert ran == ["restore"]


class _FakeFindWindow:
    def __init__(self, user32):
        self.user32 = user32
        self.restype = None

    def __call__(self, class_name, window_name):
        return self.user32.hwnd_to_return


class _FakeUser32:
    def __init__(self, initial_style=0, hwnd_to_return=12345):
        self.hwnd_to_return = hwnd_to_return
        self.style = initial_style
        self.visible = True
        self.sequence_log = []
        self.set_window_long_calls = []
        self.show_window_calls = []
        self.FindWindowW = _FakeFindWindow(self)

    def GetWindowLongW(self, hwnd, n_index):
        return self.style

    def SetWindowLongW(self, hwnd, n_index, new_long):
        self.set_window_long_calls.append((hwnd, n_index, new_long))
        self.sequence_log.append(("set_style", hwnd, new_long, self.visible))
        self.style = new_long
        return 0

    def ShowWindow(self, hwnd, cmd_show):
        self.show_window_calls.append((hwnd, cmd_show))
        if cmd_show == 0:  # SW_HIDE
            self.visible = False
        elif cmd_show == 5:  # SW_SHOW
            self.visible = True
        self.sequence_log.append(("show", hwnd, cmd_show, self.visible))
        return 1


def test_hide_and_show_taskbar_style_transitions_with_topmost(monkeypatch):
    # Literal Windows masks independently defined in tests:
    WS_EX_TOPMOST = 0x08
    WS_EX_TOOLWINDOW = 0x80
    WS_EX_APPWINDOW = 0x40000
    WS_EX_OTHER = 0x01
    SW_HIDE = 0
    SW_SHOW = 5

    # Start with APPWINDOW | TOPMOST | unrelated bit
    initial_style = WS_EX_APPWINDOW | WS_EX_TOPMOST | WS_EX_OTHER  # 0x40000 | 0x08 | 0x01 = 262153
    fake_user32 = _FakeUser32(initial_style=initial_style, hwnd_to_return=12345)

    fake_windll = type("Windll", (), {"user32": fake_user32})()
    monkeypatch.setattr(tray_functions.ctypes, "windll", fake_windll, raising=False)

    # 1. Hide from taskbar
    tray_functions.hide_from_taskbar()

    # APPWINDOW cleared (0x40000 removed), TOOLWINDOW set (0x80 added), TOPMOST (0x08) & OTHER (0x01) preserved:
    # Expected: (0x40009 & ~0x40000) | 0x80 = 0x09 | 0x80 = 0x89 = 137
    expected_hide_style = (initial_style & ~WS_EX_APPWINDOW) | WS_EX_TOOLWINDOW
    assert expected_hide_style == 137
    assert fake_user32.set_window_long_calls == [(12345, -20, 137)]
    assert fake_user32.show_window_calls == [(12345, SW_HIDE)]

    # Assert exact call sequence: SW_HIDE called BEFORE SetWindowLongW
    # At set_style call time, visible must be False (already hidden)
    assert fake_user32.sequence_log == [
        ("show", 12345, SW_HIDE, False),
        ("set_style", 12345, 137, False),
    ]

    fake_user32.set_window_long_calls.clear()
    fake_user32.show_window_calls.clear()
    fake_user32.sequence_log.clear()

    # 2. Show to taskbar
    tray_functions.show_to_taskbar()

    # TOOLWINDOW cleared (0x80 removed), APPWINDOW set (0x40000 added), TOPMOST (0x08) & OTHER (0x01) preserved:
    # Expected: (0x89 & ~0x80) | 0x40000 = 0x09 | 0x40000 = 0x40009 = 262153
    expected_show_style = (137 & ~WS_EX_TOOLWINDOW) | WS_EX_APPWINDOW
    assert expected_show_style == 262153
    assert fake_user32.set_window_long_calls == [(12345, -20, 262153)]
    assert fake_user32.show_window_calls == [(12345, SW_SHOW)]

    # Assert exact call sequence: SetWindowLongW called BEFORE SW_SHOW
    # At set_style call time, visible was False; after show, visible becomes True
    assert fake_user32.sequence_log == [
        ("set_style", 12345, 262153, False),
        ("show", 12345, SW_SHOW, True),
    ]


def test_hide_and_show_taskbar_style_transitions_without_topmost(monkeypatch):
    WS_EX_TOOLWINDOW = 0x80
    WS_EX_APPWINDOW = 0x40000
    WS_EX_OTHER = 0x01
    SW_HIDE = 0
    SW_SHOW = 5

    # Start with APPWINDOW | unrelated bit (NO TOPMOST bit 0x08)
    initial_style = WS_EX_APPWINDOW | WS_EX_OTHER  # 0x40000 | 0x01 = 262145
    fake_user32 = _FakeUser32(initial_style=initial_style, hwnd_to_return=12345)

    fake_windll = type("Windll", (), {"user32": fake_user32})()
    monkeypatch.setattr(tray_functions.ctypes, "windll", fake_windll, raising=False)

    tray_functions.hide_from_taskbar()

    # Expected hide style: (262145 & ~0x40000) | 0x80 = 0x81 = 129
    assert fake_user32.set_window_long_calls == [(12345, -20, 129)]
    assert fake_user32.show_window_calls == [(12345, SW_HIDE)]

    fake_user32.set_window_long_calls.clear()
    fake_user32.show_window_calls.clear()

    tray_functions.show_to_taskbar()

    # Expected show style: (129 & ~0x80) | 0x40000 = 0x40001 = 262145
    # Proves showing does not invent TOPMOST (0x08)
    assert fake_user32.set_window_long_calls == [(12345, -20, 262145)]
    assert fake_user32.show_window_calls == [(12345, SW_SHOW)]


def test_hide_and_show_taskbar_no_hwnd_inert(monkeypatch):
    fake_user32 = _FakeUser32(initial_style=0, hwnd_to_return=0)
    fake_windll = type("Windll", (), {"user32": fake_user32})()
    monkeypatch.setattr(tray_functions.ctypes, "windll", fake_windll, raising=False)

    tray_functions.hide_from_taskbar()
    tray_functions.show_to_taskbar()

    assert fake_user32.set_window_long_calls == []
    assert fake_user32.show_window_calls == []


def test_hide_and_show_taskbar_idempotence(monkeypatch):
    WS_EX_TOPMOST = 0x08
    WS_EX_TOOLWINDOW = 0x80
    WS_EX_APPWINDOW = 0x40000
    WS_EX_OTHER = 0x01

    initial_style = WS_EX_APPWINDOW | WS_EX_TOPMOST | WS_EX_OTHER  # 262153
    fake_user32 = _FakeUser32(initial_style=initial_style, hwnd_to_return=12345)
    fake_windll = type("Windll", (), {"user32": fake_user32})()
    monkeypatch.setattr(tray_functions.ctypes, "windll", fake_windll, raising=False)

    # First hide
    tray_functions.hide_from_taskbar()
    # Duplicate hide
    tray_functions.hide_from_taskbar()

    assert fake_user32.style == 137

    # First show
    tray_functions.show_to_taskbar()
    # Duplicate show
    tray_functions.show_to_taskbar()

    assert fake_user32.style == 262153
