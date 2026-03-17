"""CORTEX — Notification Event model."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EventSeverity(str, Enum):
    """Severity levels for CORTEX notification events."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

    @property
    def emoji(self) -> str:
        return {
            "debug": "🔍",
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "🔴",
            "critical": "💀",
        }[self.value]


@dataclass
class CortexEvent:
    """A structured event emitted by any CORTEX subsystem.

    Args:
        severity:  How urgent is this? (INFO / WARNING / ERROR / CRITICAL)
        title:     Short one-liner (used as Telegram bold header, macOS title).
        body:      Full description (shown in Telegram message body, macOS subtitle).
        source:    Which subsystem generated this (e.g. "ghost_monitor", "mejoralo").
        project:   Optional project context (e.g. "cortex", "naroa-2026").
        metadata:  Arbitrary key-value pairs for adapter-specific enrichment.
        ts:        Unix timestamp (auto-filled).
    """

    severity: EventSeverity
    title: str
    body: str
    source: str
    project: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    ts: float = field(default_factory=time.time)

    def format_text(self) -> str:
        """Human-readable text representation for plain-text adapters."""
        project_tag = f"[{self.project}] " if self.project else ""
        return (
            f"{self.severity.emoji} *{project_tag}{self.title}*\n"
            f"{self.body}\n"
            f"_Source: {self.source}_"
        )
