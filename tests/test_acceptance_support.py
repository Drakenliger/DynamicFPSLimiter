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


def test_actual_decision_observer_discards_crossed_revision(tmp_path, monkeypatch):
    from acceptance_windows import Runtime
    import threading
    from test_app_session import load_app, worker, finish
    ns, writes, _, _ = load_app()
    monkeypatch.setattr("acceptance_windows.generated_configs", lambda directory: None)
    runtime = Runtime(tmp_path, 1)
    runtime.app = ns
    ns['_acceptance_runtime'] = runtime
    def invalidate(*args):
        ns['session_number'] = 2
        ns['profile_revision'] = 1
        return True, False
    ns['fps_utils'].evaluate_cap_change = invalidate
    thread, errors = worker(lambda: ns['monitoring_loop'](1))
    finish(thread, errors)
    assert runtime.decisions == []
    assert not writes


def test_actual_monitor_restart_barrier_preserves_current_history(tmp_path, monkeypatch):
    from acceptance_windows import Runtime
    from test_app_session import load_app, worker, finish, restart
    import threading
    ns, writes, _, _ = load_app()
    monkeypatch.setattr("acceptance_windows.generated_configs", lambda directory: None)
    runtime = Runtime(tmp_path, 1)
    runtime.app = ns
    ns['_acceptance_runtime'] = runtime
    entered, release = threading.Event(), threading.Event()
    def read():
        entered.set()
        assert release.wait(2)
        return 95, 'pythonw.exe'
    ns['rtss_manager'].get_fps_for_active_window = read
    thread, errors = worker(lambda: ns['monitoring_loop'](1))
    try:
        assert entered.wait(2)
        restart(ns)
        assert thread.is_alive() and ns['running']
        ns['fps_values'] = [55]
        ns['gpu_values'] = [None]
        ns['cpu_values'] = [22]
        before = len(writes)
    finally:
        release.set()
    finish(thread, errors)
    assert len(writes) == before
    assert ns['fps_values'] == [55] and ns['cpu_values'] == [22]
    assert not runtime.samples


def test_only_pythonw_frame_response_cannot_prove_global():
    from acceptance_support import sustained_responses
    rows = [dict(time=0, profile='Global', new_cap=30),
            dict(time=10, profile='pythonw.exe', new_cap=24),
            dict(time=20, profile='pythonw.exe', new_cap=48)]
    frames = [(i / 10, 1000 / (48 if i < 100 or i >= 200 else 24)) for i in range(310)]
    responses = sustained_responses(rows, frames)
    assert responses == {('pythonw.exe', 24.), ('pythonw.exe', 48.)}
    assert ('Global', 30.) not in responses


def test_actual_finish_rejects_invalid_global_intermediate(tmp_path, monkeypatch):
    from acceptance_windows import Runtime
    from types import SimpleNamespace
    monkeypatch.setattr("acceptance_windows.generated_configs", lambda directory: None)
    runtime = Runtime(tmp_path, 1)
    runtime.rows = [dict(time=str(i), session_number=1, profile=p, new_cap=c, reason=r)
                    for i, (p,c,r) in enumerate([('Global',90,'increase'), ('Global',30,'decrease'),
                        ('pythonw.exe',24,'decrease'), ('pythonw.exe',48,'increase')], 1)]
    runtime.revisions = {r['time']: (0 if r['profile'] == 'Global' else 1) for r in runtime.rows}
    runtime.models = {0: ('Global', [30,45,60]), 1: ('pythonw.exe', [24,36,48])}
    runtime.finish(dict(running=True, exit_gui=lambda: None,
                        rtss=SimpleNamespace(get_framerate_limit=lambda *a: 48)))
    assert runtime.evidence['switch_response'] is False


@pytest.mark.parametrize('fault', ['exit', 'timeout', 'empty'])
def test_actual_parent_failure_restores_and_exports(tmp_path, monkeypatch, fault):
    import acceptance_windows as driver
    import csv
    import subprocess
    from types import SimpleNamespace
    root = tmp_path / 'repo'
    (root / '.venv/Scripts').mkdir(parents=True)
    (root / '.venv/Scripts/pythonw.exe').touch()
    profiles = tmp_path / 'Profiles'
    profiles.mkdir()
    original = b'\xffprivate\x00'
    (profiles / 'Global').write_bytes(original)
    rtss = SimpleNamespace(rtss_install_path=str(tmp_path), RTSSHOOKSFLAG_LIMITER_DISABLED=1,
        SetFlags=lambda *a: 1, UpdateProfiles=lambda: None, enable_limiter=lambda: None,
        set_fractional_fps_direct=lambda *a: True)
    monkeypatch.setattr(driver, 'ROOT', root)
    monkeypatch.setattr(driver.sys, 'platform', 'win32')
    monkeypatch.setattr(driver, 'controller', lambda: rtss)
    monkeypatch.setattr(driver.subprocess, 'check_output', lambda *a, **kw: '90ee864')
    monkeypatch.setattr(driver.time, 'sleep', lambda *a: None)
    monkeypatch.setattr(driver, 'wait_ready', lambda *a: None)
    class Process:
        pid = 123
        def __init__(self, command, **kw):
            self.child = '--child' in command
            self.returncode = None
            if self.child:
                scratch = Path(command[command.index('--child') + 1])
                if fault != 'empty':
                    with (scratch / 'cap_changes_test.csv').open('w', newline='') as out:
                        writer = csv.writer(out)
                        from acceptance_support import CAP_FIELDS
                        writer.writerow(CAP_FIELDS)
                        writer.writerow([10,1,'Global',60,30,'decrease','','',60])
                    (scratch / 'frames.csv').write_text('timestamp,frame_time_ms\n8,33\n10,33\n12,33\n')
        def wait(self, timeout):
            if self.child and fault == 'timeout' and self.returncode is None:
                raise subprocess.TimeoutExpired('limiter', timeout)
            self.returncode = 7 if self.child else 0
        def kill(self):
            self.returncode = -9
        def poll(self):
            return self.returncode
    monkeypatch.setattr(driver.subprocess, 'Popen', Process)
    assert driver.run() == 1
    assert (profiles / 'Global').read_bytes() == original
    assert not (profiles / 'pythonw.exe.cfg').exists()
    output = next((root / 'results').iterdir())
    from acceptance_support import CAP_FIELDS
    with (output / 'cap_changes.csv').open() as source:
        reader = csv.DictReader(source)
        assert reader.fieldnames == list(CAP_FIELDS)
        rows = list(reader)
    summary = (output / 'summary.md').read_text()
    assert 'child result missing or invalid' in summary and 'FAIL' in summary
    if fault != 'empty':
        assert rows[0]['new_cap'] == '30'
        assert len((output / 'frames.csv').read_text().splitlines()) == 4
        assert '| 10.0 | 33.0 | PASS |' in summary
    else:
        assert not rows and 'telemetry empty or unavailable' in summary
    assert ('process timeout' if fault == 'timeout' else 'process exit code 7') in summary


def test_actual_startup_skips_popup_ini_read_and_needs_no_early_context(tmp_path, monkeypatch):
    """Execute every top-level startup statement through the main create_context.

    OS/GUI/hardware imports are faked; actual popup and ConfigManager code run.
    The parser spy rejects every non-generated INI read, including popup reads.
    """
    import ast
    import configparser
    import os
    import runpy
    import threading
    from decimal import Decimal, InvalidOperation
    from types import SimpleNamespace, ModuleType
    from unittest.mock import MagicMock
    import acceptance_windows as driver
    sensor_module = ModuleType('core.librehardwaremonitor')
    sensor_module.get_all_sensor_infos = lambda *a: []
    monkeypatch.setitem(sys.modules, 'core.librehardwaremonitor', sensor_module)
    # Keep the actual ConfigManager implementation, with only hardware enumeration faked.
    config_module = ModuleType('core.config_manager')
    config_module.__dict__.update(runpy.run_path(str(driver.ROOT / 'src/core/config_manager.py')))
    monkeypatch.setitem(sys.modules, 'core.config_manager', config_module)
    generated = tmp_path / 'generated'
    generated.mkdir()
    real_read = configparser.ConfigParser.read
    reads = []
    def read(parser, filenames, *args, **kwargs):
        paths = [filenames] if isinstance(filenames, (str, Path)) else filenames
        for path in paths:
            assert Path(path).parent == generated, f'real INI read: {path}'
            reads.append(Path(path))
        return real_read(parser, filenames, *args, **kwargs)
    monkeypatch.setattr(configparser.ConfigParser, 'read', read)
    # ConfigManager's constructor calls makedirs before its overridable loader.
    makedirs = os.makedirs
    monkeypatch.setattr(os, 'makedirs', lambda path, **kw: makedirs(path, **kw) if Path(path) == generated else None)
    class NoEarlyDPG:
        def __init__(self):
            self.created = 0
        def create_context(self):
            self.created += 1
        def __getattr__(self, name):
            raise AssertionError('DPG used before main context: ' + name)
    dpg = NoEarlyDPG()
    class Environment(dict):
        def __missing__(self, key):
            import builtins
            if hasattr(builtins, key):
                return getattr(builtins, key)
            value = MagicMock(name=key)
            self[key] = value
            return value
    app_path = driver.ROOT / 'src/core/app.py'
    env = Environment(__builtins__=__builtins__, __file__=str(app_path), os=os, sys=sys,
        csv=__import__('csv'), logging=logging, threading=threading, time=__import__('time'),
        Decimal=Decimal, InvalidOperation=InvalidOperation, dpg=dpg,
        ConfigManager=config_module.ConfigManager,
        _acceptance_runtime=SimpleNamespace(configure_logging=lambda: None,
            config_factory=driver.generated_configs(generated), error_log_file=str(generated / 'limiter.log')))
    popup_path = driver.ROOT / 'src/core/launch_popup.py'
    popup_env = dict(configparser=configparser, os=os, sys=sys, _loading_popup_active=False)
    popup_functions = [n for n in ast.parse(popup_path.read_text()).body if isinstance(n, ast.FunctionDef)]
    exec(compile(ast.Module(body=popup_functions, type_ignores=[]), str(popup_path), 'exec'), popup_env)
    env.update({name: popup_env[name] for name in ('show_loading_popup', 'hide_loading_popup', 'show_rtss_error_and_exit')})
    startup = []
    for node in ast.parse(app_path.read_text()).body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        startup.append(node)
        if isinstance(node, ast.Expr) and ast.unparse(node) == 'dpg.create_context()':
            break
    exec(compile(ast.Module(body=startup, type_ignores=[]), str(app_path), 'exec'), env)
    assert dpg.created == 1
    assert env['Base_dir'] == str(app_path.parent)
    # Exercise subsequent generated-config startup reads too.
    env['_acceptance_runtime'].config_factory(MagicMock(), dpg, MagicMock(), None, MagicMock(), str(app_path.parent))
    assert {p.name for p in reads} == {'settings.ini', 'profiles.ini'}


def test_actual_driver_twenty_stop_start_restarts_keep_replacement_running(tmp_path, monkeypatch):
    from test_app_session import load_app
    from acceptance_windows import Runtime
    import threading
    import time
    from types import SimpleNamespace
    monkeypatch.setattr('acceptance_windows.generated_configs', lambda directory: None)
    monkeypatch.setattr('acceptance_windows.focus_game', lambda pid: None)
    ns, _, _, _ = load_app()
    ns['running'] = False
    ns['threading'] = threading
    ns['time'] = SimpleNamespace(time=time.time, sleep=lambda seconds: time.sleep(.002))
    ns['fps_utils'].current_stepped_limits = lambda: [30,45,60]
    ns['fps_utils'].evaluate_cap_change = lambda *args: (False,False)
    ns['cm'].load_profile_callback = lambda *args: None
    ns['gui_queue'] = SimpleNamespace(_on_error=lambda *args: None)
    ns['rtss_manager'].get_fps_for_active_window = lambda: (60, 'pythonw.exe')
    cap = [60]
    ns['rtss'].set_fractional_framerate = lambda profile, value: cap.__setitem__(0, value)
    ns['rtss'].set_fractional_fps_direct = ns['rtss'].set_fractional_framerate
    ns['rtss'].get_framerate_limit = lambda *args: cap[0]
    runtime = Runtime(tmp_path, 1)
    ns['_acceptance_runtime'] = runtime
    runtime.initialized(ns)
    deadline = time.monotonic() + 5
    try:
        while runtime.stage != 'warm' and time.monotonic() < deadline:
            if runtime.stage == 'quiet' and len(runtime.samples) > runtime.current_sample_start:
                runtime.due = 0
            runtime.frame(ns)
            time.sleep(.002)
        assert runtime.stage == 'warm'
        assert runtime.evidence['cycles'] == 20
        assert runtime.evidence['restart_overlaps'] == 20
        assert runtime.evidence['retired_quiet'] is True
        assert ns['running'] and runtime.current_workers[0].is_alive()
        assert not runtime.errors
    finally:
        runtime.release_barriers()
        if ns['running']:
            runtime.callback(ns)
        for thread in runtime.retired + list(runtime.current_workers):
            if thread:
                thread.join(1)


@pytest.mark.parametrize('profile,ladder,cap', [
    ('Global', [30,45,60], 90), ('Global', [30,45,60], 15),
    ('Global', [30,45,60], 40), ('pythonw.exe', [24,36,48], 60),
    ('pythonw.exe', [24,36,48], 12), ('pythonw.exe', [24,36,48], 30)])
def test_both_profile_bounds_and_ladders_reject_each_invalid_direction(profile, ladder, cap):
    from acceptance_support import profile_bounds_valid
    assert not profile_bounds_valid(dict(profile=profile, new_cap=cap), (profile, ladder))
    assert profile_bounds_valid(dict(profile=profile, new_cap=ladder[0]), (profile, ladder))
    assert profile_bounds_valid(dict(profile=profile, new_cap=ladder[-1]), (profile, ladder))
    assert not profile_bounds_valid(dict(profile=profile, new_cap=ladder[0]), None)


def test_actual_finish_confirmation_window_cuts_at_baseline_and_transition(tmp_path, monkeypatch):
    from acceptance_windows import Runtime
    from types import SimpleNamespace
    monkeypatch.setattr('acceptance_windows.generated_configs', lambda directory: None)
    runtime = Runtime(tmp_path, 1)
    runtime.models = {1: ('pythonw.exe', [24,36,48])}
    runtime.rows = [dict(time='4', session_number=1, profile='pythonw.exe', new_cap=48, reason='controlled_baseline'),
                    dict(time='5.1', session_number=1, profile='pythonw.exe', new_cap=24, reason='decrease')]
    runtime.revisions = {'4': 1, '5.1': 1}
    runtime.decisions = [(3., (True,False), 1,1), (4., (True,False), 1,1), (5., (True,False), 1,1)]
    runtime.transitions = {(1,1): 2.}
    app = dict(running=True, exit_gui=lambda: None, rtss=SimpleNamespace(get_framerate_limit=lambda *a: 48))
    runtime.finish(app)
    assert runtime.evidence['drop_delay'] is False
    runtime.rows = runtime.rows[1:]
    runtime.transitions = {(1,1): 4.}
    runtime.finish(app)
    assert runtime.evidence['drop_delay'] is False
