"""Compatibility CLI for the integrated benchmark and profiling engine."""

from __future__ import annotations

from benchmarks import benchmark_workload, export_json


def main() -> None:
    """Run a representative bounded workload and emit its telemetry."""
    result = benchmark_workload(
        size=1_000,
        duplicate_rate=0.5,
        warmups=1,
        trials=3,
        time_budget_seconds=1.0,
    )
    print(export_json(result))


if __name__ == "__main__":
    main()
