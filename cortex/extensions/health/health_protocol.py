"""MetricCollector Protocol — enforced at registration time.

Every collector must implement this protocol. The registry
rejects non-conforming objects at registration, not at runtime.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from cortex.extensions.health.models import MetricSnapshot


@runtime_checkable
class MetricCollectorProtocol(Protocol):
    """Contract for health metric collectors.

    Implementors must provide:
      - ``name``: Unique metric identifier
      - ``weight``: Default weight for scoring
      - ``collect(db_path)`` → MetricSnapshot
    """

    @property
    def name(self) -> str:
        """Unique identifier for this metric."""
        ...

    @property
    def weight(self) -> float:
        """Default scoring weight."""
        ...

    @property
    def description(self) -> str:
        """Human-readable description of what this metric measures."""
        ...

    @property
    def remediation(self) -> str:
        """Suggested action if this metric is degraded."""
        ...

    def collect(self, db_path: str) -> MetricSnapshot:
        """Collect a single metric snapshot.

        Args:
            db_path: Path to CORTEX database.

        Returns:
            Normalized MetricSnapshot (value in [0, 1]).
        """
        ...
