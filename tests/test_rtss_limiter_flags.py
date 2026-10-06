import sys
import types

import pytest


@pytest.fixture
def limiter_controller(monkeypatch, request):
    if sys.platform != "win32":
        monkeypatch.setitem(sys.modules, "winreg", types.ModuleType("winreg"))
    return request.getfixturevalue("rtss_stub")


@pytest.mark.parametrize("initial_flags", [0, 4, 0x800000AB, 0x800000AF])
@pytest.mark.parametrize("operations", [
    ("disable", "disable"),
    ("enable", "enable"),
    ("disable", "enable"),
])
def test_limiter_flags_preserve_other_bits(limiter_controller, initial_flags, operations):
    flags = initial_flags
    updated_flags = []

    def set_flags(and_mask, xor_mask):
        nonlocal flags
        flags = (flags & and_mask) ^ xor_mask
        return flags

    def update_profiles():
        updated_flags.append(flags)

    limiter_controller.SetFlags = set_flags
    limiter_controller.UpdateProfiles = update_profiles
    other_flags = initial_flags & ~4

    for call_count, operation in enumerate(operations, start=1):
        getattr(limiter_controller, f"{operation}_limiter")()
        expected_flags = other_flags | (4 if operation == "disable" else 0)
        assert flags == expected_flags
        assert flags & 4 == (4 if operation == "disable" else 0)
        assert updated_flags == [
            other_flags | (4 if previous == "disable" else 0)
            for previous in operations[:call_count]
        ]
