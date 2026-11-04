"""Compatibility wrappers for the quadratic Week 4 reference engine."""

from __future__ import annotations

import random
import time
from collections.abc import Sequence
from typing import Hashable, TypeVar

from engine_baseline import concatenate_iterative, find_duplicates_quadratic

Value = TypeVar("Value", bound=Hashable)


def generate_dataset(size: int = 20_000, seed: int = 42) -> list[int]:
    """Return reproducible integer records without mutating global RNG state."""
    if isinstance(size, bool) or not isinstance(size, int) or size < 0:
        raise ValueError("size must be a non-negative integer")
    generator = random.Random(seed)
    return [generator.randint(1, 10_000) for _ in range(size)]


def find_duplicates_slow(data: Sequence[Value]) -> list[Value]:
    """Preserve the historical API while enforcing baseline safety limits."""
    return find_duplicates_quadratic(data)


def aggregate_string_slow(iterations: int = 30_000) -> int:
    """Return the length produced by repeated string concatenation."""
    if (
        isinstance(iterations, bool)
        or not isinstance(iterations, int)
        or iterations < 0
    ):
        raise ValueError("iterations must be a non-negative integer")
    return len(
        concatenate_iterative(f"{index}," for index in range(iterations))
    )


def process_pipeline() -> float:
    """Run the legacy 5k baseline pipeline with the reference time budget."""
    started = time.perf_counter()
    data = generate_dataset(5_000)
    duplicates = find_duplicates_slow(data)
    string_length = aggregate_string_slow(15_000)
    duration = time.perf_counter() - started
    print(
        "[Slow Pipeline] Found {} duplicates, String length: {}, "
        "Elapsed: {:.4f}s".format(len(duplicates), string_length, duration)
    )
    return duration


if __name__ == "__main__":
    process_pipeline()
