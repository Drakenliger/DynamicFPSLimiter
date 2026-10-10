"""Actual-source equivalence and an intentionally red display-copy requirement.

Boundary stubs exercise Python behavior, not .NET/driver or GUI acceptance.
The benchmark imports these helpers; importing this file executes no checks.
"""
import builtins
from collections import defaultdict, deque
from contextlib import contextmanager
import importlib
from pathlib import Path
import subprocess
import threading
from types import ModuleType, SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
BASELINE = "c5aaa5115b92ec3e1349c340cf7c491ca6ded186"
HT = SimpleNamespace(Cpu="Cpu", GpuAmd="AMD", GpuNvidia="NVIDIA", GpuIntel="Intel")


def load_modules():
    source = subprocess.check_output(
        ["git", "show", f"{BASELINE}:src/core/librehardwaremonitor.py"],
        cwd=ROOT, text=True)
    baseline = ModuleType("lhm_display_copy_baseline")
    baseline.__file__ = str(ROOT / "src/core/librehardwaremonitor.py")
    exec(compile(source, f"{BASELINE}:librehardwaremonitor.py", "exec"), baseline.__dict__)
    return baseline, importlib.import_module("core.librehardwaremonitor")


def sensor(kind, name, value, identifier=None):
    return SimpleNamespace(SensorType=kind, Name=name, Value=value, Identifier=identifier)


class Hardware:
    def __init__(self, owner, name, kind):
        self.owner, self.Name, self.HardwareType = owner, name, kind
        self.Sensors = []

    def Update(self):
        m = self.owner
        held = m._lock.locked()
        m.updates.append((self.Name, held, threading.current_thread().name))
        assert held
        if m.fail == self.Name:
            raise RuntimeError("driver reset")


def make_monitor(module):
    m = object.__new__(module.LHMSensor)  # No assembly loading / native Computer.
    m._lock, m.updates, m.fail = threading.Lock(), [], None
    m.HardwareType, m.percentile, m.interval, m.max_samples = HT, 70, .1, 20
    m.CPU_SENSORS = m.GPU_SENSORS = dict.fromkeys(("Load", "Temperature", "Power"))
    for prefix, keys in (
        ("cpu", ("/cpu/shared", ("Temperature", "Package"))),
        ("gpu", ("/amd/a", "/amd/b", ("Temperature", "1 Hot"),
                 "/amd/p", "/nv/load", "/nv/power", "/intel/load")),
    ):
        for suffix, size in (("history", 20), ("history_long", 600)):
            history = defaultdict(lambda size=size: deque(maxlen=size))
            for key in keys:
                history[key] = deque((float(i % 100) for i in range(size)), maxlen=size)
            setattr(m, f"{prefix}_{suffix}", history)
        setattr(m, f"{prefix}_percentiles", defaultdict(float))
    # Intel is enumerated first, but must be emitted last.
    m.computer = SimpleNamespace(Hardware=[Hardware(m, "Intel GPU", HT.GpuIntel),
        Hardware(m, "CPU", HT.Cpu), Hardware(m, "AMD GPU", HT.GpuAmd),
        Hardware(m, "NVIDIA GPU", HT.GpuNvidia)])
    set_pass(m, 0)
    return m


def set_pass(m, tick, fail=None):
    m.fail = fail
    intel, cpu, amd, nv = m.computer.Hardware
    cpu.Sensors = [sensor("Load", "Core", 10.126 + tick, "/cpu/shared"),
        sensor("Load", "Core", 90.987 - tick, "/cpu/shared"),
        sensor("Temperature", "Package", 50.556 + tick),
        sensor("Power", "Package", None if tick == 0 else 25.333 + tick, "/cpu/none"),
        sensor("Clock", "Ignored", 123, "/ignored")]
    amd.Sensors = ([sensor("Load", "Core", 20.234, "/amd/a")] if tick == 0 else []) + [
        sensor("Load", "Core", 30.456 + tick, "/amd/b"),
        sensor("Temperature", "Hot", 40.678 + tick)] + ([
        sensor("Power", "Board", 60.123, "/amd/p")] if tick == 0 else [])
    nv.Sensors = [sensor("Load", "Core", 70.876 + tick, "/nv/load"),
        sensor("Power", "Board", None if tick == 1 else 80.222 + tick, "/nv/power")]
    intel.Sensors = [sensor("Load", "Core", 5.678 + tick, "/intel/load"),
        sensor("Temperature", "Hot", None, "/intel/none")]


def snapshot(m):
    """Every entry, insertion order, maxlen, and complete alias identity groups."""
    result = {}
    for prefix in ("cpu", "gpu"):
        for suffix in ("history", "history_long"):
            history = getattr(m, f"{prefix}_{suffix}")
            result[f"{prefix}_{suffix}"] = tuple((key, tuple(value), value.maxlen,
                tuple(k for k, v in history.items() if v is value))
                for key, value in history.items())
        result[f"{prefix}_percentiles"] = tuple(getattr(m, f"{prefix}_percentiles").items())
    result["names"] = tuple(getattr(m, "gpu_hw_names", ()))
    result["updates"] = tuple(m.updates)
    return result


def expected_text(title, rows):
    # Independent literal layout control (not calling the production formatter).
    header = "Type        | Name                      |  Current|  70th %ile"
    return "\n".join([title + ":", header, "-" * 62] + [
        f"{kind:<12}| {name:<26}| {value:>8}| {percentile:>10}"
        for kind, name, value, percentile in rows])


@contextmanager
def copy_meter(module):
    """Only module-level list(deque); percentile traversal is tracked separately.

    Normal builtins/NumPy internals remain untouched, and the real percentile
    function receives the original deque and executes on every call. Percentile
    references count input elements, not NumPy's internal traversal operations.
    """
    counts = dict(calls=0, references=0, full_calls=0, percentile_calls=0, percentile_input_references=0)
    original_percentile = module._percentile
    sentinel = object()
    original_list = module.__dict__.get("list", sentinel)

    def counted_list(value=()):
        if isinstance(value, deque):
            counts["calls"] += 1
            counts["references"] += len(value)
            counts["full_calls"] += int(len(value) == value.maxlen)
        return builtins.list(value)

    def percentile(value, rank):
        counts["percentile_calls"] += 1
        counts["percentile_input_references"] += len(value)
        return original_percentile(value, rank)

    module.list, module._percentile = counted_list, percentile
    try:
        yield counts
    finally:
        module._percentile = original_percentile
        if original_list is sentinel:
            del module.list
        else:
            module.list = original_list


@pytest.mark.parametrize("fallback", [False, True])
def test_changing_passes_complete_equivalence(monkeypatch, fallback):
    baseline, candidate = load_modules()
    if fallback:
        monkeypatch.setattr(baseline, "np", None)
        monkeypatch.setattr(candidate, "np", None)
    monitors = [make_monitor(mod) for mod in (baseline, candidate)]
    originals = [m.cpu_history["/cpu/shared"] for m in monitors]
    for tick in range(4):
        texts, states = [], []
        for m, original in zip(monitors, originals):
            set_pass(m, tick, "NVIDIA GPU" if tick == 2 else None)
            with m._lock:
                if tick == 2:
                    with pytest.raises(RuntimeError, match="^driver reset$"):
                        m._poll_pass()
                    assert m.cpu_history["/cpu/shared"] is original
                    assert tuple(original)[-2:] == (12.13, 88.99)
                    assert m.gpu_history["/amd/b"][-1] == 32.46
                    assert m.gpu_history["/nv/load"][-1] == 71.88
                    states.append(snapshot(m))  # Compare partial work before invalidation too.
                    m._invalidate_readings()
                    assert all(v is None for v in m.cpu_percentiles.values())
                    assert all(v is None for v in m.gpu_percentiles.values())
                    assert all(not getattr(m, p + s) for p in ("cpu_", "gpu_")
                               for s in ("history", "history_long"))
                else:
                    texts.append(m._poll_pass())
                    if tick < 2:
                        assert m.cpu_history["/cpu/shared"] is original
                    else:
                        assert m.cpu_history["/cpu/shared"] is not original
                states.append(snapshot(m))
            assert not m._lock.locked()
        assert texts[:1] == texts[1:]
        midpoint = len(states) // 2
        assert states[:midpoint] == states[midpoint:]
        m = monitors[1]
        assert m.gpu_hw_names == ["AMD GPU", "NVIDIA GPU", "Intel GPU"]
        for prefix in ("cpu", "gpu"):
            for suffix, size in (("history", 20), ("history_long", 600)):
                assert all(v.maxlen == size for v in getattr(m, f"{prefix}_{suffix}").values())
        expected_calls = ["CPU", "AMD GPU", "NVIDIA GPU", "Intel GPU"] * min(tick + 1, 2)
        if tick >= 2:
            expected_calls += ["CPU", "AMD GPU", "NVIDIA GPU"]
        if tick == 3:
            expected_calls += ["CPU", "AMD GPU", "NVIDIA GPU", "Intel GPU"]
        assert m.updates == [(name, True, threading.current_thread().name) for name in expected_calls]
        if tick == 0:
            rows = [("Load", "Core", "10.13", "13.3"),
                    ("Load", "Core (1)", "90.99", "14.3"),
                    ("Temperature", "Package", "50.56", "14.3")]
            assert texts[1] == "\n\n".join([expected_text("CPU", rows),
                expected_text("AMD GPU", [("Load", "1 Core", "20.23", "14.3"),
                    ("Load", "1 Core (1)", "30.46", "14.3"),
                    ("Temperature", "1 Hot", "40.68", "14.3"),
                    ("Power", "1 Board", "60.12", "14.3")]),
                expected_text("NVIDIA GPU", [("Load", "2 Core", "70.88", "14.3"),
                    ("Power", "2 Board", "80.22", "14.3")]),
                expected_text("Intel GPU", [("Load", "3 Core", "5.68", "13.3")])])
            assert tuple(m.cpu_history["/cpu/shared"]) == tuple(map(float, range(2, 20))) + (10.13, 90.99)
            assert tuple(m.cpu_history_long["/cpu/shared"]) == tuple(float(i % 100) for i in range(2, 600)) + (10.13, 90.99)
            assert "/cpu/none" not in m.cpu_history and "/intel/none" not in m.gpu_percentiles
        if tick == 1:
            assert m.gpu_percentiles["/amd/a"] is None and m.gpu_percentiles["/amd/p"] is None
            assert ("Load", "1 Core (1)") not in m.gpu_history
            assert m.gpu_history[("Load", "1 Core")] is m.gpu_history["/amd/b"]
            assert m.gpu_percentiles["/nv/power"] is None
            assert ("Power", "2 Board") not in m.gpu_history_long


def test_no_full_history_display_copy():
    baseline, candidate = load_modules()
    measured, states, texts = [], [], []
    for module in (baseline, candidate):
        m = make_monitor(module)
        with copy_meter(module) as counts, m._lock:
            texts.append(m._poll_pass())
        measured.append(counts)
        states.append(snapshot(m))
    assert texts[0] == texts[1] and states[0] == states[1]
    assert measured[0] == dict(calls=10, references=200, full_calls=10,
                               percentile_calls=10, percentile_input_references=200)
    assert measured[1]["percentile_calls"] == 10
    assert measured[1]["percentile_input_references"] == 200
    assert measured[1]["calls"] == measured[1]["references"] == 0, (
        "Performance requirement only: eliminate redundant list(deque) display copies", measured[1])


def test_public_format_history_standalone():
    for module in load_modules():
        m = make_monitor(module)
        history = {"ignored": [1], ("bad",): [2], ("Load", "empty"): [],
                   ("Power", "full"): deque([1, 2.25], maxlen=20)}
        assert m.format_history(history, {("Power", "full"): None}, "Standalone") == expected_text(
            "Standalone", [("Load", "empty", "N/A", "N/A"), ("Power", "full", "2.25", "None")])
