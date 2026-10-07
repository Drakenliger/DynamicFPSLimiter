import csv
from decimal import Decimal
import io
import threading

from core.cap_change_log import CapChangeLog, FIELDS, make_row, run_path, serialize_row


def test_csv_pure_fractional_quoting_and_unknown():
    row = make_row(Decimal('123.001'), 2, 'a,"b\nc', None,
                   Decimal('59.940'), 'increase', None, Decimal('12.5'), Decimal('61.25'))
    assert next(csv.reader(io.StringIO(serialize_row(row)))) == [
        '123.001', '2', 'a,"b\nc', '', '59.940', 'increase', '', '12.5', '61.25']
    assert make_row(1, 2, 'Global', 0, 0, 'stop')[3] == '0'


def test_ordered_file_close_flushes(tmp_path):
    errors = []
    path = run_path(tmp_path)
    assert path != run_path(tmp_path)
    log = CapChangeLog(path, errors.append)
    rows = [make_row(i + .125, 1, 'a,"b\nc', None if i == 0 else Decimal('60.5'),
                     Decimal('60.5'), 'stop_refresh') for i in range(20)]
    for row in rows:
        log.record(row)
    log.close()
    log.close()
    with path.open(newline='', encoding='utf-8') as source:
        assert list(csv.reader(source)) == [list(FIELDS)] + [list(row) for row in rows]
    assert not errors
    assert not log._thread.is_alive()


def test_output_error_visible_and_close_drains(tmp_path):
    errors = []
    log = CapChangeLog(tmp_path / 'missing' / 'events.csv', errors.append)
    log.record(make_row(1, 1, 'Global', None, 60, 'start'))
    log.close()
    assert len(errors) == 1 and 'Cap-change CSV error' in errors[0]


def test_queued_row_readable_before_close(monkeypatch, tmp_path):
    from pathlib import Path
    original = Path.open
    flushed = threading.Event()
    flush_threads = []

    class ObservedOutput:
        def __init__(self, output):
            self.output = output

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.output.close()

        def write(self, text):
            return self.output.write(text)

        def flush(self):
            self.output.flush()
            flush_threads.append(threading.current_thread().name)
            flushed.set()

    def opened(path, mode='r', *args, **kwargs):
        output = original(path, mode, *args, **kwargs)
        return ObservedOutput(output) if mode == 'x' else output

    monkeypatch.setattr(Path, 'open', opened)
    errors = []
    path = tmp_path / 'events.csv'
    log = CapChangeLog(path, errors.append)
    row = make_row(1, 1, 'Global', None, 60, 'start')
    try:
        log.record(row)
        assert flushed.wait(timeout=5), 'writer did not flush the accepted row'
        assert log._thread.is_alive()
        with path.open(newline='', encoding='utf-8') as source:
            assert list(csv.reader(source)) == [list(FIELDS), list(row)]
        assert flush_threads == ['cap-change-csv']
    finally:
        log.close()
    assert not errors


def test_row_flush_error_reports_and_drains(monkeypatch, tmp_path):
    from pathlib import Path
    reported = threading.Event()

    class Broken(io.StringIO):
        def flush(self):
            raise OSError('row flush failed')

    monkeypatch.setattr(Path, 'open', lambda *a, **kw: Broken())
    errors = []

    def report(message):
        errors.append(message)
        reported.set()

    log = CapChangeLog(tmp_path / 'events.csv', report)
    try:
        log.record(make_row(1, 1, 'Global', None, 60, 'start'))
        assert reported.wait(timeout=5)
        log.record(make_row(2, 1, 'Global', 60, 30, 'decrease'))
    finally:
        log.close()
    assert len(errors) == 1 and 'row flush failed' in errors[0]
    assert not log._thread.is_alive()


def test_flush_error_still_closes(monkeypatch, tmp_path):
    from pathlib import Path
    class Broken(io.StringIO):
        def flush(self):
            raise OSError('flush failed')
    monkeypatch.setattr(Path, 'open', lambda *a, **kw: Broken())
    errors = []
    log = CapChangeLog(tmp_path / 'events.csv', errors.append)
    log.close()
    assert 'flush failed' in errors[0]


def test_disk_io_is_only_on_writer_thread(monkeypatch, tmp_path):
    from pathlib import Path
    original = Path.open
    threads = []
    def opened(*args, **kwargs):
        threads.append(threading.current_thread().name)
        return original(*args, **kwargs)
    monkeypatch.setattr(Path, 'open', opened)
    log = CapChangeLog(tmp_path / 'events.csv', lambda _: None)
    log.record(make_row(1, 1, 'Global', None, 60, 'start'))
    log.close()
    assert threads == ['cap-change-csv']
