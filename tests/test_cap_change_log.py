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
