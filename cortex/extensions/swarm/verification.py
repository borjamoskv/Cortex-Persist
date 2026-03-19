"""
ContinuityVerifier — ΩΩ-HANDOFF Semana 3-4
Verifies the integrity and continuity of anchored CORTEX handoff events
via Arweave GraphQL queries.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger("cortex.extensions.swarm.verification")

# ---------------------------------------------------------------------------
# Domain types
# ---------------------------------------------------------------------------

VERIFICATION_HEADER = "X-Omega-Verification"
APP_NAME = "CORTEX-Ω"


@dataclass(frozen=True, slots=True)
class VerificationResult:
    """Result of a ContinuityVerifier check."""

    fact_id: str
    is_continuous: bool
    chain_length: int
    verified_txs: list[str] = field(default_factory=list)
    gaps: list[int] = field(default_factory=list)  # block-height gaps detected
    trust_score: float = 0.0
    error: str | None = None


# ---------------------------------------------------------------------------
# ContinuityVerifier
# ---------------------------------------------------------------------------


class ContinuityVerifier:
    """
    Queries Arweave GraphQL to verify the continuity of a CORTEX handoff chain.

    Continuity is defined as: all expected anchored facts are present in the
    permaweb with monotonically increasing block heights and no structural gaps
    beyond the configured tolerance.
    """

    def __init__(
        self,
        node_url: str = "https://arweave.net",
        gap_tolerance_blocks: int = 50,
        timeout: float = 15.0,
    ) -> None:
        self.node_url = node_url.rstrip("/")
        self.gap_tolerance_blocks = gap_tolerance_blocks
        self.timeout = timeout

    # ------------------------------------------------------------------
    # Core verification
    # ------------------------------------------------------------------

    async def verify(self, fact_id: str) -> VerificationResult:
        """
        Full continuity check for a single Cortex-Fact-Id.

        Returns a VerificationResult with is_continuous=True only if the chain
        is unbroken within gap_tolerance_blocks and the owner address is stable
        across all transactions in the chain.
        """
        try:
            nodes = await self._graphql_chain(fact_id)
        except Exception as exc:
            return VerificationResult(
                fact_id=fact_id,
                is_continuous=False,
                chain_length=0,
                error=str(exc),
            )

        if not nodes:
            return VerificationResult(
                fact_id=fact_id,
                is_continuous=False,
                chain_length=0,
                error="no transactions found on Arweave",
            )

        tx_ids = [n["id"] for n in nodes]
        heights = [n.get("block", {}).get("height") for n in nodes if n.get("block")]
        heights_clean = [h for h in heights if h is not None]

        gaps = self._detect_gaps(heights_clean)
        owner_stable = self._owner_stable(nodes)
        ts_continuous = self._timestamps_mononotonic(nodes)

        is_continuous = len(gaps) == 0 and owner_stable and ts_continuous

        score = self._compute_trust_score(
            chain_length=len(nodes),
            gap_count=len(gaps),
            owner_stable=owner_stable,
            ts_continuous=ts_continuous,
        )

        return VerificationResult(
            fact_id=fact_id,
            is_continuous=is_continuous,
            chain_length=len(nodes),
            verified_txs=tx_ids,
            gaps=gaps,
            trust_score=score,
        )

    async def verify_many(self, fact_ids: list[str]) -> list[VerificationResult]:
        """Batch-verify multiple fact IDs (sequential, retains order)."""
        results = []
        for fid in fact_ids:
            results.append(await self.verify(fid))
        return results

    # ------------------------------------------------------------------
    # Header factory
    # ------------------------------------------------------------------

    @staticmethod
    def build_verification_header(result: VerificationResult) -> dict[str, str]:
        """
        Build an HTTP header dict encoding the verification state.
        Format: X-Omega-Verification: <fact_id>;<is_continuous>;<score>
        """
        value = (
            f"{result.fact_id};{'OK' if result.is_continuous else 'FAIL'};{result.trust_score:.3f}"
        )
        return {VERIFICATION_HEADER: value}

    # ------------------------------------------------------------------
    # GraphQL
    # ------------------------------------------------------------------

    async def _graphql_chain(self, fact_id: str) -> list[dict[str, Any]]:
        query = """
        query($factId: String!) {
            transactions(
                tags: [
                    { name: "App-Name", values: ["CORTEX-\u03a9"] },
                    { name: "Cortex-Fact-Id", values: [$factId] }
                ]
                sort: HEIGHT_ASC
                first: 100
            ) {
                edges {
                    node {
                        id
                        owner { address }
                        tags { name value }
                        block { height timestamp }
                    }
                }
            }
        }
        """
        url = f"{self.node_url}/graphql"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url,
                json={"query": query, "variables": {"factId": fact_id}},
            )
            response.raise_for_status()
            data = response.json()
            edges = data.get("data", {}).get("transactions", {}).get("edges", [])
            return [edge["node"] for edge in edges]
        return []  # fallback

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _detect_gaps(self, heights: list[int]) -> list[int]:
        """Return list of gap sizes (in blocks) that exceed tolerance."""
        gaps = []
        for i in range(1, len(heights)):
            delta = heights[i] - heights[i - 1]
            if delta > self.gap_tolerance_blocks:
                gaps.append(delta)
        return gaps

    @staticmethod
    def _owner_stable(nodes: list[dict[str, Any]]) -> bool:
        """All transactions must share the same owner address."""
        addresses = {n.get("owner", {}).get("address") for n in nodes}
        addresses.discard(None)
        return len(addresses) <= 1

    @staticmethod
    def _timestamps_mononotonic(nodes: list[dict[str, Any]]) -> bool:
        """Arweave 'Cortex-Timestamp' tags must be monotonically increasing."""
        ts_values = []
        for node in nodes:
            tags = node.get("tags", [])
            for tag in tags:
                if tag["name"] == "Cortex-Timestamp":
                    try:
                        ts_values.append(int(tag["value"]))
                    except (ValueError, TypeError):
                        pass
                    break

        for i in range(1, len(ts_values)):
            if ts_values[i] <= ts_values[i - 1]:
                return False
        return True

    @staticmethod
    def _compute_trust_score(
        chain_length: int, gap_count: int, owner_stable: bool, ts_continuous: bool = True
    ) -> float:
        """
        Deterministic trust score in [0.0, 1.0].

        Mechanics:
          - Base: 0.5
          - Chain length bonus: +0.1 per 5 confirmed TXs (capped at +0.3)
          - Gap penalty: -0.15 per gap
          - Owner mismatch: -0.4
          - Timestamp reversal penalty: -0.5
        """
        score = 0.6
        score += min(0.3, (chain_length // 5) * 0.1)
        score -= gap_count * 0.15
        if not owner_stable:
            score -= 0.4
        if not ts_continuous:
            score -= 0.5
        return max(0.0, min(1.0, score))
