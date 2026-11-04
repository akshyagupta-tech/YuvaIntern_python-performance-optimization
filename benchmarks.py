"""Synthetic workload generation and statistical benchmark orchestration."""

from __future__ import annotations

import csv
import io
import json
import math
import platform
import random
import statistics
import sys
import time
from collections.abc import Hashable, Sequence
from typing import Any, TypeVar

from engine_baseline import find_duplicates_quadratic
from engine_optimized import cached_digest, find_duplicates_linear
from performance_exceptions import (
    BenchmarkTimeoutError,
    MalformedWorkloadError,
)
from profiler import ProfileMeasurement, profile_callable

Value = TypeVar("Value", bound=Hashable)
MAX_WORKLOAD_SIZE = 50_000
DEFAULT_WARMUPS = 5
DEFAULT_TRIALS = 7


def generate_workload(
    size: int,
    duplicate_rate: float,
    *,
    kind: str = "numeric",
    seed: int = 42,
) -> list[int] | list[str]:
    """Generate reproducible numeric or string records at an exact duplicate rate."""
    if (
        isinstance(size, bool)
        or not isinstance(size, int)
        or not 1 <= size <= MAX_WORKLOAD_SIZE
    ):
        raise MalformedWorkloadError(
            "Workload size must be between 1 and the configured maximum.",
            {"size": size, "maximum": MAX_WORKLOAD_SIZE},
        )
    if (
        isinstance(duplicate_rate, bool)
        or not isinstance(duplicate_rate, (int, float))
        or not math.isfinite(duplicate_rate)
        or not 0 <= duplicate_rate <= 1
    ):
        raise MalformedWorkloadError(
            "Duplicate rate must be finite and in the range [0, 1].",
            {"duplicate_rate": duplicate_rate},
        )
    if kind not in {"numeric", "string"}:
        raise MalformedWorkloadError(
            "Workload kind must be 'numeric' or 'string'.", {"kind": kind}
        )
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise MalformedWorkloadError(
            "Seed must be an integer.", {"seed": seed}
        )

    unique_count = max(1, round(size * (1 - duplicate_rate)))
    if kind == "numeric":
        unique_values: list[int] | list[str] = list(range(unique_count))
    else:
        unique_values = [
            f"record-{index:08d}" for index in range(unique_count)
        ]
    records: list[int] | list[str] = list(unique_values)
    generator = random.Random(seed)
    records.extend(generator.choices(unique_values, k=size - unique_count))
    generator.shuffle(records)
    return records


def summarize_samples(samples: Sequence[float]) -> dict[str, float | int]:
    """Remove strong median-absolute-deviation outliers and summarize trials."""
    if not samples:
        raise MalformedWorkloadError("At least one timing sample is required.")
    if any(
        isinstance(sample, bool)
        or not isinstance(sample, (int, float))
        or not math.isfinite(sample)
        or sample < 0
        for sample in samples
    ):
        raise MalformedWorkloadError(
            "Timing samples must be finite non-negative numbers."
        )
    median_value = statistics.median(samples)
    deviations = [abs(sample - median_value) for sample in samples]
    mad = statistics.median(deviations)
    threshold = 3 * 1.4826 * mad
    retained = (
        [
            sample
            for sample in samples
            if abs(sample - median_value) <= threshold
        ]
        if mad > 0
        else list(samples)
    )
    if not retained:
        retained = list(samples)
    return {
        "median": float(statistics.median(retained)),
        "standard_deviation": (
            float(statistics.stdev(retained)) if len(retained) > 1 else 0.0
        ),
        "sample_count": len(samples),
        "retained_count": len(retained),
        "outliers_removed": len(samples) - len(retained),
    }


def _measure_trials(
    callback: Any,
    values: Sequence[Value],
    *,
    warmups: int,
    trials: int,
    baseline: bool,
    time_budget_seconds: float,
    baseline_max_items: int,
) -> tuple[list[float], list[float], str | None]:
    wall_samples: list[float] = []
    cpu_samples: list[float] = []
    error_message: str | None = None
    total_runs = warmups + trials
    for run_index in range(total_runs):
        started_wall = time.perf_counter()
        started_cpu = time.process_time()
        try:
            if baseline:
                callback(
                    values,
                    max_items=baseline_max_items,
                    time_budget_seconds=time_budget_seconds,
                )
            else:
                callback(values)
        except BenchmarkTimeoutError as error:
            error_message = str(error)
            break
        wall_duration = time.perf_counter() - started_wall
        cpu_duration = time.process_time() - started_cpu
        if run_index >= warmups:
            wall_samples.append(wall_duration)
            cpu_samples.append(cpu_duration)
    return wall_samples, cpu_samples, error_message


def _measurement_payload(
    wall_samples: Sequence[float],
    cpu_samples: Sequence[float],
    profile: ProfileMeasurement | None,
    error_message: str | None,
) -> dict[str, Any]:
    if not wall_samples:
        payload: dict[str, Any] = {
            "status": "aborted",
            "trial_count": 0,
            "wall_median_seconds": None,
            "wall_median_microseconds": None,
            "wall_standard_deviation_seconds": None,
            "cpu_median_seconds": None,
            "cpu_median_microseconds": None,
            "peak_memory_bytes": None,
            "peak_memory_kb": None,
            "allocation_diff_bytes": None,
            "outliers_removed": 0,
        }
        if error_message:
            payload["error"] = error_message
        return payload
    wall_summary = summarize_samples(wall_samples)
    cpu_summary = summarize_samples(cpu_samples)
    payload = {
        "status": "aborted" if error_message else "completed",
        "trial_count": len(wall_samples),
        "wall_median_seconds": wall_summary["median"],
        "wall_median_microseconds": float(wall_summary["median"]) * 1_000_000,
        "wall_standard_deviation_seconds": wall_summary["standard_deviation"],
        "cpu_median_seconds": cpu_summary["median"],
        "cpu_median_microseconds": float(cpu_summary["median"]) * 1_000_000,
        "wall_samples_seconds": list(wall_samples),
        "cpu_samples_seconds": list(cpu_samples),
        "outliers_removed": wall_summary["outliers_removed"],
        "peak_memory_bytes": profile.peak_memory_bytes if profile else None,
        "peak_memory_kb": (
            profile.peak_memory_bytes / 1024 if profile else None
        ),
        "allocation_diff_bytes": (
            profile.allocation_diff_bytes if profile else None
        ),
        "gc_collection_delta": (
            profile.gc_collection_delta if profile else None
        ),
        "primitive_calls": profile.primitive_calls if profile else None,
        "profile_rows": profile.profile_rows if profile else [],
    }
    if error_message:
        payload["error"] = error_message
    return payload


def benchmark_workload(
    size: int,
    duplicate_rate: float = 0.25,
    *,
    kind: str = "numeric",
    seed: int = 42,
    warmups: int = DEFAULT_WARMUPS,
    trials: int = DEFAULT_TRIALS,
    time_budget_seconds: float = 0.25,
    baseline_max_items: int = 10_000,
    allocation_budget_bytes: int | None = None,
) -> dict[str, Any]:
    """Run parity-checked baseline/optimized benchmarks and telemetry exports."""
    if (
        isinstance(warmups, bool)
        or not isinstance(warmups, int)
        or warmups < 0
    ):
        raise MalformedWorkloadError("Warmups must be a non-negative integer.")
    if isinstance(trials, bool) or not isinstance(trials, int) or trials < 1:
        raise MalformedWorkloadError("Trial count must be a positive integer.")
    if (
        isinstance(time_budget_seconds, bool)
        or not isinstance(time_budget_seconds, (int, float))
        or not math.isfinite(time_budget_seconds)
        or time_budget_seconds <= 0
    ):
        raise MalformedWorkloadError(
            "Time budget must be positive and finite."
        )

    workload = generate_workload(size, duplicate_rate, kind=kind, seed=seed)
    optimized_result = find_duplicates_linear(workload)
    baseline_error: str | None = None
    parity_verified = False
    try:
        baseline_result = find_duplicates_quadratic(
            workload,
            max_items=baseline_max_items,
            time_budget_seconds=time_budget_seconds,
        )
        parity_verified = baseline_result == optimized_result
        if not parity_verified:
            raise AssertionError(
                "Baseline and optimized outputs do not match."
            )
    except BenchmarkTimeoutError as error:
        baseline_error = str(error)

    optimized_wall, optimized_cpu, optimized_error = _measure_trials(
        find_duplicates_linear,
        workload,
        warmups=warmups,
        trials=trials,
        baseline=False,
        time_budget_seconds=time_budget_seconds,
        baseline_max_items=baseline_max_items,
    )
    optimized_profile: ProfileMeasurement | None = None
    try:
        optimized_profile = profile_callable(
            find_duplicates_linear,
            workload,
            allocation_budget_bytes=allocation_budget_bytes,
        )
    except Exception as error:
        if optimized_error is None:
            optimized_error = (
                f"Profiling failed: {type(error).__name__}: {error}"
            )

    baseline_wall: list[float] = []
    baseline_cpu: list[float] = []
    baseline_profile: ProfileMeasurement | None = None
    if baseline_error is None:
        baseline_wall, baseline_cpu, baseline_error = _measure_trials(
            find_duplicates_quadratic,
            workload,
            warmups=warmups,
            trials=trials,
            baseline=True,
            time_budget_seconds=time_budget_seconds,
            baseline_max_items=baseline_max_items,
        )
        if baseline_error is None:
            try:
                baseline_profile = profile_callable(
                    find_duplicates_quadratic,
                    workload,
                    max_items=baseline_max_items,
                    time_budget_seconds=time_budget_seconds,
                    allocation_budget_bytes=allocation_budget_bytes,
                )
            except Exception as error:
                baseline_error = (
                    f"Profiling failed: {type(error).__name__}: {error}"
                )

    optimized_payload = _measurement_payload(
        optimized_wall, optimized_cpu, optimized_profile, optimized_error
    )
    baseline_payload = _measurement_payload(
        baseline_wall, baseline_cpu, baseline_profile, baseline_error
    )
    baseline_median = baseline_payload["wall_median_seconds"]
    optimized_median = optimized_payload["wall_median_seconds"]
    speedup = (
        baseline_median / optimized_median
        if baseline_median is not None and optimized_median
        else None
    )
    baseline_peak = baseline_payload["peak_memory_bytes"]
    optimized_peak = optimized_payload["peak_memory_bytes"]
    memory_savings = (
        100.0 * (baseline_peak - optimized_peak) / baseline_peak
        if baseline_peak is not None
        and baseline_peak > 0
        and optimized_peak is not None
        else None
    )

    cache_start = cached_digest.cache_info()
    for record in workload[: min(size, 1_000)]:
        cached_digest(str(record))
    for record in workload[: min(size, 1_000)]:
        cached_digest(str(record))
    cache_end = cached_digest.cache_info()
    return {
        "size": size,
        "kind": kind,
        "duplicate_rate": duplicate_rate,
        "warmups": warmups,
        "requested_trials": trials,
        "parity_verified": parity_verified,
        "duplicate_count": len(optimized_result),
        "baseline": baseline_payload,
        "optimized": optimized_payload,
        "speedup_factor": speedup,
        "memory_savings_percent": memory_savings,
        "cache": {
            "hits": cache_end.hits - cache_start.hits,
            "misses": cache_end.misses - cache_start.misses,
            "maxsize": cache_end.maxsize,
            "currsize": cache_end.currsize,
        },
        "hardware": {
            "platform": platform.platform(),
            "python_version": sys.version.split()[0],
            "logical_cpu_count": __import__("os").cpu_count(),
        },
        "generated_at_epoch_seconds": time.time(),
    }


def export_json(telemetry: dict[str, Any]) -> str:
    """Serialize complete benchmark and hardware telemetry as JSON."""
    return json.dumps(telemetry, indent=2, sort_keys=True)


def export_csv(telemetry: dict[str, Any]) -> str:
    """Serialize per-algorithm timing and memory telemetry as standard CSV."""
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=(
            "algorithm",
            "status",
            "trial_count",
            "wall_median_seconds",
            "wall_median_microseconds",
            "wall_standard_deviation_seconds",
            "cpu_median_seconds",
            "peak_memory_bytes",
            "allocation_diff_bytes",
            "duplicate_count",
            "speedup_factor",
            "memory_savings_percent",
        ),
        lineterminator="\n",
    )
    writer.writeheader()
    for name in ("baseline", "optimized"):
        metrics = telemetry[name]
        writer.writerow(
            {
                "algorithm": name,
                **{
                    key: metrics.get(key)
                    for key in (
                        "status",
                        "trial_count",
                        "wall_median_seconds",
                        "wall_median_microseconds",
                        "wall_standard_deviation_seconds",
                        "cpu_median_seconds",
                        "peak_memory_bytes",
                        "allocation_diff_bytes",
                    )
                },
                "duplicate_count": telemetry.get("duplicate_count"),
                "speedup_factor": telemetry.get("speedup_factor"),
                "memory_savings_percent": telemetry.get(
                    "memory_savings_percent"
                ),
            }
        )
    return output.getvalue()


__all__ = [
    "DEFAULT_TRIALS",
    "DEFAULT_WARMUPS",
    "MAX_WORKLOAD_SIZE",
    "benchmark_workload",
    "export_csv",
    "export_json",
    "generate_workload",
    "summarize_samples",
]
