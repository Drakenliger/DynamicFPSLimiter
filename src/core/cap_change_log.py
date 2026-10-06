"""Cap-write event snapshots and an asynchronous, standard-library CSV sink."""
import csv
import io
from pathlib import Path
import queue
import re
import threading
import time
import uuid


FIELDS = ('time', 'session_number', 'profile', 'old_cap', 'new_cap', 'reason',
          'gpu_reading', 'cpu_reading', 'fps_mean')

MAX_RETAINED_LOGS = 20
CAP_LOG_PATTERN = re.compile(r'^cap_changes_(\d+)_([0-9a-fA-F]{8})\.csv$')


def make_row(timestamp, session, profile, old_cap, new_cap, reason,
             gpu_reading=None, cpu_reading=None, fps_mean=None):
    """Freeze values without rounding; unknown values become empty CSV fields."""
    return tuple('' if value is None else str(value) for value in
                 (timestamp, session, profile, old_cap, new_cap, reason,
                  gpu_reading, cpu_reading, fps_mean))


def serialize_row(row):
    """Serialize one row with CSV quoting, including embedded newlines."""
    output = io.StringIO(newline='')
    csv.writer(output).writerow(row)
    return output.getvalue()


def run_path(config_dir):
    return Path(config_dir) / f'cap_changes_{time.time_ns()}_{uuid.uuid4().hex[:8]}.csv'


class CapChangeLog:
    """One FIFO writer; callers only enqueue immutable snapshots.

    close drains accepted events and joins the writer, including on output failure.
    """
    def __init__(self, path, report_error):
        self.path = Path(path)
        self._report_error = report_error
        self._queue = queue.SimpleQueue()
        self._lock = threading.Lock()
        self._closed = False
        self._thread = threading.Thread(target=self._write, name='cap-change-csv', daemon=True)
        self._thread.start()

    def _error(self, exc):
        try:
            self._report_error(f'Cap-change CSV error ({self.path}): {exc}')
        except Exception:
            pass  # An error reporter must not interrupt cap control or shutdown.

    def _prune_old_logs(self):
        try:
            parent = self.path.parent
            if not parent.is_dir():
                return
            candidates = []
            for child in parent.iterdir():
                if child.name == self.path.name:
                    continue
                match = CAP_LOG_PATTERN.match(child.name)
                if match:
                    timestamp = int(match.group(1))
                    candidates.append((timestamp, child))

            total_count = len(candidates) + 1
            if total_count > MAX_RETAINED_LOGS:
                candidates.sort(key=lambda item: (item[0], item[1].name))
                to_delete = total_count - MAX_RETAINED_LOGS
                for _, child in candidates[:to_delete]:
                    try:
                        child.unlink()
                    except Exception as exc:
                        self._error(exc)
        except Exception as exc:
            self._error(exc)

    def record(self, row):
        with self._lock:
            if not self._closed:
                self._queue.put(row)

    def close(self, timeout=5.0):
        with self._lock:
            if not self._closed:
                self._closed = True
                self._queue.put(None)
        self._thread.join(timeout=timeout)

    def _write(self):
        drained = False
        try:
            self._prune_old_logs()
            with self.path.open('x', newline='', encoding='utf-8') as output:
                output.write(serialize_row(FIELDS))
                while True:
                    row = self._queue.get()
                    if row is None:
                        drained = True
                        break
                    output.write(serialize_row(row))
                    output.flush()
                output.flush()
        except Exception as exc:
            self._error(exc)
            # Drain until shutdown so a broken sink does not retain queued events.
            while not drained and self._queue.get() is not None:
                pass
