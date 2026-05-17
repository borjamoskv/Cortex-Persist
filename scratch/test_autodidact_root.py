"""Verification Script for AUTODIDACT L2+ (The Anvil Gate)."""

import logging
from pathlib import Path

from cortex.engine.pdr_guard import PDRGuard
from cortex.engine.tis_schema import CortexTIS, TISOperation

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_autodidact_l3")

# WETH mainnet address
WETH_ADDRESS = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"


def main():
    logger.info("Starting AUTODIDACT L2+ (Anvil Gate) Verification")

    # Create PDR Guard
    key_path = Path("/tmp/test_guard.key")
    if key_path.exists():
        key_path.unlink()
    guard = PDRGuard(key_path)

    # 1. VALID TRANSACTION (WETH.totalSupply())
    # This should succeed on mainnet fork because it's a valid view function.
    valid_tis = CortexTIS(
        chain_id=1,
        target_contract=WETH_ADDRESS,
        operations=[TISOperation(type="call", calldata="0x18160ddd", value="0")],
        taint_hash="0x" + "a" * 64,
    )
    logger.info("Simulating Valid TIS (totalSupply): %s", valid_tis.intent_id)
    pdr = guard.evaluate_and_sign(valid_tis)
    logger.info("Successfully passed Anvil Gate. Issued PDR: %s", pdr.decision_id)

    # 2. INVALID TRANSACTION (WETH.transfer(address(0), 1000 ETH))
    # This should revert on mainnet because we don't have the balance.
    invalid_tis = CortexTIS(
        chain_id=1,
        target_contract=WETH_ADDRESS,
        operations=[
            TISOperation(
                type="call",
                calldata="0xa9059cbb00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000de0b6b3a7640000",
                value="0",
            )
        ],
        taint_hash="0x" + "b" * 64,
    )
    logger.info("Simulating Invalid TIS (Revert Transfer): %s", invalid_tis.intent_id)
    try:
        guard.evaluate_and_sign(invalid_tis)
        raise AssertionError("Should have failed simulation")
    except ValueError as e:
        logger.info("Successfully blocked Invalid TIS at Anvil Gate: %s", e)

    logger.info("Anvil Gate Verification Complete. AUTODIDACT L3 conforms.")


if __name__ == "__main__":
    main()
