import csv
import itertools
import os
from pathlib import Path
import pytest

from core.cap_change_log import CapChangeLog, make_row, run_path


@pytest.fixture(autouse=True)
def bounded_writer_shutdown(monkeypatch):
    """Fail a stuck real writer instead of leaving pytest in an unbounded join."""
    actual_close = CapChangeLog.close

    def close(log, timeout=None):
        result = actual_close(log, timeout=5.0 if timeout is None else min(timeout, 5.0))
        assert not log._thread.is_alive(), 'cap-change CSV writer did not stop within 5 seconds'
        return result

    monkeypatch.setattr(CapChangeLog, 'close', close)


@pytest.fixture(autouse=True)
def ordered_run_timestamps(monkeypatch):
    # Retention assertions compare launch order, so do not depend on clock precision.
    ticks = itertools.count(1_000_000_000_000_000_000)
    monkeypatch.setattr("core.cap_change_log.time.time_ns", lambda: next(ticks))


def test_prune_21_plus_logs_keeps_20_and_retains_current(tmp_path):
    errors = []
    created_paths = []

    for i in range(25):
        path = run_path(tmp_path)
        created_paths.append(path)
        log = CapChangeLog(path, errors.append)
        log.record(make_row(i, 1, 'Global', None, 60, 'start'))
        log.close(timeout=5.0)

    remaining_files = sorted(tmp_path.glob('cap_changes_*.csv'))
    assert len(remaining_files) == 20
    assert created_paths[-1] in remaining_files
    assert created_paths[0] not in remaining_files
    assert created_paths[4] not in remaining_files
    assert created_paths[5] in remaining_files
    assert not errors


def test_unrelated_files_directories_symlinks_and_newlines_preserved(tmp_path):
    errors = []

    # 1. Unrelated file
    unrelated_file = tmp_path / 'settings.json'
    unrelated_file.write_text('unrelated', encoding='utf-8')

    # 2. Filename with newline
    newline_file = tmp_path / 'cap_changes_100_00000000.csv\n'
    try:
        newline_file.write_text('newline', encoding='utf-8')
        has_newline_file = True
    except Exception:
        has_newline_file = False

    # 3. Directory matching naming pattern
    dir_matching_pattern = tmp_path / 'cap_changes_500_00000000.csv'
    dir_matching_pattern.mkdir()
    (dir_matching_pattern / 'child.txt').write_text('inside dir', encoding='utf-8')

    # 4. Symlink matching naming pattern pointing to target
    target_file = tmp_path / 'target.txt'
    target_file.write_text('target', encoding='utf-8')
    symlink_matching_pattern = tmp_path / 'cap_changes_501_00000000.csv'
    try:
        symlink_matching_pattern.symlink_to(target_file)
        has_symlink = True
    except (OSError, NotImplementedError):
        has_symlink = False

    # Pre-populate 22 old valid generated cap logs
    old_logs = []
    for i in range(1, 23):
        p = tmp_path / f'cap_changes_{1000 + i}_000000{i:02d}.csv'
        p.write_text('time,session_number...\n', encoding='utf-8')
        old_logs.append(p)

    current_path = run_path(tmp_path)
    log = CapChangeLog(current_path, errors.append)
    log.record(make_row(1, 1, 'Global', None, 60, 'start'))
    log.close(timeout=5.0)

    # Verify preservation
    assert unrelated_file.exists()
    assert dir_matching_pattern.is_dir()
    if has_newline_file:
        assert newline_file.exists()
    if has_symlink:
        assert symlink_matching_pattern.is_symlink() or symlink_matching_pattern.exists()

    retained_logs = sorted([p for p in tmp_path.glob('cap_changes_*.csv') if p.is_file() and not p.is_symlink()])
    assert len(retained_logs) == 20
    assert current_path in retained_logs
    assert old_logs[0] not in retained_logs
    assert old_logs[2] not in retained_logs
    assert old_logs[3] in retained_logs
    assert not errors


def test_failed_creation_preserves_old_logs(tmp_path):
    errors = []
    old_logs = []
    for i in range(1, 25):
        p = tmp_path / f'cap_changes_{1000 + i}_000000{i:02d}.csv'
        p.write_text('header\n', encoding='utf-8')
        old_logs.append(p)

    # Attempt to initialize CapChangeLog at an existing file path (raises FileExistsError on open('x'))
    invalid_path = old_logs[0]
    log = CapChangeLog(invalid_path, errors.append)
    log.record(make_row(1, 1, 'Global', None, 60, 'start'))
    log.close(timeout=5.0)

    # All 24 old logs must be preserved without history loss
    for p in old_logs:
        assert p.exists(), f'Old log {p.name} was wrongly deleted on file creation failure'

    assert len(errors) == 1
    assert 'Cap-change CSV error' in errors[0]


def test_close_drains_accepted_rows_and_waits_writer(tmp_path):
    errors = []
    path = run_path(tmp_path)
    log = CapChangeLog(path, errors.append)

    count = 100
    for i in range(count):
        log.record(make_row(i, 1, 'Global', None, 60, 'start'))

    log.close()  # The fixture bounds the real writer join.

    assert not log._thread.is_alive()
    assert path.exists()

    with path.open(newline='', encoding='utf-8') as source:
        rows = list(csv.reader(source))
    assert len(rows) == count + 1  # header + count rows
    assert not errors


def test_prune_filesystem_error_reports_safely_and_does_not_block(monkeypatch, tmp_path):
    errors = []

    # Create 22 pre-existing valid generated log files
    for i in range(1, 23):
        p = tmp_path / f'cap_changes_{1000 + i}_000000{i:02d}.csv'
        p.write_text('header\n', encoding='utf-8')

    original_unlink = Path.unlink

    def failing_unlink(self, *args, **kwargs):
        if 'cap_changes_1001_' in self.name:
            raise OSError('Permission denied')
        return original_unlink(self, *args, **kwargs)

    monkeypatch.setattr(Path, 'unlink', failing_unlink)

    current_path = run_path(tmp_path)
    log = CapChangeLog(current_path, errors.append)
    log.record(make_row(1, 1, 'Global', None, 60, 'start'))
    log.close(timeout=5.0)

    assert current_path.exists()
    with current_path.open(newline='', encoding='utf-8') as source:
        rows = list(csv.reader(source))
    assert len(rows) == 2

    assert len(errors) == 1
    assert 'Cap-change CSV error' in errors[0]
    assert 'Permission denied' in errors[0]
