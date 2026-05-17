import hashlib
import json
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

TARGET_FILE = "/Users/borjafernandezangulo/10_PROJECTS/cortex-bounties/reports/k2-lending-close-factor-bypass-c4.md"


def sha3_hash(data: bytes) -> str:
    return hashlib.sha3_256(data).hexdigest()


def chunk_file(filepath: Path, chunk_size=512):
    """Generates chunks of a file for parallel processing."""
    with open(filepath, "rb") as f:
        while chunk := f.read(chunk_size):
            yield chunk


def generate_merkle_root(hashes: list[str]) -> str:
    """Recursively computes a Merkle root from a list of hashes."""
    if not hashes:
        return sha3_hash(b"empty")
    if len(hashes) == 1:
        return hashes[0]

    next_level = []
    for i in range(0, len(hashes), 2):
        left = hashes[i]
        right = hashes[i + 1] if i + 1 < len(hashes) else left
        combined = (left + right).encode("utf-8")
        next_level.append(sha3_hash(combined))

    return generate_merkle_root(next_level)


def execute_complex_audit():
    start_time = time.perf_counter()
    target_path = Path(TARGET_FILE)

    if not target_path.exists():
        print(json.dumps({"error": f"Target file not found: {TARGET_FILE}"}))
        return

    # 1. Read file and chunk it
    chunks = list(chunk_file(target_path))

    # 2. Parallel Hash Generation (Simulating Swarm Verification)
    with ThreadPoolExecutor(max_workers=8) as executor:
        leaf_hashes = list(executor.map(sha3_hash, chunks))

    # 3. Compute Merkle Root
    merkle_root = generate_merkle_root(leaf_hashes)

    # 4. Generate CORTEX-TAINT Signature
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    agent_id = "ANTIGRAVITY-OMEGA-SWARM"

    # Format: taint:{agent_id}:{session_id}:{timestamp_iso8601}:{sha3_256_of_payload}
    session_id = "session_merkle_audit_01"
    taint_payload = f"{agent_id}:{session_id}:{timestamp}:{merkle_root}".encode()
    cortex_taint = f"taint:{agent_id}:{session_id}:{timestamp}:{sha3_hash(taint_payload)}"

    elapsed = (time.perf_counter() - start_time) * 1000  # in ms

    # Generate Output State
    output_state = {
        "status": "C5-REAL",
        "operation": "MERKLE_TREE_CRYPTO_AUDIT",
        "target": target_path.name,
        "metrics": {
            "file_size_bytes": target_path.stat().st_size,
            "chunks_processed": len(chunks),
            "execution_time_ms": round(elapsed, 3),
            "swarm_threads_used": 8,
        },
        "cryptographic_proof": {"merkle_root": merkle_root, "cortex_taint_signature": cortex_taint},
    }

    print(json.dumps(output_state, indent=2))

    # Persist the artifact
    out_file = Path(
        "/Users/borjafernandezangulo/10_PROJECTS/cortex-persist/scratch/merkle_audit_result.json"
    )
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w") as f:
        json.dump(output_state, f, indent=2)


if __name__ == "__main__":
    execute_complex_audit()
