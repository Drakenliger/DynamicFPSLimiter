"""Independent cap ladder and custom parser value tests.

Verifies make_stepped_values, make_ratioed_values, and
parse_and_normalize_string_to_decimal_set against hard-coded expected outputs
rather than self-comparison against helper methods.
"""
import ast
from decimal import Decimal, InvalidOperation
from pathlib import Path
from types import SimpleNamespace


def _get_parse_and_normalize_func():
    try:
        from core.config_manager import ConfigManager

        return ConfigManager.parse_and_normalize_string_to_decimal_set
    except ImportError:
        src = Path(__file__).resolve().parent.parent / "src" / "core" / "config_manager.py"
        tree = ast.parse(src.read_text(encoding="utf-8"))
        method_node = next(
            n
            for n in ast.walk(tree)
            if isinstance(n, ast.FunctionDef) and n.name == "parse_and_normalize_string_to_decimal_set"
        )
        mod = ast.Module(body=[method_node], type_ignores=[])
        ns = {"Decimal": Decimal, "InvalidOperation": InvalidOperation}
        exec(compile(mod, filename=str(src), mode="exec"), ns)
        return ns["parse_and_normalize_string_to_decimal_set"]


def _get_fps_utils_methods():
    try:
        from core.fps_utils import FPSUtils

        return FPSUtils.make_stepped_values, FPSUtils.make_ratioed_values
    except ImportError:
        src = Path(__file__).resolve().parent.parent / "src" / "core" / "fps_utils.py"
        tree = ast.parse(src.read_text(encoding="utf-8"))
        nodes = [
            n
            for n in ast.walk(tree)
            if isinstance(n, ast.FunctionDef) and n.name in ("make_stepped_values", "make_ratioed_values")
        ]
        mod = ast.Module(body=nodes, type_ignores=[])
        ns = {}
        exec(compile(mod, filename=str(src), mode="exec"), ns)
        return ns["make_stepped_values"], ns["make_ratioed_values"]


def test_parse_and_normalize_string_to_decimal_set_unique_sorted():
    parse_func = _get_parse_and_normalize_func()
    cm = SimpleNamespace(logger=SimpleNamespace(add_log=lambda msg: None))

    result = parse_func(cm, "30, 45.5, 30")
    assert result == [Decimal("30.0"), Decimal("45.5")]
    # Assert exact string representations and exponents independently to catch quantization mutations
    assert [str(d) for d in result] == ["30.0", "45.5"]
    assert [d.as_tuple().exponent for d in result] == [-1, -1]


def test_make_stepped_values_independent_expected():
    make_stepped_values, _ = _get_fps_utils_methods()

    # Evenly dividing step
    assert make_stepped_values(None, 100, 40, 10) == [40, 50, 60, 70, 80, 90, 100]

    # Non-evenly dividing step (100 to 45 by step 10 -> includes 45)
    assert make_stepped_values(None, 100, 45, 10) == [45, 50, 60, 70, 80, 90, 100]


def test_make_ratioed_values_independent_expected():
    _, make_ratioed_values = _get_fps_utils_methods()

    # Ratio ladder (100 to 40 by ratio 10%)
    assert make_ratioed_values(None, 100, 40, 10) == [40, 43, 48, 53, 59, 66, 73, 81, 90, 100]
