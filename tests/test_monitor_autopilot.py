"""Tests for monitoring_loop autopilot behavior."""
from types import SimpleNamespace
from decimal import Decimal
import pytest

from tests.test_app_session import load_app


def test_global_to_detected_profile_switch():
    """Verify Global switches to detected profile when process_name is in profiles."""
    ns, writes, submitted, spawned = load_app()
    ns['cm'].autopilot = True
    ns['cm'].autopilot_only_profiles = False
    ns['cm'].current_profile = "Global"
    ns['cm'].profiles_config = SimpleNamespace(sections=lambda: ["GameA.exe", "GameB.exe"])

    ns['get_foreground_process_name'] = lambda: "GameA.exe"
    ns['rtss_manager'].get_fps_for_active_window = lambda: (Decimal(60), "GameA.exe")

    def stop_after_one_tick(_):
        ns['running'] = False

    ns['time'].sleep = stop_after_one_tick

    ns['monitoring_loop'](1)

    # Check submitted GUI actions
    profile_load_calls = [s for s in submitted if s[0] == ns['_load_profile_on_gui']]
    assert len(profile_load_calls) >= 1
    assert profile_load_calls[0] == (ns['_load_profile_on_gui'], "GameA.exe")


def test_no_profile_fallback_global():
    """Verify fallback to Global when selected profile process is no longer active."""
    ns, writes, submitted, spawned = load_app()
    ns['cm'].autopilot = True
    ns['cm'].autopilot_only_profiles = False
    ns['cm'].current_profile = "GameA.exe"
    ns['cm'].profiles_config = SimpleNamespace(sections=lambda: ["GameA.exe"])

    ns['get_foreground_process_name'] = lambda: "Desktop.exe"
    ns['rtss_manager'].get_fps_for_active_window = lambda: (Decimal(60), "Desktop.exe")

    def stop_after_one_tick(_):
        ns['running'] = False

    ns['time'].sleep = stop_after_one_tick

    ns['monitoring_loop'](1)

    profile_load_calls = [s for s in submitted if s[0] == ns['_load_profile_on_gui']]
    assert len(profile_load_calls) >= 1
    assert profile_load_calls[0] == (ns['_load_profile_on_gui'], "Global")


def test_only_profiles_stop():
    """Verify monitoring stops when selected profile process is no longer active and autopilot_only_profiles is True."""
    ns, writes, submitted, spawned = load_app()
    ns['cm'].autopilot = True
    ns['cm'].autopilot_only_profiles = True
    ns['cm'].current_profile = "GameA.exe"
    ns['cm'].profiles_config = SimpleNamespace(sections=lambda: ["GameA.exe"])

    ns['get_foreground_process_name'] = lambda: "Desktop.exe"
    ns['rtss_manager'].get_fps_for_active_window = lambda: (Decimal(60), "Desktop.exe")

    def stop_after_one_tick(_):
        ns['running'] = False

    ns['time'].sleep = stop_after_one_tick

    ns['monitoring_loop'](1)

    stop_calls = [s for s in submitted if s[0] == ns['start_stop_callback']]
    assert len(stop_calls) >= 1
    assert stop_calls[0] == (ns['start_stop_callback'], None, None, ns['cm'])


def test_autopilot_disabled_no_action():
    """Verify no autopilot actions occur when cm.autopilot is False."""
    ns, writes, submitted, spawned = load_app()
    ns['cm'].autopilot = False
    ns['cm'].current_profile = "GameA.exe"
    ns['cm'].profiles_config = SimpleNamespace(sections=lambda: ["GameA.exe"])

    ns['get_foreground_process_name'] = lambda: "Desktop.exe"
    ns['rtss_manager'].get_fps_for_active_window = lambda: (Decimal(60), "Desktop.exe")

    def stop_after_one_tick(_):
        ns['running'] = False

    ns['time'].sleep = stop_after_one_tick

    ns['monitoring_loop'](1)

    autopilot_calls = [s for s in submitted if s[0] in (ns['_load_profile_on_gui'], ns['start_stop_callback'])]
    assert len(autopilot_calls) == 0
