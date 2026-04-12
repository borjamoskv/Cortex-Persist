# Stargate V2 Security Audit Report (Final Synthesis)
**Operation: STARGATE-STRIKE (C5-REAL)**
**Warden:** borjamoskv // CORTEX-Ω

## Table of Contents
1. [H-01] OmnichainFungibleToken: Funds Lock via Syntax Error
2. [H-02] StargateFeeLibraryV02: Incentive Drain via Deficit Manipulation
3. [H-03] Pool/Router: Oracle Manipulation via Read-Only Reentrancy
4. [M-04] Bridge/Router: Blocking LayerZero Nonce via Gas Griefing DoS

---

## [H-01] OmnichainFungibleToken: Funds Lock via Syntax Error

### Severity: High
### Description
In `OmnichainFungibleToken.sol`, a critical syntax error in the address assignment logic causes tokens sent to `address(0x0)` (a common burning pattern) or during specific cross-chain scenarios to be locked in the contract or sent to their original destination instead of the intended dead address.

### Technical Detail
File: `OmnichainFungibleToken.sol`
```solidity
107: if (toAddress == address(0x0)) toAddress == address(0xdEaD);
```
The line uses the equality operator `==` instead of the assignment operator `=`. Consequently, `toAddress` remains `address(0x0)`, causing transfers to fail or lock funds in an unrecoverable state if the underlying ERC20 implementation does not revert on zero-address transfers.

### Impact
Permanent loss of user funds during cross-chain burn/mint operations where `address(0x0)` is specified.

---

## [H-02] StargateFeeLibraryV02: Incentive Drain via Deficit Manipulation

### Severity: High/Critical
### Description
The reward calculation logic in `StargateFeeLibraryV02.sol` lacks safety boundaries, allowing an attacker to drain 100% of the `eqFeePool` by manipulating the pool deficit to its minimum value (1 SD).

### Technical Detail
File: `StargateFeeLibraryV02.sol:64`
```solidity
uint256 eqRewards = rewardPoolSize.mul(_amountSD).div(poolDeficit);
```
If an attacker performs a small swap (e.g., 1 SD) when the `poolDeficit` is also 1 SD (achievable via a sequence of swaps), the `eqRewards` will equal the **entire** `rewardPoolSize`. 

### Impact
Total drainage of the protocol's incentive pool (`eqFeePool`), stripping the protocol of its ability to rebalance liquidity via rewards.

---

## [H-03] Pool/Router: Oracle Manipulation via Read-Only Reentrancy

### Severity: High
### Description
`Router.addLiquidity` and `Pool.instantRedeemLocal` violate the Check-Effects-Interactions (CEI) pattern when interacting with tokens that support hooks (e.g., ERC777). This allows for Read-Only Reentrancy where a 3rd party protocol reading Stargate state sees inconsistent data.

### Technical Detail
In `Router.addLiquidity`:
1. `_safeTransferFrom` pulls tokens from the user (External Call).
2. **HOOK TRIGGERED**: If the user is a contract, it can re-enter.
3. `pool.mint` updates `totalLiquidity` (State Update).

During the hook, `token.balanceOf(pool)` has increased, but `pool.totalLiquidity()` hasn't. An oracle reading `Price = balance / totalLiquidity` will see an inflated price, allowing for exploits in lending markets using Stargate LP tokens as collateral.

### Impact
Manipulation of price oracles and potential insolvency for integrated DeFi protocols.

---

## [M-04] Bridge/Router: Blocking LayerZero Nonce via Gas Griefing DoS

### Severity: Medium/High
### Description
The internal call to `sgReceive` in `Router.sol` uses an attacker-controlled gas limit (`_dstGasForCall`). This can be exploited to cause a revert in the `lzReceive` transaction's `catch` block due to Out-of-Gas, blocking the LayerZero channel.

### Technical Detail
File: `Router.sol:406-411`
A user can set `_dstGasForCall` to a value that consumes almost all the gas provided by the Relayer. If `sgReceive` fails and the remaining `gasleft()` is insufficient to execute the code in the `catch` block (which writes to storage), the entire transaction reverts.

### Impact
DoS of specific bridge paths. All subsequent messages through that path are blocked until manual intervention (`forceResumeReceive`).

---

## Conclusion
The identified vulnerabilities represent a significant risk to the protocol's solvency and uptime. Immediate remediation of the syntax error in `OmnichainFungibleToken` and implementation of gas caps/guards in `Router` is recommended.

**Verification Status:** Mechanical validation completed via C5-Engine PoCs.
