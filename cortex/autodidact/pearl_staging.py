# CORTEX Autodidact — PeARL Staging Validator (AX-043)
# Apache-2.0 · (c) 2026 CORTEX Swarm

"""Physics-validated pre-flight for MEV bundles.

Before a capital transaction hits the hash-chain, its logic
is expressed as a PeARL program and evaluated in a deterministic
sandbox. This enforces AX-043: structural common sense gates
every financial write.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from cortex.autodidact.dual_ledger import DualLedger, TxType
from cortex.engine.pearl import PearlEngine
from cortex.utils.errors import PearlError

__all__ = ["PeARLStagingValidator", "StagingResult"]

logger = logging.getLogger("cortex.autodidact.pearl_staging")


@dataclass(frozen=True)
class StagingResult:
    """Outcome of a PeARL-validated MEV staging attempt."""

    valid: bool
    tx_hash: str = ""
    error: str = ""
    sandbox_output: Any = None
    pearl_expression: str = ""


class PeARLStagingValidator:
    """Bridges PeARL induction into MEV pre-flight (AX-043).

    Flow
    ----
    1. Extract logic from bundle as a PeARL expression string.
    2. Sandbox-evaluate against simulated env state.
    3. If valid → record CAPITAL tx in the dual ledger.
    4. If invalid → reject with structured error.

    Parameters
    ----------
    pearl : PearlEngine
        The PeARL primitive induction engine.
    ledger : DualLedger
        Unified dual-stream hash-chain.
    """

    def __init__(self, pearl: PearlEngine, ledger: DualLedger) -> None:
        self.pearl = pearl
        self.ledger = ledger

    def _extract_pearl_expression(self, bundle: dict[str, Any]) -> str:
        """Derive a PeARL expression from an MEV bundle.

        Convention: bundles carry a ``pearl_expr`` key with the
        validation logic. If absent, a no-op expression ``1`` is used
        (pass-through staging for bundles without physics constraints).
        """
        return str(bundle.get("pearl_expr", "1"))

    async def stage_mev_bundle(
        self,
        bundle: dict[str, Any],
        env_state: dict[str, Any] | None = None,
        *,
        project: str = "ouroboros",
        tenant_id: str = "default",
    ) -> StagingResult:
        """Validate and stage a single MEV bundle.

        Parameters
        ----------
        bundle : dict
            MEV payload. Must contain at least ``signed_txs``.
            Optional ``pearl_expr`` for physics validation.
        env_state : dict, optional
            Simulated environmental state for the sandbox.
        """
        signed_txs = bundle.get("signed_txs", [])
        if not signed_txs:
            return StagingResult(valid=False, error="Empty signed_txs. Atomicity violation.")

        pearl_expr = self._extract_pearl_expression(bundle)
        context = dict(env_state or {})

        # Sandbox evaluation (AX-043: deterministic physics gate)
        try:
            result = self.pearl.evaluate(pearl_expr, context)
        except PearlError as exc:
            logger.warning("PeARL staging REJECT: %s", exc)
            return StagingResult(
                valid=False,
                error=str(exc),
                pearl_expression=pearl_expr,
            )

        # Truthy result → valid bundle
        if not result:
            return StagingResult(
                valid=False,
                error="PeARL expression evaluated to falsy.",
                sandbox_output=result,
                pearl_expression=pearl_expr,
            )

        # Persist as CAPITAL tx in the dual ledger
        detail = {
            "signed_txs_count": len(signed_txs),
            "pearl_expr": pearl_expr,
            "sandbox_result": str(result),
            "exergy_usd": float(bundle.get("estimated_yield_usd", 0)),
        }

        tx_hash = await self.ledger.record_capital(
            project=project,
            action="mev_staged",
            detail=detail,
            tenant_id=tenant_id,
        )

        return StagingResult(
            valid=True,
            tx_hash=tx_hash,
            sandbox_output=result,
            pearl_expression=pearl_expr,
        )

    async def stage_batch(
        self,
        bundles: list[dict[str, Any]],
        env_state: dict[str, Any] | None = None,
        **kw: Any,
    ) -> list[StagingResult]:
        """Validate a batch of MEV bundles sequentially.

        Each bundle is staged independently; a failure in one does not
        abort the rest (non-atomic batch — atomicity is per-bundle).
        """
        results: list[StagingResult] = []
        for bundle in bundles:
            r = await self.stage_mev_bundle(bundle, env_state, **kw)
            results.append(r)
        return results
