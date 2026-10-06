"""C3 regression tests: Framerate section cap key management.

Ensures Limit and LimitDenominator keys are updated or inserted within the
[Framerate] section, handles missing trailing newlines gracefully (no line gluing),
creates [Framerate] section if absent, and preserves unrelated content (e.g. [OSD]).
"""
from pathlib import Path


def _profile_file(rtss_stub, name="Global"):
    if name.lower() == "global":
        return Path(rtss_stub.rtss_install_path) / "Profiles" / "Global"
    return Path(rtss_stub.rtss_install_path) / "Profiles" / f"{name}.cfg"


def test_absent_framerate_section_appends_section_and_keys(rtss_stub):
    path = _profile_file(rtss_stub)
    path.write_text("[OSD]\nLabel=x\n", encoding="utf-8")

    assert rtss_stub.set_fractional_fps_direct("Global", 60, update=False) is True

    content = path.read_text(encoding="utf-8")
    expected = "[OSD]\nLabel=x\n[Framerate]\nLimit=60\nLimitDenominator=1\n"
    assert content == expected


def test_later_osd_section_preserves_osd_keys_and_updates_framerate_section(rtss_stub):
    path = _profile_file(rtss_stub)
    path.write_text("[OSD]\nLimit=99\nLabel=x\n[Framerate]\nLimit=30\nLimitDenominator=1\n", encoding="utf-8")

    assert rtss_stub.set_fractional_fps_direct("Global", 60, update=False) is True

    content = path.read_text(encoding="utf-8")
    assert "[OSD]\nLimit=99\nLabel=x\n" in content
    assert "[Framerate]\nLimit=60\nLimitDenominator=1\n" in content


def test_missing_trailing_newline_does_not_glue_keys(rtss_stub):
    path = _profile_file(rtss_stub)
    path.write_text("[OSD]\nLabel=x", encoding="utf-8")

    assert rtss_stub.set_fractional_fps_direct("Global", 60, update=False) is True

    content = path.read_text(encoding="utf-8")
    assert "Label=xLimit" not in content
    assert "Label=x[" not in content
    assert content == "[OSD]\nLabel=x\n[Framerate]\nLimit=60\nLimitDenominator=1\n"


def test_missing_one_key_in_framerate_section_inserts_missing_key(rtss_stub):
    path = _profile_file(rtss_stub)
    path.write_text("[Framerate]\nLimit=30\n[OSD]\nLabel=x\n", encoding="utf-8")

    assert rtss_stub.set_limit_denominator("Global", 100, update=False) is True

    content = path.read_text(encoding="utf-8")
    expected = "[Framerate]\nLimit=30\nLimitDenominator=100\n[OSD]\nLabel=x\n"
    assert content == expected


def test_existing_keys_in_framerate_section_updated_in_place(rtss_stub):
    path = _profile_file(rtss_stub)
    path.write_text("[Framerate]\nLimit=30\nLimitDenominator=1\n", encoding="utf-8")

    assert rtss_stub.set_fractional_fps_direct("Global", 59.94, update=False) is True

    content = path.read_text(encoding="utf-8")
    expected = "[Framerate]\nLimit=5994\nLimitDenominator=100\n"
    assert content == expected
