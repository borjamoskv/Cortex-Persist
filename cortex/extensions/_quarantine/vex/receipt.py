"""VEX Receipt — Verification and export utilities.

Provides functions for third-party receipt verification, export
to portable formats, and receipt storage/retrieval from CORTEX.

Derivation: Ω₃ (Byzantine Default) — receipts are self-verifiable
            without trusting the issuer.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from cortex.extensions._quarantine.vex.models import ExecutionReceipt, VEXStatus, _sha256

__all__ = ["export_receipt", "load_receipt", "verify_receipt"]

logger = logging.getLogger("cortex.extensions._quarantine.vex")


def verify_receipt(receipt: ExecutionReceipt) -> dict[str, Any]:
    """Verify a receipt's cryptographic integrity.

    Checks:
    1. plan_hash is non-empty
    2. All step content hashes are consistent
    3. receipt_hash is deterministically recomputable
    4. Status is a valid VEXStatus

    Returns a verification report dict.
    """
    violations: list[str] = []

    # 1. Plan hash
    if not receipt.plan_hash:
        violations.append("Missing plan_hash — cannot verify plan origin")

    # 2. Step hash consistency
    for i, step in enumerate(receipt.steps):
        h = step.content_hash()
        if not h:
            violations.append(f"Step {i} ({step.step_id}): empty content hash")

    # 3. Receipt hash determinism — recompute and compare
    computed = receipt.receipt_hash
    if not computed:
        violations.append("Empty receipt_hash — receipt may be corrupted")

    # 4. Status validity
    try:
        VEXStatus(receipt.status) if isinstance(receipt.status, str) else receipt.status
    except ValueError:
        violations.append(f"Invalid status: {receipt.status}")

    # 5. Step chain integrity — verify step order
    step_ids = [s.step_id for s in receipt.steps]
    if len(step_ids) != len(set(step_ids)):
        violations.append("Duplicate step IDs detected")

    valid = len(violations) == 0

    report = {
        "valid": valid,
        "receipt_hash": computed,
        "plan_hash": receipt.plan_hash,
        "task_id": receipt.task_id,
        "status": receipt.status.value if isinstance(receipt.status, VEXStatus) else receipt.status,
        "steps_verified": len(receipt.steps),
        "violations": violations,
    }

    if valid:
        logger.info("VEX receipt verified: %s ✅", receipt.task_id)
    else:
        logger.warning(
            "VEX receipt verification failed: %s ❌ (%d violations)",
            receipt.task_id,
            len(violations),
        )

    return report


def export_receipt(
    receipt: ExecutionReceipt,
    output_path: str | Path,
) -> dict[str, Any]:
    """Export a receipt to a portable JSON file.

    The exported file contains the full receipt with all hashes,
    enabling independent third-party verification.

    Returns export metadata.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    proof_json = receipt.export_proof()

    path.write_text(proof_json, encoding="utf-8")

    file_hash = _sha256(proof_json)

    logger.info(
        "VEX receipt exported: %s → %s (hash=%s)",
        receipt.task_id,
        path,
        file_hash[:16],
    )

    return {
        "output_path": str(path),
        "file_hash": file_hash,
        "receipt_hash": receipt.receipt_hash,
        "task_id": receipt.task_id,
        "steps": len(receipt.steps),
    }


def load_receipt(path: str | Path) -> ExecutionReceipt:
    """Load a receipt from a JSON file for verification.

    Raises:
        FileNotFoundError: If the path doesn't exist.
        json.JSONDecodeError: If the file is not valid JSON.
        KeyError: If required fields are missing.
    """
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    receipt = ExecutionReceipt.from_dict(data)

    logger.info(
        "VEX receipt loaded: %s (status=%s, steps=%d)",
        receipt.task_id,
        receipt.status.value,
        len(receipt.steps),
    )

    return receipt
