# [C5-REAL] Exergy-Maximized
# 1. Splinter ledger_core.py
ledger_path = "cortex/ledger/ledger_core.py"
with open(ledger_path) as f:
    ledger_content = f.read()

# Extract merkle components
# MerkleNode, MerkleTree, SemanticMerkleTree
merkle_start = ledger_content.find("class MerkleNode:")
merkle_end = ledger_content.find("class SovereignLedger:")

if merkle_start != -1 and merkle_end != -1:
    merkle_code = ledger_content[merkle_start:merkle_end]
    # Write to merkle.py
    with open("cortex/ledger/merkle.py", "w") as f:
        f.write('"""Merkle tree structures for CORTEX Ledger."""\n\n')
        f.write("import hashlib\nimport json\nfrom typing import Any\n\n")
        f.write(merkle_code)

    # Remove from ledger_core.py
    new_ledger = (
        ledger_content[:merkle_start]
        + "from .merkle import MerkleNode, MerkleTree, SemanticMerkleTree\n\n\n"
        + ledger_content[merkle_end:]
    )
    with open(ledger_path, "w") as f:
        f.write(new_ledger)
    print("Splintered ledger_core.py -> merkle.py")
