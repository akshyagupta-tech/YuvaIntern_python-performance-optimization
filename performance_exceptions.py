"""Structured exceptions raised by the performance benchmark engine."""

from __future__ import annotations

from typing import Any, Mapping


class PerformanceEngineError(Exception):
    """Base exception carrying machine-readable telemetry context."""

    def __init__(
        self,
        message: str,
        context: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.context = dict(context or {})


class BenchmarkTimeoutError(PerformanceEngineError, TimeoutError):
    """Raised when quadratic work reaches its configured safety limit."""


class AllocationBudgetExceededException(PerformanceEngineError, MemoryError):
    """Raised when a profiled call exceeds its allocation budget."""


class MalformedWorkloadError(PerformanceEngineError, ValueError):
    """Raised when workload data or benchmark options are invalid."""
