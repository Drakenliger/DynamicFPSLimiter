"""Tests for resetting Legacy CPU samples and percentile at DFL Stop."""

import threading
import time
from unittest.mock import MagicMock, patch
import pytest

from core.cpu_monitor import CPUUsageMonitor


class StubLogger:
    def add_log(self, msg):
        pass


class StubDPG:
    pass


def test_cpu_monitor_reset_directly():
    """Direct CPUUsageMonitor.reset() clears samples and sets cpu_percentile to 0."""
    running_state = [False]
    monitor = CPUUsageMonitor(
        get_running=lambda: running_state[0],
        logger_instance=StubLogger(),
        dpg_instance=StubDPG(),
        interval=0.05,
    )
    try:
        with monitor._lock:
            monitor.samples = [85.0, 90.0, 95.0]
            monitor.cpu_percentile = 90

        assert monitor.samples == [85.0, 90.0, 95.0]
        assert monitor.cpu_percentile == 90

        monitor.reset()

        assert monitor.samples == []
        assert monitor.cpu_percentile == 0
    finally:
        monitor.stop()


def test_cpu_monitor_repeated_stop_reset():
    """Repeated reset calls are idempotent and keep monitor state clean."""
    running = False
    monitor = CPUUsageMonitor(
        get_running=lambda: running,
        logger_instance=StubLogger(),
        dpg_instance=StubDPG(),
        interval=0.05,
    )
    try:
        for _ in range(3):
            monitor.reset()
            assert monitor.samples == []
            assert monitor.cpu_percentile == 0
    finally:
        monitor.stop()


def test_app_stop_hook_clears_cpu_monitor():
    """Actual app start_stop_callback hook clears cpu_monitor samples and percentile at Stop."""
    from test_start_stop_write_admission import load_app_custom

    ns, writes, _, _ = load_app_custom()

    # Pass callback connected directly to app running state
    cpu_mon = CPUUsageMonitor(
        get_running=lambda: ns["running"],
        logger_instance=StubLogger(),
        dpg_instance=StubDPG(),
        interval=0.05,
    )

    try:
        # Populate pre-stop samples in cpu_monitor
        with cpu_mon._lock:
            cpu_mon.samples = [95.0, 98.0, 100.0]
            cpu_mon.cpu_percentile = 98

        # Inject cpu_mon into app namespace
        ns["cpu_monitor"] = cpu_mon
        ns["running"] = True  # currently running

        # Execute Stop via start_stop_callback
        ns["start_stop_callback"](None, None, ns["cm"])

        # Verify DFL is stopped
        assert ns["running"] is False

        # Assert monitor samples and percentile were synchronously reset
        assert cpu_mon.samples == []
        assert cpu_mon.cpu_percentile == 0

        # Assert that prior high percentile (98) is no longer present in cpu_values
        assert ns["cpu_values"] == []

        # Restart session
        ns["start_stop_callback"](None, None, ns["cm"])
        assert ns["running"] is True

        # Initial post-restart Legacy decisions see 0, not 98
        assert cpu_mon.cpu_percentile == 0
    finally:
        ns["running"] = False
        cpu_mon.stop()


def test_app_stop_hook_no_monitor_present():
    """start_stop_callback handles DFL Stop gracefully when cpu_monitor is None."""
    from test_start_stop_write_admission import load_app_custom

    ns, writes, _, _ = load_app_custom()

    ns["cpu_monitor"] = None
    ns["running"] = True

    # Should not raise any AttributeError / TypeError
    ns["start_stop_callback"](None, None, ns["cm"])
    assert ns["running"] is False


def test_fresh_post_start_samples():
    """After Stop and restart, new samples collected update samples and cpu_percentile afresh."""
    running_state = [True]
    pass_event = threading.Event()

    def mock_cpu_percent(percpu=True):
        res = [50.0, 60.0] if running_state[0] else [10.0, 10.0]
        pass_event.set()
        return res

    with patch("psutil.cpu_percent", side_effect=mock_cpu_percent):
        monitor = CPUUsageMonitor(
            get_running=lambda: running_state[0],
            logger_instance=StubLogger(),
            dpg_instance=StubDPG(),
            interval=0.01,
        )
        try:
            assert pass_event.wait(timeout=5)
            pass_event.clear()

            with monitor._lock:
                assert len(monitor.samples) > 0
                assert monitor.cpu_percentile == 60

            # Stop
            running_state[0] = False
            monitor.reset()

            assert monitor.samples == []
            assert monitor.cpu_percentile == 0

            # Restart
            running_state[0] = True

            assert pass_event.wait(timeout=5)

            with monitor._lock:
                assert len(monitor.samples) > 0
                assert monitor.cpu_percentile == 60
        finally:
            running_state[0] = False
            monitor.stop()


def test_paused_psutil_sample_crossing_stop_start_after_snapshot():
    """A psutil sample call paused AFTER epoch snapshot is discarded when Stop/Start occurs before publication."""
    running_state = [True]
    psutil_entered = threading.Event()
    psutil_release = threading.Event()

    pass2_entered = threading.Event()
    pass2_release = threading.Event()

    call_count = [0]

    def mock_cpu_percent(percpu=True):
        call_count[0] += 1
        if call_count[0] == 1:
            psutil_entered.set()
            assert psutil_release.wait(timeout=5)
            return [99.0, 99.0]
        else:
            pass2_entered.set()
            assert pass2_release.wait(timeout=5)
            return [10.0, 10.0]

    with patch("psutil.cpu_percent", side_effect=mock_cpu_percent):
        monitor = CPUUsageMonitor(
            get_running=lambda: running_state[0],
            logger_instance=StubLogger(),
            dpg_instance=StubDPG(),
            interval=0.01,
        )
        try:
            # 1. Wait until cpu_run enters psutil.cpu_percent on the first pass (snapshot captured)
            assert psutil_entered.wait(timeout=5)

            # 2. Stop occurs and resets monitor (running False, _reset_count incremented)
            running_state[0] = False
            monitor.reset()

            # 3. Start occurs (running True)
            running_state[0] = True

            # 4. Release Pass 1
            psutil_release.set()

            # 5. Wait for Pass 2 to enter psutil.cpu_percent BEFORE Pass 2 publishes.
            # This guarantees Pass 1 has finished processing under lock and Pass 2 has NOT published yet!
            assert pass2_entered.wait(timeout=5)

            # 6. Immediately observe monitor state. Pass 1 (99.0) must NOT have been published!
            with monitor._lock:
                assert 99.0 not in monitor.samples
                assert monitor.samples == []
                assert monitor.cpu_percentile == 0

            # 7. Release Pass 2 and verify Pass 2 publishes fresh data
            pass2_release.set()

            timeout = time.time() + 2.0
            while time.time() < timeout:
                with monitor._lock:
                    if 10.0 in monitor.samples:
                        break
                time.sleep(0.01)

            with monitor._lock:
                assert 10.0 in monitor.samples
                assert monitor.cpu_percentile == 10
        finally:
            running_state[0] = False
            psutil_release.set()
            pass2_release.set()
            monitor.stop()


def test_paused_psutil_sample_crossing_stop_start_before_snapshot():
    """Worker paused BEFORE taking snapshot lock at pass start sees running=False after Stop and skips psutil."""
    running_state = [True]

    get_running_entered = threading.Event()
    get_running_release = threading.Event()

    pass2_entered = threading.Event()
    pass2_release = threading.Event()

    call_count = [0]
    get_running_count = [0]

    def controlled_get_running():
        get_running_count[0] += 1
        if get_running_count[0] == 1:
            get_running_entered.set()
            get_running_release.wait(timeout=5)
        return running_state[0]

    def mock_cpu_percent(percpu=True):
        call_count[0] += 1
        pass2_entered.set()
        assert pass2_release.wait(timeout=5)
        return [20.0, 20.0]

    with patch("psutil.cpu_percent", side_effect=mock_cpu_percent):
        monitor = CPUUsageMonitor(
            get_running=controlled_get_running,
            logger_instance=StubLogger(),
            dpg_instance=StubDPG(),
            interval=0.01,
        )
        try:
            # 1. Wait until worker enters snapshot lock and invokes controlled_get_running
            assert get_running_entered.wait(timeout=5)

            # 2. DFL Stop occurs while worker is paused inside snapshot lock
            running_state[0] = False

            # Release snapshot evaluation and execute reset
            get_running_release.set()
            monitor.reset()

            # Give worker time to complete pass 1 (which sees running=False and skips psutil)
            time.sleep(0.05)

            # 3. Assert psutil was NOT called while stopped (call_count is 0) and samples remain []
            with monitor._lock:
                assert call_count[0] == 0
                assert monitor.samples == []
                assert monitor.cpu_percentile == 0

            # 4. Now Start DFL
            running_state[0] = True

            # Wait for fresh pass post-start
            assert pass2_entered.wait(timeout=5)
            pass2_release.set()

            timeout = time.time() + 2.0
            while time.time() < timeout:
                with monitor._lock:
                    if 20.0 in monitor.samples:
                        break
                time.sleep(0.01)

            with monitor._lock:
                assert 20.0 in monitor.samples
                assert monitor.cpu_percentile == 20
        finally:
            running_state[0] = False
            get_running_release.set()
            pass2_release.set()
            monitor.stop()
