import hashlib
import json
import sqlite3
from decimal import Decimal
from datetime import datetime, timezone
from cortex.compliance import ComplianceTracker
from cortex.crypto.merkle import EvidenceManifest

# Register Decimal adapter for sqlite3 (Policy Ω₂ compatibility)
def adapt_decimal(d):
    return str(d)

def convert_decimal(s):
    return Decimal(s.decode('ascii'))

sqlite3.register_adapter(Decimal, adapt_decimal)
sqlite3.register_converter("DECIMAL", convert_decimal)

def test_compliance_flow():
    print("--- 🚀 Starting Compliance Flow Test ---")
    
    with ComplianceTracker(db_path="scratch/compliance_test.db") as tracker:
        # 1. Log some decisions
        print("Logging decisions...")
        tracker.log_decision(content="Decision A", agent_id="agent-1")
        tracker.log_decision(content="Decision B", agent_id="agent-2")
        
        # 2. Verify integrity
        print("Verifying chain...")
        integrity = tracker.verify_chain()
        print(f"Integrity Valid: {integrity['valid']}")
        assert integrity['valid'] is True
        
        # 3. Export audit with manifest
        print("Exporting audit report...")
        report = tracker.export_audit(include_facts=True)
        manifest_dict = report["manifest"]
        
        print(f"Manifest ID: {manifest_dict['manifest_id']}")
        print(f"Merkle Root: {manifest_dict['merkle_root']}")
        print(f"Signature: {manifest_dict['signature']}")
        
        # 4. Verify manifest
        print("Verifying manifest...")
        is_valid = EvidenceManifest.verify_manifest(manifest_dict)
        print(f"Manifest Verification: {'✅ PASSED' if is_valid else '❌ FAILED'}")
        assert is_valid is True
        
    print("--- ✅ Test Complete ---")

if __name__ == "__main__":
    test_compliance_flow()
