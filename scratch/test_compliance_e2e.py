#!/usr/bin/env python3
"""
End-to-end Compliance Flow Test.

Validates: log_decision → verify_chain → export_audit → manifest verification.
Run: PYTHONPATH=. CORTEX_MASTER_KEY=$(python3 -c "...") python3 scratch/test_compliance_e2e.py
"""

import json
import os
import sqlite3
import sys
import tempfile
from decimal import Decimal

# Decimal adapter for sqlite3
sqlite3.register_adapter(Decimal, lambda d: str(d))
sqlite3.register_converter("DECIMAL", lambda s: Decimal(s.decode("ascii")))

# Generate a temporary master key for the test
if not os.environ.get("CORTEX_MASTER_KEY"):
    import base64
    os.environ["CORTEX_MASTER_KEY"] = base64.b64encode(
        os.urandom(32)
    ).decode()

from cortex.compliance import ComplianceTracker
from cortex.crypto.merkle import EvidenceManifest

PASS = "✅"
FAIL = "❌"


def main() -> int:
    print("=" * 60)
    print("  CORTEX Compliance E2E Test")
    print("=" * 60)

    db_path = os.path.join(tempfile.mkdtemp(), "compliance_e2e.db")
    errors = 0

    with ComplianceTracker(db_path=db_path, project="e2e-test") as tracker:
        # 1. Log decisions
        print("\n[1] Logging decisions...")
        ids = []
        for i in range(5):
            fid = tracker.log_decision(
                content=f"Decision #{i}: approved transaction {i * 100}",
                agent_id=f"agent-{i % 2}",
                decision_type="approval",
                confidence="C4",
            )
            ids.append(fid)
            print(f"  {PASS} Logged fact_id={fid}")

        # 2. Verify chain
        print("\n[2] Verifying chain integrity...")
        integrity = tracker.verify_chain()
        ok = integrity["valid"]
        icon = PASS if ok else FAIL
        print(f"  {icon} Chain valid: {ok}")
        if not ok:
            errors += 1

        # 3. Export audit
        print("\n[3] Exporting audit report...")
        report = tracker.export_audit(include_facts=True)

        status = report["eu_ai_act"]["status"]
        score = report["eu_ai_act"]["score"]
        icon = PASS if status == "COMPLIANT" else FAIL
        print(f"  {icon} Status: {status} ({score})")

        facts_count = report["facts_summary"]["total_facts"]
        print(f"  {PASS} Facts: {facts_count}")

        # 4. Verify manifest
        print("\n[4] Verifying EvidenceManifest...")
        manifest = report["manifest"]
        print(f"  Manifest ID:  {manifest['manifest_id']}")
        print(f"  Merkle Root:  {manifest['merkle_root'][:32]}…")
        print(f"  Algorithm:    {manifest['algorithm']}")
        print(f"  Tree Type:    {manifest['tree_type']}")
        print(f"  Events:       {manifest['total_events']}")
        print(f"  Signer DID:   {manifest['signer_did'][:32]}…")
        print(f"  Proofs:       {len(manifest['proofs'])} inclusion proofs")
        print(f"  Metadata:     {list(manifest.get('metadata', {}).keys())}")
        print(f"  Compliance:   {manifest.get('compliance', {})}")

        valid = EvidenceManifest.verify_manifest(manifest)
        icon = PASS if valid else FAIL
        print(f"  {icon} Manifest cryptographic verification: {'PASSED' if valid else 'FAILED'}")
        if not valid:
            errors += 1

        # 5. Verify individual proofs
        print("\n[5] Verifying individual inclusion proofs...")
        from cortex.crypto.merkle import MerkleProof
        for leaf_hash, proof_data in manifest["proofs"].items():
            proof = MerkleProof(**proof_data) if isinstance(proof_data, dict) else proof_data
            ok = proof.verify()
            icon = PASS if ok else FAIL
            print(f"  {icon} Proof[{proof.leaf_index}]: {leaf_hash[:16]}…")
            if not ok:
                errors += 1

        # 6. Full manifest JSON export
        print("\n[6] JSON export size...")
        json_str = json.dumps(manifest, indent=2)
        print(f"  {PASS} Manifest JSON: {len(json_str)} bytes")

    # Cleanup
    try:
        os.unlink(db_path)
    except OSError:
        pass

    print("\n" + "=" * 60)
    if errors == 0:
        print(f"  {PASS} ALL CHECKS PASSED — Compliance pipeline verified.")
    else:
        print(f"  {FAIL} {errors} CHECK(S) FAILED")
    print("=" * 60)

    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
