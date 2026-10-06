"""Portable Legacy confirmation evidence and numeric compatibility checks."""
from itertools import product

import pytest

from core.cap_policy import evaluate_legacy_cap_change


def evaluate(gpu, cpu, drop=2, rise=2):
    return evaluate_legacy_cap_change(gpu, cpu, drop, rise, 90, 90, 70, 70)


@pytest.mark.parametrize('channel', ['gpu', 'cpu'])
@pytest.mark.parametrize('drop,rise', [(2, 4), (4, 2)])
@pytest.mark.parametrize('position', range(4))
@pytest.mark.parametrize('other', [0, 95])
def test_none_in_either_relevant_window_is_neutral(channel, drop, rise, position, other):
    incomplete = [0] * 4
    incomplete[position] = None
    gpu, cpu = (incomplete, [other] * 4) if channel == 'gpu' else ([other] * 4, incomplete)
    assert evaluate(gpu, cpu, drop, rise) == (False, False)


@pytest.mark.parametrize('drop,rise', [(2, 3), (3, 2)])
@pytest.mark.parametrize('gpu,cpu,expected', [
    (0, 0, (False, True)), (95, 0, (True, False)),
    (0, 95, (True, False)), (80, 80, (False, False)),
])
def test_none_older_than_both_windows_does_not_block(drop, rise, gpu, cpu, expected):
    length = max(drop, rise)
    assert evaluate([None] + [gpu] * length, [None] + [cpu] * length, drop, rise) == expected


def test_complete_numeric_histories_preserve_original_policy_including_zero():
    histories = [list(values) for length in range(4)
                 for values in product((0, 70, 80, 90, 95), repeat=length)]
    for gpu, cpu in product(histories, repeat=2):
        for drop, rise in ((1, 2), (2, 1), (2, 3), (3, 2)):
            expected = (
                (len(gpu) >= drop and all(v >= 90 for v in gpu[-drop:]))
                or (len(cpu) >= drop and all(v >= 90 for v in cpu[-drop:])),
                (len(gpu) >= rise and all(v <= 70 for v in gpu[-rise:]))
                and (len(cpu) >= rise and all(v <= 70 for v in cpu[-rise:])),
            )
            assert evaluate(gpu, cpu, drop, rise) == expected
