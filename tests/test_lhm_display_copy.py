"""Independent candidate contracts plus optional actual-source equivalence.

Boundary stubs exercise Python behavior, not .NET/driver or GUI acceptance.
The benchmark imports these helpers; importing this file executes no checks.
"""
import builtins
from collections import defaultdict, deque
from contextlib import contextmanager
import importlib
import os
from pathlib import Path
import subprocess
import threading
from types import ModuleType, SimpleNamespace
import warnings

import pytest

ROOT = Path(__file__).resolve().parents[1]
BASELINE = "c5aaa5115b92ec3e1349c340cf7c491ca6ded186"
HT = SimpleNamespace(Cpu="Cpu", GpuAmd="AMD", GpuNvidia="NVIDIA", GpuIntel="Intel")


def load_modules(*, optional_baseline=False):
    """Tests may omit extra historical comparisons; benchmarks require source."""
    candidate = importlib.import_module("core.librehardwaremonitor")
    env = dict(os.environ, GIT_NO_LAZY_FETCH="1")
    available = (ROOT / ".git").exists()
    if optional_baseline and available:
        # Batch-check reports an absent object explicitly with exit status zero.
        # Git/process errors, corrupt objects and unexpected replies remain fatal.
        reply = subprocess.check_output(
            ["git", "cat-file", "--batch-check"], input=(BASELINE + "\n").encode("ascii"),
            cwd=ROOT, env=env).decode("ascii").strip()
        available = reply != f"{BASELINE} missing"
        parts = reply.split()
        if available and not (len(parts) == 3 and parts[:2] == [BASELINE, "commit"]
                              and parts[2].isdigit()):
            raise RuntimeError(f"Unexpected historical object response: {reply!r}")
    if optional_baseline and not available:
        warnings.warn("Historical object unavailable: extra baseline comparisons omitted; "
                      "all independent candidate checks still run.", stacklevel=2)
        return (candidate,)
    source = subprocess.check_output(
        ["git", "show", f"{BASELINE}:src/core/librehardwaremonitor.py"],
        cwd=ROOT, env=env).decode("utf-8")
    baseline = ModuleType("lhm_display_copy_baseline")
    baseline.__file__ = str(ROOT / "src/core/librehardwaremonitor.py")
    exec(compile(source, f"{BASELINE}:librehardwaremonitor.py", "exec"), baseline.__dict__)
    return baseline, candidate


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


def assert_expected_data(m, tick, invalid=False):
    """Declarative rounded sample/percentile trace, independent of either backend.

    Includes seeded tails, missing canonicals, detached/rebound aliases, partial
    failure before invalidation, and fresh recovery after invalidation.
    """
    cpu_temp, gpu_temp = ("Temperature", "Package"), ("Temperature", "1 Hot")
    traces = {
        "cpu": {
            "/cpu/shared": (((10.13, 90.99), (11.13, 89.99), (12.13, 88.99), (13.13, 87.99)), (14.3, 15.3, 16.3, 65.53)),
            cpu_temp: (((50.56,), (51.56,), (52.56,), (53.56,)), (14.3, 15.3, 16.3, 53.56)),
            "/cpu/none": (((), (26.33,), (27.33,), (28.33,)), (None, 26.33, 27.03, 28.33))},
        "gpu": {
            "/amd/a": (((20.23,), (), (), ()), (14.3, None, None, None)),
            "/amd/b": (((30.46,), (31.46,), (32.46,), (33.46,)), (14.3, 15.3, 16.3, 33.46)),
            gpu_temp: (((40.68,), (41.68,), (42.68,), (43.68,)), (14.3, 15.3, 16.3, 43.68)),
            "/amd/p": (((60.12,), (), (), ()), (14.3, None, None, None)),
            "/nv/load": (((70.88,), (71.88,), (), (73.88,)), (14.3, 15.3, 15.3, 73.88)),
            "/nv/power": (((80.22,), (), (), (83.22,)), (14.3, None, None, 83.22)),
            "/intel/load": (((5.68,), (6.68,), (), (8.68,)), (13.3, 13.3, 13.3, 8.68))}}
    for prefix, trace in traces.items():
        aliases = ({("Load", "Core"): "/cpu/shared", ("Load", "Core (1)"): "/cpu/shared",
                    ("Power", "Package"): "/cpu/none"} if prefix == "cpu" else {
                    ("Load", "1 Core"): "/amd/a", ("Load", "1 Core (1)"): "/amd/b",
                    ("Power", "1 Board"): "/amd/p", ("Load", "2 Core"): "/nv/load",
                    ("Power", "2 Board"): "/nv/power", ("Load", "3 Core"): "/intel/load"})
        # Percentile insertion order persists even after histories are cleared.
        pkeys = [k for canon in trace if canon != "/cpu/none" or tick > 0
                 for k in (canon, *(a for a, c in aliases.items() if c == canon))]
        if prefix == "gpu" and tick > 0:
            aliases[("Load", "1 Core")] = "/amd/b"
        detached = {("Load", "1 Core (1)"), ("Power", "1 Board"), ("Power", "2 Board")}
        live_aliases = [a for a in aliases if (prefix == "cpu" and (tick > 0 or a[0] == "Load"))
                        or (prefix == "gpu" and (tick == 0 or a not in detached or tick == 3 and a == ("Power", "2 Board")))]
        seeded = [k for k in trace if k != "/cpu/none"]
        keys = seeded + live_aliases
        if prefix == "cpu" and tick > 0:
            keys.insert(-1, "/cpu/none")
        if tick == 3:
            keys = [k for canon, (samples, _) in trace.items() if samples[3]
                    for k in (canon, *(a for a in live_aliases if aliases[a] == canon))]
        expected = {}
        for suffix, size in (("history", 20), ("history_long", 600)):
            def values(canon):
                seed = [float(i % 100) for i in range(size)] if tick < 3 and canon in seeded else []
                samples = trace[canon][0][3:] if tick == 3 else trace[canon][0][:tick + 1]
                return tuple((seed + [v for batch in samples for v in batch])[-size:])
            canonical = lambda key: aliases.get(key, key)
            expected[suffix] = () if invalid else tuple((k, values(canonical(k)), size,
                tuple(a for a in keys if canonical(a) == canonical(k))) for k in keys)
        percentiles = {k: None if invalid or k in aliases and k not in live_aliases
                       else trace[aliases.get(k, k)][1][tick] for k in pkeys}
        if not invalid and prefix == "cpu":
            percentiles[("Load", "Core")] = (13.3, 14.3, 15.3, 13.13)[tick]
        expected["percentiles"] = tuple(percentiles.items())
        actual = snapshot(m)
        assert {suffix: actual[f"{prefix}_{suffix}"] for suffix in expected} == expected


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
    modules = load_modules(optional_baseline=True)
    if fallback:
        for module in modules:
            monkeypatch.setattr(module, "np", None)
    monitors = [make_monitor(mod) for mod in modules]
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
                    assert_expected_data(m, tick)
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
                assert_expected_data(m, tick, invalid=tick == 2)
            assert not m._lock.locked()
        assert all(text == texts[0] for text in texts)
        if len(monitors) == 2:
            midpoint = len(states) // 2
            assert states[:midpoint] == states[midpoint:]
        m = monitors[-1]
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
        if tick != 2:
            cpu_values = ((10.13, 90.99, 50.56), (11.13, 89.99, 51.56), (), (13.13, 87.99, 53.56))[tick]
            cpu_p = ((13.3, 14.3, 14.3), (14.3, 15.3, 15.3), (), (13.13, 65.53, 53.56))[tick]
            rows = [(kind, name, value, p) for (kind, name), value, p in zip(
                (("Load", "Core"), ("Load", "Core (1)"), ("Temperature", "Package")), cpu_values, cpu_p)]
            if tick > 0:
                value = 26.33 if tick == 1 else 28.33
                rows.append(("Power", "Package", value, value))
            amd_rows = ([("Load", "1 Core", 20.23, 14.3), ("Load", "1 Core (1)", 30.46, 14.3),
                ("Temperature", "1 Hot", 40.68, 14.3), ("Power", "1 Board", 60.12, 14.3)] if tick == 0 else
                [("Load", "1 Core", 31.46 if tick == 1 else 33.46, 15.3 if tick == 1 else 33.46),
                 ("Temperature", "1 Hot", 41.68 if tick == 1 else 43.68, 15.3 if tick == 1 else 43.68)])
            nv_value, intel_value = (70.88, 71.88, None, 73.88)[tick], (5.68, 6.68, None, 8.68)[tick]
            nv_rows = [("Load", "2 Core", nv_value, (14.3, 15.3, None, 73.88)[tick])]
            if tick != 1:
                value = 80.22 if tick == 0 else 83.22
                nv_rows.append(("Power", "2 Board", value, 14.3 if tick == 0 else value))
            assert texts[-1] == "\n\n".join([expected_text("CPU", rows),
                expected_text("AMD GPU", amd_rows), expected_text("NVIDIA GPU", nv_rows),
                expected_text("Intel GPU", [("Load", "3 Core", intel_value, 13.3 if tick < 3 else intel_value)])])
        if tick == 0:
            assert "/cpu/none" not in m.cpu_history and "/intel/none" not in m.gpu_percentiles
        if tick == 1:
            assert m.gpu_percentiles["/amd/a"] is None and m.gpu_percentiles["/amd/p"] is None
            assert ("Load", "1 Core (1)") not in m.gpu_history
            assert m.gpu_history[("Load", "1 Core")] is m.gpu_history["/amd/b"]
            assert m.gpu_percentiles["/nv/power"] is None
            assert ("Power", "2 Board") not in m.gpu_history_long


def test_no_full_history_display_copy():
    modules = load_modules(optional_baseline=True)
    measured, states, texts = [], [], []
    for module in modules:
        m = make_monitor(module)
        with copy_meter(module) as counts, m._lock:
            texts.append(m._poll_pass())
        measured.append(counts)
        states.append(snapshot(m))
        assert_expected_data(m, 0)
    if len(modules) == 2:
        assert texts[0] == texts[1] and states[0] == states[1]
        assert measured[0] == dict(calls=10, references=200, full_calls=10,
                                   percentile_calls=10, percentile_input_references=200)
    assert measured[-1]["percentile_calls"] == 10
    assert measured[-1]["percentile_input_references"] == 200
    assert measured[-1]["calls"] == measured[-1]["references"] == measured[-1]["full_calls"] == 0, (
        "Performance requirement only: eliminate redundant list(deque) display copies", measured[-1])


def test_public_format_history_standalone():
    for module in load_modules(optional_baseline=True):
        m = make_monitor(module)
        history = {"ignored": [1], ("bad",): [2], ("Load", "empty"): [],
                   ("Power", "full"): deque([1, 2.25], maxlen=20)}
        assert m.format_history(history, {("Power", "full"): None}, "Standalone") == expected_text(
            "Standalone", [("Load", "empty", "N/A", "N/A"), ("Power", "full", "2.25", "None")])
