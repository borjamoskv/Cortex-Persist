import sys
import time

# Add cortex to path
sys.path.append("/Users/borjafernandezangulo/cortex")
from cortex.cli.bicameral import bicameral


def simulate_cortex_pulse():
    print("🚀 Starting CORTEX Pulse Simulation...")

    print("Phase 1: Limbic Consolidation (Lore)")
    bicameral.log_limbic("Consolidating memories of previous workspace pivots.", source="LORE")
    time.sleep(2)

    print("Phase 2: Trust Engine (Merkle)")
    bicameral.log_trust("Generating Merkle root for transaction 0x...deadbeef", detail="LEDGER")
    time.sleep(2)

    print("Phase 3: Nemesis Warning")
    bicameral.log_limbic(
        "Allergy triggered: Unexpected 'any' type in core module.", source="NEMESIS"
    )
    time.sleep(2)

    print("Phase 4: Autonomic Safety Check")
    bicameral.log_autonomic("CPU temperature approaching tether limit: 85C", check="TETHER")
    print("✅ Simulation Complete.")


if __name__ == "__main__":
    simulate_cortex_pulse()
