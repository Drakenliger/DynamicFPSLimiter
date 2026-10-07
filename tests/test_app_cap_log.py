"""Exercise the actual app AST helper and admitted write call sites."""
import ast
import csv
import logging
import sys
from decimal import Decimal
from types import SimpleNamespace as NS

import pytest

from core.cap_change_log import CapChangeLog, run_path
from test_app_session import APP, load_app
from test_librehm_policy import run_passes


@pytest.fixture(autouse=True)
def bounded_writer_shutdown(monkeypatch):
    """Fail a stuck real writer instead of leaving pytest in an unbounded join."""
    actual_close = CapChangeLog.close

    def close(log, timeout=None):
        result = actual_close(log, timeout=5.0 if timeout is None else min(timeout, 5.0))
        assert not log._thread.is_alive(), 'cap-change CSV writer did not stop within 5 seconds'
        return result

    monkeypatch.setattr(CapChangeLog, 'close', close)


def test_initializer_csv_error_without_gui_queue(tmp_path, monkeypatch, fake_dpg):
    import core.logger as logger

    monkeypatch.setattr(logger, '_gui_queue', None)
    monkeypatch.setattr(logger, '_dpg', fake_dpg)
    monkeypatch.setattr(logging.getLogger(), 'handlers', [])
    monkeypatch.setattr(logging.getLogger(), 'level', logging.WARNING)
    monkeypatch.setattr(sys, 'excepthook', sys.excepthook)
    error_path = tmp_path / 'error_log.txt'
    ns = dict(logger=logger, logging=logging, CapChangeLog=CapChangeLog,
              run_path=run_path, cm=NS(config_dir=tmp_path / 'missing'),
              error_log_file=str(error_path))
    tree = ast.parse(APP.read_text())
    initializer = [n for n in tree.body if
                   (isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
                    and isinstance(n.value.func, ast.Attribute)
                    and n.value.func.attr == 'init_logging') or
                   (isinstance(n, ast.Assign) and any(
                       isinstance(t, ast.Name) and t.id == 'cap_change_log'
                       for t in n.targets))]
    assert len(initializer) == 2
    try:
        exec(compile(ast.Module(body=initializer, type_ignores=[]), str(APP), 'exec'), ns)
        ns['cap_change_log'].close()
        message = error_path.read_text()
        assert 'ERROR - Cap-change CSV error' in message
        assert str(ns['cap_change_log'].path) in message
        assert not fake_dpg.calls
    finally:
        for handler in logging.getLogger().handlers:
            handler.close()


def setup():
    ns, writes, _, _ = load_app()
    rows, errors, closed = [], [], []
    ns['cap_change_log'] = NS(record=rows.append, close=lambda: closed.append(True))
    ns['logger'].add_log = errors.append
    ns['rtss'].get_framerate_limit = lambda profile, get_denominator: Decimal('90.125')
    return ns, writes, rows, errors, closed


@pytest.mark.parametrize('direct,result,count', [(True, False, 0), (True, True, 1), (True, None, 1), (False, (60, 1), 1), (False, False, 0)])
def test_helper_success_timestamp_snapshot_and_return(direct, result, count):
    ns, _, rows, _, _ = setup()
    ns.update(gpu_values=[Decimal('80.25')], cpu_values=[Decimal('20.5')], fps_mean=Decimal('61.125'))
    clock = [123.25]
    ns['time'].time = lambda: clock[0]
    def write(*args):
        assert ns['session_lock'].locked()
        clock[0] = 999
        ns['gpu_values'].clear()
        ns['cpu_values'].clear()
        ns['fps_mean'] = 0
        return result
    ns['rtss'].set_fractional_fps_direct = ns['rtss'].set_fractional_framerate = write
    with ns['session_lock']:
        assert ns['_write_cap']('quoted,"profile', Decimal('90.125'), 'test', direct=direct) == result
    assert len(rows) == count
    if count:
        assert rows[0] == ('123.25', '1', 'quoted,"profile', '90.125', '90.125', 'test', '80.25', '20.5', '61.125')


@pytest.mark.parametrize('old', [None, 'missing', 'raises'])
def test_unknown_read_does_not_block_write(old):
    ns, writes, rows, errors, _ = setup()
    if old == 'missing':
        del ns['rtss'].get_framerate_limit
    elif old == 'raises':
        def read(*a, **kw):
            raise OSError('unreadable')
        ns['rtss'].get_framerate_limit = read
    else:
        ns['rtss'].get_framerate_limit = lambda *a, **kw: None
    with ns['session_lock']:
        ns['_write_cap']('Global', 60, 'test', direct=True)
    assert len(writes) == len(rows) == 1
    assert rows[0][3] == ''
    assert bool(errors) == (old is not None)


def test_log_and_error_reporter_failure_do_not_block_cap():
    ns, writes, _, _, _ = setup()
    def fail(*a, **kw):
        raise OSError('failed')
    ns['rtss'].get_framerate_limit = fail
    ns['cap_change_log'].record = fail
    ns['logger'].add_log = fail
    with ns['session_lock']:
        ns['_write_cap']('Global', 60, 'test')
    assert len(writes) == 1


def test_rtss_exception_semantics_preserved():
    ns, _, rows, _, _ = setup()
    def fail(*a):
        raise RuntimeError('RTSS failure')
    ns['rtss'].set_fractional_framerate = fail
    with pytest.raises(RuntimeError, match='RTSS failure'), ns['session_lock']:
        ns['_write_cap']('Global', 60, 'test')
    assert not rows


@pytest.mark.parametrize('starting', [True, False])
def test_start_stop_both_calls_and_same_value(starting):
    ns, writes, rows, _, _ = setup()
    ns['running'] = not starting
    ns['start_stop_callback'](None, None, ns['cm'])
    reason = 'start' if starting else 'stop'
    assert [r[5] for r in rows] == [reason, reason + '_refresh']
    assert len(writes) == len(rows) == 2
    assert all(r[1] == '2' for r in rows)


@pytest.mark.parametrize('offset,decisions,reason', [(0, (True, False), 'decrease'), (-60, (False, True), 'increase'), (-55, (False, True), 'increase')])
def test_monitor_drop_raise_and_off_ladder(offset, decisions, reason):
    ns, writes, rows, _, _ = setup()
    ns['CurrentFPSOffset'] = offset
    run_passes(ns, writes, [decisions], samples=[(Decimal('95.5'), 'game')])
    assert len(writes) == len(rows) == 1
    assert rows[0][5:] == (reason, '90', '50', '95.5')
    assert ns['fps_mean'] == 0 and ns['gpu_values'] == []


def test_idle_and_restore():
    ns, writes, rows, _, _ = setup()
    ns['cm'].idle_mode = True
    calls = iter([True, False])
    ns['monitor_idle'] = lambda _: next(calls)
    run_passes(ns, writes, [(False, False)] * 2, samples=[(95, 'game')] * 2)
    assert [r[5] for r in rows] == ['idle', 'idle_restore']
    assert len(writes) == len(rows) == 2


def test_exit_all_three_calls_and_real_file_flush(tmp_path):
    ns, writes, _, errors, _ = setup()
    path = tmp_path / 'exit.csv'
    ns['cap_change_log'] = CapChangeLog(path, errors.append)
    ns['cm'].globallimitonexit = True
    ns['cm'].globallimitonexit_fps = Decimal('72.25')
    ns.update(gpu_values=[80], cpu_values=[20], fps_mean=Decimal('61.5'))
    ns['exit_gui']()
    with path.open(newline='') as source:
        rows = list(csv.DictReader(source))
    assert [r['reason'] for r in rows] == ['exit', 'exit_refresh', 'exit_global']
    assert rows[0]['fps_mean'] == '61.5'
    assert rows[-1]['new_cap'] == '72.25'
    assert len(writes) == 3 and not errors
    assert not ns['cap_change_log']._thread.is_alive()


def test_all_ten_sites_route_through_helper():
    tree = ast.parse(APP.read_text())
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in ('start_stop_callback', 'monitoring_loop', 'exit_gui')]
    calls = [n for f in funcs for n in ast.walk(f) if isinstance(n, ast.Call)]
    assert sum(isinstance(n.func, ast.Name) and n.func.id == '_write_cap' for n in calls) == 10
    assert not any(isinstance(n.func, ast.Attribute) and n.func.attr in ('set_fractional_framerate', 'set_fractional_fps_direct') for n in calls)


@pytest.mark.parametrize('reject', ['session', 'profile'])
def test_rejected_monitor_produces_no_write_or_row(reject):
    ns, writes, rows, _, _ = setup()
    def decision(*a):
        if reject == 'session':
            ns['session_number'] += 1
        else:
            ns['profile_revision'] += 1
        return True, False
    samples = []
    def sample():
        if samples:
            ns['running'] = False
        samples.append(True)
        return Decimal(95), 'game'
    ns['rtss_manager'].get_fps_for_active_window = sample
    ns['fps_utils'].evaluate_cap_change = decision
    ns['time'].sleep = lambda _: ns.update(running=False)
    ns['monitoring_loop'](1)
    assert not writes and not rows


def test_rejected_exit_still_closes():
    ns, writes, rows, _, closed = setup()
    ns['session_is_current'] = lambda *a, **kw: False
    ns['exit_gui']()
    assert not writes and not rows and closed == [True]
