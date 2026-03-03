"""
Base Filter Interface for IMMUNE-SYSTEM-V1.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Verdict(Enum):
    PASS = "PASS"
    HOLD = "HOLD"
    BLOCK = "BLOCK"


@dataclass(frozen=True, slots=True)
class FilterResult:
    filter_id: str
    verdict: Verdict
    score: float  # 0-100
    justification: str
    metadata: dict[str, Any] = field(default_factory=dict)


class ImmuneFilter(ABC):
    """Abstract base class for all immunological filters."""

    @property
    @abstractmethod
    def filter_id(self) -> str:
        """The canonical ID of the filter (e.g. 'F1', 'F2')."""
        pass

    @abstractmethod
    async def evaluate(self, signal: Any, context: dict[str, Any]) -> FilterResult:
        """Evaluate a signal and return a verdict."""
        pass
