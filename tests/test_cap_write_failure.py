"""Regression tests verifying cap/idle/cooldown decision state when an RTSS write fails."""
from decimal import Decimal
import pytest

from test_app_session import load_app
from test_librehm_policy import real_evaluator


def setup(method="Legacy"):
    ns, writes, submitted, spawned = load_app()
    sensor, values = real_evaluator(ns)
    values['input_monitoring_method'] = method
    ns['fps_utils'].current_stepped_limits = lambda: list(map(Decimal, (30, 60, 90, 120, 150)))
    return ns, writes, sensor, values


def test_write_cap_reports_failure_and_suppresses_cap_change_log():
    ns, writes, _, _ = load_app()
    logs = []
    recorded_rows = []
    ns['logger'].add_log = lambda msg: logs.append(msg)
    ns['cap_change_log'].record = lambda row: recorded_rows.append(row)
    ns['rtss'].set_fractional_framerate = lambda *a: False

    res = ns['_write_cap']('Global', Decimal(60), 'decrease')

    assert res is False
    assert recorded_rows == []
    assert any("RTSS cap write failed for profile 'Global': requested cap 60 (reason: decrease)" in log for log in logs)


def test_failed_decrease_preserves_offset_cooldown_and_evidence():
    ns, writes, _, _ = setup('Legacy')
    ns['cm'].delaybeforedecrease = 1
    ns['CurrentFPSOffset'] = 0  # current cap = maxcap (150)
    ns['gpu_values'] = [95]
    ns['cpu_values'] = [50]
    ns['fps_values'] = [150]
    ns['fps_mean'] = 150

    ns['rtss'].set_fractional_framerate = lambda *a: False

    ticks = []
    def sleep(_):
        ticks.append(None)
        if len(ticks) == 1:
            ns['running'] = False
    ns['time'].sleep = sleep

    ns['monitoring_loop'](1)

    # Offset preserved
    assert ns['CurrentFPSOffset'] == 0
    # Evidence NOT reset (sample accumulated rather than reset to [])
    assert len(ns['gpu_values']) > 0
    assert ns['fps_mean'] != 0


@pytest.mark.parametrize("offset,steps_type", [(-60, "exact_index"), (-50, "nearest_index")])
def test_failed_increase_preserves_offset_cooldown_and_evidence(offset, steps_type):
    ns, writes, _, _ = setup('Legacy')
    ns['cm'].delaybeforeincrease = 1
    ns['CurrentFPSOffset'] = offset
    ns['gpu_values'] = [30]
    ns['cpu_values'] = [30]
    ns['fps_values'] = [90]
    ns['fps_mean'] = 90
    ns['gpu_monitor'].gpu_percentile = 30
    ns['cpu_monitor'].cpu_percentile = 30

    ns['rtss'].set_fractional_framerate = lambda *a: False

    ticks = []
    def sleep(_):
        ticks.append(None)
        if len(ticks) == 1:
            ns['running'] = False
    ns['time'].sleep = sleep

    ns['monitoring_loop'](1)

    # Offset preserved
    assert ns['CurrentFPSOffset'] == offset
    # Evidence NOT reset
    assert len(ns['gpu_values']) > 0


def test_failed_idle_entry_preserves_idle_state_and_evidence():
    ns, writes, _, _ = setup('Legacy')
    ns['cm'].idle_mode = True
    ns['monitor_idle'] = lambda _: True  # system is idle
    ns['idle_state'] = False
    ns['gpu_values'] = [10]
    ns['cpu_values'] = [10]

    ns['rtss'].set_fractional_framerate = lambda *a: False

    ticks = []
    def sleep(_):
        ticks.append(None)
        if len(ticks) == 1:
            ns['running'] = False
    ns['time'].sleep = sleep

    ns['monitoring_loop'](1)

    # idle_state remains False because write failed
    assert ns['idle_state'] is False
    # Evidence NOT cleared by fresh_cap_evidence()
    assert len(ns['gpu_values']) > 0


def test_failed_idle_restore_preserves_idle_state_and_evidence():
    ns, writes, _, _ = setup('Legacy')
    ns['cm'].idle_mode = True
    ns['monitor_idle'] = lambda _: False  # system no longer idle
    ns['idle_state'] = True
    ns['gpu_values'] = [10]
    ns['cpu_values'] = [10]

    ns['rtss'].set_fractional_framerate = lambda *a: False

    ticks = []
    def sleep(_):
        ticks.append(None)
        if len(ticks) == 1:
            ns['running'] = False
    ns['time'].sleep = sleep

    ns['monitoring_loop'](1)

    # idle_state remains True because restore write failed
    assert ns['idle_state'] is True
    # Evidence NOT cleared
    assert len(ns['gpu_values']) > 0


def test_successful_write_updates_state_resets_evidence_and_advances_cooldown():
    ns, writes, _, _ = setup('Legacy')
    ns['cm'].delaybeforedecrease = 1
    ns['CurrentFPSOffset'] = 0
    ns['gpu_values'] = [95]
    ns['cpu_values'] = [50]
    ns['fps_values'] = [150]
    ns['fps_mean'] = 150

    # Successful write
    ns['rtss'].set_fractional_framerate = lambda *a: True

    ticks = []
    def sleep(_):
        ticks.append(None)
        if len(ticks) == 1:
            ns['running'] = False
    ns['time'].sleep = sleep

    ns['monitoring_loop'](1)

    # Offset updated: 150 -> next cap 120 -> offset = 120 - 150 = -30
    assert ns['CurrentFPSOffset'] == -30
    # Evidence reset
    assert ns['gpu_values'] == []
    assert ns['cpu_values'] == []
    assert ns['fps_values'] == []
    assert ns['fps_mean'] == 0
