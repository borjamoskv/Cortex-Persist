# [C5-REAL] Exergy-Maximized
import json
import logging
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

# Local imports (running from cortex-persist directory)
import sys

sys.path.append("/app/cortex-persist")
try:
    from cortex.utils.canonical import canonical_json
except ImportError:
    # Fallback if canonical.py is not reachable in path
    def canonical_json(obj):
        return json.dumps(
            obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str
        )


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] C5-REAL | %(message)s")
logger = logging.getLogger("sdk_init")


def generate_ed25519_keys(output_dir: Path):
    """Generate and serialize an Ed25519 key pair for the SDK."""
    logger.info("Initializing Ed25519 Key Pair Generation")
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_dir / "sdk_private.pem", "wb") as f:
        f.write(private_bytes)

    with open(output_dir / "sdk_public.pem", "wb") as f:
        f.write(public_bytes)

    logger.info(f"Keys generated securely at {output_dir}")
    return private_key, public_key


def test_canonical_serialization():
    """Verify Canonical Serialization is working deterministically."""
    logger.info("Testing Canonical (JSON/CBOR) Serialization...")
    test_payload = {
        "tenant_id": "legion-10k",
        "action": "init",
        "nested": {"z": 1, "a": 2},
        "sequence": 1,
    }

    canonical_payload = canonical_json(test_payload)
    logger.info(f"Canonical Output: {canonical_payload}")

    # Ensuring determinism
    expected = r'{"action":"init","nested":{"a":2,"z":1},"sequence":1,"tenant_id":"legion-10k"}'
    assert canonical_payload == expected, "Serialization is NOT canonical!"
    logger.info("Canonical Serialization Verified.")


if __name__ == "__main__":
    logger.info("Starting SDK Init Sequence (C5-REAL)")

    # Use /app/data if running in Docker, else local ./data
    data_dir = Path("/app/data") if Path("/app").exists() else Path("./data")
    keys_dir = data_dir / "keys"

    generate_ed25519_keys(keys_dir)
    test_canonical_serialization()

    logger.info("SDK Initialized successfully. Handing over to CORTEX-Persist Engine.")
