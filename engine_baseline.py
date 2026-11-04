"""Quadratic reference algorithms with bounded execution safeguards."""

from __future__ import annotations

import math
import time
from collections.abc import Hashable, Iterable, Sequence
from typing import TypeVar

from performance_exceptions import (
    BenchmarkTimeoutError,
    MalformedWorkloadError,
)

Value = TypeVar("Value", bound=Hashable)
DEFAULT_BASELINE_MAX_ITEMS = 10_000
DEFAULT_TIME_BUDGET_SECONDS = 0.25
_CHECK_INTERVAL = 256


def _validate_sequence(values: Sequence[Value], name: str) -> None:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise MalformedWorkloadError(
            "Quadratic algorithms require an indexed sequence.",
            {"field": name, "received_type": type(values).__name__},
        )


def _validate_hashability(
    values: Sequence[Value],
    name: str,
    deadline: float,
    item_count: int,
    time_budget_seconds: float,
) -> None:
    for index, value in enumerate(values):
        _check_deadline(
            deadline,
            item_count,
            index,
            time_budget_seconds,
        )
        try:
            hash(value)
        except TypeError as error:
            raise MalformedWorkloadError(
                "Workload values must be hashable records.",
                {
                    "field": name,
                    "index": index,
                    "received_type": type(value).__name__,
                },
            ) from error


def _validate_limits(
    item_count: int,
    max_items: int,
    time_budget_seconds: float,
) -> float:
    if (
        isinstance(max_items, bool)
        or not isinstance(max_items, int)
        or max_items < 1
    ):
        raise MalformedWorkloadError(
            "The quadratic item limit must be a positive integer.",
            {"max_items": max_items},
        )
    if (
        isinstance(time_budget_seconds, bool)
        or not isinstance(time_budget_seconds, (int, float))
        or not math.isfinite(time_budget_seconds)
        or time_budget_seconds <= 0
    ):
        raise MalformedWorkloadError(
            "The quadratic time budget must be positive and finite.",
            {"time_budget_seconds": time_budget_seconds},
        )
    if item_count > max_items:
        raise BenchmarkTimeoutError(
            "Quadratic workload exceeds the configured item safety clamp.",
            {"item_count": item_count, "max_items": max_items},
        )
    return time.perf_counter() + time_budget_seconds


def _check_deadline(
    deadline: float,
    item_count: int,
    comparisons: int,
    time_budget_seconds: float,
) -> None:
    if comparisons % _CHECK_INTERVAL == 0 and time.perf_counter() >= deadline:
        raise BenchmarkTimeoutError(
            "Quadratic workload exceeded its execution time budget.",
            {
                "item_count": item_count,
                "comparisons": comparisons,
                "time_budget_seconds": time_budget_seconds,
            },
        )


def find_duplicates_quadratic(
    values: Sequence[Value],
    other: Sequence[Value] | None = None,
    *,
    max_items: int = DEFAULT_BASELINE_MAX_ITEMS,
    time_budget_seconds: float = DEFAULT_TIME_BUDGET_SECONDS,
) -> list[Value]:
    """Find repeated values or cross-sequence matches using nested scans."""
    _validate_sequence(values, "values")
    if other is not None:
        _validate_sequence(other, "other")
    item_count = len(values) + (len(other) if other is not None else 0)
    deadline = _validate_limits(item_count, max_items, time_budget_seconds)
    _validate_hashability(
        values, "values", deadline, item_count, time_budget_seconds
    )
    if other is not None:
        _validate_hashability(
            other, "other", deadline, item_count, time_budget_seconds
        )
    comparisons = 0
    result: list[Value] = []
    result_seen: set[Value] = set()

    if other is not None:
        for value in values:
            for candidate in other:
                comparisons += 1
                _check_deadline(
                    deadline,
                    item_count,
                    comparisons,
                    time_budget_seconds,
                )
                if value == candidate:
                    if value not in result_seen:
                        result_seen.add(value)
                        result.append(value)
                    break
        return result

    for index, value in enumerate(values):
        _check_deadline(
            deadline,
            item_count,
            comparisons,
            time_budget_seconds,
        )
        for earlier_index in range(index):
            comparisons += 1
            _check_deadline(
                deadline,
                item_count,
                comparisons,
                time_budget_seconds,
            )
            if value == values[earlier_index]:
                if value not in result_seen:
                    result_seen.add(value)
                    result.append(value)
                break
    return result


def concatenate_iterative(parts: Iterable[str]) -> str:
    """Build a string by repeated immutable concatenation for comparison."""
    result = ""
    for index, part in enumerate(parts):
        if not isinstance(part, str):
            raise MalformedWorkloadError(
                "String aggregation requires string parts.",
                {"index": index, "received_type": type(part).__name__},
            )
        result += part
    return result


__all__ = [
    "DEFAULT_BASELINE_MAX_ITEMS",
    "DEFAULT_TIME_BUDGET_SECONDS",
    "concatenate_iterative",
    "find_duplicates_quadratic",
]
