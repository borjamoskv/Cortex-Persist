"""
CORTEX v4.0 — Prometheus Metrics.

Lightweight metrics middleware for the CORTEX API.
No prometheus_client dependency — uses a simple in-memory registry
that exposes a /metrics endpoint in Prometheus text format.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any

_HISTOGRAM_MAX_OBSERVATIONS = 1000


@dataclass
class MetricsRegistry:
    """Simple in-memory metrics registry (no external deps)."""

    _counters: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    _histograms: dict[str, deque[float]] = field(
        default_factory=lambda: defaultdict(lambda: deque(maxlen=_HISTOGRAM_MAX_OBSERVATIONS))
    )
    _hist_count: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    _hist_sum: dict[str, float] = field(default_factory=lambda: defaultdict(float))
    _gauges: dict[str, float] = field(default_factory=lambda: defaultdict(float))

    def inc(self, name: str, labels: dict[str, str] | None = None, value: int = 1) -> None:
        """Increment a counter."""
        key = self._key(name, labels)
        self._counters[key] += value

    def observe(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Record a histogram observation (capped circular buffer)."""
        key = self._key(name, labels)
        self._histograms[key].append(value)
        self._hist_count[key] += 1
        self._hist_sum[key] += value

    def set_gauge(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Set a gauge value."""
        key = self._key(name, labels)
        self._gauges[key] = value

    def _key(self, name: str, labels: dict[str, str] | None = None) -> str:
        if not labels:
            return name
        label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    def to_prometheus(self) -> str:
        """Render all metrics in Prometheus text exposition format."""
        lines: list[str] = []

        # Counters
        seen_counter_names: set[str] = set()
        for key, value in sorted(self._counters.items()):
            base_name = key.split("{")[0]
            if base_name not in seen_counter_names:
                lines.append(f"# TYPE {base_name} counter")
                seen_counter_names.add(base_name)
            lines.append(f"{key} {value}")

        # Gauges
        seen_gauge_names: set[str] = set()
        for key, value in sorted(self._gauges.items()):
            base_name = key.split("{")[0]
            if base_name not in seen_gauge_names:
                lines.append(f"# TYPE {base_name} gauge")
                seen_gauge_names.add(base_name)
            lines.append(f"{key} {value:.2f}")

        # Histograms (simplified: sum + count)
        seen_hist_names: set[str] = set()
        for key in sorted(self._histograms):
            base_name = key.split("{")[0]
            if base_name not in seen_hist_names:
                lines.append(f"# TYPE {base_name} summary")
                seen_hist_names.add(base_name)
            count = self._hist_count.get(key, 0)
            total = self._hist_sum.get(key, 0.0)
            if count > 0:
                lines.append(f"{key}_count {count}")
                lines.append(f"{key}_sum {total:.4f}")
                lines.append(f"{key}_avg {total / count:.4f}")

        return "\n".join(lines) + "\n"

    def reset(self) -> None:
        """Reset all metrics."""
        self._counters.clear()
        self._histograms.clear()
        self._hist_count.clear()
        self._hist_sum.clear()
        self._gauges.clear()


# Global singleton
metrics = MetricsRegistry()


class MetricsMiddleware:
    """ASGI middleware for tracking request metrics."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict, receive: Any, send: Any):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "unknown")
        method = scope.get("method", "GET")

        # Skip metrics endpoint itself
        if path == "/metrics":
            await self.app(scope, receive, send)
            return

        start = time.perf_counter()
        status_code = 200

        async def send_wrapper(message: dict):
            nonlocal status_code
            if message.get("type") == "http.response.start":
                status_code = message.get("status", 200)
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            status_code = 500
            raise
        finally:
            duration = time.perf_counter() - start
            labels = {"method": method, "path": path, "status": str(status_code)}
            metrics.inc("cortex_http_requests_total", labels)
            metrics.observe("cortex_http_request_duration_seconds", duration, labels)
