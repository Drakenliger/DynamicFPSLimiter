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
    running = True
    monitor = CPUUsageMonitor(
        get_running=lambda: running,
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

    running_state = True
    cpu_mon = CPUUsageMonitor(
        get_running=lambda: running_state,
        logger_instance=StubLogger(),
        dpg_instance=StubDPG(),
        interval=0.05,
    )

    try:
        # Simulate high pre-stop samples in cpu_monitor
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

    with patch("psutil.cpu_percent", return_value=[50.0, 60.0]):
        monitor = CPUUsageMonitor(
            get_running=lambda: running_state[0],
            logger_instance=StubLogger(),
            dpg_instance=StubDPG(),
            interval=0.01,
        )
        try:
            # Wait for at least one sampling pass
            timeout = time.time() + 2.0
            while time.time() < timeout:
                with monitor._lock:
                    if len(monitor.samples) > 0:
                        break
                time.sleep(0.01)

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

            timeout = time.time() + 2.0
            while time.time() < timeout:
                with monitor._lock:
                    if len(monitor.samples) > 0:
                        break
                time.sleep(0.01)

            with monitor._lock:
                assert len(monitor.samples) > 0
                assert monitor.cpu_percentile == 60
        finally:
            monitor.stop()


def test_paused_psutil_sample_crossing_stop_start():
    """A psutil sample call paused before Stop does not publish pre-Stop data into a restarted session."""
    running_state = [True]
    psutil_entered = threading.Event()
    psutil_release = threading.Event()
    call_count = [0]

    def mock_cpu_percent(percpu=True):
        call_count[0] += 1
        if call_count[0] == 1:
            psutil_entered.set()
            assert psutil_release.wait(timeout=5)
            return [99.0, 99.0]
        return [10.0, 10.0]

    with patch("psutil.cpu_percent", side_effect=mock_cpu_percent):
        monitor = CPUUsageMonitor(
            get_running=lambda: running_state[0],
            logger_instance=StubLogger(),
            dpg_instance=StubDPG(),
            interval=0.01,
        )
        try:
            # Wait until cpu_run enters psutil.cpu_percent on the first pass
            assert psutil_entered.wait(timeout=5)

            # While psutil call is in-flight, Stop occurs and resets monitor
            running_state[0] = False
            monitor.reset()

            # Now Start occurs
            running_state[0] = True

            # Release the first psutil call
            psutil_release.set()

            # Wait for at least one fresh sampling pass post-restart
            timeout = time.time() + 2.0
            while time.time() < timeout:
                with monitor._lock:
                    if 10.0 in monitor.samples:
                        break
                time.sleep(0.01)

            # Assert stale sample 99.0 was discarded and never added to samples
            with monitor._lock:
                assert 99.0 not in monitor.samples
                assert 10.0 in monitor.samples
                assert monitor.cpu_percentile == 10
        finally:
            psutil_release.set()
            monitor.stop()
