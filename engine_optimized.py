"""Linear-time hash-set algorithms, streaming helpers, and cached digests."""

from __future__ import annotations

import hashlib
from collections.abc import Hashable, Iterable, Iterator
from functools import lru_cache
from typing import TypeVar

from performance_exceptions import MalformedWorkloadError

Value = TypeVar("Value", bound=Hashable)


def find_duplicates_linear(values: Iterable[Value]) -> list[Value]:
    """Return unique duplicate values in first-repeat order using hash sets."""
    seen: set[Value] = set()
    duplicate_set: set[Value] = set()
    duplicates: list[Value] = []
    for index, value in enumerate(values):
        try:
            if value in seen:
                if value not in duplicate_set:
                    duplicate_set.add(value)
                    duplicates.append(value)
            else:
                seen.add(value)
        except TypeError as error:
            raise MalformedWorkloadError(
                "Workload values must be hashable records.",
                {"index": index, "received_type": type(value).__name__},
            ) from error
    return duplicates


def match_values_linear(
    left: Iterable[Value],
    right: Iterable[Value],
) -> list[Value]:
    """Return unique left-side records present in the right-side hash set."""
    try:
        right_values = set(right)
    except TypeError as error:
        raise MalformedWorkloadError(
            "Right-side workload values must be hashable records."
        ) from error
    matches: list[Value] = []
    matched: set[Value] = set()
    for index, value in enumerate(left):
        try:
            if value in right_values and value not in matched:
                matched.add(value)
                matches.append(value)
        except TypeError as error:
            raise MalformedWorkloadError(
                "Left-side workload values must be hashable records.",
                {"index": index, "received_type": type(value).__name__},
            ) from error
    return matches


def concatenate_join(parts: Iterable[str]) -> str:
    """Aggregate string parts with one C-level join allocation."""
    validated: list[str] = []
    for index, part in enumerate(parts):
        if not isinstance(part, str):
            raise MalformedWorkloadError(
                "String aggregation requires string parts.",
                {"index": index, "received_type": type(part).__name__},
            )
        validated.append(part)
    return "".join(validated)


def iter_chunks(
    values: Iterable[Value], chunk_size: int
) -> Iterator[list[Value]]:
    """Yield bounded lists from an iterable without materializing the source."""
    if (
        isinstance(chunk_size, bool)
        or not isinstance(chunk_size, int)
        or chunk_size < 1
    ):
        raise MalformedWorkloadError(
            "Chunk size must be a positive integer.",
            {"chunk_size": chunk_size},
        )
    chunk: list[Value] = []
    for value in values:
        chunk.append(value)
        if len(chunk) == chunk_size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


def iter_unique(values: Iterable[Value]) -> Iterator[Value]:
    """Lazily yield each hashable record once, retaining a seen set."""
    seen: set[Value] = set()
    for index, value in enumerate(values):
        try:
            if value not in seen:
                seen.add(value)
                yield value
        except TypeError as error:
            raise MalformedWorkloadError(
                "Streaming records must be hashable.",
                {"index": index, "received_type": type(value).__name__},
            ) from error


@lru_cache(maxsize=16_384)
def cached_digest(payload: str) -> str:
    """Return a cached SHA-256 digest for repeated immutable string payloads."""
    if not isinstance(payload, str):
        raise MalformedWorkloadError("Cached digest input must be a string.")
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _cache_telemetry() -> dict[str, int | None]:
    info = cached_digest.cache_info()
    return {
        "hits": info.hits,
        "misses": info.misses,
        "maxsize": info.maxsize,
        "currsize": info.currsize,
    }


cached_digest.cache_telemetry = _cache_telemetry  # type: ignore[attr-defined]


__all__ = [
    "cached_digest",
    "concatenate_join",
    "find_duplicates_linear",
    "iter_chunks",
    "iter_unique",
    "match_values_linear",
]
