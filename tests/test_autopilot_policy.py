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
