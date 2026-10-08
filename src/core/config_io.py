"""DFL INI parsing and missing-default merging, without GUI/native imports."""
import configparser
import locale
import os
import tempfile
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


def write_config(config, path):
    """Write ConfigParser object atomically to path using a temporary file and os.replace."""
    target_path = Path(path)
    target_dir = target_path.parent
    if not target_dir.exists():
        target_dir.mkdir(parents=True, exist_ok=True)

    tmp_file = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=target_dir,
        prefix=f".{target_path.name}.",
        suffix=".tmp",
        delete=False,
    )
    tmp_path = Path(tmp_file.name)
    try:
        try:
            config.write(tmp_file)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())
        finally:
            tmp_file.close()
        os.replace(tmp_path, target_path)
    except BaseException:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError:
            pass
        raise
