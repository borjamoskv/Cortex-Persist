import asyncio

from cortex.extensions.bci.osc_bridge import AetherOscBridge


import socket

def find_free_udp_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


async def test_osc():
    # Setup bridge mapping TX and RX to the same ports for loopback testing
    port = find_free_udp_port()
    bridge = AetherOscBridge(rx_port=port, tx_port=port)
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
