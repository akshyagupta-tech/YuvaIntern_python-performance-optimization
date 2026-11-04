"""Compatibility facade around the linear Week 4 processing engine."""

from __future__ import annotations

from typing import Any

from benchmarks import generate_workload
from engine_optimized import concatenate_join, find_duplicates_linear
from profiler import profile_callable


class OptimizedDataEngine:
    """Expose the historical class API over the new optimized functions."""

    @staticmethod
    def generate_workload(size: int = 10_000, seed: int = 42) -> list[int]:
        """Generate numeric records at the legacy 50-percent duplicate rate."""
        values = generate_workload(size, 0.5, kind="numeric", seed=seed)
        return [int(value) for value in values]

    @staticmethod
    def find_duplicates_linear(data: list[Any]) -> list[Any]:
        """Return unique duplicate values using a one-pass hash-set scan."""
        return find_duplicates_linear(data)

    @staticmethod
    def buffer_stream_concatenation(iterations: int = 25_000) -> int:
        """Return comma-separated output length using the optimized join path."""
        if (
            isinstance(iterations, bool)
            or not isinstance(iterations, int)
            or iterations < 0
        ):
            raise ValueError("iterations must be a non-negative integer")
        joined = concatenate_join(str(index) for index in range(iterations))
        return len(f"{joined},")

    @classmethod
    def run_instrumented_pipeline(
        cls,
        data_size: int = 8_000,
        str_iters: int = 20_000,
    ) -> dict[str, Any]:
        """Run and profile the optimized duplicate and string aggregation path."""
        dataset = cls.generate_workload(data_size)
        measurement = profile_callable(find_duplicates_linear, dataset)
        string_length = cls.buffer_stream_concatenation(str_iters)
        return {
            "duplicate_count": len(measurement.result),
            "string_buffer_length": string_length,
            "duration_seconds": round(measurement.wall_seconds, 6),
            "cpu_seconds": round(measurement.cpu_seconds, 6),
            "peak_memory_kb": round(measurement.peak_memory_bytes / 1024, 2),
            "primitive_calls": measurement.primitive_calls,
            "gc_collection_delta": measurement.gc_collection_delta,
        }


if __name__ == "__main__":
    pipeline_metrics = OptimizedDataEngine.run_instrumented_pipeline()
    print("[Engine Output] Optimized execution finished:")
    for metric, value in pipeline_metrics.items():
        print(f"  {metric}: {value}")
