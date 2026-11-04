"""Wall/CPU profiling, heap tracing, GC churn, and cProfile summaries."""

from __future__ import annotations

import cProfile
import gc
import pstats
import time
import tracemalloc
from dataclasses import asdict, dataclass
from typing import Any, Callable, TypeVar

from performance_exceptions import AllocationBudgetExceededException

Result = TypeVar("Result")


@dataclass(frozen=True)
class ProfileMeasurement:
    """Metrics and result produced by one instrumented callable invocation."""

    result: Any
    wall_seconds: float
    cpu_seconds: float
    peak_memory_bytes: int
    allocation_diff_bytes: int
    gc_count_before: tuple[int, int, int]
    gc_count_after: tuple[int, int, int]
    gc_collection_delta: int
    primitive_calls: int
    profile_rows: list[dict[str, Any]]

    @property
    def wall_microseconds(self) -> float:
        return self.wall_seconds * 1_000_000

    @property
    def cpu_microseconds(self) -> float:
        return self.cpu_seconds * 1_000_000

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-ready telemetry without the potentially large result."""
        values = asdict(self)
        values.pop("result")
        values["wall_microseconds"] = self.wall_microseconds
        values["cpu_microseconds"] = self.cpu_microseconds
        values["peak_memory_kb"] = self.peak_memory_bytes / 1024
        values["allocation_diff_kb"] = self.allocation_diff_bytes / 1024
        values["gc_churn"] = sum(
            abs(after - before)
            for before, after in zip(
                self.gc_count_before, self.gc_count_after, strict=True
            )
        )
        return values


def _gc_collections() -> int:
    return sum(int(generation["collections"]) for generation in gc.get_stats())


def _profile_rows(
    profiler: cProfile.Profile, limit: int
) -> list[dict[str, Any]]:
    stats = pstats.Stats(profiler)
    ordered = sorted(
        stats.stats.items(), key=lambda item: item[1][3], reverse=True
    )
    rows: list[dict[str, Any]] = []
    for (filename, line, function), values in ordered[:limit]:
        primitive_calls, total_calls, total_time, cumulative_time, _ = values
        rows.append(
            {
                "function": f"{filename}:{line}({function})",
                "primitive_calls": primitive_calls,
                "total_calls": total_calls,
                "total_time_seconds": total_time,
                "cumulative_time_seconds": cumulative_time,
                "per_call_cumulative_microseconds": (
                    cumulative_time * 1_000_000 / total_calls
                    if total_calls
                    else 0.0
                ),
            }
        )
    return rows


def profile_callable(
    callback: Callable[..., Result],
    *args: Any,
    allocation_budget_bytes: int | None = None,
    profile_limit: int = 20,
    **kwargs: Any,
) -> ProfileMeasurement:
    """Measure one call's latency, CPU, allocations, GC, and primitive calls."""
    if not callable(callback):
        raise TypeError("callback must be callable")
    if allocation_budget_bytes is not None and (
        isinstance(allocation_budget_bytes, bool)
        or not isinstance(allocation_budget_bytes, int)
        or allocation_budget_bytes < 0
    ):
        raise ValueError(
            "allocation_budget_bytes must be a non-negative integer"
        )
    if (
        isinstance(profile_limit, bool)
        or not isinstance(profile_limit, int)
        or profile_limit < 1
    ):
        raise ValueError("profile_limit must be a positive integer")

    owns_tracing = not tracemalloc.is_tracing()
    if owns_tracing:
        tracemalloc.start()
    start_current, previous_peak = tracemalloc.get_traced_memory()
    if owns_tracing:
        tracemalloc.reset_peak()
        previous_peak = start_current
    before_snapshot = tracemalloc.take_snapshot()
    gc_count_before = gc.get_count()
    collections_before = _gc_collections()
    profiler = cProfile.Profile()
    wall_start = time.perf_counter()
    cpu_start = time.process_time()
    try:
        result = profiler.runcall(callback, *args, **kwargs)
    finally:
        wall_seconds = time.perf_counter() - wall_start
        cpu_seconds = time.process_time() - cpu_start
        gc_count_after = gc.get_count()
        collections_after = _gc_collections()
        end_snapshot = tracemalloc.take_snapshot()
        _, peak_bytes = tracemalloc.get_traced_memory()
        if owns_tracing:
            tracemalloc.stop()

    allocation_diff = sum(
        statistic.size_diff
        for statistic in end_snapshot.compare_to(before_snapshot, "filename")
    )
    peak_increment = max(0, peak_bytes - previous_peak)
    stats = pstats.Stats(profiler)
    primitive_calls = sum(values[0] for values in stats.stats.values())
    measurement = ProfileMeasurement(
        result=result,
        wall_seconds=wall_seconds,
        cpu_seconds=cpu_seconds,
        peak_memory_bytes=peak_increment,
        allocation_diff_bytes=allocation_diff,
        gc_count_before=gc_count_before,
        gc_count_after=gc_count_after,
        gc_collection_delta=max(0, collections_after - collections_before),
        primitive_calls=primitive_calls,
        profile_rows=_profile_rows(profiler, profile_limit),
    )
    if (
        allocation_budget_bytes is not None
        and peak_increment > allocation_budget_bytes
    ):
        raise AllocationBudgetExceededException(
            "Profiled call exceeded its allocation budget.",
            {
                "allocation_budget_bytes": allocation_budget_bytes,
                "peak_memory_bytes": peak_increment,
                "allocation_diff_bytes": allocation_diff,
                "wall_seconds": wall_seconds,
                "cpu_seconds": cpu_seconds,
            },
        )
    return measurement


__all__ = ["ProfileMeasurement", "profile_callable"]
