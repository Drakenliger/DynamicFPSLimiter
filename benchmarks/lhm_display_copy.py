"""Python/stub _poll_pass comparison; no native sensor overhead or game-FPS claim."""
import argparse
import json
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
from test_lhm_display_copy import BASELINE, copy_meter, load_modules, make_monitor


def measure(module, warmup, reps, batches):
    m = make_monitor(module)
    with m._lock:
        for _ in range(warmup):
            m._poll_pass()
        with copy_meter(module) as counts:
            m._poll_pass()
    # Fresh seeded monitors per batch; instrumentation is absent during timing.
    timings = []
    for _ in range(batches):
        m = make_monitor(module)
        with m._lock:
            for _ in range(warmup):
                m._poll_pass()
            start = time.perf_counter_ns()
            for _ in range(reps):
                m._poll_pass()
            timings.append((time.perf_counter_ns() - start) / reps / 1000)
    return dict(numpy_available=module.np is not None, warmup=warmup, reps=reps,
                batches=batches, median_poll_pass_us=statistics.median(timings),
                batch_poll_pass_us=timings, copies_per_pass=counts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--warmup", type=int, default=30)
    parser.add_argument("--reps", type=int, default=200)
    parser.add_argument("--batches", type=int, default=5)
    args = parser.parse_args()
    if min(args.warmup, args.reps, args.batches) < 1:
        parser.error("warmup, reps and batches must be positive")
    baseline, candidate = load_modules()
    print(json.dumps(dict(baseline_sha=BASELINE,
        baseline=measure(baseline, **vars(args)), candidate=measure(candidate, **vars(args))), indent=2))


if __name__ == "__main__":
    main()
