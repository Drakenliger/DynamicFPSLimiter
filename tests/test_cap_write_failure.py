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


def logical_passes(ns, count):
    """Advance an isolated clock and capture state after each actual loop pass."""
    states = []
    ns['time'].time = lambda: 100 + len(states)

    def sleep(seconds):
        assert seconds == 1
        states.append((ns['CurrentFPSOffset'], ns['idle_state'],
                       list(ns['gpu_values']), list(ns['cpu_values']),
                       list(ns['fps_values']), ns['fps_mean']))
        if len(states) == count:
            ns['running'] = False

    ns['time'].sleep = sleep
    return states


@pytest.mark.parametrize('offset', [-60, -50], ids=['exact_index', 'nearest_index'])
def test_failed_increases_retry_next_pass_without_cooldown(offset):
    ns, _, _, _ = setup('Legacy')
    ns['cm'].delaybeforeincrease = 3
    ns['CurrentFPSOffset'] = offset
    ns['gpu_values'] = [30] * 3
    ns['cpu_values'] = [30] * 3
    ns['gpu_monitor'].gpu_percentile = 30
    ns['cpu_monitor'].cpu_percentile = 30
    states = logical_passes(ns, 4)
    attempts = []
    ns['rtss'].get_framerate_limit = lambda *a, **kw: 150 + offset

    def write(profile, cap):
        attempts.append((ns['time'].time(), profile, cap))
        return len(attempts) == 4

    ns['rtss'].set_fractional_framerate = write
    ns['monitoring_loop'](1)

    assert attempts == [(100 + i, 'Global', Decimal(120)) for i in range(4)]
    assert [state[0] for state in states] == [offset, offset, offset, -30]
    for state in states[:3]:
        assert state[2] and all(v == 30 for v in state[2])
        assert state[3] and all(v == 30 for v in state[3])
        assert state[4] and state[5] == 95
    assert states[3][2:] == ([], [], [], 0)


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


def test_failed_idle_restore_preserves_remembered_active_cap_and_evidence():
    ns, _, _, _ = setup('Legacy')
    ns['cm'].idle_mode = True
    ns['CurrentFPSOffset'] = -60  # Active cap 90 differs from idle and maximum.
    states = logical_passes(ns, 3)
    ns['monitor_idle'] = lambda _: not states
    ns['gpu_monitor'].gpu_percentile = 30
    ns['cpu_monitor'].cpu_percentile = 30
    ns['rtss'].get_framerate_limit = lambda *a, **kw: 90
    attempts = []

    def write(profile, cap):
        assert isinstance(cap, (int, Decimal))
        attempts.append((ns['time'].time(), profile, cap))
        return len(attempts) == 1  # Idle entry succeeds; activity restores fail.

    ns['rtss'].set_fractional_framerate = write
    ns['monitoring_loop'](1)

    assert attempts == [(100, 'Global', 20), (101, 'Global', Decimal(90)),
                        (102, 'Global', Decimal(90))]
    assert states[0] == (-60, True, [], [], [], 0)
    assert states[1] == (-60, True, [30], [30], [Decimal(95)], Decimal(95))
    assert states[2] == (-60, True, [30, 30], [30, 30],
                         [Decimal(95), Decimal(95)], Decimal(95))


@pytest.mark.parametrize('offset,first_cap', [(-90, 90), (-100, 60)],
                         ids=['exact_index', 'nearest_index'])
def test_successful_increases_delay_next_eligible_increase(offset, first_cap):
    ns, _, _, _ = setup('Legacy')
    ns['cm'].delaybeforeincrease = 3
    ns['CurrentFPSOffset'] = offset
    ns['gpu_monitor'].gpu_percentile = 30
    ns['cpu_monitor'].cpu_percentile = 30
    # Keep every pass eligible to isolate cooldown from evidence-window delays.
    ns['fps_utils'].evaluate_cap_change = lambda *_: (False, True)
    ns['rtss'].get_framerate_limit = lambda *a, **kw: 150 + ns['CurrentFPSOffset']
    states = logical_passes(ns, 4)
    attempts = []

    def write(profile, cap):
        attempts.append((ns['time'].time(), profile, cap))
        return True

    ns['rtss'].set_fractional_framerate = write
    ns['monitoring_loop'](1)

    assert attempts == [(100, 'Global', Decimal(first_cap)),
                        (103, 'Global', Decimal(first_cap + 30))]
    assert [state[0] for state in states] == [first_cap - 150] * 3 + [first_cap - 120]
    assert states[0][2:] == states[3][2:] == ([], [], [], 0)
    assert states[1][2:] == ([30], [30], [Decimal(95)], Decimal(95))
    assert states[2][2:] == ([30, 30], [30, 30], [Decimal(95), Decimal(95)], Decimal(95))


def test_profile_rollback_reports_each_failed_write_once_and_transition_reason():
    ns, _, _, _ = setup()
    ns['CurrentFPSOffset'] = -60
    ns['rtss'].get_framerate_limit = lambda *a, **kw: 90
    ns['cm'].load_profile_raw = lambda name, **kw: True
    attempts, logs = [], []
    ns['logger'].add_log = logs.append

    def write(profile, cap):
        attempts.append((profile, cap))
        assert ns['session_lock'].locked()
        return len(attempts) == 1

    ns['rtss'].set_fractional_framerate = write

    assert ns['_load_profile_on_gui']('gameA') is False
    assert attempts == [('Global', Decimal(150)), ('gameA', Decimal(150)),
                        ('Global', Decimal(90))]
    assert logs == [
        "RTSS cap write failed for profile 'gameA': requested cap 150 (reason: profile_start)",
        "RTSS cap write failed for profile 'Global': requested cap 90 (reason: profile_rollback)",
        "Profile transition to gameA failed: incoming cap write failed",
    ]
    assert ns['cm'].current_profile == 'Global'
    assert ns['profile_revision'] == 0
    assert ns['CurrentFPSOffset'] == -60
