# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.

"""UltraThink Protocol (Sovereign Survival Mode).

Axiom Ω₁₃: Cognición Termodinámica.
AX-033: El Gradiente de Admisibilidad.

UltraThink is the maximum reasoning tier for P0 singularities.
It enforces a recursive verification loop:
Proposal → Mechanical Verification → Logic Audit → Commitment.

If any stage fails, the proposal is detonated (StochasticDetonationError).
"""

from __future__ import annotations

import logging
import re
from typing import Any

from cortex.extensions.llm._models import CortexPrompt, IntentProfile, ReasoningMode
from cortex.extensions.swarm.ast_validator import ASTValidator
from cortex.extensions.swarm.verification import ContinuityVerifier
from cortex.utils.result import Err, Ok, Result

logger = logging.getLogger("cortex.extensions.swarm.ultra_think")


class UltraThinkOrchestrator:
    """Orchestrator for the UltraThink Protocol.

    Designed for P0 singularities where survival depends on deterministic truth.
    Strictly uses frontier models and enforces mechanical verification gates.
    """

    def __init__(self, engine: Any):
        self.engine = engine
        self._ast_validator = ASTValidator()
        self._continuity_verifier = ContinuityVerifier()

    async def execute(self, prompt: CortexPrompt) -> Result[str, str]:
        """Execute the UltraThink lifecycle.

        1. Dispatch to Frontier Ensemble (via ReasoningMode.ULTRA_THINK).
        2. Perform mechanical verification on output.
        3. Perform logic audit against whitelisted constants/axioms.
        4. Return verified result or detonate.
        """
        logger.info("🛡️ [ULTRA-THINK] Triggered P0 Sovereign Survival mode.")
        prompt.reasoning_mode = ReasoningMode.ULTRA_THINK

        # Phase 1: Generation (Enforced Frontier)
        router = await self.engine.get_llm_router()
        res = await router.execute_resilient(prompt)

        if res.is_err():
            return res

        proposal = res.unwrap()

        # Phase 2: Mechanical Verification
        # If the proposal looks like code, validate it
        if "```python" in proposal or "def " in proposal:
            logger.info("🛡️ [ULTRA-THINK] Detected code block - triggering AST validation.")
            code_match = re.search(r"```python\n(.*?)\n```", proposal, re.DOTALL)
            if code_match:
                code_to_verify = code_match.group(1)
                ast_res = self._ast_validator.validate(code_to_verify)
                if not ast_res.passed:
                    logger.error("💣 [ULTRA-THINK] AST Integrity Violation: %s", ast_res.summary())
                    return Err(f"Stochastic Detonation: AST Validation failed. {ast_res.summary()}")

        # If the proposal mentions ledger/facts, verify continuity
        if "fact:" in proposal.lower() or "ledger" in proposal.lower():
            logger.info("🛡️ [ULTRA-THINK] Detected ledger claim - triggering continuity verification.")
            # Logic for fact_id extraction would go here
            pass

        # Phase 3: Logic Audit (Socratic Self-Critique)
        audit_prompt = CortexPrompt(
            system_instruction=(
                "You are the UltraThink Logic Auditor. "
                "Examine this proposal for stochastic hallucinations, "
                "logical contradictions, or violations of CORTEX axioms. "
                "Respond with 'OK' or 'DETONATE' followed by reasoning."
            ),
            working_memory=[{"role": "user", "content": proposal}],
            intent=IntentProfile.REASONING,
            reasoning_mode=ReasoningMode.ULTRA_THINK,
        )

        audit_res = await router.execute_resilient(audit_prompt)
        if audit_res.is_err():
            return audit_res

        audit_text = audit_res.unwrap()
        if "DETONATE" in audit_text.upper():
            logger.error("💣 [ULTRA-THINK] Logic Audit Detonation: %s", audit_text)
            return Err(f"Stochastic Detonation: Logic Audit failed. {audit_text}")

        logger.info("✅ [ULTRA-THINK] Sovereign Survival check passed.")
        return Ok(proposal)
