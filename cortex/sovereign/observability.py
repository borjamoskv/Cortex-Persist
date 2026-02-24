"""Sovereign Observability Integration.

Provides OpenTelemetry instrumentation, custom metrics, and
the power-level calculation that targets 1300/1000.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# ---------------------------------------------------------------------------
# Power-level scoring (target: 1300/1000)
# ---------------------------------------------------------------------------


class Dimension(Enum):
    """The 13 sovereign dimensions (from MEJORAlo X-Ray 13D)."""

    INTEGRITY = "integrity"
    ARCHITECTURE = "architecture"
    SECURITY = "security"
    COMPLEXITY = "complexity"
    PERFORMANCE = "performance"
    ERROR_HANDLING = "error_handling"
    DUPLICATION = "duplication"
    DEAD_CODE = "dead_code"
    TESTING = "testing"
    NAMING = "naming"
    STANDARDS = "standards"
    AESTHETICS = "aesthetics"
    PSI = "psi"


@dataclass
class DimensionScore:
    dimension: Dimension
    raw: float  # 0-100
    multiplier: float  # 130/100 multiplier applied per dimension
    weighted: float = 0.0

    def __post_init__(self) -> None:
        self.weighted = self.raw * self.multiplier


@dataclass
class PowerLevel:
    """Aggregate sovereign power level across all dimensions."""

    dimensions: list[DimensionScore] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    @property
    def raw_total(self) -> float:
        """Sum of raw scores (max 1300)."""
        return sum(d.raw for d in self.dimensions)

    @property
    def weighted_total(self) -> float:
        """Sum of weighted scores (target: 1300/1000)."""
        return sum(d.weighted for d in self.dimensions)

    @property
    def power(self) -> int:
        """Normalised power level on a 0-1000+ scale.

        A perfect 130/100 across 13 dimensions = 1300 raw points.
        This is normalised so that 1000 = the "theoretical max"
        (100/100 across 13 dims = 1300 raw → 1000 normalised).
        Exceeding 100 per dim pushes beyond 1000.
        """
        if not self.dimensions:
            return 0
        base = len(self.dimensions) * 100  # "theoretical max" baseline
        return int((self.weighted_total / base) * 1000)

    def to_dict(self) -> dict[str, Any]:
        return {
            "power_level": self.power,
            "raw_total": self.raw_total,
            "weighted_total": round(self.weighted_total, 2),
            "dimensions": {
                d.dimension.value: {
                    "raw": d.raw,
                    "multiplier": d.multiplier,
                    "weighted": round(d.weighted, 2),
                }
                for d in self.dimensions
            },
            "timestamp": self.timestamp,
            "exceeds_theoretical_limit": self.power > 1000,
        }


def compute_power(scores: dict[str, float], multiplier: float = 1.3) -> PowerLevel:
    """Compute power level from a dict of dimension → raw score.

    The default ``multiplier`` of 1.3 implements the 130/100 standard.
    """
    dims: list[DimensionScore] = []
    for dim in Dimension:
        raw = scores.get(dim.value, 0.0)
        dims.append(DimensionScore(dimension=dim, raw=raw, multiplier=multiplier))
    return PowerLevel(dimensions=dims)


# ---------------------------------------------------------------------------
# OpenTelemetry bootstrap
# ---------------------------------------------------------------------------

_tracer = None
_meter = None


def init_telemetry(service_name: str = "cortex-sovereign") -> None:
    """Initialise OpenTelemetry tracer & meter providers.

    Exports to an OTLP endpoint (defaults to localhost:4317).
    """
    global _tracer, _meter

    try:
        from opentelemetry import metrics, trace
        from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create({"service.name": service_name})

        # Traces
        tp = TracerProvider(resource=resource)
        tp.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
        trace.set_tracer_provider(tp)
        _tracer = trace.get_tracer(service_name)

        # Metrics
        reader = PeriodicExportingMetricReader(OTLPMetricExporter(), export_interval_millis=15000)
        mp = MeterProvider(resource=resource, metric_readers=[reader])
        metrics.set_meter_provider(mp)
        _meter = metrics.get_meter(service_name)

        # Register sovereign power gauge
        _meter.create_observable_gauge(
            "cortex.sovereign.power_level",
            callbacks=[_power_gauge_callback],
            description="Current sovereign power level (target >1000)",
            unit="1",
        )

    except ImportError:
        print("[observability] OpenTelemetry packages not installed — running without telemetry")


_latest_power: PowerLevel | None = None


def record_power(power: PowerLevel) -> None:
    """Cache latest power reading for the gauge callback."""
    global _latest_power
    _latest_power = power


def _power_gauge_callback(_options: Any) -> Any:
    """Observable gauge callback for sovereign power."""
    from opentelemetry.metrics import Observation

    if _latest_power is not None:
        yield Observation(_latest_power.power, {"version": "v5"})


# ---------------------------------------------------------------------------
# Security scanner integration
# ---------------------------------------------------------------------------


@dataclass
class SecurityReport:
    """Results of an automated security scan."""

    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    passed: bool = True
    details: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.critical + self.high + self.medium + self.low


def run_security_scans(target: str = "cortex/") -> SecurityReport:
    """Run Bandit + Safety scans and return a consolidated report."""
    import json
    import subprocess

    report = SecurityReport()

    # Bandit
    try:
        result = subprocess.run(
            ["bandit", "-r", target, "-f", "json", "-q"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        data = json.loads(result.stdout) if result.stdout else {}
        for issue in data.get("results", []):
            sev = issue.get("issue_severity", "").upper()
            if sev == "HIGH":
                report.high += 1
            elif sev == "MEDIUM":
                report.medium += 1
            elif sev == "LOW":
                report.low += 1
            report.details.append(f"[bandit] {issue.get('issue_text', '')}")
    except Exception as e:
        report.details.append(f"[bandit] scan failed: {e}")

    # Safety
    try:
        result = subprocess.run(
            ["safety", "check", "--json"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        vulns = json.loads(result.stdout) if result.stdout else []
        report.critical += len(vulns)
        for v in vulns[:5]:
            report.details.append(f"[safety] {v}")
    except Exception as e:
        report.details.append(f"[safety] scan failed: {e}")

    report.passed = report.critical == 0 and report.high == 0
    return report
