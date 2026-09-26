"""
Legacy Inefficient Data Cruncher (Baseline)
Author: Akshya Gupta (YuvaIntern Junior Python Developer - Week 4)
Contains deliberate bottlenecks: O(N^2) searches, repeated list allocations, slow concatenation.
"""

import time
import random

def generate_dataset(size=20000):
    random.seed(42)
    return [random.randint(1, 10000) for _ in range(size)]

def find_duplicates_slow(data):
    # Bottleneck: O(N^2) complexity using nested list lookups
    duplicates = []
    for i in range(len(data)):
        for j in range(i + 1, len(data)):
            if data[i] == data[j] and data[i] not in duplicates:
                duplicates.append(data[i])
    return duplicates

def aggregate_string_slow(iterations=30000):
    # Bottleneck: Inefficient immutable string concatenation in loop
    result = ""
    for i in range(iterations):
        result += str(i) + ","
    return len(result)

def process_pipeline():
    start = time.perf_counter()
    data = generate_dataset(5000)
    dupes = find_duplicates_slow(data)
    str_len = aggregate_string_slow(15000)
    duration = time.perf_counter() - start
    print(f"[Slow Pipeline] Found {len(dupes)} duplicates, String length: {str_len}, Elapsed: {duration:.4f}s")
    return duration

if __name__ == "__main__":
    process_pipeline()
