"""Evidence requirements, independent of app implementation and Windows APIs."""
import logging
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from acceptance_support import SCENARIOS, SafeFormatter, Snapshot, correlate, expectations, sanitize
from acceptance_windows import wait_ready


def test_sanitize_paths_processes_and_formatted_traceback():
    try:
        raise RuntimeError(r'C:\Users\PrivateOwner\Documents\settings.ini')
    except RuntimeError:
        record = logging.LogRecord('test', logging.ERROR, __file__, 1,
            'application secret-game.exe failed', (), sys.exc_info())
    result = SafeFormatter().format(record)
    assert 'PrivateOwner' not in result and 'secret-game.exe' not in result
    assert '%USERPROFILE%' in result and 'Traceback' in result
    assert sanitize('pythonw.exe') == 'pythonw.exe'
    assert sanitize('DynamicFPSLimiter.exe') == 'DynamicFPSLimiter.exe'
    assert 'private' not in sanitize('/home/private/work/data')


def test_restoration_after_failure_preserves_bytes_and_absence(tmp_path):
    present = tmp_path / 'Global'
    absent = tmp_path / 'pythonw.exe.cfg'
    original = b'\xff\x00private\r\n'
    present.write_bytes(original)
    snapshot = Snapshot([present, absent])
    try:
        present.write_bytes(b'controlled')
        absent.write_bytes(b'controlled')
        raise RuntimeError('child crashed')
    except RuntimeError:
        pass
    finally:
        snapshot.restore()
    assert present.read_bytes() == original
    assert not absent.exists()


def test_correlates_each_write_with_fixed_window_and_no_spike_threshold():
    frames = [(t / 10, 500 if t == 100 else 16) for t in range(70, 141)]
    result = correlate([{'time': '10'}, {'time': '13'}, {'time': '40'}], frames)
    assert result[0] == {'time': 10, 'complete': True, 'worst_ms': 500}
    assert result[1]['complete'] is False
    assert result[2]['worst_ms'] is None
    assert result[2]['complete'] is False


@pytest.mark.parametrize('payload', [{}, {'cycles': 20}, {'physical_sensor': True},
                                  {'exit_running': True}, {'cleared': True}])
def test_incomplete_evidence_never_passes_all_scenarios(payload):
    result = expectations(payload)
    assert list(result) == list(SCENARIOS)
    assert any(row['status'] == 'FAIL' for row in result.values())


def complete_evidence():
    return dict(cycles=20, retired_quiet=True, switch_ladders=[[30,45,60],[24,36,48]],
                switch_response=True, drop_delay=True, raise_delay=True, physical_sensor=True,
                hooked=True, pdh_unavailable=True, cleared=True, settled=True, exit_running=True, exit_readback=48)


@pytest.mark.parametrize('field,invalid,scenario', [
    ('cycles', 19, 0), ('retired_quiet', False, 0),
    ('switch_ladders', [[30,45,60],[30,45,60]], 1), ('switch_response', False, 1),
    ('drop_delay', False, 2), ('raise_delay', False, 2), ('physical_sensor', False, 2),
    ('hooked', False, 2), ('pdh_unavailable', False, 2), ('cleared', False, 3), ('settled', False, 3),
    ('exit_running', False, 4), ('exit_readback', 24, 4)])
def test_each_named_scenario_requires_its_independent_evidence(field, invalid, scenario):
    evidence = complete_evidence()
    assert all(r['status'] == 'PASS' for r in expectations(evidence).values())
    evidence[field] = invalid
    assert expectations(evidence)[SCENARIOS[scenario]]['status'] == 'FAIL'


def test_readiness_timeout_and_process_failure_are_explicit(tmp_path):
    class Process:
        def poll(self):
            return None
    with pytest.raises(TimeoutError, match='readiness timeout'):
        wait_ready(Process(), tmp_path / 'missing', 0)
    class Crashed:
        def poll(self):
            return 1
    with pytest.raises(RuntimeError, match='exited before readiness'):
        wait_ready(Crashed(), tmp_path / 'missing', 1)


def test_delay_evidence_cannot_reuse_samples_before_a_write_or_accept_early_response():
    from acceptance_support import confirmed_delay
    readings = [(1., (True,False)), (2., (True,False)), (3., (True,False)),
                (4., (True,False)), (5., (True,False))]
    assert confirmed_delay(3.1, readings, (True,False), 0)
    assert not confirmed_delay(5.1, readings, (True,False), 3.1)
    assert not confirmed_delay(2.1, readings, (True,False), 0)
    assert not confirmed_delay(5.1, [(3.,(False,False)), (4.,(True,False)), (5.,(True,False))], (True,False), 0)


def test_timeout_or_queued_exception_overrides_otherwise_complete_evidence():
    from acceptance_support import final_results
    for error in ['limiter process timeout', 'GUI queue exception', 'forced fake game termination: incomplete telemetry']:
        result = final_results(complete_evidence(), [error])
        assert all(row['status'] == 'FAIL' and error in row['detail'] for row in result.values())


def test_restore_attempts_other_file_even_if_first_restore_fails(tmp_path, monkeypatch):
    present = tmp_path / 'Global'
    absent = tmp_path / 'pythonw.exe.cfg'
    present.write_bytes(b'original')
    snapshot = Snapshot([present, absent])
    present.write_bytes(b'changed')
    absent.write_bytes(b'created')
    real_write = Path.write_bytes
    def fail_one(path, data):
        if path == present:
            raise OSError('access denied')
        return real_write(path, data)
    monkeypatch.setattr(Path, 'write_bytes', fail_one)
    with pytest.raises(RuntimeError, match='restoration failed'):
        snapshot.restore()
    assert not absent.exists()
