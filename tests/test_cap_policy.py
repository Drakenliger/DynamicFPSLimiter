"""F1 regression tests: cap step-down policy (src/core/cap_policy.py).

The original code in app.monitoring_loop had a dead
``if current_index < 0:`` branch (``list.index`` raises instead of
returning negative), so the intended one-rung step-down never executed.
The policy was extracted to ``cap_policy.next_cap_on_decrease`` and is
tested here purely — no DPG, no RTSS, no .NET.
"""
from decimal import Decimal
from pathlib import Path

import pytest

from core.cap_policy import next_cap_on_decrease

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"

LADDER = [30, 45, 60, 75, 90]


@pytest.mark.parametrize(
    ("ladder", "current_cap", "fps_mean", "expected"),
    [
        # empty ladder
        ([], 60, 50, None),
        # in ladder at the lowest rung: already at floor
        (LADDER, 30, 25, None),
        (LADDER, 30, 90, None),
        # in ladder mid-range, cap <= fps_mean: step down exactly one rung
        (LADDER, 90, 95, 75),
        (LADDER, 75, 80, 60),
        (LADDER, 60, 60, 45),  # cap == fps_mean boundary
        (LADDER, 45, 45.5, 30),
        # in ladder, cap > fps_mean: jump to highest rung below fps_mean
        (LADDER, 90, 60, 45),
        (LADDER, 75, 30, None),  # nothing below fps_mean
        # not in ladder: highest rung below current cap
        (LADDER, 80, 95, 75),
        (LADDER, 50, 95, 45),
        (LADDER, 25, 95, None),  # below the whole ladder
        # unsorted custom ladder still behaves by membership/order
        ([60, 30, 90], 90, 95, 30),  # rung before 90 in user order
        ([60, 30, 90], 20, 95, None),
    ],
)
def test_next_cap_on_decrease(ladder, current_cap, fps_mean, expected):
    assert next_cap_on_decrease(ladder, current_cap, fps_mean) == expected


def test_app_wired_to_policy_and_dead_check_removed():
    """Guard the integration point: app's decrease branch must call the
    policy and must not contain the dead ``current_index < 0`` check."""
    src = (SRC_DIR / "core" / "app.py").read_text(encoding="utf-8")
    assert "from core.cap_policy import next_cap_on_decrease" in src
    assert "next_cap_on_decrease(fps_limit_list, current_fps_cap, fps_mean)" in src
    assert "current_index < 0" not in src


@pytest.mark.parametrize(
    ('limits', 'expected_padding'),
    [
        ([30, 60, 90], Decimal('6')),
        (['12.5', '24.5', '36.5'], Decimal('2')),
        ([144], Decimal('1')),
    ]
)
def test_cap_model_snapshot(limits, expected_padding):
    from decimal import Decimal
    from core.cap_policy import build_cap_model
    values = [Decimal(x) for x in limits]
    model = build_cap_model(values)
    values.clear()
    ladder, minimum, maximum, lower, upper = model
    assert ladder == tuple(Decimal(x) for x in limits)
    assert minimum == min(ladder)
    assert maximum == max(ladder)
    assert (lower, upper) == (minimum - expected_padding, maximum + expected_padding)


@pytest.mark.parametrize(
    ('limits', 'expected_bounds'),
    [
        (['59.94', 60], (Decimal('59.94'), Decimal('60'))),
        ([59, 60], (Decimal('59'), Decimal('60'))),
    ]
)
def test_narrow_multi_rung_bounds_unchanged(limits, expected_bounds):
    from decimal import Decimal
    from core.cap_policy import build_cap_model

    values = [Decimal(x) for x in limits]
    _, _, _, min_ft, max_ft = build_cap_model(values)
    assert (min_ft, max_ft) == expected_bounds


@pytest.mark.parametrize('single_rung', [60, '59.94'])
def test_equal_cap_plot_bounds_and_scaling(single_rung):
    from decimal import Decimal
    from core.cap_policy import build_cap_model

    rung = Decimal(single_rung)
    ladder, minimum, maximum, min_ft, max_ft = build_cap_model([rung])

    assert ladder == (rung,)
    assert minimum == rung
    assert maximum == rung

    assert min_ft < max_ft
    assert min_ft.is_finite() and max_ft.is_finite()

    current_maxcap = maximum
    CurrentFPSOffset = Decimal('0')
    test_fps_values = [rung - Decimal('0.5'), rung, rung + Decimal('0.5')]

    for fps in test_fps_values:
        scaled_fps = ((fps - min_ft) / (max_ft - min_ft)) * Decimal('100')
        scaled_cap = ((Decimal(current_maxcap) + Decimal(CurrentFPSOffset) - min_ft) / (max_ft - min_ft)) * Decimal('100')

        assert scaled_fps.is_finite()
        assert scaled_cap.is_finite()


def test_multi_rung_ordinary_bounds_unchanged():
    from decimal import Decimal
    from core.cap_policy import build_cap_model

    ladder, minimum, maximum, min_ft, max_ft = build_cap_model([30, 60, 90])
    assert ladder == (Decimal(30), Decimal(60), Decimal(90))
    assert (minimum, maximum) == (Decimal(30), Decimal(90))
    assert (min_ft, max_ft) == (Decimal(24), Decimal(96))
