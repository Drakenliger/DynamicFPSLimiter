from decimal import Decimal


def exit_restore_cap(running, profile, limits):
    """Restore a running profile to its ladder maximum; stopped exits skip it."""
    return (profile, Decimal(max(limits))) if running else None


def build_cap_model(limits):
    """Snapshot a cap ladder and its extrema and padded plot bounds."""
    ladder = tuple(sorted(set(Decimal(x) for x in limits)))
    minimum, maximum = min(ladder), max(ladder)
    padding = round((maximum - minimum) * Decimal("0.1"))
    return ladder, minimum, maximum, minimum - padding, maximum + padding


# cap_policy.py
# Pure FPS cap decrease policy, extracted from app.monitoring_loop so it
# can be unit-tested without a GUI, RTSS, or .NET.


def next_cap_on_decrease(fps_limit_list, current_cap, fps_mean):
    """Return the next FPS cap to apply after a decrease decision, or None
    when no decrease is possible.

    ``fps_limit_list`` is the ladder of stepped cap values (e.g.
    [30, 45, 60, 75, 90]); ``current_cap`` is the cap currently applied
    (maxcap + CurrentFPSOffset); ``fps_mean`` is the recent average FPS.

    Policy:
    - empty ladder: None
    - ``current_cap`` in ladder at the lowest rung: None (already at floor)
    - ``current_cap`` in ladder above the floor:
        - ``current_cap <= fps_mean`` (the cap is the limiting factor):
          step down exactly one rung
        - ``current_cap > fps_mean``: jump to the highest rung below
          ``fps_mean``
    - ``current_cap`` not in ladder: highest rung below ``current_cap``
    """
    if not fps_limit_list:
        return None
    try:
        idx = fps_limit_list.index(current_cap)
    except ValueError:
        below_cap = [x for x in fps_limit_list if x < current_cap]
        return max(below_cap) if below_cap else None
    if idx == 0:
        return None
    if current_cap <= fps_mean:
        return fps_limit_list[idx - 1]
    below_mean = [x for x in fps_limit_list if x < fps_mean]
    return max(below_mean) if below_mean else None


def cap_readings_valid(method, gpu_usage, fps, fps_mean, min_gpu, min_fps):
    """LibreHM needs live FPS; Legacy retains its PDH and mean-FPS gates."""
    if method == "LibreHM":
        return fps is not None and fps > 0 and fps > min_fps
    return gpu_usage is not None and gpu_usage > min_gpu and fps_mean > min_fps


def confirm_librehm_decision(history, decrease, increase, drop_delay, raise_delay):
    """Count consecutive monitoring passes independently in each direction.

    Neutral/no-data passes reset both counts. Counts saturate at the configured
    delay; cap writes do not reset them here.
    """
    drop_delay, raise_delay = max(1, drop_delay), max(1, raise_delay)
    drops = min(history[0] + 1, drop_delay) if decrease else 0
    raises = min(history[1] + 1, raise_delay) if increase else 0
    return (drops, raises), (drops >= drop_delay, raises >= raise_delay)


def evaluate_legacy_cap_change(gpu_values, cpu_values, drop_delay, raise_delay,
                               gpu_upper, cpu_upper, gpu_lower, cpu_lower):
    """Preserve Legacy thresholds; incomplete evidence makes this pass neutral.

    Check both channels over both relevant windows before comparing values, so
    an overloaded channel cannot authorize a drop with missing peer evidence.
    """
    gpu_drop, cpu_drop = gpu_values[-drop_delay:], cpu_values[-drop_delay:]
    gpu_raise, cpu_raise = gpu_values[-raise_delay:], cpu_values[-raise_delay:]
    if any(value is None for window in (gpu_drop, cpu_drop, gpu_raise, cpu_raise)
           for value in window):
        return False, False
    decrease = (len(gpu_values) >= drop_delay and all(v >= gpu_upper for v in gpu_drop)
                or len(cpu_values) >= drop_delay and all(v >= cpu_upper for v in cpu_drop))
    increase = (len(gpu_values) >= raise_delay and all(v <= gpu_lower for v in gpu_raise)
                and len(cpu_values) >= raise_delay and all(v <= cpu_lower for v in cpu_raise))
    return decrease, increase


def fresh_cap_evidence():
    """Discard pre-write samples and confirmations without changing cap state.

    Each call owns three distinct lists, including across successive resets.
    """
    return [], [], [], 0, (0, 0)
