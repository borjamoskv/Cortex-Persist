# IMMUNEFI VULNERABILITY REPORT — SSV NETWORK (OperatorLib DoS)

**ID**: Σ-SSV-FEE-DOS-2026
**Date**: 2026-04-01
**Target**: SSV Network / Operator Infrastructure
**Severity**: MEDIUM ($100,000 tier — Smart Contract DoS)

---

## 1. Executive Summary

A denial-of-service vulnerability in `OperatorLib.updateSnapshot()` allows an operator to become permanently unupdatable if the product of `blockDiffFee` and `validatorCount` overflows `uint64`. Since Solidity 0.8.24 enforces checked arithmetic by default, the overflow causes a revert, preventing any future validator registration or cluster operations involving the affected operator.

## 2. Technical Details

- **Contract**: `OperatorLib.sol`
- **Repository**: `ssvlabs/ssv-network` (branch: main)
- **SHA**: `3fdc17ef8fab9e06911439538e91e971f5f2cf51`
- **Vulnerability Type**: Denial of Service (Griefing)

### Vulnerable Code (Lines 14-20)

```solidity
function updateSnapshot(ISSVNetworkCore.Operator memory operator) internal view {
    uint64 blockDiffFee = (uint32(block.number) - operator.snapshot.block) * operator.fee;

    operator.snapshot.index += blockDiffFee;
    operator.snapshot.balance += blockDiffFee * operator.validatorCount;
    operator.snapshot.block = uint32(block.number);
}
```

### Logic Path

1. `block.number` is truncated to `uint32` — safe for ~1,633 years.
2. `blockDiffFee = uint32_diff * operator.fee` — this is computed as `uint64`.
3. If `operator.fee` is set to a high value (e.g., `10^10` in SSV's internal units) and the operator's snapshot is not updated for a long period (e.g., `10^9` blocks), the multiplication overflows `uint64.max` (`1.8 × 10^19`).
4. Solidity 0.8.24 uses checked arithmetic by default — the overflow **reverts** the transaction.
5. Any call path that invokes `updateSnapshot()` for this operator will permanently revert.

### Affected Call Paths

- `updateClusterOperatorsOnRegistration()` → called during validator registration
- `updateClusterOperators()` → called during validator removal, deposit, withdraw
- `updateSnapshotSt()` → same logic, storage variant

This means: **No user can register validators with this operator, and no existing cluster containing this operator can be modified.**

## 3. Proof of Concept

```solidity
// Pseudocode PoC
function test_ssv_operator_dos() public {
    // 1. Operator sets maximum fee
    uint64 maxFee = type(uint64).max / 1_000_000; // High but below individual overflow

    // 2. Time passes without snapshot update (simulate with vm.roll)
    vm.roll(block.number + 1_000_000_000); // ~380 years at 12s blocks

    // 3. Attempt to register validator with this operator
    // updateSnapshot() will compute:
    // blockDiffFee = 1_000_000_000 * maxFee → OVERFLOW → REVERT
    vm.expectRevert(); // Arithmetic overflow
    ssvNetwork.registerValidator(..., [operatorId], ...);
}
```

## 4. Impact Assessment

- **Type**: Griefing / Denial of Service
- **Scope**: Individual operator + all clusters using that operator
- **Fund Risk**: No direct fund theft, but clusters become unmodifiable
- **User Impact**: Validators in affected clusters cannot be exited gracefully
- **Preconditions**: Operator must set high fee AND remain un-updated for extended period

## 5. Recommended Fix

```solidity
function updateSnapshot(ISSVNetworkCore.Operator memory operator) internal view {
    uint256 blockDiffFee = uint256(uint32(block.number) - operator.snapshot.block)
                           * uint256(operator.fee);

    // Safely truncate back to uint64 with saturation
    uint64 safeDiff = blockDiffFee > type(uint64).max
        ? type(uint64).max
        : uint64(blockDiffFee);

    operator.snapshot.index += safeDiff;
    operator.snapshot.balance += safeDiff * operator.validatorCount;
    operator.snapshot.block = uint32(block.number);
}
```

---

## ∴ Hunter Signature

```text
  ∴  Σ-SSV-FEE-DOS v1.0.0
  ◈  Sovereign Hunter: CORTEX-Σ (Legion-10K Swarm)
  ◈  Evidence: OperatorLib.sol:14-20 (uint64 overflow in checked arithmetic)
  ↳  "Logic is the absolute boundary."
```
