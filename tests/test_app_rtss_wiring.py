"""Execute the actual app constructor assignment without native DLL imports."""
import ast
from pathlib import Path
from core.ui_scale import ScaledDPG


def assert_app_rtss_wiring():
    tree = ast.parse((Path(__file__).resolve().parents[1] / 'src/core/app.py').read_text())
    assignment = next(n for n in tree.body if isinstance(n, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == 'rtss' for t in n.targets))
    raw = object()
    dpg = ScaledDPG(raw, 2)
    logger = object()
    calls = []
    sentinel = object()
    controller = object()
    def construct(actual_logger, *, error_handler):
        assert actual_logger is logger
        error_handler(sentinel)
        return controller
    ns = dict(RTSSController=construct, logger=logger, dpg=dpg,
              show_rtss_error_and_exit=lambda path, *, dpg: calls.append((path, dpg)))
    exec(compile(ast.Module(body=[assignment], type_ignores=[]), 'app.py', 'exec'), ns)
    assert calls == [(sentinel, dpg)]
    assert calls[0][1].raw is raw
    assert ns['rtss'] is controller


def test_app_injects_scaled_rtss_error_handler():
    assert_app_rtss_wiring()
