"""ENCB v2 — Pluggable Resolvers Protocol.

Defines the interface for resolving epistemic chaos, allowing engine-agnostic
evaluation between CORTEX, Baseline RAG, and an Upper Bound Oracle.
"""

from typing import Any, Protocol, runtime_checkable

from benchmarks.encb_chaos_generator import ChaosEvent


@runtime_checkable
class Resolver(Protocol):
    """
    Interface for Epistemic Chaos Resolution.
    Any memory system tested in the ENCB must implement this protocol.
    """

    async def ingest(self, events: list[ChaosEvent]) -> None:
        """
        Ingest a batch of chaos events into the memory system.
        The system handles internal networking, CRDT merges, etc.
        """
        ...

    async def resolve(self, key: str) -> tuple[Any, float]:
        """
        Query the system for the resolved belief value associated with a key.
        Returns:
            Tuple of (resolved_value, confidence [0.0 - 1.0]).
            If the key is not found, should return (None, 0.0).
        """
        ...

    async def detect_byzantine(self) -> set[str]:
        """
        Query the system for the set of node IDs it has identified as Byzantine.
        Returns empty set if the system does not support Byzantine detection.
        """
        ...

    def name(self) -> str:
        """
        Return the name of the resolver strategy (e.g. 'LogOP', 'AppendOnly', 'Oracle').
        """
        ...


class AppendOnlyResolver:
    """
    Append-only memory system. No governance, no consensus, no Byzantine detection.
    This serves as the Baseline RAG control group.
    """

    def __init__(self) -> None:
        self._facts: list[ChaosEvent] = []

    async def ingest(self, events: list[ChaosEvent]) -> None:
        # Just append everything. No deduplication, no consistency logic.
        self._facts.extend(events)

    async def resolve(self, key: str) -> tuple[Any, float]:
        """
        Naive resolution: Just return the value from the most recent event matching the key.
        Confidence is always 1.0 (blind trust).
        """
        # Using string matching on content to mimic simple RAG retrieval
        for event in reversed(self._facts):
            # In ENCB, event context holds the prop being updated
            if key in event.content:
                return (event.content, 1.0)
        return (None, 0.0)

    async def detect_byzantine(self) -> set[str]:
        # No trust model, so no Byzantine detection.
        return set()

    def name(self) -> str:
        return "AppendOnly (RAG)"


class OracleResolver:
    """
    Negative control group. An Oracle that perfectly knows the ground truth.
    Should score 1.0 on all metrics. If metrics fail with Oracle, the metrics are broken.
    """

    def __init__(self, ground_truth: dict[str, str]) -> None:
        self._ground_truth = ground_truth

    async def ingest(self, events: list[ChaosEvent]) -> None:
        # Oracle ignores incoming events because it already knows the truth
        pass

    async def resolve(self, key: str) -> tuple[Any, float]:
        if key in self._ground_truth:
            return (self._ground_truth[key], 1.0)
        return (None, 0.0)

    async def detect_byzantine(self) -> set[str]:
        # Oracle conceptually knows who is Byzantine, but it doesn't process events here.
        # It's intended to perfectly resolve ground truth for Recovery/KL metrics.
        return set()

    def name(self) -> str:
        return "Oracle"
