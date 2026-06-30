import json
import zipfile
import base64
import hashlib
import pytest
from pathlib import Path
from babylon60.crypto.keys import KeyManager, Signer
from babylon60.audit.compliance_verifier import ComplianceVerifier


@pytest.fixture
def km():
    manager = KeyManager(service_name="test_compliance_verifier")
    yield manager


@pytest.fixture
def valid_bundle(tmp_path, km):
    actor_id = "verifier_test"
    km.revoke_key(actor_id)
    public_key_b64 = km.generate_and_store_key(actor_id)
    private_key_b64 = km.get_private_key_b64(actor_id)

    zip_path = tmp_path / "valid_bundle.zip"

    # Create valid mock data for 2 rows in 1 batch
    prev_hash = "0" * 64
    audit_id_1 = "audit-1"
    audit_id_2 = "audit-2"

    merkle_payload = audit_id_1 + audit_id_2 + prev_hash
    merkle_root = hashlib.sha256(merkle_payload.encode()).hexdigest()

    entry_hash_payload = f"merkle_batch:{merkle_root}:{prev_hash}"
    entry_hash = hashlib.sha256(entry_hash_payload.encode()).hexdigest()

    # Sign it
    # We must replicate ledger.py signing (bytes -> hex)
    from cryptography.hazmat.primitives import serialization
    import cryptography.hazmat.primitives.asymmetric.ed25519 as ed25519

    priv_bytes = base64.b64decode(private_key_b64)
    try:
        priv_key = ed25519.Ed25519PrivateKey.from_private_bytes(priv_bytes)
    except ValueError:
        priv_key = serialization.load_pem_private_key(priv_bytes, password=None)

    signature = priv_key.sign(entry_hash.encode()).hex()

    export_data = [
        {
            "audit_id": audit_id_1,
            "prev_hash": prev_hash,
            "signature": signature,
            "external_anchor": None,
        },
        {
            "audit_id": audit_id_2,
            "prev_hash": prev_hash,
            "signature": signature,
            "external_anchor": None,
        },
    ]

    with zipfile.ZipFile(zip_path, "w") as zipf:
        zipf.writestr("metadata.json", json.dumps({"format": "EU_AI_ACT_COMPLIANCE"}))
        zipf.writestr("ledger_export.json", json.dumps(export_data))

    return str(zip_path), public_key_b64


def test_compliance_verifier_valid(valid_bundle):
    bundle_path, public_key_b64 = valid_bundle
    verifier = ComplianceVerifier(bundle_path=bundle_path, public_key_b64=public_key_b64)
    report = verifier.verify()
    assert report["status"] == "VALID"
    assert report["records_verified"] == 2
    assert report["batches_verified"] == 1


def test_compliance_verifier_tampered_hash(valid_bundle, tmp_path):
    bundle_path, public_key_b64 = valid_bundle

    # Unpack, tamper, repack
    tampered_zip = tmp_path / "tampered_bundle.zip"

    with zipfile.ZipFile(bundle_path, "r") as z_in:
        metadata = z_in.read("metadata.json")
        export_data = json.loads(z_in.read("ledger_export.json"))

    # Tamper the prev_hash
    export_data[0]["prev_hash"] = "1" * 64

    with zipfile.ZipFile(tampered_zip, "w") as z_out:
        z_out.writestr("metadata.json", metadata)
        z_out.writestr("ledger_export.json", json.dumps(export_data))

    verifier = ComplianceVerifier(bundle_path=str(tampered_zip), public_key_b64=public_key_b64)
    report = verifier.verify()
    assert report["status"] == "CRITICAL_TAMPER_DETECTED"
    assert "Signature mismatch" in report["reason"]
