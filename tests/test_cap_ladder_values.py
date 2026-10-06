"""Independent cap ladder and custom parser value tests.

Verifies make_stepped_values, make_ratioed_values, and
parse_and_normalize_string_to_decimal_set against hard-coded expected outputs
rather than self-comparison against helper methods.
"""
import sys
import types
from decimal import Decimal
from types import SimpleNamespace

try:
    import clr
except ImportError:
    sys.modules["clr"] = types.ModuleType("clr")

try:
    import numpy
except ImportError:
    fake_np = types.ModuleType("numpy")
    fake_np.isscalar = lambda x: isinstance(x, (int, float, complex))
    sys.modules["numpy"] = fake_np


def test_parse_and_normalize_string_to_decimal_set_unique_sorted():
    from core.config_manager import ConfigManager

    cm = ConfigManager.__new__(ConfigManager)
    cm.logger = SimpleNamespace(add_log=lambda msg: None)

    result = cm.parse_and_normalize_string_to_decimal_set("30, 45.5, 30")
    assert result == [Decimal("30.0"), Decimal("45.5")]


def test_make_stepped_values_independent_expected():
    from core.fps_utils import FPSUtils

    fu = FPSUtils.__new__(FPSUtils)

    # Evenly dividing step
    assert fu.make_stepped_values(100, 40, 10) == [40, 50, 60, 70, 80, 90, 100]

    # Non-evenly dividing step (100 to 45 by step 10 -> includes 45)
    assert fu.make_stepped_values(100, 45, 10) == [45, 50, 60, 70, 80, 90, 100]


def test_make_ratioed_values_independent_expected():
    from core.fps_utils import FPSUtils

    fu = FPSUtils.__new__(FPSUtils)

    # Ratio ladder (100 to 40 by ratio 10%)
    assert fu.make_ratioed_values(100, 40, 10) == [40, 43, 48, 53, 59, 66, 73, 81, 90, 100]
