# [C5-REAL] Exergy-Maximized
"""
cat_id: test-osc
cat_type: script
version: 1.0.0
reality_level: C5-REAL
owner: borjamoskv
exergy_tier: P2
"""

import asyncio

from cortex.extensions.bci.osc_bridge import AetherOscBridge


async def test_osc():
    # Setup bridge mapping TX and RX to the same ports for loopback testing
    bridge = AetherOscBridge(rx_port=9005, tx_port=9005)
    await bridge.start()

    print("[TEST] Emitting Ledger Mutation Datagram...")
    bridge.emit_ledger_mutation(tx_id="tx_c5_test", entropy_level=0.99, source="System")

    print("[TEST] Emitting Swarm Consensus Datagram...")
    bridge.emit_swarm_consensus(agent_id="legionnaire_1", vote="STRIKE", confidence=1.0)

    # Wait for UDP loopback to hit the local AsyncIOOSCUDPServer
    await asyncio.sleep(0.5)

    print("[TEST] Stopping Bridge...")
    await bridge.stop()


if __name__ == "__main__":
    # Ensure logs show up
    import logging

    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_osc())
