"""Correctness tests for Week 4 benchmarking algorithms."""

import unittest

from core.week4_profiler import (
    concatenate_iterative,
    concatenate_join,
    duplicate_finder_fast,
    duplicate_finder_slow,
    run_benchmarks,
)


class TestWeek4Profiler(unittest.TestCase):
    def test_duplicate_finders_return_identical_results(self) -> None:
        values = [4, 2, 4, 3, 2, 4, 8]

        self.assertEqual(
            duplicate_finder_slow(values),
            duplicate_finder_fast(values),
        )
        self.assertEqual(duplicate_finder_fast(values), [4, 2])

    def test_duplicate_finders_handle_empty_and_unique_inputs(self) -> None:
        for values in ([], [1, 2, 3]):
            with self.subTest(values=values):
                self.assertEqual(duplicate_finder_slow(values), [])
                self.assertEqual(duplicate_finder_fast(values), [])

    def test_string_concatenation_methods_match(self) -> None:
        parts = ["alpha", ",", "beta", ",", "gamma"]

        self.assertEqual(
            concatenate_iterative(parts),
            concatenate_join(parts),
        )

    def test_benchmark_returns_time_and_memory_metrics(self) -> None:
        metrics = run_benchmarks(20)

        self.assertEqual(metrics["item_count"], 20)
        for key in (
            "duplicate_finder_slow",
            "duplicate_finder_fast",
            "string_concatenation_iterative",
            "string_concatenation_join",
        ):
            with self.subTest(key=key):
                self.assertGreaterEqual(metrics[key]["seconds"], 0)
                self.assertGreaterEqual(metrics[key]["peak_memory_kb"], 0)

    def test_benchmark_rejects_invalid_size(self) -> None:
        for size in (0, -1, True):
            with self.subTest(size=size):
                with self.assertRaises(ValueError):
                    run_benchmarks(size)

    def test_benchmark_preserves_odd_item_count(self) -> None:
        metrics = run_benchmarks(1)

        self.assertEqual(metrics["item_count"], 1)
        self.assertEqual(
            metrics["duplicate_finder_slow"]["duplicate_count"],
            0,
        )


if __name__ == "__main__":
    unittest.main()