"""
High-Precision Performance Profiler & Architectural Benchmark Suite
Author: Akshya Gupta (YuvaIntern Junior Python Developer)
"""

import cProfile
import pstats
import io
import json
import time
import tracemalloc
import data_cruncher_slow
from data_cruncher_fast import OptimizedDataEngine

def profile_subsystem(callback, label: str):
    print(f"\n{'='*20} PROFILING: {label} {'='*20}")
    profiler = cProfile.Profile()
    
    tracemalloc.start()
    start_wall = time.perf_counter()
    profiler.enable()

    result = callback()

    profiler.disable()
    wall_duration = time.perf_counter() - start_wall
    _, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    stream = io.StringIO()
    ps = pstats.Stats(profiler, stream=stream).sort_stats('tottime')
    ps.print_stats(6)

    print(stream.getvalue())
    print(f"[Telemetry] Wall-Clock Duration: {wall_duration:.5f}s | Peak Heap: {peak_mem / 1024:.2f} KB")
    return wall_duration, peak_mem / 1024

def compare_string_mechanisms(iterations=25000):
    print("\n--- String Concatenation Paradigm Comparison ---")
    
    # Method A: Inefficient '+='
    t0 = time.perf_counter()
    s_accum = ""
    for i in range(iterations):
        s_accum += str(i) + ","
    t_slow = time.perf_counter() - t0

    # Method B: Preallocated join()
    t1 = time.perf_counter()
    s_join = ",".join(str(i) for i in range(iterations)) + ","
    t_fast = time.perf_counter() - t1

    speedup = t_slow / t_fast if t_fast > 0 else 0.0
    print(f"  • Naive += Loop:      {t_slow:.4f}s")
    print(f"  • Preallocated join: {t_fast:.4f}s (Speedup: {speedup:.1f}x)")
    return {"method_plus_equal_sec": round(t_slow, 4), "method_join_sec": round(t_fast, 4), "speedup": round(speedup, 1)}

def main():
    print("=" * 65)
    print("   YUVAINTERN PERFORMANCE BENCHMARK & SYSTEM OPTIMIZATION HARNESS   ")
    print("=" * 65)

    # 1. Profile Baseline Legacy
    slow_time, slow_mem = profile_subsystem(data_cruncher_slow.process_pipeline, "Legacy Baseline (O(N^2))")

    # 2. Profile Hardened Pipeline
    fast_time, fast_mem = profile_subsystem(OptimizedDataEngine.run_instrumented_pipeline, "Optimized Pipeline (O(N))")

    overall_speedup = slow_time / fast_time if fast_time > 0 else 0.0
    mem_delta = slow_mem - fast_mem

    string_metrics = compare_string_mechanisms()

    telemetry = {
        "candidate": "Akshya Gupta",
        "internship_track": "YuvaIntern Junior Python Developer",
        "baseline_runtime_sec": round(slow_time, 4),
        "optimized_runtime_sec": round(fast_time, 4),
        "overall_speedup_factor": f"{overall_speedup:.2f}x",
        "baseline_peak_mem_kb": round(slow_mem, 2),
        "optimized_peak_mem_kb": round(fast_mem, 2),
        "string_concatenation_analysis": string_metrics
    }

    with open("benchmark_telemetry.json", "w") as f:
        json.dump(telemetry, f, indent=2)

    print("\n" + "=" * 65)
    print("                      EXECUTIVE RESULTS SUMMARY                      ")
    print("=" * 65)
    print(f"Baseline Execution Time:  {slow_time:.4f}s")
    print(f"Optimized Execution Time: {fast_time:.4f}s")
    print(f"Relative Execution Speedup: {overall_speedup:.2f}x faster")
    print(f"Telemetry artifacts dumped to: benchmark_telemetry.json")
    print("=" * 65 + "\n")

if __name__ == "__main__":
    main()
