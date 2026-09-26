"""
Enterprise Performance-Optimized Data Processing Engine
Author: Akshya Gupta (YuvaIntern Junior Python Developer Track - Week 4)
Features: O(N) Hash-Set Indices, Memory Buffer Allocation, Generator Streams
"""

from __future__ import annotations
import io
import time
import random
import tracemalloc
from typing import List, Set, Tuple, Dict, Any

class OptimizedDataEngine:
    @staticmethod
    def generate_workload(size: int = 10000, seed: int = 42) -> List[int]:
        random.seed(seed)
        return [random.randint(1, size // 2) for _ in range(size)]

    @staticmethod
    def find_duplicates_linear(data: List[int]) -> List[int]:
        """
        O(N) single-pass duplicate detector using dual hash-sets.
        Eliminates quadratic linear scans over unbounded arrays.
        """
        seen: Set[int] = set()
        duplicates: Set[int] = set()
        for item in data:
            if item in seen:
                duplicates.add(item)
            else:
                seen.add(item)
        return list(duplicates)

    @staticmethod
    def buffer_stream_concatenation(iterations: int = 25000) -> int:
        """
        Memory-efficient string aggregation using C-level preallocated str.join.
        Avoids repeated immutable string buffer reallocations.
        """
        return len(",".join(str(i) for i in range(iterations)) + ",")

    @classmethod
    def run_instrumented_pipeline(cls, data_size: int = 8000, str_iters: int = 20000) -> Dict[str, Any]:
        tracemalloc.start()
        start_time = time.perf_counter()

        dataset = cls.generate_workload(size=data_size)
        duplicates = cls.find_duplicates_linear(dataset)
        str_len = cls.buffer_stream_concatenation(iterations=str_iters)

        execution_duration = time.perf_counter() - start_time
        current_mem, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        return {
            "duplicate_count": len(duplicates),
            "string_buffer_length": str_len,
            "duration_seconds": round(execution_duration, 5),
            "peak_memory_kb": round(peak_mem / 1024, 2)
        }

if __name__ == "__main__":
    metrics = OptimizedDataEngine.run_instrumented_pipeline()
    print("[Engine Output] Optimized execution finished:")
    for k, v in metrics.items():
        print(f"  • {k}: {v}")
