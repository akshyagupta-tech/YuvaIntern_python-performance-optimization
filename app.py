"""Streamlit dashboard for the high-throughput benchmark and profiling engine."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from benchmarks import benchmark_workload, export_csv, export_json
from performance_exceptions import MalformedWorkloadError

st.set_page_config(
    page_title="High-Throughput Algorithmic Benchmark & Profiling Engine",
    layout="wide",
)
st.title("High-Throughput Algorithmic Benchmark & Profiling Engine")
st.caption("Quadratic reference versus linear hash-set processing")

controls, results_column = st.columns([1, 2], gap="large")
with controls:
    size = st.slider(
        "Dataset size (N)",
        min_value=100,
        max_value=10_000,
        value=1_000,
        step=100,
    )
    duplicate_rate = st.slider(
        "Duplicate rate",
        min_value=0.0,
        max_value=0.9,
        value=0.3,
        step=0.05,
    )
    record_kind = st.radio(
        "Record type", ("numeric", "string"), horizontal=True
    )
    if st.button("Run benchmark", type="primary", use_container_width=True):
        try:
            with st.spinner("Generating workload and collecting telemetry..."):
                st.session_state["benchmark_result"] = benchmark_workload(
                    size=size,
                    duplicate_rate=duplicate_rate,
                    kind=record_kind,
                )
        except MalformedWorkloadError as error:
            st.error(f"Workload rejected: {error}")
        except Exception as error:
            st.error(f"Benchmark failed: {type(error).__name__}: {error}")

telemetry: dict[str, Any] | None = st.session_state.get("benchmark_result")
if telemetry is None:
    with results_column:
        st.info(
            "Choose a workload and run the benchmark to inspect measured results."
        )
else:
    with results_column:
        baseline = telemetry["baseline"]
        optimized = telemetry["optimized"]
        metric_columns = st.columns(3)
        baseline_value = baseline["wall_median_microseconds"]
        optimized_value = optimized["wall_median_microseconds"]
        metric_columns[0].metric(
            "Baseline O(N^2)",
            (
                f"{baseline_value:,.1f} us"
                if baseline_value is not None
                else "Aborted"
            ),
        )
        metric_columns[1].metric(
            "Optimized O(N)",
            (
                f"{optimized_value:,.1f} us"
                if optimized_value is not None
                else "Unavailable"
            ),
        )
        speedup = telemetry["speedup_factor"]
        metric_columns[2].metric(
            "Measured speedup",
            f"{speedup:,.2f}x" if speedup is not None else "Not available",
        )
        st.write(
            f"Parity verified: **{telemetry['parity_verified']}** · "
            f"Duplicates found: **{telemetry['duplicate_count']:,}** · "
            f"Trials: **{telemetry['requested_trials']}** after "
            f"**{telemetry['warmups']}** warmups"
        )
        if baseline["status"] == "aborted":
            st.warning(
                "The quadratic baseline was stopped by its safety clamp. "
                + baseline.get("error", "No baseline samples were collected.")
            )

    baseline_peak = telemetry["baseline"]["peak_memory_kb"]
    optimized_peak = telemetry["optimized"]["peak_memory_kb"]
    if baseline_peak is not None and optimized_peak is not None:
        left, right = st.columns(2)
        maximum_peak = max(baseline_peak, optimized_peak, 1.0)
        for column, label, peak in (
            (left, "Baseline peak traced memory", baseline_peak),
            (right, "Optimized peak traced memory", optimized_peak),
        ):
            column.metric(label, f"{peak:,.1f} KB ({peak / 1024:,.3f} MB)")
            column.progress(min(peak / maximum_peak, 1.0))

    chart_rows = []
    for label, metrics in (
        ("Quadratic baseline", telemetry["baseline"]),
        ("Linear hash set", telemetry["optimized"]),
    ):
        value = metrics["wall_median_microseconds"]
        if value is not None:
            chart_rows.append(
                {"Algorithm": label, "Median latency (us)": value}
            )
    if chart_rows:
        st.subheader("Latency comparison")
        chart_frame = pd.DataFrame(chart_rows).set_index("Algorithm")
        st.bar_chart(chart_frame)

    st.subheader("Benchmark telemetry")
    telemetry_rows = [
        {
            "Algorithm": label,
            "Status": metrics["status"],
            "Trials": metrics["trial_count"],
            "Median wall (us)": metrics["wall_median_microseconds"],
            "Wall stdev (s)": metrics["wall_standard_deviation_seconds"],
            "Median CPU (us)": metrics["cpu_median_microseconds"],
            "Peak memory (KB)": metrics["peak_memory_kb"],
            "Allocation delta (bytes)": metrics["allocation_diff_bytes"],
            "GC collections": metrics["gc_collection_delta"],
            "Primitive calls": metrics["primitive_calls"],
        }
        for label, metrics in (
            ("Quadratic baseline", telemetry["baseline"]),
            ("Linear hash set", telemetry["optimized"]),
        )
    ]
    st.dataframe(telemetry_rows, use_container_width=True, hide_index=True)

    memory_savings = telemetry["memory_savings_percent"]
    st.write(
        "Peak memory change: "
        + (
            f"{memory_savings:.2f}% savings"
            if memory_savings is not None and memory_savings >= 0
            else (
                f"{abs(memory_savings):.2f}% additional optimized allocation"
                if memory_savings is not None
                else "not available"
            )
        )
    )
    st.write("Cache telemetry", telemetry["cache"])

    with st.expander("cProfile cumulative-time details"):
        for label, metrics in (
            ("Baseline", telemetry["baseline"]),
            ("Optimized", telemetry["optimized"]),
        ):
            st.markdown(f"**{label}**")
            if metrics["profile_rows"]:
                st.dataframe(metrics["profile_rows"], use_container_width=True)
            else:
                st.write("No profile was collected.")

    download_json, download_csv = st.columns(2)
    download_json.download_button(
        "Export JSON",
        data=export_json(telemetry),
        file_name="benchmark-telemetry.json",
        mime="application/json",
        use_container_width=True,
    )
    download_csv.download_button(
        "Export CSV",
        data=export_csv(telemetry),
        file_name="benchmark-telemetry.csv",
        mime="text/csv",
        use_container_width=True,
    )
