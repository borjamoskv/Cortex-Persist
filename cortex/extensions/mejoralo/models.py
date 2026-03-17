"""Data types for MEJORAlo engine."""

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = [
    "DimensionResult",
    "ScanResult",
    "ShipResult",
    "ShipSeal",
    "AntipatternFinding",
    "AntipatternReport",
    "MacSnapshot",
]


@dataclass
class DimensionResult:
    """Result for a single X-Ray dimension."""

    name: str
    score: int  # 0-100, higher is better
    weight: str  # "critical", "high", "medium", "low"
    findings: list[str] = field(default_factory=list)


@dataclass
class ScanResult:
    """Full X-Ray 13D scan result."""

    project: str
    stack: str
    score: int  # Weighted average 0-100
    dimensions: list[DimensionResult]
    dead_code: bool  # True if score < 50
    total_files: int = 0
    total_loc: int = 0
    brutal: bool = False


@dataclass
class ShipSeal:
    """Result for a single Ship Gate seal."""

    name: str
    passed: bool
    detail: str = ""


@dataclass
class ShipResult:
    """Ship Gate (7 Seals) result."""

    project: str
    ready: bool
    seals: list[ShipSeal]
    passed: int = 0
    total: int = 7


@dataclass
class AntipatternFinding:
    """A single antipattern detection."""

    scanner: str  # Which scanner found it
    severity: str  # "critical", "high", "medium", "low"
    file: str  # Relative path
    line: int  # Line number
    message: str  # Human-readable description
    fix_hint: str  # Suggested fix


@dataclass
class AntipatternReport:
    """Aggregate report from all scanners."""

    findings: list[AntipatternFinding] = field(default_factory=list)
    files_scanned: int = 0
    scanners_run: int = 0

    @property
    def total(self) -> int:
        return len(self.findings)

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "critical")

    @property
    def high_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "high")

    def by_severity(self) -> dict[str, list[AntipatternFinding]]:
        result: dict[str, list[AntipatternFinding]] = {}
        for f in self.findings:
            result.setdefault(f.severity, []).append(f)
        return result

    def score_penalty(self) -> int:
        """Calculate penalty points for MEJORAlo score integration."""
        penalties = {"critical": 15, "high": 8, "medium": 3, "low": 1}
        return sum(penalties.get(f.severity, 1) for f in self.findings)


@dataclass
class MacSnapshot:
    """Live macOS system telemetry snapshot."""

    platform: str  # "darwin" or "unsupported"
    cpu_percent: float  # 0.0-100.0
    memory_pressure: str  # "ok" | "warn" | "critical"
    thermal_state: str  # "Nominal" | "Fair" | "Serious" | "Critical"
    process_count: int  # Number of running processes
    ax_trusted: bool  # Accessibility permissions granted
    gpu_active: bool  # Discrete GPU active
    timestamp: str  # ISO8601 UTC timestamp
