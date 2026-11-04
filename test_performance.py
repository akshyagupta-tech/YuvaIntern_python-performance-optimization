"""Contract and regression tests for the high-throughput benchmark engine."""

from __future__ import annotations

import csv
import io
import json
import math
import unittest

from benchmarks import (
    benchmark_workload,
    export_csv,
    export_json,
    generate_workload,
    summarize_samples,
)
from engine_baseline import concatenate_iterative, find_duplicates_quadratic
from engine_optimized import (
    cached_digest,
    concatenate_join,
    find_duplicates_linear,
    iter_chunks,
    iter_unique,
    match_values_linear,
)
from performance_exceptions import (
    AllocationBudgetExceededException,
    BenchmarkTimeoutError,
    MalformedWorkloadError,
)
from profiler import profile_callable


class TestAlgorithmParity(unittest.TestCase):
    def test_quadratic_and_linear_duplicate_results_match_in_order(
        self,
    ) -> None:
        values = [4, 2, 4, 3, 2, 4, 8]
        self.assertEqual(
            find_duplicates_quadratic(values),
            find_duplicates_linear(values),
        )
        self.assertEqual(find_duplicates_linear(values), [4, 2])

    def test_matchers_return_identical_intersection(self) -> None:
        left = [1, 2, 2, 5, 8]
        right = [2, 5, 5, 9]
        self.assertEqual(
            find_duplicates_quadratic(left, right),
            match_values_linear(left, right),
        )

    def test_iterative_and_join_aggregation_match(self) -> None:
        parts = ["alpha", ",", "beta", ",", "gamma"]
        self.assertEqual(concatenate_iterative(parts), concatenate_join(parts))
        self.assertEqual(concatenate_join([]), "")

    def test_streaming_chunks_and_unique_items_are_lazy_and_correct(
        self,
    ) -> None:
        self.assertEqual(
            list(iter_chunks(range(7), chunk_size=3)),
            [[0, 1, 2], [3, 4, 5], [6]],
        )
        self.assertEqual(list(iter_unique(iter([1, 2, 1, 3, 2]))), [1, 2, 3])

    def test_unhashable_records_raise_domain_error(self) -> None:
        with self.assertRaises(MalformedWorkloadError):
            find_duplicates_linear([[1], [1]])  # type: ignore[list-item]


class TestWorkloadGeneration(unittest.TestCase):
    def test_numeric_and_string_workloads_are_reproducible(self) -> None:
        for kind in ("numeric", "string"):
            first = generate_workload(100, 0.25, kind=kind, seed=3)
            second = generate_workload(100, 0.25, kind=kind, seed=3)
            self.assertEqual(first, second)
            self.assertEqual(len(first), 100)
            self.assertEqual(len(set(first)), 75)

    def test_invalid_workloads_and_rates_are_rejected(self) -> None:
        for size, duplicate_rate in (
            (0, 0.2),
            (-1, 0.2),
            (10, -0.1),
            (10, 1.1),
        ):
            with self.subTest(size=size, duplicate_rate=duplicate_rate):
                with self.assertRaises(MalformedWorkloadError):
                    generate_workload(size, duplicate_rate)
        all_duplicates = generate_workload(10, 1.0)
        self.assertEqual(len(set(all_duplicates)), 1)


class TestSafetyAndProfiling(unittest.TestCase):
    def test_quadratic_baseline_obeys_item_safety_clamp(self) -> None:
        with self.assertRaises(BenchmarkTimeoutError):
            find_duplicates_quadratic([1, 2, 3], max_items=2)

    def test_item_clamp_runs_before_workload_iteration(self) -> None:
        class UnreadableList(list[int]):
            def __iter__(self):
                raise AssertionError("clamped workloads must not be iterated")

        with self.assertRaises(BenchmarkTimeoutError):
            find_duplicates_quadratic(UnreadableList([1, 2, 3]), max_items=2)

    def test_quadratic_baseline_obeys_time_budget(self) -> None:
        with self.assertRaises(BenchmarkTimeoutError):
            find_duplicates_quadratic(
                list(range(1_000)), time_budget_seconds=1e-12
            )

    def test_profile_captures_wall_cpu_memory_calls_and_gc(self) -> None:
        measurement = profile_callable(sum, range(100))
        self.assertGreaterEqual(measurement.wall_seconds, 0.0)
        self.assertGreaterEqual(measurement.cpu_seconds, 0.0)
        self.assertGreaterEqual(measurement.peak_memory_bytes, 0)
        self.assertGreaterEqual(measurement.primitive_calls, 1)
        self.assertIn("gc_collection_delta", measurement.to_dict())
        self.assertTrue(measurement.profile_rows)

    def test_profiler_leaves_external_tracemalloc_session_running(
        self,
    ) -> None:
        import tracemalloc

        tracemalloc.start()
        try:
            profile_callable(sum, range(10))
            self.assertTrue(tracemalloc.is_tracing())
        finally:
            tracemalloc.stop()

    def test_allocation_budget_raises_with_measured_context(self) -> None:
        with self.assertRaises(AllocationBudgetExceededException) as raised:
            profile_callable(lambda: [0] * 10_000, allocation_budget_bytes=1)
        self.assertGreater(raised.exception.context["peak_memory_bytes"], 1)

    def test_lru_cache_reports_hits_and_misses(self) -> None:
        cached_digest.cache_clear()
        self.assertEqual(cached_digest("payload"), cached_digest("payload"))
        telemetry = cached_digest.cache_telemetry()
        self.assertEqual(telemetry["hits"], 1)
        self.assertEqual(telemetry["misses"], 1)


class TestStatisticalBenchmark(unittest.TestCase):
    def test_outlier_filter_uses_median_and_sample_deviation(self) -> None:
        result = summarize_samples([1.0, 2.0, 3.0, 100.0])
        self.assertEqual(result["median"], 2.0)
        self.assertEqual(result["outliers_removed"], 1)
        self.assertGreater(result["standard_deviation"], 0.0)

    def test_benchmark_parity_speedup_memory_and_multi_trial_metrics(
        self,
    ) -> None:
        result = benchmark_workload(
            size=500,
            duplicate_rate=0.3,
            warmups=1,
            trials=3,
            time_budget_seconds=1.0,
        )
        self.assertTrue(result["parity_verified"])
        self.assertEqual(result["size"], 500)
        self.assertEqual(result["baseline"]["trial_count"], 3)
        self.assertEqual(result["optimized"]["trial_count"], 3)
        self.assertGreater(result["speedup_factor"], 0.0)
        self.assertGreater(result["speedup_factor"], 1.0)
        self.assertTrue(math.isfinite(result["memory_savings_percent"]))

    def test_large_baseline_benchmark_reports_safe_abort(self) -> None:
        result = benchmark_workload(
            size=20,
            duplicate_rate=0.0,
            warmups=1,
            trials=2,
            time_budget_seconds=0.01,
            baseline_max_items=10,
        )
        self.assertEqual(result["baseline"]["status"], "aborted")
        self.assertEqual(result["optimized"]["status"], "completed")
        self.assertIn("error", result["baseline"])

    def test_invalid_benchmark_parameters_are_rejected(self) -> None:
        for options in (
            {"size": 10, "warmups": -1},
            {"size": 10, "trials": 0},
            {"size": 10, "time_budget_seconds": 0},
        ):
            with self.subTest(options=options):
                with self.assertRaises(MalformedWorkloadError):
                    benchmark_workload(**options)

    def test_json_and_csv_exports_round_trip(self) -> None:
        result = benchmark_workload(
            size=40,
            duplicate_rate=0.25,
            warmups=1,
            trials=2,
            time_budget_seconds=1.0,
        )
        self.assertEqual(json.loads(export_json(result))["size"], 40)
        rows = list(csv.DictReader(io.StringIO(export_csv(result))))
        self.assertEqual(
            {row["algorithm"] for row in rows}, {"baseline", "optimized"}
        )


if __name__ == "__main__":
    unittest.main()
