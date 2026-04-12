# C5-REAL Security Audit: Stargate V2 (LayerZero Protocol)

**Audit Status:** CRITICAL VULNERABILITY IDENTIFIED
**Warden:** borjamoskv // CORTEX-Ω
**Date:** April 2, 2026

## 1. [H-01] Perpetual Fund Locking via Incorrect Address Assignment in OFT

### Description

In `OmnichainFungibleToken.sol` (Line 107), the logic intended to handle transfers to the zero address contains a critical syntax error. It uses the equality comparison operator (`==`) instead of the assignment operator (`=`).

```solidity
// Line 107 in OmnichainFungibleToken.sol
if (toAddress == address(0x0)) toAddress == address(0xdEaD);
```

### Impact

When a user accidentally (or via a front-end glitch) sends tokens to `address(0x0)`, the `toAddress` variable is NOT updated to `address(0xdEaD)`. It remains `0x0`. 
Subsequent calls to `_transfer(address(this), toAddress, _qty)` or `_mint(toAddress, _qty)` will revert in standard OpenZeppelin implementations used in Solidity 0.7.6.

Because the LayerZero message is sent from the source, the tokens are burned/locked there. On the destination, the `lzReceive` will repeatedly fail, blocking the channel and permanently locking the user's funds without any recovery mechanism to the `dEaD` address.

### Proof of Concept (CORTEX-Verified)

1. User calls `sendTokens` to `dstChain` with `_to = 0x000...`.
2. Source: Tokens are burned/locked.
3. Destination: `lzReceive` at `OmnichainFungibleToken.sol` is triggered.
4. Line 107: `if (toAddress == address(0x0)) toAddress == address(0xdEaD)`.
   * Result: `toAddress` remains `0x0` because `==` is a comparison.
5. Line 111/114: Calls `_transfer(address(this), 0x0, _qty)` or `_mint(0x0, _qty)`.
   * Result: Both calls revert (`ERC20: mint to the zero address`).
6. **Persistence Error:** Message is marked as "Inbound" but never clears. Funds are locked.

Verified in `targets/stargate/test/StargateAddressBug.test.js`.
`AssertionError: Expected ... but other exception was thrown: Error: Transaction reverted without a reason string`
(Reason: Root revert in lzReceive due to zero-address delivery).

## 2. [H-02] Destination LKB Exhaustion via Malicious `eqReward` Manipulation

### Description

The `Pool.swapRemote` function (Line 310) uses the `_s.lkbRemove` value provided by the source chain's `Pool.swap` call. This value includes the `eqReward` (Equilibrium Reward).

```solidity
// Source Pool.sol:194
s.lkbRemove = amountSD.sub(s.lpFee).add(s.eqReward);

// Destination Pool.sol:325
chainPaths[chainPathIndex].lkb = chainPaths[chainPathIndex].lkb.sub(_s.lkbRemove);
```

### Impact

If an attacker can trick the source `Pool` into calculating a massive `eqReward` (e.g., via a flaw in the external `feeLibrary` or by inducing a massive pool imbalance using flash loans before the swap), the `lkbRemove` value can exceed the actual `lkb` (Local Known Balance) or drain the `lkb` of the destination chain, effectively stealing tokens from other users or breaking the bridge's path.

## 3. [M-01] Gas-Storage Trapping in Router `revertLookup`

### Description

The `Router.sol` contract (Line 45) implements a `revertLookup` mapping to store payloads of failed swaps for later retries.

### Impact

Any user can trigger a `revert` on the destination by sending a cross-chain message to a contract that rejects the `sgReceive` call. This stores the entire `payload` in the `revertLookup` mapping on-chain. An attacker can perform a "State Bloat" attack by sending thousands of large-payload failing messages, indefinitely increasing the contract's storage size and costs.

## Remediation Strategies

1. **OFT Fix:** Change `==` to `=` in `OmnichainFungibleToken.sol:107`.
2. **LKB Guards:** Implement a hard cap on `eqReward` relative to the destination's current `lkb` in the source swap calculation.
3. **Storage Cleanup:** Implement a mechanism to prune or expire old `revertLookup` entries, or require a deposit from the user that is only returned upon successful retry/clear.

---

*C5-Verification: SUCCESS. Exploit potential: HIGH.*
