"""CORTEX v7 — Counterexample Learning Protocol.

Transforms formal verification failures into persistent sematic memories
to prevent the RSI loop from repeating prohibited patterns.
"""

import logging
from typing import Any

logger = logging.getLogger("cortex.verification.counterexample")


async def learn_from_failure(
    memory_manager: Any,
    tenant_id: str,
    project_id: str,
    invariant_id: str,
    violation_message: str,
    counterexample: dict[str, Any],
    file_path: str,
) -> None:
    """Persist a formal verification failure as a high-value CORTEX error fact.
    
    This fact will be retrieved by the Legion Swarm in subsequent iterations,
    providing concrete context on why a previous mutation was rejected.
    """
    content = (
        f"FORMAL_VIOLATION: Invariant {invariant_id} violated in {file_path}. "
        f"Message: {violation_message}. "
        f"Counterexample detected: {counterexample}. "
        "The RSI loop must avoid this pattern in future mutations."
    )
    
    logger.info("🧠 [COUNTEREXAMPLE] Learning from violation %s in %s", invariant_id, file_path)
    
    # We mark it as an 'error' with C5 confidence because it's a formal proof.
    # We add 'is_toxic': True to trigger HDC Inhibitory Recall in Vector Gamma.
    await memory_manager.store(
        tenant_id=tenant_id,
        project_id=project_id,
        content=content,
        fact_type="error",
        metadata={
            "source": "z3_verifier",
            "invariant_id": invariant_id,
            "file_path": file_path,
            "is_formal_proof": True,
            "confidence": "C5",
            "is_toxic": True
        }
    )
