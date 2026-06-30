import asyncio

from babylon60.audit.compliance_bundle import ComplianceBundler
from babylon60.audit.compliance_verifier import ComplianceVerifier
from babylon60.audit.ledger import MasterLedger
from babylon60.crypto.keys import KeyManager


async def test_e2e():
    import os

    if os.path.exists(".cortex/cortex_ledger.db"):
        os.remove(".cortex/cortex_ledger.db")

    km = KeyManager(service_name="test_e2e")

    # Init ledger
    ledger = MasterLedger(db_path=".cortex/cortex_ledger.db")

    # Submit some records
    await ledger.submit_fact("tenant1", "system", "user-1", "CREATE", "fact_1", "SUCCESS")
    await ledger.submit_fact("tenant1", "system", "user-1", "CREATE", "fact_2", "SUCCESS")

    # Wait for batch
    await asyncio.sleep(2.0)

    # Get the public key
    pub_b64 = km.get_public_key_b64("system")

    # Export bundle
    bundler = ComplianceBundler(db_path=".cortex/cortex_ledger.db")
    bundler.export_bundle("test_bundle.zip")

    # Verify bundle
    verifier = ComplianceVerifier(bundle_path="test_bundle.zip", public_key_b64=pub_b64)
    report = verifier.verify()
    print("Report:", report)


if __name__ == "__main__":
    asyncio.run(test_e2e())
