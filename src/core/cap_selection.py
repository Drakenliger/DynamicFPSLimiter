"""Pure cap-ladder validation and legacy decrease selection."""

from __future__ import annotations

from decimal import Decimal
from typing import Iterable, Sequence


ExactCapValue = int | Decimal


def _as_finite_decimal(value: ExactCapValue, *, label: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, Decimal)):
        raise TypeError(f"{label} must be an exact int or Decimal")

    converted = Decimal(value)
    if not converted.is_finite():
        raise ValueError(f"{label} must be finite")
    return converted


def validate_cap_ladder(
    values: Iterable[ExactCapValue],
    *,
    lower_bound: ExactCapValue,
    upper_bound: ExactCapValue,
) -> tuple[Decimal, ...]:
    """Validate an ascending cap ladder without applying it to runtime state."""

    lower = _as_finite_decimal(lower_bound, label="lower_bound")
    upper = _as_finite_decimal(upper_bound, label="upper_bound")
    if lower > upper:
        raise ValueError("lower_bound must not exceed upper_bound")

    ladder = tuple(
        _as_finite_decimal(value, label=f"values[{index}]")
        for index, value in enumerate(values)
    )
    if not ladder:
        raise ValueError("cap ladder must not be empty")

    for index, value in enumerate(ladder):
        if value < lower or value > upper:
            raise ValueError(
                f"values[{index}] must be between lower_bound and upper_bound"
            )
        if index and value <= ladder[index - 1]:
            if value == ladder[index - 1]:
                raise ValueError("cap ladder must not contain duplicates")
            raise ValueError("cap ladder must be strictly ascending")

    return ladder


def select_legacy_decrease_cap(
    cap_ladder: Sequence[ExactCapValue],
    current_cap: ExactCapValue,
    measured_fps: ExactCapValue,
    decrease_requested: bool,
) -> ExactCapValue | None:
    """Reproduce the reviewed decrease choice, including CTRL-001.

    This intentionally leaves the normal one-step decrease unreachable when the
    current cap is present in the ladder and is at or below measured FPS.
    """

    if not decrease_requested or not cap_ladder:
        return None
    if current_cap == min(cap_ladder):
        return None

    try:
        lower_values = [value for value in cap_ladder if value < measured_fps]
        if lower_values:
            if current_cap <= measured_fps:
                current_index = cap_ladder.index(current_cap)
                if current_index < 0:
                    return cap_ladder[current_index - 1]
            else:
                return max(lower_values)
    except ValueError:
        lower_values = [value for value in cap_ladder if value < current_cap]
        if lower_values:
            return max(lower_values)

    return None
