"""Metric collector registry and built-in collectors.

Adding a metric = creating a class + calling ``registry.register()``.
The monolithic collector is dead. Plugin-based. O(1) lookup.
"""

from __future__ import annotations

import logging
import os
import sqlite3
from pathlib import Path
from typing import Any

from cortex.extensions.health.health_protocol import MetricCollectorProtocol
from cortex.extensions.health.models import HealthThresholds, MetricSnapshot

logger = logging.getLogger("cortex.extensions.health.collector")


# ─── Registry ────────────────────────────────────────────────


class CollectorRegistry:
    """Plugin registry for metric collectors.

    Enforces MetricCollectorProtocol at registration time.
    Duplicate names are rejected.
    """

    def __init__(self) -> None:
        self._collectors: dict[str, MetricCollectorProtocol] = {}

    def register(self, collector: Any) -> None:
        """Register a collector. Rejects non-conforming objects."""
        if not isinstance(collector, MetricCollectorProtocol):
            raise TypeError(
                f"{type(collector).__name__} does not implement MetricCollectorProtocol"
            )
        name = collector.name
        if name in self._collectors:
            raise ValueError(f"Collector '{name}' already registered")
        self._collectors[name] = collector
        logger.debug("Registered health collector: %s", name)

    def unregister(self, name: str) -> None:
        """Remove a collector by name."""
        self._collectors.pop(name, None)

    def list_collectors(self) -> list[str]:
        """Return registered collector names."""
        return list(self._collectors.keys())

    def collect_all(self, db_path: str) -> list[MetricSnapshot]:
        """Run all registered collectors and measure latency."""
        import time

        results: list[MetricSnapshot] = []
        for name, collector in self._collectors.items():
            t0 = time.perf_counter()
            try:
                snap = collector.collect(db_path)
                latency = (time.perf_counter() - t0) * 1000.0

                # Enrich snapshot with collector metadata and timing
                object.__setattr__(snap, "latency_ms", latency)
                if not getattr(snap, "description", None):
                    object.__setattr__(snap, "description", getattr(collector, "description", ""))
                if not getattr(snap, "remediation", None):
                    object.__setattr__(snap, "remediation", getattr(collector, "remediation", ""))

                results.append(snap)
            except Exception as e:  # noqa: BLE001
                latency = (time.perf_counter() - t0) * 1000.0
                logger.warning(
                    "Collector %s failed: %s",
                    name,
                    e,
                )
                results.append(
                    MetricSnapshot(
                        name=name,
                        value=0.0,
                        weight=collector.weight,
                        latency_ms=latency,
                        description=getattr(collector, "description", ""),
                        remediation=f"Error collecting metric: {e}",
                    )
                )
        return results

    def __len__(self) -> int:
        return len(self._collectors)

    def __bool__(self) -> bool:
        """A registry is always truthy, even if empty.

        Prevents the 'registry or default' bug where len==0 makes bool==False.
        """
        return True

    def __contains__(self, name: str) -> bool:
        return name in self._collectors


# ─── Built-in Collectors ─────────────────────────────────────


class DbCollector:
    """Database existence and size check."""

    @property
    def name(self) -> str:
        return "db"

    @property
    def weight(self) -> float:
        return 1.5

    @property
    def description(self) -> str:
        return "Core SQLite database file size and health."

    @property
    def remediation(self) -> str:
        return "Run `cortex gc` or consider archiving old facts."

    def collect(self, db_path: str) -> MetricSnapshot:
        t = HealthThresholds()
        if not db_path or not Path(db_path).exists():
            return MetricSnapshot(
                name=self.name,
                value=0.0,
                weight=self.weight,
            )
        try:
            size_mb = os.path.getsize(db_path) / (1024 * 1024)
        except OSError:
            return MetricSnapshot(
                name=self.name,
                value=0.0,
                weight=self.weight,
            )
        if size_mb < t.db_warn_mb:
            val = 1.0
        elif size_mb < t.db_crit_mb:
            val = 0.8
        else:
            val = 0.5
        return MetricSnapshot(
            name=self.name,
            value=val,
            weight=self.weight,
        )


class LedgerCollector:
    """Ledger integrity via hash chain verification."""

    @property
    def name(self) -> str:
        return "ledger"

    @property
    def weight(self) -> float:
        return 1.2

    @property
    def description(self) -> str:
        return "Cryptographic hash chain integrity check."

    @property
    def remediation(self) -> str:
        return "Run `cortex ledger verify`. If broken, DB may be tampered."

    def collect(self, db_path: str) -> MetricSnapshot:
        if not db_path or not Path(db_path).exists():
            return MetricSnapshot(
                name=self.name,
                value=0.0,
                weight=self.weight,
            )
        try:
            conn = sqlite3.connect(db_path, timeout=2.0)
            conn.row_factory = sqlite3.Row
            try:
                cur = conn.execute("SELECT COUNT(*) as cnt FROM cortex_ledger")
                row = cur.fetchone()
                count = row["cnt"] if row else 0
                if count == 0:
                    return MetricSnapshot(
                        name=self.name,
                        value=0.5,
                        weight=self.weight,
                    )
                cur = conn.execute("SELECT hash FROM cortex_ledger ORDER BY rowid DESC LIMIT 1")
                last = cur.fetchone()
                val = 1.0 if (last and last["hash"]) else 0.7
                return MetricSnapshot(
                    name=self.name,
                    value=val,
                    weight=self.weight,
                )
            finally:
                conn.close()
        except (sqlite3.Error, OSError) as e:
            logger.debug("Ledger check failed: %s", e)
            return MetricSnapshot(
                name=self.name,
                value=0.3,
                weight=self.weight,
            )


class EntropyCollector:
    """Entropy from fact type diversity + volume."""

    @property
    def name(self) -> str:
        return "entropy"

    @property
    def weight(self) -> float:
        return 1.0

    @property
    def description(self) -> str:
        return "Type diversity and information volume (Shannon)."

    @property
    def remediation(self) -> str:
        return "Inject more varied context via ADK or Web tools."

    def collect(self, db_path: str) -> MetricSnapshot:
        t = HealthThresholds()
        if not db_path or not Path(db_path).exists():
            return MetricSnapshot(
                name=self.name,
                value=0.5,
                weight=self.weight,
            )
        try:
            conn = sqlite3.connect(db_path, timeout=2.0)
            try:
                cur = conn.execute(
                    "SELECT COUNT(DISTINCT fact_type) as types, "
                    "COUNT(*) as total FROM facts "
                    "WHERE valid_until IS NULL"
                )
                row = cur.fetchone()
                if not row or row[1] == 0:
                    return MetricSnapshot(
                        name=self.name,
                        value=0.5,
                        weight=self.weight,
                    )
                type_score = min(1.0, row[0] / t.type_diversity)
                vol_score = min(1.0, row[1] / t.fact_target)
                combined = type_score * 0.6 + vol_score * 0.4
                return MetricSnapshot(
                    name=self.name,
                    value=combined,
                    weight=self.weight,
                )
            finally:
                conn.close()
        except (sqlite3.Error, OSError):
            return MetricSnapshot(
                name=self.name,
                value=0.5,
                weight=self.weight,
            )


class FactCountCollector:
    """Active fact volume measurement."""

    @property
    def name(self) -> str:
        return "facts"

    @property
    def weight(self) -> float:
        return 0.8

    @property
    def description(self) -> str:
        return "Total volume of active mnemonic facts."

    @property
    def remediation(self) -> str:
        return "Store more facts to build agent context, or compact if too high."

    def collect(self, db_path: str) -> MetricSnapshot:
        t = HealthThresholds()
        if not db_path or not Path(db_path).exists():
            return MetricSnapshot(
                name=self.name,
                value=0.0,
                weight=self.weight,
            )
        try:
            conn = sqlite3.connect(db_path, timeout=2.0)
            try:
                cur = conn.execute("SELECT COUNT(*) FROM facts WHERE valid_until IS NULL")
                row = cur.fetchone()
                count = row[0] if row else 0
                val = min(1.0, count / t.fact_target)
                return MetricSnapshot(
                    name=self.name,
                    value=val,
                    weight=self.weight,
                )
            finally:
                conn.close()
        except (sqlite3.Error, OSError):
            return MetricSnapshot(
                name=self.name,
                value=0.0,
                weight=self.weight,
            )


class WalCollector:
    """WAL file pressure check."""

    @property
    def name(self) -> str:
        return "wal"

    @property
    def weight(self) -> float:
        return 0.6

    @property
    def description(self) -> str:
        return "Write-Ahead Log size (checkpoint pressure)."

    @property
    def remediation(self) -> str:
        return "Restart daemon or force SQLite PRAGMA wal_checkpoint."

    def collect(self, db_path: str) -> MetricSnapshot:
        t = HealthThresholds()
        if not db_path:
            return MetricSnapshot(
                name=self.name,
                value=1.0,
                weight=self.weight,
            )
        wal_path = Path(f"{db_path}-wal")
        if not wal_path.exists():
            return MetricSnapshot(
                name=self.name,
                value=1.0,
                weight=self.weight,
            )
        try:
            wal_mb = os.path.getsize(wal_path) / (1024 * 1024)
            if wal_mb < t.wal_warn_mb:
                val = 1.0
            elif wal_mb < t.wal_crit_mb:
                val = 0.5
            else:
                val = 0.2
            return MetricSnapshot(
                name=self.name,
                value=val,
                weight=self.weight,
            )
        except OSError:
            return MetricSnapshot(
                name=self.name,
                value=1.0,
                weight=self.weight,
            )


class SystemLoadCollector:
    """OS-level system load (1m/5m/15m) measurement."""

    @property
    def name(self) -> str:
        return "sysload"

    @property
    def weight(self) -> float:
        return 1.0

    @property
    def description(self) -> str:
        return "1-minute system load average vs CPU core count."

    @property
    def remediation(self) -> str:
        return "High load detected. Throttle agent concurrency or pause NightShift."

    def collect(self, db_path: str) -> MetricSnapshot:
        try:
            load_1m, _, _ = os.getloadavg()
            cores = os.cpu_count() or 4

            # Load > Cores means processes are waiting for CPU
            ratio = load_1m / cores

            if ratio < 0.7:
                val = 1.0
            elif ratio < 1.0:
                val = 0.8
            elif ratio < 1.5:
                val = 0.5
            else:
                val = 0.2

            return MetricSnapshot(
                name=self.name,
                value=val,
                weight=self.weight,
                description=f"Load: {load_1m:.2f} (Cores: {cores})",
            )
        except (OSError, AttributeError):
            return MetricSnapshot(
                name=self.name,
                value=1.0,  # Assume healthy if unsupported
                weight=self.weight,
            )


# ─── Default Registry ────────────────────────────────────────

_BUILTINS = [
    DbCollector,
    LedgerCollector,
    EntropyCollector,
    FactCountCollector,
    WalCollector,
    SystemLoadCollector,
]


def create_default_registry() -> CollectorRegistry:
    """Create a registry with all built-in collectors."""
    reg = CollectorRegistry()
    for cls in _BUILTINS:
        reg.register(cls())
    return reg


# ─── Backward-compatible wrapper ─────────────────────────────


class HealthCollector:
    """Facade for backward compatibility.

    Wraps the CollectorRegistry so existing code still works:
    ``HealthCollector(db_path).collect_all()``
    """

    def __init__(
        self,
        db_path: str | Path = "",
        registry: CollectorRegistry | None = None,
    ) -> None:
        self._db_path = str(db_path) if db_path else ""
        self._registry = registry or create_default_registry()

    def collect_all(self) -> list[MetricSnapshot]:
        """Run all registered collectors."""
        return self._registry.collect_all(self._db_path)

    @property
    def registry(self) -> CollectorRegistry:
        """Access the underlying registry."""
        return self._registry
