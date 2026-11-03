"""Benchmark duplicate detection and string construction strategies."""

import json
import time
import tracemalloc
from typing import Callable, Dict, List, Tuple, TypeVar


Result = TypeVar("Result")


def duplicate_finder_slow(arr: List[int]) -> List[int]:
    """Find repeated values with a quadratic nested scan."""
    duplicates: List[int] = []
    duplicate_values = set()
    for index, value in enumerate(arr):
        for later_index in range(index + 1, len(arr)):
            if value == arr[later_index]:
                if value not in duplicate_values:
                    duplicate_values.add(value)
                    duplicates.append(value)
                break
    return duplicates


def duplicate_finder_fast(arr: List[int]) -> List[int]:
    """Find repeated values in one pass using hash sets."""
    seen = set()
    duplicate_values = set()
    duplicates: List[int] = []
    for value in arr:
        if value in seen:
            if value not in duplicate_values:
                duplicate_values.add(value)
                duplicates.append(value)
        else:
            seen.add(value)
    return duplicates


def concatenate_iterative(parts: List[str]) -> str:
    """Build a string by repeatedly appending immutable string parts."""
    result = ""
    for part in parts:
        result += part
    return result


def concatenate_join(parts: List[str]) -> str:
    """Build a string with a single join allocation."""
    return "".join(parts)


def _measure(
    callback: Callable[[List[Result]], Result],
    values: List[Result],
) -> Tuple[Result, float, float]:
    """Return callback result, elapsed seconds, and peak traced KB."""
    tracemalloc.start()
    start_time = time.perf_counter()
    try:
        result = callback(values)
        elapsed = time.perf_counter() - start_time
        _, peak_bytes = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return result, elapsed, peak_bytes / 1024


def run_benchmarks(size: int) -> Dict[str, object]:
    """Run duplicate and string benchmarks for the requested item count."""
    if isinstance(size, bool) or not isinstance(size, int) or size < 1:
        raise ValueError("Benchmark size must be a positive integer.")

    half_size = size // 2
    values = list(range(half_size)) * 2
    if size % 2:
        values.append(half_size)
    string_parts = [f"{index}," for index in range(size)]

    slow_duplicates, slow_seconds, slow_peak_kb = _measure(
        duplicate_finder_slow,
        values,
    )
    fast_duplicates, fast_seconds, fast_peak_kb = _measure(
        duplicate_finder_fast,
        values,
    )
    if slow_duplicates != fast_duplicates:
        raise AssertionError("Duplicate finder results do not match.")

    iterative_result, iterative_seconds, iterative_peak_kb = _measure(
        concatenate_iterative,
        string_parts,
    )
    join_result, join_seconds, join_peak_kb = _measure(
        concatenate_join,
        string_parts,
    )
    if iterative_result != join_result:
        raise AssertionError("String concatenation results do not match.")

    return {
        "item_count": size,
        "duplicate_finder_slow": {
            "seconds": slow_seconds,
            "peak_memory_kb": slow_peak_kb,
            "duplicate_count": len(slow_duplicates),
        },
        "duplicate_finder_fast": {
            "seconds": fast_seconds,
            "peak_memory_kb": fast_peak_kb,
            "duplicate_count": len(fast_duplicates),
        },
        "string_concatenation_iterative": {
            "seconds": iterative_seconds,
            "peak_memory_kb": iterative_peak_kb,
            "result_length": len(iterative_result),
        },
        "string_concatenation_join": {
            "seconds": join_seconds,
            "peak_memory_kb": join_peak_kb,
            "result_length": len(join_result),
        },
    }


def _run_streamlit_app() -> None:
    """Render the interactive benchmark comparison and JSON export."""
    import streamlit as st

    st.title("Algorithm and Memory Profiler")
    size = st.slider(
        "Array and string part count",
        min_value=1_000,
        max_value=20_000,
        value=5_000,
        step=1_000,
    )

    if st.button("Run benchmarks"):
        with st.spinner("Running benchmark comparisons..."):
            st.session_state.week4_telemetry = run_benchmarks(size)

    telemetry = st.session_state.get("week4_telemetry")
    if telemetry is None:
        return

    duplicate_metrics = [
        {
            "Algorithm": label,
            **telemetry[key],
        }
        for label, key in (
            ("Quadratic nested loops", "duplicate_finder_slow"),
            ("Linear hash set", "duplicate_finder_fast"),
        )
    ]
    string_metrics = [
        {
            "Method": label,
            **telemetry[key],
        }
        for label, key in (
            ("Iterative +=", "string_concatenation_iterative"),
            ("Preallocated join", "string_concatenation_join"),
        )
    ]

    st.subheader("Duplicate detection")
    st.bar_chart(duplicate_metrics, x="Algorithm", y="seconds")
    st.dataframe(duplicate_metrics, use_container_width=True)

    st.subheader("String construction")
    st.bar_chart(string_metrics, x="Method", y="seconds")
    st.dataframe(string_metrics, use_container_width=True)

    st.download_button(
        "Export telemetry JSON",
        data=json.dumps(telemetry, indent=2),
        file_name="week4_benchmark_telemetry.json",
        mime="application/json",
    )


if __name__ == "__main__":
    _run_streamlit_app()