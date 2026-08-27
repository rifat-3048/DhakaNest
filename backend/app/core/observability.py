"""Small dependency-free observability helpers for local and hosted use."""

import json
import logging
from datetime import datetime, timezone
from collections import defaultdict
from contextvars import ContextVar
from threading import Lock
from typing import Any


request_id_context: ContextVar[str] = ContextVar("request_id", default="system")
logger = logging.getLogger("dhakanest.routing")
ROUTING_COUNTERS = (
    "routing_requests_total",
    "routing_failures_total",
    "routing_cache_hits_total",
    "routing_cache_misses_total",
    "routing_fallback_total",
    "routing_circuit_open_total",
)


class RoutingMetrics:
    """Thread-safe process-local counters and latency aggregates."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._counters: dict[str, int] = defaultdict(int)
        self._latency_total_ms = 0.0
        self._latency_samples = 0

    def increment(self, metric: str, amount: int = 1) -> None:
        with self._lock:
            self._counters[metric] += amount

    def observe_latency(self, duration_ms: float) -> None:
        with self._lock:
            self._latency_total_ms += duration_ms
            self._latency_samples += 1

    def snapshot(self) -> dict[str, int | float]:
        with self._lock:
            values: dict[str, int | float] = {
                metric: self._counters.get(metric, 0)
                for metric in ROUTING_COUNTERS
            }
            values["routing_latency_samples"] = self._latency_samples
            values["routing_latency_average_ms"] = round(
                self._latency_total_ms / self._latency_samples, 2
            ) if self._latency_samples else 0.0
            return values

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()
            self._latency_total_ms = 0.0
            self._latency_samples = 0


routing_metrics = RoutingMetrics()


def log_routing_event(**fields: Any) -> None:
    """Emit one safe JSON event with the current request correlation ID."""
    safe_fields = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": "INFO",
        "event": "routing",
        "request_id": request_id_context.get(),
        **fields,
    }
    logger.info(json.dumps(safe_fields, sort_keys=True, default=str))
