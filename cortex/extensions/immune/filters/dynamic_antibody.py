"""
F7 — DYNAMIC ANTIBODY: Evolutionary Defense Layer.
"""

from __future__ import annotations

import json
import os
from typing import Any

from cortex.extensions.immune.filters.base import FilterResult, ImmuneFilter, Verdict


class DynamicAntibodyFilter(ImmuneFilter):
    """F7: Dynamic Antibody Filter.

    Enforces rules synthesized by the AntibodyForge from prior failures.
    """

    def __init__(
        self,
        storage_path: str = (
            "/Users/borjafernandezangulo/30_CORTEX"
            "/cortex/extensions/immune/antibodies.json"
        ),
    ) -> None:
        self.storage_path = storage_path

    @property
    def filter_id(self) -> str:
        return "F7"

    async def evaluate(self, signal: Any, context: dict[str, Any]) -> FilterResult:
        """Check if any active antibodies match the current signal/context."""
        if not os.path.exists(self.storage_path):
            return self._pass("No antibodies forged yet.")

        try:
            with open(self.storage_path) as f:
                antibodies = json.load(f)
        except (json.JSONDecodeError, OSError):
            return self._pass("Antibody store unreachable.")

        source = context.get("source", "unknown")

        for ab_id, ab in antibodies.items():
            # Evaluation logic: Match source and intent keywords
            target_source = ab.get("target_source", "")
            if target_source and target_source in source:
                return FilterResult(
                    filter_id=self.filter_id,
                    verdict=Verdict.BLOCK,
                    score=0,
                    justification=ab.get("justification", "Blocked by dynamic antibody."),
                    metadata={"antibody_id": ab_id}
                )

        return self._pass("No matching antibodies found.")

    def _pass(self, reason: str) -> FilterResult:
        return FilterResult(
            filter_id=self.filter_id,
            verdict=Verdict.PASS,
            score=100,
            justification=reason
        )
