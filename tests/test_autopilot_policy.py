from core.autopilot import canonical_profile, autopilot_decision


def test_exact_priority_and_unknown():
    profiles = ['Global', 'Game.exe', 'game.exe']
    assert canonical_profile('game.exe', profiles) == 'game.exe'
    assert canonical_profile('GAME.EXE', profiles) == 'Game.exe'
    for running in (False, True):
        for only in (False, True):
            assert autopilot_decision(None, profiles, 'Game.exe', running, only) is None
    assert autopilot_decision('game.exe', profiles, 'Game.exe', True, True) == ('stop', 'Game.exe')
    assert autopilot_decision('GAME.EXE', profiles, 'Game.exe', True, False) is None


def test_reserved_global_identity_and_missing_current():
    profiles = ['Global', 'global', 'GLOBAL', 'Game.exe', 'game.exe']
    for only in (False, True):
        for current in ('Global', 'global', 'GLOBAL'):
            assert autopilot_decision('game.exe', profiles, current, True, only) == ('select', 'game.exe')
            assert autopilot_decision('unmatched.exe', profiles, current, True, only) is None
    assert autopilot_decision('game.exe', profiles, None, True, True) is None
    assert autopilot_decision('game.exe', profiles, None, True, False) == ('select', 'Global')
