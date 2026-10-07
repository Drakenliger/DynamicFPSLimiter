"""DFL INI parsing and missing-default merging, without GUI/native imports."""
import configparser
import locale
from pathlib import Path


def new_config():
    return configparser.ConfigParser(interpolation=None)


def read_config(config, path):
    """Decode the whole file before parsing; retain legacy Windows encodings."""
    try:
        data = Path(path).read_bytes()
    except FileNotFoundError:
        return
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = data.decode(locale.getencoding())
    config.read_string(text, source=str(path))


def merge_defaults(config, defaults):
    """Seed missing sections/keys in memory, preserving user and unknown values."""
    for section, values in defaults.items():
        if not config.has_section(section):
            config.add_section(section)
        for key, value in values.items():
            if key not in config[section]:
                config[section][key] = str(value)
