"""Tests for monitoring_loop autopilot behavior and exact sequence assertions."""
from types import SimpleNamespace
from decimal import Decimal
import pytest

from tests.test_app_session import load_app


def get_autopilot_actions(ns, submitted):
    """Filter submitted actions to only autopilot lifecycle and profile switch calls."""
    return [s for s in submitted if s[0] in (ns['_load_profile_on_gui'], ns['start_stop_callback'])]


def test_global_to_detected_profile_switch():
    """Verify Global switches to detected profile and submits exactly one action with no extras/contradictions/duplicates."""
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

    expected_action = (ns['_load_profile_on_gui'], "GameA.exe", 1, 0)
    actions = get_autopilot_actions(ns, submitted)

    # Assert exact single action sequence
    assert actions == [expected_action]

    # Demonstrate in-memory mutations (contradictory opposite action or duplicate) fail exact assertion
    opposite_action = (ns['start_stop_callback'], None, None, ns['cm'])
    with pytest.raises(AssertionError):
        assert actions + [opposite_action] == [expected_action]

    with pytest.raises(AssertionError):
        assert actions + [expected_action] == [expected_action]


def test_no_profile_fallback_global():
    """Verify fallback to Global when selected profile process is no longer active and submits exactly one action."""
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

    expected_action = (ns['_load_profile_on_gui'], "Global", 1, 0)
    actions = get_autopilot_actions(ns, submitted)

    # Assert exact single action sequence
    assert actions == [expected_action]

    # Demonstrate in-memory mutations (contradictory opposite action or duplicate) fail exact assertion
    opposite_action = (ns['start_stop_callback'], None, None, ns['cm'])
    with pytest.raises(AssertionError):
        assert actions + [opposite_action] == [expected_action]

    with pytest.raises(AssertionError):
        assert actions + [expected_action] == [expected_action]


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

    expected_action = (ns['start_stop_callback'], None, None, ns['cm'])
    actions = get_autopilot_actions(ns, submitted)

    # Assert exact single action sequence
    assert actions == [expected_action]

    # Demonstrate in-memory mutations (contradictory opposite action or duplicate) fail exact assertion
    opposite_action = (ns['_load_profile_on_gui'], "Global", 1, 0)
    with pytest.raises(AssertionError):
        assert actions + [opposite_action] == [expected_action]

    with pytest.raises(AssertionError):
        assert actions + [expected_action] == [expected_action]


def test_autopilot_disabled_no_action():
    """Verify no autopilot actions occur when cm.autopilot is False (exact empty sequence)."""
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

    actions = get_autopilot_actions(ns, submitted)
    assert actions == []

    # Demonstrate in-memory mutation fails exact empty assertion
    with pytest.raises(AssertionError):
        assert actions + [(ns['_load_profile_on_gui'], "Global", 1, 0)] == []
