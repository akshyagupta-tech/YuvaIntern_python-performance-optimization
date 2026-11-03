"""Compare baseline and optimized duplicate-finding and string-building approaches."""

import cProfile
import pstats
import time


DATA_SIZE = 4_000
STRING_PART_COUNT = 20_000
REPEATS = 3


def find_duplicates_nested(values):
    duplicates = set()
    for index, value in enumerate(values):
        for later_index in range(index + 1, len(values)):
            if value == values[later_index]:
                duplicates.add(value)
                break
    return duplicates


def find_duplicates_hash_set(values):
    seen = set()
    duplicates = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        else:
            seen.add(value)
    return duplicates


def concatenate_with_plus(parts):
    result = ""
    for part in parts:
        result += part
    return result


def concatenate_with_join(parts):
    return "".join(parts)


def measure(callback, *args):
    durations = []
    for _ in range(REPEATS):
        start = time.perf_counter()
        callback(*args)
        durations.append(time.perf_counter() - start)
    return min(durations)


def print_profile(callback, label, *args):
    profiler = cProfile.Profile()
    profiler.enable()
    callback(*args)
    profiler.disable()

    print(f"\n{label} profile:")
    pstats.Stats(profiler).strip_dirs().sort_stats("cumulative").print_stats(5)


def report_comparison(label, baseline, optimized, args):
    baseline_result = baseline(*args)
    optimized_result = optimized(*args)
    assert baseline_result == optimized_result, f"{label} results differ"

    baseline_time = measure(baseline, *args)
    optimized_time = measure(optimized, *args)
    speedup = baseline_time / optimized_time if optimized_time else float("inf")

    print(f"\n{label}")
    print(f"  Baseline:  {baseline_time:.6f}s")
    print(f"  Optimized: {optimized_time:.6f}s")
    print(f"  Speedup:   {speedup:.2f}x")
    print_profile(baseline, "Baseline", *args)
    print_profile(optimized, "Optimized", *args)


def main():
    values = list(range(DATA_SIZE // 2)) * 2
    string_parts = [f"{index}," for index in range(STRING_PART_COUNT)]

    report_comparison(
        "Duplicate finding (nested scan O(N^2) vs hash sets O(N) average)",
        find_duplicates_nested,
        find_duplicates_hash_set,
        (values,),
    )
    report_comparison(
        "String building (+= vs ''.join())",
        concatenate_with_plus,
        concatenate_with_join,
        (string_parts,),
    )


if __name__ == "__main__":
    main()