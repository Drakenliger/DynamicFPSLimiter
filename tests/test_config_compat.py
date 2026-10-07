"""Portable DFL INI compatibility tests; all paths are temporary."""
import runpy
import sys
import types
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

from core.config_io import new_config, read_config, merge_defaults
from core.pre_launch import _is_first_launch
from core.ui_scale import read_preference


@pytest.fixture
def manager(tmp_path, monkeypatch, fake_dpg, stub_logger):
    hardware = types.ModuleType('core.librehardwaremonitor')
    hardware.get_all_sensor_infos = lambda *a: []
    monkeypatch.setitem(sys.modules, 'core.librehardwaremonitor', hardware)
    cls = runpy.run_path(str(Path(__file__).parents[1] / 'src/core/config_manager.py'))['ConfigManager']
    def create():
        return cls(stub_logger, fake_dpg, NS(set_profile_property=lambda *a, **k: True),
                   None, NS(themes={}), str(tmp_path / 'core'))
    return create


@pytest.mark.parametrize('settings', [
    '[Preferences]\nshowtooltip=False\n',
    '[GlobalSettings]\nminvalidfps=27\n',
    '[Unknown]\nvalue=keep100%\n',
])
@pytest.mark.parametrize('profiles', [
    '[Other]\nmaxcap=73\nunknown=keep%\n',
    '[Global]\nmaxcap=61\nunknown=keep%\n[Other]\nunknown=keep%\n',
])
def test_legacy_missing_defaults_are_in_memory(manager, tmp_path, settings, profiles):
    directory = tmp_path / 'config'
    directory.mkdir()
    settings_path = directory / 'settings.ini'
    profiles_path = directory / 'profiles.ini'
    settings_path.write_text(settings, encoding='utf-8')
    profiles_path.write_text(profiles, encoding='utf-8')
    before = (settings_path.read_bytes(), profiles_path.read_bytes())
    cm = manager()
    assert cm.autopilot is False and cm.hide_loading_popup is False
    assert cm.first_launch_done is False and cm.ui_scale == 'Auto'
    assert cm.showtooltip is ('showtooltip=False' not in settings)
    assert cm.Default_settings['minvalidfps'] == (27 if 'minvalidfps=27' in settings else 14)
    assert cm.Default_settings['cpucutoffforincrease'] == 101
    assert cm.Default_settings['cpucutofffordecrease'] == 105
    assert cm.profiles_config['Global']['maxcap'] == ('61' if 'maxcap=61' in profiles else '114')
    for key in cm.settings_config['Preferences']:
        assert hasattr(cm, key)
    assert cm.profiles_config['Other']['unknown'] == 'keep%'
    assert before == (settings_path.read_bytes(), profiles_path.read_bytes())


def test_merge_preserves_values_and_unknowns():
    cfg = new_config()
    cfg.read_string('[Global]\nmaxcap=55\nunknown=100%\n[Extra]\nname=雪\n')
    merge_defaults(cfg, {'Global': {'maxcap': 114, 'mincap': 40}, 'Preferences': {'ui_scale': 'Auto'}})
    assert dict(cfg['Global']) == {'maxcap': '55', 'unknown': '100%', 'mincap': '40'}
    assert cfg['Extra']['name'] == '雪'
    assert cfg['Preferences']['ui_scale'] == 'Auto'


def test_locale_fallback_and_all_startup_readers(manager, tmp_path, monkeypatch):
    monkeypatch.setattr('core.config_io.locale.getencoding', lambda: 'cp1252')
    directory = tmp_path / 'config'
    directory.mkdir()
    settings = directory / 'settings.ini'
    settings.write_bytes(('[Preferences]\nui_scale=150%%\nfirst_launch_done=True\n'
                          'hide_loading_popup=True\nunknown=café100%\n'
                          '[GlobalSettings]\nprofileonstartup_name=Game100%.exe\n').encode('cp1252'))
    (directory / 'profiles.ini').write_bytes('[Game100%.exe]\nunknown=café%\n'.encode('cp1252'))
    cm = manager()
    assert cm.Default_settings['profileonstartup_name'] == 'Game100%.exe'
    assert cm.settings_config['Preferences']['unknown'] == 'café100%'
    assert cm.profiles_config['Game100%.exe']['unknown'] == 'café%'
    assert read_preference(settings) == cm.ui_scale == '150%'
    assert _is_first_launch(tmp_path) is False
    # Execute the real popup reader; hidden popup must return before context use.
    import ast
    popup = Path(__file__).parents[1] / 'src/core/launch_popup.py'
    tree = ast.parse(popup.read_text())
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'show_loading_popup')
    ns = {'os': __import__('os'), 'new_config': new_config, 'read_config': read_config,
          '_scaled_popup_dpg': lambda dpg: dpg}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(popup), 'exec'), ns)
    class NoContext:
        def create_context(self):
            pytest.fail('legacy hidden popup created a context')
    ns['show_loading_popup'](Base_dir=str(tmp_path / 'core'), dpg=NoContext())
    cm.update_preference_setting('unknown', None, '雪100%', None)
    assert '雪100%'.encode('utf-8') in settings.read_bytes()
    assert manager().settings_config['Preferences']['unknown'] == '雪100%'


def test_unicode_percent_survive_every_save_path(manager, tmp_path, fake_dpg):
    cm = manager()
    name = '雪100%.exe'
    cm.settings_config['Unknown'] = {'value': '雪100%'}
    cm.settings_config['Preferences']['unknown'] = '雪100%'
    cm.profiles_config['Unknown'] = {'value': '雪100%'}
    for key in cm.input_field_keys:
        fake_dpg.set_value('input_' + key, cm.Default_settings_original[key])
    cm.save_profile(name)
    cm.profiles_config[name]['unknown'] = '雪100%'
    fake_dpg.set_value('profile_dropdown', name)
    cm.save_to_profile()
    cm.select_default_profile_callback(None, None, None)
    cm.update_GlobalSettings_settings('minvalidfps', None, 25, None)
    cm.update_preference_setting('showtooltip', None, False, None)
    cm.update_ui_scale_preference(None, '150%')
    restarted = manager()
    assert restarted.Default_settings['profileonstartup_name'] == name
    assert restarted.ui_scale == read_preference(cm.settings_path) == '150%'
    assert restarted.settings_config['Unknown']['value'] == '雪100%'
    assert restarted.settings_config['Preferences']['unknown'] == '雪100%'
    assert restarted.profiles_config['Unknown']['value'] == '雪100%'
    assert name in restarted.profiles_config
    assert restarted.profiles_config[name]['unknown'] == '雪100%'
    for path in (cm.settings_path, cm.profiles_path):
        assert '雪100%'.encode('utf-8') in Path(path).read_bytes()
    cm.current_profile = 'Global'
    cm.delete_selected_profile_callback()
    deleted = manager()
    assert name not in deleted.profiles_config
    assert deleted.profiles_config['Unknown']['value'] == '雪100%'
    assert deleted.settings_config['Unknown']['value'] == '雪100%'


def test_utf8_first_and_no_parse_on_decode_failure(tmp_path, monkeypatch):
    path = tmp_path / 'settings.ini'
    path.write_text('[Extra]\nvalue=雪100%\n', encoding='utf-8')
    def unexpected_locale():
        pytest.fail('UTF-8 input invoked legacy fallback')
    monkeypatch.setattr('core.config_io.locale.getencoding', unexpected_locale)
    cfg = new_config()
    read_config(cfg, path)
    assert cfg['Extra']['value'] == '雪100%'
    monkeypatch.setattr('core.config_io.locale.getencoding', lambda: 'ascii')
    path.write_bytes(b'[Partial]\nvalue=ok\n[Bad]\nvalue=\xff\n')
    with pytest.raises(UnicodeDecodeError):
        read_config(cfg, path)
    assert cfg.sections() == ['Extra']


@pytest.mark.parametrize('explicit', [None, '39'])
@pytest.mark.parametrize('key,value,expected', [
    ('minvalidfps', '27', 27),
    ('idle_fps_cap', '29', 29),
    ('profileonstartup_name', 'Game100%.exe', 'Game100%.exe'),
])
def test_defaults_preserve_legacy_global_setting(manager, tmp_path, key, value, expected, explicit):
    directory = tmp_path / 'config'
    directory.mkdir()
    settings = directory / 'settings.ini'
    profiles = directory / 'profiles.ini'
    text = '[Preferences]\nshowtooltip=True\n[GlobalSettings]\n'
    if explicit is not None:
        text += key + '=' + explicit + '\n'
    settings.write_text(text, encoding='utf-8')
    profiles.write_text('[Global]\n' + key + '=' + value + '\n', encoding='utf-8')
    before = (settings.read_bytes(), profiles.read_bytes())
    cm = manager()
    wanted = cm.key_type_map[key](explicit) if explicit is not None else expected
    assert cm.Default_settings[key] == wanted
    assert cm.profiles_config['Global'][key] == value
    assert before == (settings.read_bytes(), profiles.read_bytes())


@pytest.mark.parametrize('stored_name,profile_names,enabled,expected', [
    ('Game100%%.exe', ['Game100%.exe'], True, 'Game100%.exe'),
    ('Game%%100%%.exe', ['Game%100%.exe'], True, 'Game%100%.exe'),
    ('Game100%%.exe', ['Game100%%.exe', 'Game100%.exe'], True, 'Game100%%.exe'),
    ('Game100%%.exe', ['Game100%%.exe'], True, 'Game100%%.exe'),
    ('Game100%.exe', ['Game100%.exe'], True, 'Game100%.exe'),
    ('Game100%%%%.exe', ['Game100%%.exe'], True, 'Game100%%.exe'),
    ('Game100%%%%.exe', ['Game100%.exe'], True, 'Global'),
    ('Game100%%.exe', ['Other.exe'], True, 'Global'),
    ('Missing.exe', ['Other.exe'], True, 'Global'),
    ('Game100%%.exe', ['game100%.exe'], True, 'Global'),
    ('Game100%%.exe', ['Game100%.exe'], False, None),
    ('Game100%%.exe', ['Game100%%.exe', 'Game100%.exe'], False, None),
    ('Missing.exe', ['Other.exe'], False, None),
])
def test_actual_startup_selection_legacy_percent(
        manager, tmp_path, stub_logger, stored_name, profile_names, enabled, expected):
    """Run the real ConfigManager startup method against on-disk legacy INIs.

    The manager fixture uses runpy and a restored monkeypatch for sensors;
    only the downstream loading callback is replaced to record selection.
    """
    directory = tmp_path / 'config'
    directory.mkdir()
    settings = directory / 'settings.ini'
    profiles = directory / 'profiles.ini'
    settings.write_text(
        f'[Preferences]\nprofileonstartup={enabled}\nunknown=keep%%\n'
        f'[GlobalSettings]\nprofileonstartup_name={stored_name}\n', encoding='utf-8')
    profiles.write_text(
        '[Global]\nmaxcap=60\n' + ''.join(
            f'[{name}]\nmaxcap=48\nunknown=keep%%\n' for name in profile_names),
        encoding='utf-8')
    before = (settings.read_bytes(), profiles.read_bytes())
    cm = manager()
    selected = []
    cm.load_profile_callback = lambda sender, profile, data: selected.append(profile)

    cm.startup_profile_selection()

    assert selected == ([] if expected is None else [expected])
    assert cm.settings_config['GlobalSettings']['profileonstartup_name'] == stored_name
    assert cm.settings_config['Preferences']['unknown'] == 'keep%%'
    assert cm.profiles_config.sections() == ['Global', *profile_names]
    for name in profile_names:
        assert cm.profiles_config[name]['unknown'] == 'keep%%'
    assert before == (settings.read_bytes(), profiles.read_bytes())
    fallback_message = f"Profile '{stored_name}' not found. Defaulting to 'Global'."
    assert (fallback_message in stub_logger.messages) is (expected == 'Global')
