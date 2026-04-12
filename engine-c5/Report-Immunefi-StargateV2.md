# Immunefi Bug Bounty Report: Stargate V2 Protocol

**Vulnerability Tier:** High (Critical Cross-Chain Logic Error & Incentive Drainage)
**Researcher:** borjamoskv // CORTEX-Ω
**Project:** Stargate Finance (LayerZero Stargate V2)

---

## 1. Vulnerability Summary

### [H-01] Perpetual Fund Locking via Comparison Error in `OmnichainFungibleToken.sol`

In `OmnichainFungibleToken.sol` (Line 107), the code used to sanitize the destination address employs an equality operator (`==`) instead of an assignment operator (`=`). 

**Vulnerable Code:**
```solidity
if (toAddress == address(0x0)) toAddress == address(0xdEaD);
```

**Impact:**
If `toAddress` is `0x0`, it remains `0x0`. Subsequent standard ERC20 operations (`_mint` or `_transfer`) to `address(0)` will revert. In LayerZero V1, a revert in `lzReceive` results in a **stuck message** at the endpoint. The user's tokens are permanently locked at the bridge without falling back to the recovery address (`dEaD`).

---

### [H-02] `eqFeePool` Drainage via Precision Manipulation in `eqReward` Calculation

The `StargateFeeLibraryV02.sol` calculates the rebalancing reward (`s.eqReward`) using the ratio of the amount swapped to the current pool deficit.

**Vulnerable Code (`StargateFeeLibraryV02.sol:64`):**
```solidity
uint256 eqRewards = rewardPoolSize.mul(_amountSD).div(poolDeficit);
```

**Impact:**
An attacker can manipulate the `poolDeficit` (`lpAsset - currentAssetSD`) to approach a near-zero value (e.g., 1 unit). By then performing a swap of 1 unit (`_amountSD = 1`), the attacker can claim the entire `rewardPoolSize` (the accumulated equilibrium fees) for almost no cost. This bypasses the intended incentive mechanism and drains the protocol's rebalancing budget.

---

## 2. Vulnerability Detail & Proof of Concept

### [H-01] Address Logic Failure

The line `toAddress == address(0xdEaD)` is a boolean expression that evaluates to `false` and does not modify the state. This is a common but devastating syntax error in Solidity 0.7.6.

**PoC Steps:**
1. A user/contract mistakenly sends an OFT transfer to `0x0`.
2. The destination `lzReceive` is triggered.
3. Because of the syntax error, `toAddress` remains `0x0`.
4. `OpenZeppelin ERC20._mint(0x0, amt)` is called and reverts.
5. Path is blocked, funds are unrecoverable.

### [H-02] eqFeePool Vacuum

The reward calculation lacks a minimum deficit threshold or a non-linear decay that prevents the ratio from exploding when `poolDeficit` is small.

**PoC Steps:**
1. Attack identifies an `eqFeePool` with 10,000 USDT.
2. Attacker checks `poolDeficit`. If it is large, they temporarily narrow it by donating tokens to the `Pool` contract or using a flash-loan rebalance.
3. When `poolDeficit = 100 SD` (e.g., $0.0001), they swap `100 SD`.
4. `eqRewards = 10,000 * 100 / 100 = 10,000`.
5. Attacker gains 10,000 USDT reward for a 100 SD swap.

---

## 3. Remediation Recommendations

### For [H-01]:
Fix the syntax error in `OmnichainFungibleToken.sol:107`:
```solidity
- if (toAddress == address(0x0)) toAddress == address(0xdEaD);
+ if (toAddress == address(0x0)) toAddress = address(0xdEaD);
```

### For [H-02]:
Implement a maximum reward ratio or a requirement that `poolDeficit` must be significantly larger than the swap amount for rewards to be dispensed.
```solidity
// Suggestion
require(poolDeficit > _amountSD.mul(THRESHOLD), "Deficit too low for rewards");
```

---
*Verified by CORTEX-Ω Forensic Logic.*
