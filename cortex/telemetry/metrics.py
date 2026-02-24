"""
CORTEX v5.0 — Prometheus Metrics.

Lightweight metrics middleware for the CORTEX API.
No prometheus_client dependency — uses a simple in-memory registry
that exposes a /metrics endpoint in Prometheus text format.

Critical metrics (ledger errors, consensus failures) are also persisted
to CORTEX as ``system_health`` facts so they survive process restarts
and remain queryable during forensic analysis.
"""

import asyncio
import logging
import sqlite3
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any

__all__ = ["MetricsRegistry", "MetricsMiddleware"]

logger = logging.getLogger("cortex")

_HISTOGRAM_MAX_OBSERVATIONS = 1000
_CRITICAL_DEBOUNCE_SECONDS = 60

# Metric names that will be persisted as system_health facts.
CRITICAL_METRICS: set[str] = {
    "cortex_ledger_violations_total",
    "cortex_ledger_checkpoint_failures_total",
    "cortex_consensus_failures_total",
    "cortex_integrity_checks_total",
}


@dataclass
class MetricsRegistry:
    """Simple in-memory metrics registry (no external deps).

    When a *critical* metric is incremented, this registry also persists
    the event as a ``system_health`` fact in CORTEX (debounced to avoid
    flooding the DB during cascading failures).
    """

    _counters: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    _histograms: dict[str, deque[float]] = field(
        default_factory=lambda: defaultdict(lambda: deque(maxlen=_HISTOGRAM_MAX_OBSERVATIONS))
    )
    _hist_count: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    _hist_sum: dict[str, float] = field(default_factory=lambda: defaultdict(float))
    _gauges: dict[str, float] = field(default_factory=lambda: defaultdict(float))
    # Critical-metrics persistence
    _engine: Any = field(default=None, repr=False)
    _last_persisted: dict[str, float] = field(default_factory=dict)

    # ─── Engine injection ─────────────────────────────────────────

    def set_engine(self, engine: Any) -> None:
        """Inject the CortexEngine so critical metrics can be persisted.

        Called once during ``CortexEngine.init_db()``.  Avoids circular
        imports by accepting ``Any``.
        """
        self._engine = engine

    # ─── Core metric operations ───────────────────────────────────

    def inc(
        self,
        name: str,
        labels: dict[str, str] | None = None,
        value: int = 1,
        *,
        meta: dict[str, Any] | None = None,
    ) -> None:
        """Increment a counter.

        If *name* is in ``CRITICAL_METRICS`` and an engine is available,
        the event is also scheduled for persistence as a ``system_health``
        fact (debounced).
        """
        key = self._key(name, labels)
        self._counters[key] += value

        if name in CRITICAL_METRICS and self._engine is not None:
            self._schedule_persist(name, key, labels, meta)

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

    # ─── Critical metrics persistence ─────────────────────────────

    def _schedule_persist(
        self,
        name: str,
        key: str,
        labels: dict[str, str] | None,
        meta: dict[str, Any] | None,
    ) -> None:
        """Schedule an async persist if debounce window has elapsed."""
        now = time.monotonic()
        last = self._last_persisted.get(key, 0.0)
        if now - last < _CRITICAL_DEBOUNCE_SECONDS:
            return
        self._last_persisted[key] = now
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._persist_critical(name, key, labels, meta))
        except RuntimeError:
            # No running loop — skip persistence (e.g. during tests).
            pass

    async def _persist_critical(
        self,
        name: str,
        key: str,
        labels: dict[str, str] | None,
        extra_meta: dict[str, Any] | None,
    ) -> None:
        """Persist a critical metric event as a ``system_health`` fact."""
        try:
            counter_val = self._counters.get(key, 0)
            fact_meta: dict[str, Any] = {
                "metric": name,
                "key": key,
                "labels": labels or {},
                "counter_value": counter_val,
            }
            if extra_meta:
                fact_meta.update(extra_meta)

            labels_str = f" ({', '.join(f'{k}={v}' for k, v in labels.items())})" if labels else ""
            content = f"[METRIC] {name}: {counter_val}{labels_str}"

            await self._engine.store(
                project="__system__",
                content=content,
                fact_type="system_health",
                tags=["metrics", "critical", name],
                confidence="verified",
                source="metrics_registry",
                meta=fact_meta,
            )
            logger.debug("Persisted critical metric: %s", key)
        except (sqlite3.Error, OSError):
            # Never let metric persistence crash the caller.
            logger.warning("Failed to persist critical metric %s", key, exc_info=True)

    # ─── Prometheus rendering ─────────────────────────────────────

    def to_prometheus(self) -> str:
        """Render all metrics in Prometheus text exposition format."""
        lines: list[str] = []
        lines.extend(self._render_counters())
        lines.extend(self._render_gauges())
        lines.extend(self._render_histograms())
        return "\n".join(lines) + "\n"

    def _render_counters(self) -> list[str]:
        lines: list[str] = []
        seen_names: set[str] = set()
        for key, value in sorted(self._counters.items()):
            base_name = key.split("{")[0]
            if base_name not in seen_names:
                lines.append(f"# TYPE {base_name} counter")
                seen_names.add(base_name)
            lines.append(f"{key} {value}")
        return lines

    def _render_gauges(self) -> list[str]:
        lines: list[str] = []
        seen_names: set[str] = set()
        for key, value in sorted(self._gauges.items()):
            base_name = key.split("{")[0]
            if base_name not in seen_names:
                lines.append(f"# TYPE {base_name} gauge")
                seen_names.add(base_name)
            lines.append(f"{key} {value:.2f}")
        return lines

    def _render_histograms(self) -> list[str]:
        lines: list[str] = []
        seen_names: set[str] = set()
        for key in sorted(self._histograms):
            base_name = key.split("{")[0]
            if base_name not in seen_names:
                lines.append(f"# TYPE {base_name} summary")
                seen_names.add(base_name)

            count = self._hist_count.get(key, 0)
            if count <= 0:
                continue

            total = self._hist_sum.get(key, 0.0)
            lines.extend(self._render_quantiles(key, self._histograms[key]))
            lines.append(f"{key}_count {count}")
            lines.append(f"{key}_sum {total:.4f}")
        return lines

    def _render_quantiles(self, key: str, observations: deque[float]) -> list[str]:
        """Helper to render summary quantiles without deep nesting."""
        lines = []
        obs_sorted = sorted(observations)
        for quantile in (0.5, 0.95, 0.99):
            idx = min(int(quantile * len(obs_sorted)), len(obs_sorted) - 1)
            val = obs_sorted[idx]
            # Embed quantile label into key
            if "{" in key:
                q_key = key.replace("}", f',quantile="{quantile}"}}')
            else:
                q_key = f'{key}{{quantile="{quantile}"}}'
            lines.append(f"{q_key} {val:.6f}")
        return lines

    def reset(self) -> None:
        """Reset all metrics."""
        self._counters.clear()
        self._histograms.clear()
        self._hist_count.clear()
        self._hist_sum.clear()
        self._gauges.clear()
        self._last_persisted.clear()


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
        except (sqlite3.Error, OSError):
            status_code = 500
            raise
        finally:
            duration = time.perf_counter() - start
            labels = {"method": method, "path": path, "status": str(status_code)}
            metrics.inc("cortex_http_requests_total", labels)
            metrics.observe("cortex_http_request_duration_seconds", duration, labels)
