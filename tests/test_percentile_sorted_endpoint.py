import ast
from pathlib import Path
import unittest

REPO_ROOT = Path(__file__).resolve().parents[1]


def get_calculate_percentile(rel_path: str, class_name: str):
    file_path = REPO_ROOT / rel_path
    tree = ast.parse(file_path.read_text(encoding="utf-8"))
    cls_node = next(
        n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == class_name
    )
    func_node = next(
        n
        for n in cls_node.body
        if isinstance(n, ast.FunctionDef) and n.name == "calculate_percentile"
    )
    func_node.decorator_list = []
    scope = {}
    exec(
        compile(
            ast.Module(body=[func_node], type_ignores=[]),
            filename=str(file_path),
            mode="exec",
        ),
        scope,
    )
    return scope["calculate_percentile"]


class TestPercentileSortedEndpoint(unittest.TestCase):
    def setUp(self):
        self.implementations = {
            "cpu": get_calculate_percentile("src/core/cpu_monitor.py", "CPUUsageMonitor"),
            "gpu": get_calculate_percentile("src/core/gpu_monitor.py", "GPUUsageMonitor"),
        }

    def test_unsorted_input_at_100_percentile_returns_maximum(self):
        for name, calc in self.implementations.items():
            with self.subTest(impl=name):
                data = [10.0, 90.0, 20.0, 50.0, 30.0]
                data_copy = list(data)
                result = calc(data, 100.0)
                self.assertEqual(
                    result,
                    90.0,
                    f"{name} calculate_percentile(data, 100) should return max (90.0), got {result}",
                )
                self.assertEqual(
                    data,
                    data_copy,
                    f"{name} input list was mutated",
                )

    def test_singleton_input(self):
        for name, calc in self.implementations.items():
            with self.subTest(impl=name):
                for p in [0.0, 50.0, 100.0]:
                    data = [42.0]
                    data_copy = list(data)
                    result = calc(data, p)
                    self.assertEqual(result, 42.0)
                    self.assertEqual(data, data_copy)

    def test_existing_interpolation_behavior(self):
        for name, calc in self.implementations.items():
            with self.subTest(impl=name):
                # Sample dataset: sorted is [10.0, 20.0, 30.0, 40.0, 50.0]
                data = [50.0, 10.0, 40.0, 20.0, 30.0]
                data_copy = list(data)

                # 0th percentile -> 10.0
                res_0 = calc(data, 0.0)
                self.assertEqual(res_0, 10.0)

                # 50th percentile (k = 4 * 0.5 = 2.0 -> integer index -> sorted_data[2] = 30.0)
                res_50 = calc(data, 50.0)
                self.assertEqual(res_50, 30.0)

                # 25th percentile (k = 4 * 0.25 = 1.0 -> integer index -> sorted_data[1] = 20.0)
                res_25 = calc(data, 25.0)
                self.assertEqual(res_25, 20.0)

                # 80th percentile (k = 4 * 0.8 = 3.2 -> interpolated: sorted[3] + 0.2*(sorted[4]-sorted[3]) = 40.0 + 0.2*10.0 = 42.0)
                res_80 = calc(data, 80.0)
                self.assertAlmostEqual(res_80, 42.0)

                # Ensure input list is not mutated
                self.assertEqual(data, data_copy)


if __name__ == "__main__":
    unittest.main()
