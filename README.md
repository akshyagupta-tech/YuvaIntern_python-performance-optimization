# High-Throughput Algorithmic Benchmark & Profiling Engine

**Intern:** Akshya Gupta  
**Track:** YuvaIntern — Junior Python Developer  
**Milestone:** Week 4 Task

## Overview
The Week 4 project compares a deadline-bounded quadratic reference implementation
with an average-linear hash-set pipeline. It includes reproducible synthetic
workloads, warmup and trial statistics, wall/CPU timing, `tracemalloc`, `cProfile`,
GC telemetry, streaming helpers, a cached digest utility, and JSON/CSV exports.

## Modules
- `engine_baseline.py`: O(N^2) reference algorithms with item and time guards.
- `engine_optimized.py`: O(N) hash-set algorithms, lazy chunk helpers, join aggregation, and cached digests.
- `profiler.py`: Wall/CPU timing, peak and differential allocations, GC churn, and cProfile rows.
- `benchmarks.py`: Workload generation, parity verification, statistical trials, speedup and memory metrics, JSON/CSV export.
- `performance_exceptions.py`: Context-carrying benchmark, allocation, and workload exceptions.
- `test_performance.py`: Focused parity, safety, telemetry, workload, and regression tests.
- `app.py`: Interactive Streamlit dashboard with size and duplicate-rate controls.
- Legacy scripts and `core/week4_profiler.py` remain available for existing callers and lessons.

## Setup
```bash
python3 -m pip install -r requirements.txt
```

## Run Tests
```bash
python3 -m unittest -v test_performance.py
python3 -m unittest discover -v
```

## Run the Web Dashboard
```bash
streamlit run app.py
```

The dashboard defaults to five warmups and seven measured trials. The quadratic
reference stops at its configured item clamp or time budget; larger workloads
still report optimized measurements and identify the baseline as aborted.

## Run a Command-Line Benchmark
```bash
python3 optimization_benchmark.py
```
