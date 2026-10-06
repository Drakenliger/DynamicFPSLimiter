"""Portable evidence rules for the local Windows acceptance runner."""
import logging
import re
from pathlib import Path

SCENARIOS = ('restart isolation', 'active profile switching', 'LibreHM drop and raise delays',
             'settling and history clearing', 'exit while running')
WINDOW_SECONDS = 2.0


def sanitize(text):
    # Apply to formatted exceptions too, before a handler writes anything.
    text = re.sub(r'(?i)(?:[a-z]:[\\/]|/home/|/Users/)[^\n\r\"\']*', '%USERPROFILE%', str(text))
    text = re.sub(r'(?i)\b[\w .-]+\.exe\b', lambda m: m[0] if m[0].strip().lower() in
                  {'pythonw.exe', 'dynamicfpslimiter.exe'} else 'other', text)
    return text


class SafeFormatter(logging.Formatter):
    def format(self, record):
        return sanitize(super().format(record))


class Snapshot:
    """Only caller-specified files; original content never leaves memory."""
    def __init__(self, paths):
        self.files = [(Path(p), Path(p).read_bytes() if Path(p).exists() else None) for p in paths]

    def restore(self):
        errors = []
        for path, data in self.files:
            try:
                if data is None:
                    path.unlink(missing_ok=True)
                else:
                    path.write_bytes(data)
            except OSError as exc:
                errors.append(exc)
        if errors:
            raise RuntimeError('RTSS file restoration failed') from errors[0]


def correlate(writes, frames):
    """Worst frame interval in [write-2s, write+2s], with coverage required."""
    result = []
    for write in writes:
        t = float(write['time'])
        selected = [(float(a), float(b)) for a, b in frames if t-WINDOW_SECONDS <= float(a) <= t+WINDOW_SECONDS]
        covered = (len(selected) >= 3 and min(a for a, _ in selected) <= t-1.5
                   and max(a for a, _ in selected) >= t+1.5)
        result.append({'time': t, 'complete': covered,
                       'worst_ms': max((b for _, b in selected), default=None)})
    return result


def verdict(condition, detail):
    return {'status': 'PASS' if condition else 'FAIL', 'detail': sanitize(detail)}


def expectations(e):
    """Require independently observed callbacks, writes, state and telemetry."""
    return {
        SCENARIOS[0]: verdict(e.get('cycles') == 20 and e.get('retired_quiet') is True,
                             '20 cycles; retired workers and write admission checked'),
        SCENARIOS[1]: verdict(e.get('switch_ladders') == [[30, 45, 60], [24, 36, 48]]
                             and e.get('switch_response') is True, 'Two distinct bounds and runtime cap response'),
        SCENARIOS[2]: verdict(e.get('drop_delay') is True and e.get('raise_delay') is True
                             and e.get('physical_sensor') is True and e.get('hooked') is True
                             and e.get('pdh_unavailable') is True,
                             'Real LibreHM readings, controlled thresholds, real RTSS/FPS'),
        SCENARIOS[3]: verdict(e.get('cleared') is True and e.get('settled') is True,
                             'Empty histories after writes; consecutive decisions separated'),
        SCENARIOS[4]: verdict(e.get('exit_running') is True and e.get('exit_readback') == 48,
                             'Real exit callback; active profile max read back'),
    }


def confirmed_delay(write_time, decisions, direction, since):
    """Independent observation: three consecutive eligible samples after reset."""
    eligible = [(timestamp, decision) for timestamp, decision in decisions
                if since < timestamp <= write_time]
    tail = eligible[-3:]
    return (len(tail) == 3 and all(decision == direction for _, decision in tail)
            and tail[-1][0] - tail[0][0] >= 1.8)


def final_results(evidence, errors):
    if errors:
        return {name: verdict(False, '; '.join(errors)) for name in SCENARIOS}
    return expectations(evidence)
