"""T3: Tests for idle write once, disabled idle mode, and activity restoration."""
from decimal import Decimal
from types import SimpleNamespace as NS

from test_app_session import load_app
from test_librehm_policy import run_passes


def test_consecutive_idle_passes_write_idle_cap_once():
    ns, writes, _, _ = load_app()
    rows = []
    ns['cap_change_log'] = NS(record=rows.append, close=lambda: None)
    ns['cm'].idle_mode = True
    ns['cm'].idle_fps_cap = 20
    ns['monitor_idle'] = lambda _: True

    run_passes(ns, writes, [(False, False)] * 5, samples=[(Decimal(95), 'game')] * 5)

    assert len(writes) == 1
    assert writes[0][1] == ('Global', 20)
    assert len(rows) == 1
    assert rows[0][4] == '20'
    assert rows[0][5] == 'idle'
    assert ns['idle_state'] is True


def test_idle_mode_disabled_never_enters_idle():
    ns, writes, _, _ = load_app()
    rows = []
    ns['cap_change_log'] = NS(record=rows.append, close=lambda: None)
    ns['cm'].idle_mode = False
    ns['cm'].idle_fps_cap = 20
    ns['monitor_idle'] = lambda _: True

    run_passes(ns, writes, [(False, False)] * 3, samples=[(Decimal(95), 'game')] * 3)

    assert len(writes) == 0
    assert len(rows) == 0
    assert ns['idle_state'] is False


def test_restoring_activity_writes_cached_cap_once():
    ns, writes, _, _ = load_app()
    rows = []
    ns['cap_change_log'] = NS(record=rows.append, close=lambda: None)
    ns['cm'].idle_mode = True
    ns['cm'].idle_fps_cap = 20
    ns['CurrentFPSOffset'] = -30

    idle_flags = [True, True, False, False, False]
    idle_iter = iter(idle_flags)
    ns['monitor_idle'] = lambda _: next(idle_iter)

    run_passes(ns, writes, [(False, False)] * 5, samples=[(Decimal(95), 'game')] * 5)

    assert len(writes) == 2
    assert writes[0][1] == ('Global', 20)
    assert writes[1][1] == ('Global', Decimal(60))
    assert len(rows) == 2
    assert rows[0][5] == 'idle'
    assert rows[1][5] == 'idle_restore'
    assert rows[1][4] == '60'
    assert ns['idle_state'] is False
