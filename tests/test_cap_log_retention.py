import csv
import os
from pathlib import Path
import pytest

from core.cap_change_log import CapChangeLog, make_row, run_path


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


def test_unrelated_files_preserved(tmp_path):
    errors = []
    unrelated_files = [
        tmp_path / 'settings.json',
        tmp_path / 'results.csv',
        tmp_path / 'cap_changes_settings.csv',
        tmp_path / 'cap_changes_summary.csv',
        tmp_path / 'cap_changes_123_invalid.csv',
        tmp_path / 'cap_changes_100_nothex12.csv',
        tmp_path / 'cap_changes_100_00000000.txt',
    ]
    for p in unrelated_files:
        p.write_text('unrelated', encoding='utf-8')

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

    for p in unrelated_files:
        assert p.exists(), f'Unrelated file {p.name} was wrongly deleted'

    retained_logs = sorted([p for p in tmp_path.glob('cap_changes_*.csv') if p not in unrelated_files])
    assert len(retained_logs) == 20
    assert current_path in retained_logs
    assert old_logs[0] not in retained_logs
    assert old_logs[2] not in retained_logs
    assert old_logs[3] in retained_logs
    assert not errors


def test_prune_filesystem_error_reports_safely_and_does_not_block(monkeypatch, tmp_path):
    errors = []

    # Create 22 pre-existing valid generated log files
    for i in range(1, 23):
        p = tmp_path / f'cap_changes_{1000 + i}_000000{i:02d}.csv'
        p.write_text('header\n', encoding='utf-8')

    # Force Path.unlink to fail with OSError during pruning
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

    # Log file writing must still succeed and not be blocked
    assert current_path.exists()
    with current_path.open(newline='', encoding='utf-8') as source:
        rows = list(csv.reader(source))
    assert len(rows) == 2  # header + row recorded

    # Prune failure must be reported safely
    assert len(errors) == 1
    assert 'Cap-change CSV error' in errors[0]
    assert 'Permission denied' in errors[0]
