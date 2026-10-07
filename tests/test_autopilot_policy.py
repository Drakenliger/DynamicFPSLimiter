from types import SimpleNamespace as NS
from core.autopilot import canonical_profile, autopilot_decision, autopilot_request_current


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


def test_canonical_profile_edges():
    assert canonical_profile(None, ['Global']) is None
    assert canonical_profile('', ['Global']) is None
    profiles = ['GAME.EXE', 'Game.exe', 'game.exe', 'GLOBAL']
    assert canonical_profile('game.exe', profiles) == 'game.exe'
    assert canonical_profile('Game.exe', profiles) == 'Game.exe'
    assert canonical_profile('GAME.EXE', profiles) == 'GAME.EXE'
    assert canonical_profile('gAmE.eXe', profiles) == 'GAME.EXE'
    assert canonical_profile('global', profiles) == 'GLOBAL'
    assert canonical_profile('Global', profiles) == 'GLOBAL'
    assert canonical_profile('unknown.exe', profiles) is None


def test_autopilot_decision_stopped_matrix():
    profiles = ['Global', 'Game.exe']
    assert autopilot_decision(None, profiles, 'Global', running=False, only_profiles=False) is None
    assert autopilot_decision('', profiles, 'Global', running=False, only_profiles=False) is None
    assert autopilot_decision('game.exe', profiles, 'Global', running=False, only_profiles=True) == ('start', 'Game.exe')
    assert autopilot_decision('game.exe', profiles, 'Global', running=False, only_profiles=False) == ('start', 'Game.exe')
    assert autopilot_decision('other.exe', profiles, 'Global', running=False, only_profiles=True) is None
    assert autopilot_decision('other.exe', profiles, 'Global', running=False, only_profiles=False) == ('start', 'Global')
    aliased = ['GLOBAL', 'Game.exe']
    assert autopilot_decision('other.exe', aliased, 'GLOBAL', running=False, only_profiles=False) == ('start', 'GLOBAL')
    assert autopilot_decision('other.exe', ['Game.exe'], 'Game.exe', running=False, only_profiles=False) is None


def test_autopilot_decision_running_game_transitions():
    profiles = ['Global', 'GameA.exe', 'GameB.exe']
    assert autopilot_decision('gamea.exe', profiles, 'GameA.exe', running=True, only_profiles=False) is None
    assert autopilot_decision('gamea.exe', profiles, 'GameA.exe', running=True, only_profiles=True) is None
    assert autopilot_decision('desktop.exe', profiles, 'GameA.exe', running=True, only_profiles=True) == ('stop', 'GameA.exe')
    assert autopilot_decision('desktop.exe', profiles, 'GameA.exe', running=True, only_profiles=False) == ('select', 'Global')
    assert autopilot_decision('gameb.exe', profiles, 'GameA.exe', running=True, only_profiles=True) == ('stop', 'GameA.exe')
    assert autopilot_decision('gameb.exe', profiles, 'GameA.exe', running=True, only_profiles=False) == ('select', 'Global')
    aliased = ['GLOBAL', 'GameA.exe']
    assert autopilot_decision('desktop.exe', aliased, 'GameA.exe', running=True, only_profiles=False) == ('select', 'GLOBAL')
    no_global = ['GameA.exe', 'GameB.exe']
    assert autopilot_decision('desktop.exe', no_global, 'GameA.exe', running=True, only_profiles=False) is None


def test_autopilot_decision_running_global_alias_transitions():
    profiles = ['GLOBAL', 'Game.exe']
    assert autopilot_decision('desktop.exe', profiles, 'GLOBAL', running=True, only_profiles=False) is None
    assert autopilot_decision('desktop.exe', profiles, 'GLOBAL', running=True, only_profiles=True) is None
    assert autopilot_decision('global', profiles, 'GLOBAL', running=True, only_profiles=False) is None
    assert autopilot_decision('game.exe', profiles, 'GLOBAL', running=True, only_profiles=False) == ('select', 'Game.exe')
    assert autopilot_decision('game.exe', profiles, 'GLOBAL', running=True, only_profiles=True) == ('select', 'Game.exe')


def test_autopilot_request_current_admission():
    expected = (1, 2, True, False, 'Game.exe')
    def make_cm(autopilot=True, only=False, sections=None):
        return NS(
            autopilot=autopilot,
            autopilot_only_profiles=only,
            profiles_config=NS(sections=lambda: sections if sections is not None else ['Global', 'Game.exe']),
        )
    assert autopilot_request_current(expected, 1, 2, True, make_cm()) is True
    assert autopilot_request_current(expected, 2, 2, True, make_cm()) is False
    assert autopilot_request_current(expected, 1, 3, True, make_cm()) is False
    assert autopilot_request_current(expected, 1, 2, False, make_cm()) is False
    assert autopilot_request_current(expected, 1, 2, True, make_cm(autopilot=False)) is False
    assert autopilot_request_current(expected, 1, 2, True, make_cm(only=True)) is False
    assert autopilot_request_current(expected, 1, 2, True, make_cm(sections=['Global'])) is False

